# F1: Relay control and status: validation

Status: **pre-implementation** (what and how we verify). The "Test(s)" and "Result" columns are filled in during validation.
All checks are E2E: `host` = `relay-host` CLI, `control` = the simulator control API; "state X" is read
with `GET_STATE`. Every test starts after `RESET` (state `OFF`, no fault or silence, clock 0).
**Pass criterion for F1:** every row passes in one `python run.py` (= 5 consecutive suite runs).

| AC | What we verify | How (setup -> action -> expected) | Test(s) | Result |
|---|---|---|---|---|
| AC-F1-01 | ON from OFF | set OFF -> `ON` -> `OK`, exit 0, state ON | | |
| AC-F1-02 | OFF from ON | set ON -> `OFF` -> `OK`, exit 0, state OFF | | |
| AC-F1-03 | STATUS reflects state, default OFF | (a) just-started simulator, no RESET -> `STATUS OFF`; (b) set ON, RESET -> `STATUS OFF`; (c) set OFF / ON -> `STATUS OFF` / `STATUS ON`; state unchanged, exit 0 | | |
| AC-F1-04 | Repeated same command is a no-op | set ON -> `ON` -> `OK`/0, state ON; set OFF -> `OFF` -> `OK`/0, state OFF | | |
| AC-F1-05 | Unknown command | each of `TOGGLE`, `RESET`, `X`, from both states -> `ERR UNKNOWN_CMD`/1, state unchanged | | |
| AC-F1-06 | Non-uppercase rejected | each of `on`, `off`, `Off`, `oN`, `status`, from both states -> `ERR UNKNOWN_CMD`/1, state unchanged | | |
| AC-F1-07 | Empty line | from both states, host `""` -> `ERR EMPTY`/1, state unchanged | | |
| AC-F1-08 | Whitespace or extra character | each of `" ON"`, `"ON "`, `"O N"`, `"ON\t"`, `"ON\r"`, `"   "`, from both states -> `ERR UNKNOWN_CMD`/1, state unchanged | | |
| AC-F1-09 | Length limit and priority | 32 x `A` -> `ERR UNKNOWN_CMD`; 33 x `A` -> `ERR TOO_LONG`; 31 x `A` + `\r` (32 B) -> `ERR UNKNOWN_CMD`; 32 x `A` + `\r` (33 B) -> `ERR TOO_LONG`; 33 x `o` and `ON` + 31 spaces -> `ERR TOO_LONG`; all exit 1, from both states, state unchanged | | |
| AC-F1-10 | HW fault, priority, recovery | `FAULT HW_FAULT`, from both states: `ON` and `OFF` (incl. the current state) -> `ERR HW_FAULT`/1, state unchanged; `STATUS` -> correct/0; `on` -> `ERR UNKNOWN_CMD`, `""` -> `ERR EMPTY`, 33 B -> `ERR TOO_LONG`; recovery: from OFF and from ON, `FAULT NONE` -> the opposite command -> `OK`, state changed | | |
| AC-F1-11 | Silent device | state OFF, `SILENCE ON` -> host `ON` with `--timeout 0.5` -> exit 3, stderr `ERROR: no response from device within 0.5s`, host log TX -> TIMEOUT <= 1.0 s, state still OFF; `SILENCE OFF` -> `STATUS` -> `STATUS OFF`/0 | | |
| AC-F1-12 | Simulator unreachable | host on `dead_port` -> exit 2, stderr starts with `ERROR: cannot connect`, finishes in < 6 s (pyserial's connect limit is 5 s; Windows retries a refused loopback connect for ~2 s per address) | | |
| AC-F1-13 | State persists across connections | host `ON` (process 1) -> host `STATUS` (process 2) -> `STATUS ON`; host `OFF` -> host `STATUS` -> `STATUS OFF` | | |
| AC-F1-14 | Quick sequence, no clock advance | four separate host calls `ON`, `OFF`, `ON`, `STATUS` with no `ADVANCE` -> `OK`, `OK`, `OK`, `STATUS ON`; final state ON. Expected to be affected by CR-01 | | |
| AC-F1-15 | Usage error sends nothing | host with no COMMAND, with `--port 70000`, with `--timeout 0` -> exit 2, stderr = usage line + one `ERROR:` line, host log has no `TX`, state unchanged | | |

## Non-functional checks
| Check | How | Result |
|---|---|---|
| Exchange log with timestamps in the report | Inspect `reports/e2e-report.html`: every test has a log with `HOST TX/RX` and `CTRL` lines and ISO timestamps (ms) | |
| No sleep in tests | `grep -rnE "time\.sleep|asyncio\.sleep" tests/` finds nothing | |
| Test independence | Suite passes in normal order and with `pytest --reverse`; any single test passes when run alone | |
| 5 green runs in a row | `python run.py` -> `reports/e2e-runs.md` shows 5/5 passed | |
| AC coverage | `.claude/skills/e2e-test-conventions/scripts/ac_coverage.py` exits 0, no AC uncovered | |
| AC convention enforced | A test with no `ac` marker, or a name not matching it, stops collection | |

## Run results
_To be filled in during validation._
