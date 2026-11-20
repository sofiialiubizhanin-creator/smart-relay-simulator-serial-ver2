# F1: Relay control and status: validation

Status: **pre-implementation** (what and how we verify). The "Test(s)" and "Result" columns are filled in during validation.
All checks are E2E: `host` = `relay-host` CLI, `control` = the simulator control API. Every test starts
after `RESET` (state `OFF`, no fault or silence, clock 0). **Pass criterion for F1:** every row passes in
5 runs in a row of `python run.py`.

| AC | What we verify | How (setup -> action -> expected) | Test(s) | Result |
|---|---|---|---|---|
| AC-F1-01 | ON from OFF | set OFF -> `ON` -> `OK`, exit 0, state ON | | |
| AC-F1-02 | OFF from ON | set ON -> `OFF` -> `OK`, exit 0, state OFF | | |
| AC-F1-03 | STATUS reflects state, default OFF | (a) after reset -> `STATUS` -> `STATUS OFF`; (b) set ON -> `STATUS ON`; state unchanged, exit 0 | | |
| AC-F1-04 | Repeated same command is a no-op | set ON -> `ON` -> `OK`/0, state ON; set OFF -> `OFF` -> `OK`/0, state OFF | | |
| AC-F1-05 | Unknown command | each of `TOGGLE`, `RESET`, `X`, from both states -> `ERR UNKNOWN_CMD`/1, state unchanged | | |
| AC-F1-06 | Non-uppercase rejected | each of `on`, `Off`, `oN`, `status`, from both states -> `ERR UNKNOWN_CMD`/1, state unchanged | | |
| AC-F1-07 | Empty line | from both states, host `""` -> `ERR EMPTY`/1, state unchanged | | |
| AC-F1-08 | Whitespace or extra character | each of `" ON"`, `"ON "`, `"O N"`, `"ON\t"`, `"ON\r"`, `"   "` -> `ERR UNKNOWN_CMD`/1, state unchanged | | |
| AC-F1-09 | Length limit and priority | 32 x `A` -> `ERR UNKNOWN_CMD`; 33 x `A` -> `ERR TOO_LONG`; 31 x `A` + `\r` (32 B) -> `ERR UNKNOWN_CMD`; 32 x `A` + `\r` (33 B) -> `ERR TOO_LONG`; 33 x `o` and `ON` + 31 spaces -> `ERR TOO_LONG`; all exit 1, state unchanged | | |
| AC-F1-10 | HW fault and recovery | `FAULT HW_FAULT`, state OFF/ON -> `ON` and `OFF` -> `ERR HW_FAULT`/1, state unchanged; `STATUS` -> correct, exit 0; `on` -> `ERR UNKNOWN_CMD`; `""` -> `ERR EMPTY`; `FAULT NONE` -> `ON` -> `OK`, state ON | | |
| AC-F1-11 | Silent device | `SILENCE ON` -> host `STATUS` with `--timeout 0.5` -> exit 3, stderr contains "no response", duration < 1.0 s; `SILENCE OFF` -> `STATUS` -> `STATUS OFF`/0 | | |
| AC-F1-12 | Simulator unreachable | host on `dead_port` -> exit 2, stderr contains a connection error, finishes quickly (< timeout + 0.5 s) | | |
| AC-F1-13 | State persists across connections | host `ON` (process 1) -> host `STATUS` (process 2) -> `STATUS ON`; host `OFF` -> host `STATUS` -> `STATUS OFF` | | |
| AC-F1-14 | Quick sequence, no clock advance | `ON`, `OFF`, `ON`, `STATUS` with no `ADVANCE` -> `OK`, `OK`, `OK`, `STATUS ON`; final state ON. Expected to be affected by CR-01 | | |

## Non-functional checks
| Check | How | Result |
|---|---|---|
| Exchange log with timestamps in the report | Inspect `reports/e2e-report.html`: every test has a log with `HOST TX/RX` and `CTRL` lines and ISO timestamps | |
| No `sleep` in tests | `grep -rn "sleep" tests/` finds nothing | |
| Test independence | Suite passes in normal order and in reverse order (`pytest --reverse`, an option in conftest); any single test passes when run alone | |
| 5 green runs in a row | `python run.py` -> `reports/e2e-runs.md` shows 5/5 passed | |
| AC coverage | `ac_coverage.py` exits 0, no AC uncovered | |

## Run results
_To be filled in during validation._
