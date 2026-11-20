# Tech stack

**Language/libs:** Python 3.11+ (developed on 3.14), pyserial (host side, its `socket://host:port` handler),
simulator built on the standard library only. **Tests:** pytest, pytest-html (report).

## Architecture
```
relay-host CLI --pyserial socket://--> [serial port] Simulator [control port] <--TCP-- test fixtures
```
- **Simulator** (`src/relay_sim`): relay state machine, swappable clock (real or manual), fault and silence flags.
- **Host** (`src/relay_host`): one-shot CLI that sends one command line exactly as given, prints the reply and returns an exit code.
- **Transport:** TCP on localhost, so it works the same on any OS. **Control API:** separate TCP port, for tests only.

## Testing conventions (details: skill `.claude/skills/e2e-test-conventions`)
- E2E tests drive the product only through the `relay-host` CLI; the simulator is set up and inspected only through the control API.
- No `time.sleep`: time-dependent behavior uses the simulator's manual clock (`ADVANCE`); every wait is bounded by a deadline (socket timeout, queue or event wait).
- Tests are independent: each one starts from a reset simulator and passes alone, in normal order and in reverse order.
- Names: `test_ac_<feature>_<nn>_<behavior>`, plus the marker `@pytest.mark.ac("AC-F1-01")`.
- The host-to-simulator exchange log, with timestamps, is attached to every test in `reports/e2e-report.html`.
- **One command:** `python run.py` creates `.venv`, installs the dependencies, runs the E2E suite 5 times in a row and writes the reports.
