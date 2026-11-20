"""E2E fixtures (conventions: skill .claude/skills/e2e-test-conventions; design: plan.md G4)."""
import os
import queue
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from helpers import ControlClient, ExchangeLog, HostResult, SimInfo, host_log_timing

ROOT = Path(__file__).resolve().parents[2]
SIM_LOG_DIR = ROOT / "reports" / "runs"
ENV = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [str(ROOT / "src"), os.environ.get("PYTHONPATH")]))}
AC_ID = re.compile(r"^AC-([A-Z0-9]+)-(\d+)$")
LOG_KEY = pytest.StashKey[ExchangeLog]()
E2E_DIR = Path(__file__).resolve().parent


# ---------- collection: AC markers are mandatory; optional reverse order ----------
def pytest_addoption(parser):
    parser.addoption("--reverse", action="store_true", help="run E2E tests in reverse order (independence check)")


def pytest_collection_modifyitems(config, items):
    errors = []
    for item in items:
        if E2E_DIR not in Path(item.path).parents:
            continue
        marker = item.get_closest_marker("ac")
        ids = marker.args if marker else ()
        if not ids or not all(isinstance(i, str) and AC_ID.match(i) for i in ids):
            errors.append(f"{item.nodeid}: missing or invalid @pytest.mark.ac('AC-<FEATURE>-<NN>')")
            continue
        feature, num = AC_ID.match(ids[0]).groups()
        prefix = f"test_ac_{feature.lower()}_{num}_"
        if not item.originalname.startswith(prefix):
            errors.append(f"{item.nodeid}: name must start with {prefix} to match {ids[0]}")
    if errors:
        raise pytest.UsageError("AC convention violations:\n  " + "\n  ".join(errors))
    if config.getoption("--reverse"):
        items.reverse()


# ---------- simulator and control API ----------
def _start_simulator(log_name: str):
    """Start `python -m relay_sim` on free ports with the manual clock; wait (deadline) for READY."""
    SIM_LOG_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [sys.executable, "-m", "relay_sim", "--port", "0", "--control-port", "0", "--clock", "manual",
         "--log", str(SIM_LOG_DIR / log_name)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=ENV, cwd=ROOT)
    lines: queue.Queue[str] = queue.Queue()
    threading.Thread(target=lambda: lines.put(proc.stdout.readline()), daemon=True).start()
    try:
        ready = lines.get(timeout=15)
    except queue.Empty:
        ready = ""
    m = re.match(r"READY serial=(\d+) control=(\d+)", ready)
    if not m:
        proc.kill()
        pytest.fail(f"simulator did not report READY (got {ready!r}); see {SIM_LOG_DIR / log_name}")
    return proc, SimInfo(int(m.group(1)), int(m.group(2)))


def _stop_simulator(proc) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def simulator():
    proc, info = _start_simulator("simulator.log")
    yield info
    _stop_simulator(proc)


@pytest.fixture
def exchange_log(request, tmp_path) -> ExchangeLog:
    log = ExchangeLog(tmp_path / "exchange.log")
    request.node.stash[LOG_KEY] = log
    return log


@pytest.fixture(autouse=True)
def control(simulator, exchange_log):
    client = ControlClient(simulator.control_port, exchange_log)
    client.reset()
    yield client
    client.close()


@pytest.fixture
def fresh_simulator(exchange_log):
    """A separate, just-started simulator (for 'after startup' checks). Yields (SimInfo, ControlClient).

    No RESET is sent to it, so its state is exactly the startup state.
    """
    proc, info = _start_simulator("simulator-fresh.log")
    client = ControlClient(info.control_port, exchange_log)
    yield info, client
    client.close()
    _stop_simulator(proc)


# ---------- host CLI ----------
@pytest.fixture
def host(simulator, exchange_log):
    """host(command, *, timeout=1.0, port=None) -> HostResult. command=None omits COMMAND (usage error)."""
    env = {**ENV, "RELAY_HOST_LOG": str(exchange_log.path)}

    def run(command: str | None, *, timeout: float = 1.0, port: int | None = None) -> HostResult:
        target = port if port is not None else simulator.serial_port
        args = [sys.executable, "-m", "relay_host", "--port", str(target), "--timeout", str(timeout)]
        if command is not None:
            args += ["--", command]
        exchange_log.write("TEST", ">", f"relay-host --port {target} --timeout {timeout} "
                                        f"{'<no command>' if command is None else repr(command)}")
        start_offset = exchange_log.size()
        started = time.monotonic()
        proc = subprocess.run(args, capture_output=True, text=True, env=env, cwd=ROOT, timeout=timeout + 15)
        duration = time.monotonic() - started
        sent, send_to_end = host_log_timing(exchange_log.read(start_offset))
        result = HostResult(proc.stdout.removesuffix("\n"), proc.stderr.strip(), proc.returncode,
                            duration, sent, send_to_end)
        exchange_log.write("TEST", "<", f"exit={result.exit_code} stdout={result.stdout!r} "
                                        f"stderr={result.stderr!r} duration={duration:.3f}s "
                                        f"send_to_end={send_to_end}")
        return result

    return run


@pytest.fixture
def dead_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------- report: exchange log + AC column in reports/e2e-report.html ----------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    marker = item.get_closest_marker("ac")
    report.ac = ", ".join(marker.args) if marker else ""
    log = item.stash.get(LOG_KEY, None)
    if log is not None and (report.when == "call" or (report.when == "setup" and report.failed)):
        report.sections.append(("Exchange log (host <-> simulator)", log.read()))


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_header(cells):
    cells.insert(1, '<th class="sortable" data-column-type="ac">AC</th>')


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_row(report, cells):
    cells.insert(1, f'<td class="col-ac">{getattr(report, "ac", "")}</td>')
