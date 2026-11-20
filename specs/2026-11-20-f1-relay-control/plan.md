# F1: Relay control and status: plan

Status: approved 2026-11-20 (updated after the G0-G3 review) | Inputs: `requirements.md`, `../tech-stack.md`, skill `e2e-test-conventions`

## G0. Project skeleton
- `pyproject.toml`: src layout, packages `relay_sim` and `relay_host`, dependency `pyserial>=3.5,<4`,
  dev extras `pytest` and `pytest-html`, console scripts `relay-sim` and `relay-host`, pytest config
  (`testpaths`, marker `ac`, `--strict-markers`).
- `.gitattributes` (LF line endings), `README.md`, `CHANGELOG.md` skeletons.

## G1. Simulator core (`src/relay_sim`), pure logic with no I/O
- `clock.py`: a `Clock` protocol, `RealClock` (monotonic), `ManualClock` (starts at 0, `advance(s)`,
  rejects negative and non-finite values).
- `device.py`: `RelayDevice(clock)` holding `state`, `hw_fault` and `silent`, and
  `handle_line(line: bytes, overflow: bool = False) -> bytes | None` (`overflow` = the line was longer than
  32 bytes and its content was dropped). It applies the error priority from requirements section 3 in this order:
  silence -> empty -> too long -> exact match -> HW_FAULT -> execute. Control operations: `reset`,
  `set_state`, `set_fault`, `set_silent`.

## G2. Simulator servers and launcher
- `server.py`: a threaded TCP "serial" server (one thread per connection) that reads bytes up to `\n` and
  writes one reply line per command (none when silent). A lock serializes all device access, so the
  shared state stays consistent; concurrent clients are not modelled beyond that (out of scope).
  Lines longer than 32 bytes are read to the `\n` and then rejected (bounded buffer, no disconnect).
  A control server runs the control API (requirements section 2.3); client disconnects never print tracebacks.
  For `localhost` both 127.0.0.1 and ::1 listen on the same port (on Windows a refused ::1 connect costs ~2 s).
- Exchange log: timestamped lines to stderr, or to `--log FILE`.
- `__main__.py`: `relay-sim` / `python -m relay_sim` with the options of requirements section 2.4;
  prints `READY serial=<p> control=<p>`; a port that cannot be opened gives one `ERROR:` line and exit 1.

## G3. Host CLI (`src/relay_host`)
- `cli.py` / `__main__.py`: argparse with `--host`, `--port` (1-65535), `--timeout` (> 0) and a positional
  `COMMAND` (sent as is, `""` allowed). Uses pyserial's `socket://` handler
  (`serial.urlhandler.protocol_socket.Serial`, the class `serial_for_url` returns for `socket://`) through
  a subclass that only drops pyserial's hard-coded 0.3 s sleep in `close()`. IPv6 hosts are bracketed in the URL.
- Writes `COMMAND\n` and reads one line until the deadline. Exit codes 0/1/2/3 and stderr messages as in
  requirements section 4. If `RELAY_HOST_LOG` is set, it appends timestamped `HOST TX/RX/TIMEOUT/ERROR`
  lines to that file; logging errors are ignored.

## G4. E2E framework (`tests/e2e`), built per skill `e2e-test-conventions`
- `conftest.py`: the fixtures `simulator` (simulator log to `reports/runs/` via `--log`), `control`
  (autouse, RESET), `host`, `fresh_simulator` (a just-started simulator for "after startup" checks),
  `dead_port` and `exchange_log`. A collection hook fails any test that has no valid `ac` marker or whose
  name does not match it. A `--reverse` option runs the tests in reverse order. A report hook attaches
  the exchange log and an AC column to `reports/e2e-report.html`.
- `helpers.py`: `ControlClient`, `HostResult` (incl. `sent` and `send_to_end`: seconds from the host's
  `TX` to its `RX`/`TIMEOUT`, read from the host log), `wait_until`.

## G5. E2E tests (`tests/e2e/test_f1_relay_control.py`)
- Written from `requirements.md` section 5 and `validation.md` (one row per AC), not from the G1-G3 code.

## G6. One-command runner
- `run.py` (standard library only): creates `.venv` if it's missing, runs `pip install -e .[dev]`,
  then runs pytest 5 times in a row. Each run writes `reports/runs/e2e-run-<n>.html`, the last one is
  copied to `reports/e2e-report.html`, and the results are summarized in `reports/e2e-runs.md`.
  The exit code is non-zero if any run fails. `python run.py demo` starts the simulator with the real clock.
- README: start with a single command, plus manual usage of `relay-sim` and `relay-host`.

## G7. Validation
- Run `python run.py`. Fill in the AC <> test table and the run results in `validation.md`, check
  with `.claude/skills/e2e-test-conventions/scripts/ac_coverage.py`, and write the CHANGELOG entry.
- Skill evals: run on v1 right after G4 (before G5), refine the skill to v2, run again, and record the
  results in `reports/skill-evals.md`. G5 is then written with v2.

## Risks
- Windows argv passing of `""`, `\t` and `\r`: `subprocess` passes them unchanged (checked); Windows
  PowerShell 5.1 drops `""` (accepted, documented in requirements section 4).
- Port reuse in `dead_port` (AC-F1-12): we use a freshly closed ephemeral port; the race window is negligible on localhost.

---

## CR-01: Toggle rate limit (Phase 2)
Status: approved 2026-11-20; G8-G11 done 2026-11-20 (see validation.md "CR-01") | Inputs: `requirements.md` section 8 (CR-01), skill `e2e-test-conventions`.
G0-G7 above stay as they are; CR-01 adds the groups below.

### G8. Implementation (`src/relay_sim/device.py`)
- `RelayDevice` keeps `last_toggle_ms` (`None` at startup and after `reset()`); time is
  `round(clock.now() * 1000)` in integer ms, so `1.999 + 0.001` cannot fall below 2000 by float rounding.
- In `handle_line`, after the existing rules 1-5: an `ON`/`OFF` that would change the state while
  `last_toggle_ms` is set and `now_ms - last_toggle_ms < 2000` -> `BUSY` (rule 6). An accepted toggle sets
  `last_toggle_ms = now_ms`. No-op `ON`/`OFF`, `STATUS` and rejected commands do not touch it.
- `set_state` (control API) does not touch `last_toggle_ms`; `reset` clears it. Same logic for real and manual clocks.
- Host: no change (`BUSY` already gives exit code 1).

### G9. Regression run (before any test is changed)
- Run the **unchanged** F1 suite (`tests/e2e/test_f1_relay_control.py` as of commit `4293653`) against G8:
  `python run.py --runs 1`.
- Record in `reports/regression-cr01.md`: every failing test, its AC, expected vs. actual replies, the cause
  (which toggle fell inside the window), and the action. Passing tests are listed as unaffected.
- If a failing test belongs to an AC other than AC-F1-14, add that AC to requirements section 8
  "Supersedes" first and **stop for user review** before changing its test.

### G10. Tests (`tests/e2e/test_f1_relay_control.py`, per skill)
- Update the tests of superseded ACs to section 8. The quick sequence of AC-F1-14 keeps no clock
  advance; other affected tests get an explicit `control.advance(2.0)` between toggles, where the AC is not about timing.
- Add tests for AC-F1-17..22 with `control.advance()` only (boundary pair 1.999 / 2.000 s, both directions, multi-step advance).
- Fill the Test(s) cells of the CR-01 rows in `validation.md`.

### G11. Validation and release
- `python run.py` (5 runs) green; coverage script: every AC (incl. 17-22) covered; `--reverse` green.
- Fill the CR-01 Result cells and Run results in `validation.md`; CHANGELOG `0.2.0`; README protocol table
  (`BUSY`); roadmap phase 2 done.
