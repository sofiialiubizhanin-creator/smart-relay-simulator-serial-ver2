# F1: Relay control and status: plan

Status: draft for review | Inputs: `requirements.md`, `../tech-stack.md`, skill `e2e-test-conventions`

## G0. Project skeleton
- `pyproject.toml`: src layout, packages `relay_sim` and `relay_host`, dependency `pyserial`,
  dev extras `pytest` and `pytest-html`, console scripts `relay-sim` and `relay-host`, pytest config
  (`testpaths`, marker `ac`, `--strict-markers`).
- `.gitattributes` (LF line endings), `README.md`, `CHANGELOG.md` skeletons.

## G1. Simulator core (`src/relay_sim`), pure logic with no I/O
- `clock.py`: a `Clock` protocol, `RealClock` (monotonic), `ManualClock` (starts at 0, `advance(s)`, rejects negative values).
- `device.py`: `RelayDevice(clock)` holding `state`, `hw_fault` and `silent`, and
  `handle_line(raw: bytes) -> bytes | None`. It applies the error priority from requirements section 3 in this order:
  silence -> empty -> too long -> exact match -> HW_FAULT -> execute. It also has the control operations
  (`reset`, `set_state`, ...).

## G2. Simulator servers and launcher
- `server.py`: a threaded TCP "serial" server that reads bytes up to `\n` and writes one reply line per
  command (none when silent). Connections are handled one at a time, and the device state is shared.
  Lines longer than 32 bytes are read to the `\n` and then rejected (no buffer overflow, no
  disconnect). There is also a control server running the control API (requirements section 2.3).
  A lock serializes all device access.
- `__main__.py`: `python -m relay_sim [--host] [--port 5000] [--control-port 5001] [--clock real|manual]`.
  Port `0` picks a free port. Once both servers are listening, it prints `READY serial=<p> control=<p>`.

## G3. Host CLI (`src/relay_host`)
- `cli.py` / `__main__.py`: argparse with `--host`, `--port`, `--timeout` and a positional `COMMAND`
  (sent as is, `""` allowed). Opens `serial.serial_for_url("socket://host:port", timeout=...)`,
  writes `COMMAND\n` and reads one line until the deadline.
- Exit codes 0/1/2/3 and stderr messages as in requirements section 4. If `RELAY_HOST_LOG` is set,
  it appends timestamped `HOST TX/RX/TIMEOUT/ERROR` lines to that file.

## G4. E2E framework (`tests/e2e`), built per skill `e2e-test-conventions`
- `conftest.py`: the fixtures `simulator`, `control` (autouse, RESET), `host`, `dead_port` and
  `exchange_log`. A collection hook fails any test that has no valid `ac` marker. A report hook attaches
  the exchange log to `reports/e2e-report.html`.
- `helpers.py`: `ControlClient`, `HostResult`, `wait_until`.

## G5. E2E tests (`tests/e2e/test_f1_relay_control.py`)
- Written from `validation.md` (one row per AC), not from the G1-G3 code.

## G6. One-command runner
- `run.py` (standard library only): creates `.venv` if it's missing, runs `pip install -e .[dev]`,
  then runs pytest 5 times in a row. Each run writes `reports/runs/e2e-run-<n>.html`, the last one is
  copied to `reports/e2e-report.html`, and the results are summarized in `reports/e2e-runs.md`.
  The exit code is non-zero if any run fails. `python run.py demo` starts the simulator with the real clock.
- README: start with a single command, plus manual usage of `relay-sim` and `relay-host`.

## G7. Validation
- Run `python run.py`. Fill in the AC <> test table and the run results in `validation.md`, check
  with `ac_coverage.py`, and write the CHANGELOG entry.
- Run the skill evals on v1, refine the skill to v2, run them again, and record the results in `reports/skill-evals.md`.

## Risks
- Windows argv passing of `""`, `\t` and `\r` to the subprocess: check this in G5. If argv can't carry
  them, `relay-host` gets a documented `--raw-hex` option (this needs a requirements change first).
- Port reuse in `dead_port` (AC-F1-12): we use a freshly closed ephemeral port; the race window is negligible on localhost.
