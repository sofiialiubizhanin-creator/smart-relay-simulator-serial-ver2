# F1: Relay control and status: validation

Status: **validated** 2026-11-20. Written before implementation (what and how we verify); the "Test(s)" column was filled in G5 and "Result" during validation (G7).
All checks are E2E: `host` = `relay-host` CLI, `control` = the simulator control API; "state X" is read
with `GET_STATE`. Every test starts after `RESET` (state `OFF`, no fault or silence, clock 0).
**Pass criterion for F1:** every row passes in one `python run.py` (= 5 consecutive suite runs).

| AC | What we verify | How (setup -> action -> expected) | Test(s) | Result |
|---|---|---|---|---|
| AC-F1-01 | ON from OFF | set OFF -> `ON` -> `OK`, exit 0, state ON | `test_ac_f1_01_on_from_off_replies_ok` | PASS 5/5 (1 case) |
| AC-F1-02 | OFF from ON | set ON -> `OFF` -> `OK`, exit 0, state OFF | `test_ac_f1_02_off_from_on_replies_ok` | PASS 5/5 (1 case) |
| AC-F1-03 | STATUS reflects state, default OFF | (a) just-started simulator, no RESET -> `STATUS OFF`; (b) set ON, RESET -> `STATUS OFF`; (c) set OFF / ON -> `STATUS OFF` / `STATUS ON`; state unchanged, exit 0 | `test_ac_f1_03_status_off_after_startup`, `test_ac_f1_03_status_off_after_reset`, `test_ac_f1_03_status_reports_current_state` | PASS 5/5 (4 cases) |
| AC-F1-04 | Repeated same command is a no-op | set ON -> `ON` -> `OK`/0, state ON; set OFF -> `OFF` -> `OK`/0, state OFF | `test_ac_f1_04_repeated_command_replies_ok_without_change` | PASS 5/5 (2 cases) |
| AC-F1-05 | Unknown command | each of `TOGGLE`, `RESET`, `X`, from both states -> `ERR UNKNOWN_CMD`/1, state unchanged | `test_ac_f1_05_unknown_command_rejected` | PASS 5/5 (6 cases) |
| AC-F1-06 | Non-uppercase rejected | each of `on`, `off`, `Off`, `oN`, `status`, from both states -> `ERR UNKNOWN_CMD`/1, state unchanged | `test_ac_f1_06_non_uppercase_command_rejected` | PASS 5/5 (10 cases) |
| AC-F1-07 | Empty line | from both states, host `""` -> `ERR EMPTY`/1, state unchanged | `test_ac_f1_07_empty_line_replies_err_empty` | PASS 5/5 (2 cases) |
| AC-F1-08 | Whitespace or extra character | each of `" ON"`, `"ON "`, `"O N"`, `"ON\t"`, `"ON\r"`, `"   "`, from both states -> `ERR UNKNOWN_CMD`/1, state unchanged | `test_ac_f1_08_whitespace_or_extra_char_rejected` | PASS 5/5 (12 cases) |
| AC-F1-09 | Length limit and priority | 32 x `A` -> `ERR UNKNOWN_CMD`; 33 x `A` -> `ERR TOO_LONG`; 31 x `A` + `\r` (32 B) -> `ERR UNKNOWN_CMD`; 32 x `A` + `\r` (33 B) -> `ERR TOO_LONG`; 33 x `o` and `ON` + 31 spaces -> `ERR TOO_LONG`; all exit 1, from both states, state unchanged | `test_ac_f1_09_length_limit` | PASS 5/5 (12 cases) |
| AC-F1-10 | HW fault, priority, recovery | `FAULT HW_FAULT`, from both states: `ON` and `OFF` (incl. the current state) -> `ERR HW_FAULT`/1, state unchanged; `STATUS` -> correct/0; `on` -> `ERR UNKNOWN_CMD`, `""` -> `ERR EMPTY`, 33 B -> `ERR TOO_LONG`; recovery: from OFF and from ON, `FAULT NONE` -> the opposite command -> `OK`, state changed | `test_ac_f1_10_hw_fault_blocks_on_off`, `test_ac_f1_10_hw_fault_status_still_works`, `test_ac_f1_10_hw_fault_invalid_line_keeps_own_error`, `test_ac_f1_10_recovers_after_fault_cleared` | PASS 5/5 (14 cases) |
| AC-F1-11 | Silent device | state OFF, `SILENCE ON` -> host `ON` with `--timeout 0.5` -> exit 3, stderr `ERROR: no response from device within 0.5s`, host log TX -> TIMEOUT <= 1.0 s, state still OFF; `SILENCE OFF` -> `STATUS` -> `STATUS OFF`/0 | `test_ac_f1_11_silent_device_times_out_and_discards_command`, `test_ac_f1_11_recovers_after_silence_off` | PASS 5/5 (2 cases) |
| AC-F1-12 | Simulator unreachable | host on `dead_port` -> exit 2, stderr starts with `ERROR: cannot connect`, finishes in < 6 s (pyserial's connect limit is 5 s; Windows retries a refused loopback connect for ~2 s per address) | `test_ac_f1_12_unreachable_device_connection_error` | PASS 5/5 (1 case) |
| AC-F1-13 | State persists across connections | host `ON` (process 1) -> host `STATUS` (process 2) -> `STATUS ON`; host `OFF` -> host `STATUS` -> `STATUS OFF` | `test_ac_f1_13_state_persists_across_host_calls` | PASS 5/5 (1 case) |
| AC-F1-14 | Quick sequence, no clock advance | four separate host calls `ON`, `OFF`, `ON`, `STATUS` with no `ADVANCE` -> `OK`, `OK`, `OK`, `STATUS ON`; final state ON. Expected to be affected by CR-01 | `test_ac_f1_14_quick_sequence_without_clock_advance` | PASS 5/5 (1 case) |
| AC-F1-15 | Usage error sends nothing | host with no COMMAND, with `--port 70000`, with `--timeout 0` -> exit 2, stderr = usage line + one `ERROR:` line, host log has no `TX`, state unchanged | `test_ac_f1_15_usage_error_sends_nothing` | PASS 5/5 (3 cases) |
| AC-F1-16 | Silence wins over HW fault | state OFF, `FAULT HW_FAULT`, `SILENCE ON` -> host `ON` with `--timeout 0.5` -> exit 3, no stdout, state OFF; `SILENCE OFF` -> host `ON` -> `ERR HW_FAULT`/1, state OFF | `test_ac_f1_16_silence_wins_over_hw_fault` | PASS 5/5 (1 case) |

## Non-functional checks
| Check | How | Result |
|---|---|---|
| Exchange log with timestamps in the report | Inspect `reports/e2e-report.html`: every test has a log with `HOST TX/RX` and `CTRL` lines and ISO timestamps (ms) | PASS: all 73 tests have an "Exchange log (host <-> simulator)" section with `CTRL`/`TEST`/`HOST TX`/`HOST RX` lines and ms timestamps; all 73 rows have an AC cell (16 distinct ACs) |
| No sleep in tests | `grep -rnE "time\.sleep|asyncio\.sleep" tests/` finds nothing | PASS: no matches |
| Test independence | Suite passes in normal order and with `pytest --reverse`; any single test passes when run alone | PASS: normal order 73 passed; `--reverse` 73 passed; AC-F1-14, AC-F1-03 (startup) and AC-F1-16 tests each pass alone |
| 5 green runs in a row | `python run.py` -> `reports/e2e-runs.md` shows 5/5 passed | PASS: 5/5 runs, 73/73 each (`reports/e2e-runs.md`, 2026-11-20 15:01) |
| AC coverage | `.claude/skills/e2e-test-conventions/scripts/ac_coverage.py` exits 0, no AC uncovered | PASS: exit 0, 16/16 ACs covered |
| AC convention enforced | A test with no `ac` marker, or a name not matching it, stops collection | PASS: a temporary test without a marker stopped collection (`AC convention violations`, exit 4); file deleted after the check |

## Run results
| Date | Command | Environment | Result |
|---|---|---|---|
| 2026-11-20 15:01 | `python run.py` (5 consecutive suite runs) | Windows 11, Python 3.14.10, pytest 9.2.0, pyserial 3.5 | **5/5 PASS**: 73 passed, 0 failed, 0 skipped per run, about 21-22 s each (`reports/e2e-runs.md`) |
| 2026-11-20 | `pytest tests/e2e --reverse` | same | 73 passed |

All 16 F1 acceptance criteria pass. AC-F1-14 is expected to change with CR-01 (phase 2).

---

## CR-01: Toggle rate limit (requirements section 8)
Status: **validated** 2026-11-20. Written before implementation; Test(s) filled in G10, Result in G11.
The F1 results above stay as the phase 1 record; CR-01 results are filled in below. Time is moved only with `control.advance()` (manual clock), never sleep.
"Toggle X" = host `X` that changes the state and replies `OK`.

| AC | What we verify | How (setup -> action -> expected) | Test(s) | Result |
|---|---|---|---|---|
| AC-F1-13 (changed) | State persists, with the toggle window | host `ON` -> `STATUS ON`; advance 2.0; host `OFF` -> `OK` -> `STATUS OFF`; state OFF (found by the regression run) | `test_ac_f1_13_state_persists_across_host_calls` | PASS 5/5 (1 case) |
| AC-F1-14 (changed) | Quick sequence under CR-01 | four separate host calls `ON`, `OFF`, `ON`, `STATUS`, no `ADVANCE` -> `OK`, `BUSY`, `OK`, `STATUS ON`; final state ON | `test_ac_f1_14_quick_sequence_without_clock_advance` | PASS 5/5 (1 case) |
| AC-F1-17 | Toggle inside the window is `BUSY` | both directions (set OFF -> toggle `ON`; set ON -> toggle `OFF`); then advance 0 / 1.999 -> the opposite command -> `BUSY`/1, state unchanged | `test_ac_f1_17_toggle_inside_window_replies_busy` | PASS 5/5 (4 cases) |
| AC-F1-18 | Toggle at or after 2.000 s is accepted | both directions; after the first toggle advance 2.000, 2.5, or 1.999 + 0.001 (two steps) -> the opposite command -> `OK`/0, state changed | `test_ac_f1_18_toggle_at_or_after_window_replies_ok` | PASS 5/5 (6 cases) |
| AC-F1-19 | `BUSY` does not restart the window | toggle `ON` at 0; advance 1.5 -> `OFF` -> `BUSY`; advance 0.5 (t = 2.0) -> `OFF` -> `OK`, state OFF | `test_ac_f1_19_busy_does_not_restart_window` | PASS 5/5 (1 case) |
| AC-F1-20 | `STATUS` and no-op inside the window | toggle `ON` at 0; advance 1.0 -> `STATUS` -> `STATUS ON`/0, `ON` -> `OK`/0, state ON; advance 1.0 (t = 2.0) -> `OFF` -> `OK`, state OFF | `test_ac_f1_20_status_and_noop_inside_window` | PASS 5/5 (1 case) |
| AC-F1-21 | `RESET` clears the window; `SET_STATE` starts none | (a) toggle `ON`, `RESET` (state OFF) -> `ON` at once -> `OK`, state ON; (b) `SET_STATE ON` -> `OFF` at once -> `OK`, state OFF | `test_ac_f1_21_reset_clears_window`, `test_ac_f1_21_set_state_starts_no_window` | PASS 5/5 (2 cases) |
| AC-F1-22 | Priority over `BUSY` | toggle `ON` at 0, advance 0.5: with `FAULT HW_FAULT` -> `OFF` -> `ERR HW_FAULT`/1; without fault: `""` -> `ERR EMPTY`, 33 B -> `ERR TOO_LONG`, `off` -> `ERR UNKNOWN_CMD` (never `BUSY`); state stays ON | `test_ac_f1_22_hw_fault_has_priority_over_busy`, `test_ac_f1_22_invalid_line_inside_window_keeps_own_error` | PASS 5/5 (4 cases) |

| Check | How | Result |
|---|---|---|
| Regression run | Unchanged F1 suite (commit `4293653`) against the CR-01 implementation; failing tests, cause and action recorded in `reports/regression-cr01.md` | DONE: 2 of 73 failed (AC-F1-13, AC-F1-14), 71 unaffected; both superseded in requirements section 8 and updated in G10 |
| 5 green runs in a row | `python run.py` -> 5/5 with the updated and new tests | PASS: 5/5 runs, 91/91 each (`reports/e2e-runs.md`, 2026-11-20 15:43) |
| AC coverage / independence | coverage script exits 0 (AC-F1-01..22); suite green with `--reverse` | PASS: exit 0, 22/22 ACs covered; `--reverse` 91 passed; no sleep; all 91 tests have an exchange log and an AC cell in the report |

### CR-01 run results
| Date | Command | Environment | Result |
|---|---|---|---|
| 2026-11-20 15:26 | `python run.py --runs 1` (regression: unchanged F1 suite) | Windows 11, Python 3.14.10, pytest 9.2.0, pyserial 3.5 | 2 failed, 71 passed: expected, see `reports/regression-cr01.md` |
| 2026-11-20 15:43 | `python run.py` (5 consecutive suite runs) | same | **5/5 PASS**: 91 passed, 0 failed, 0 skipped per run, about 30-32 s each |
| 2026-11-20 | `pytest tests/e2e --reverse` | same | 91 passed |

All 22 acceptance criteria (AC-F1-01..16 as superseded by section 8, AC-F1-17..22) pass.
