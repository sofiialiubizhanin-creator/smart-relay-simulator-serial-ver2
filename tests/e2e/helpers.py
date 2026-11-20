"""Helpers for E2E tests: exchange log, control API client, host result, condition waits (no sleep)."""
import socket
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class ExchangeLog:
    """Per-test timestamped log. The host process appends to the same file via RELAY_HOST_LOG."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.touch()

    def write(self, source: str, direction: str, payload: object) -> None:
        ts = datetime.now().isoformat(timespec="milliseconds")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(f"{ts} {source} {direction} {payload!r}\n")

    def size(self) -> int:
        return self.path.stat().st_size

    def read(self, start: int = 0) -> str:
        with open(self.path, "rb") as f:
            f.seek(start)
            return f.read().decode("utf-8")


@dataclass(frozen=True)
class SimInfo:
    serial_port: int
    control_port: int


@dataclass(frozen=True)
class HostResult:
    stdout: str                    # reply line without the trailing newline
    stderr: str
    exit_code: int
    duration: float               # seconds, host process start to exit (wall clock)
    sent: bool                    # the host logged a TX line (something was sent to the device)
    send_to_end: float | None     # seconds from the host's TX to its RX/TIMEOUT/ERROR (host log)


def host_log_timing(lines: str) -> tuple[bool, float | None]:
    """Parse `<ISO ts> HOST <DIR> ...` lines written by one host call: (sent, TX -> end seconds)."""
    tx = end = None
    for line in lines.splitlines():
        parts = line.split(" ", 3)
        if len(parts) < 3 or parts[1] != "HOST":
            continue
        ts = datetime.fromisoformat(parts[0])
        if parts[2] == "TX":
            tx = ts
        elif parts[2] in ("RX", "TIMEOUT", "ERROR") and tx is not None:
            end = ts
    return tx is not None, (end - tx).total_seconds() if tx and end else None


class ControlClient:
    """Client for the simulator control API (requirements section 2.3)."""

    def __init__(self, port: int, log: ExchangeLog, timeout: float = 5.0) -> None:
        self._log = log
        self._sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        self._rfile = self._sock.makefile("rb")

    def _cmd(self, line: str) -> str:
        self._log.write("CTRL", ">", line)
        self._sock.sendall(line.encode("ascii") + b"\n")
        reply = self._rfile.readline().decode("ascii").rstrip("\n")
        self._log.write("CTRL", "<", reply)
        return reply

    def _expect_ok(self, line: str) -> None:
        reply = self._cmd(line)
        assert reply == "OK", f"control API {line!r} replied {reply!r}"

    def reset(self) -> None:
        self._expect_ok("RESET")

    def set_state(self, state: str) -> None:
        self._expect_ok(f"SET_STATE {state}")

    def get_state(self) -> str:
        reply = self._cmd("GET_STATE")
        assert reply in ("STATE ON", "STATE OFF"), f"GET_STATE replied {reply!r}"
        return reply.split()[1]

    def fault(self, kind: str) -> None:
        self._expect_ok(f"FAULT {kind}")

    def silence(self, on: bool) -> None:
        self._expect_ok(f"SILENCE {'ON' if on else 'OFF'}")

    def advance(self, seconds: float) -> None:
        self._expect_ok(f"ADVANCE {seconds}")

    def close(self) -> None:
        self._rfile.close()
        self._sock.close()


def wait_until(predicate, timeout: float, message: str, interval: float = 0.01):
    """Return predicate()'s value as soon as it is truthy; fail with `message` at the deadline.

    Waits on an Event with a deadline instead of fixed sleeps: it never waits longer than needed.
    """
    deadline = time.monotonic() + timeout
    tick = threading.Event()
    while True:
        value = predicate()
        if value:
            return value
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f"timed out after {timeout}s: {message}")
        tick.wait(min(interval, remaining))
