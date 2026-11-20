# CR-01 regression run

**Purpose:** show which F1 tests are affected by CR-01 (toggle rate limit) **before any test is changed**
(roadmap phase 2, plan G9).

| Item | Value |
|---|---|
| Date | 2026-11-20 15:26 |
| Product | commit `f22e502` (CR-01 G8: BUSY within 2 s) |
| Tests | `tests/e2e/test_f1_relay_control.py` **unchanged** since commit `4293653` (`git diff 4293653 f22e502 -- tests/` is empty) |
| Command | `python run.py --runs 1 -- -rf` |
| Result | **2 failed, 71 passed** (73 cases) |
| Full report | `reports/regression-cr01.html` (HTML report of this run, with the exchange log of every test) |

## Failing tests

| Test | AC | Expected (F1) | Actual (CR-01) | Cause | Action |
|---|---|---|---|---|---|
| `test_ac_f1_14_quick_sequence_without_clock_advance` | AC-F1-14 | `OK`, `OK`, `OK`, `STATUS ON` | `OK`, `BUSY`, `OK`, `STATUS ON` | The 2nd call `OFF` is a toggle 0 s after the `ON` (CR-01 rule 1); the 3rd call `ON` is then a no-op (rule 2) | Already superseded in requirements section 8: update the test to `OK`, `BUSY`, `OK`, `STATUS ON` (no clock advance) |
| `test_ac_f1_13_state_persists_across_host_calls` | AC-F1-13 | `ON` -> `OK`, `STATUS ON`, `OFF` -> `OK`, `STATUS OFF` | 3rd call `OFF` -> `BUSY` (exit 1) | `OFF` is a toggle ~0.3 s (manual clock: 0 s) after the `ON` | Added to section 8 "Supersedes": the test advances the clock 2.0 s before `OFF`; the AC text is unchanged (it is about state persistence, not timing). **Approved 2026-11-20.** |

Exchange log excerpts (from the run's report):
```
AC-F1-13
TEST > relay-host 'ON'      TEST < exit=0 stdout='OK'
TEST > relay-host 'STATUS'  TEST < exit=0 stdout='STATUS ON'
TEST > relay-host 'OFF'     TEST < exit=1 stdout='BUSY'        <- toggle inside the 2 s window

AC-F1-14
TEST > relay-host 'ON'      TEST < exit=0 stdout='OK'
TEST > relay-host 'OFF'     TEST < exit=1 stdout='BUSY'        <- toggle inside the 2 s window
TEST > relay-host 'ON'      TEST < exit=0 stdout='OK'          <- no-op, relay still ON
TEST > relay-host 'STATUS'  TEST < exit=0 stdout='STATUS ON'
```

## Unaffected (71 passed)
Every other F1 test passed unchanged, including:
- **AC-F1-10 recovery:** the toggle rejected with `ERR HW_FAULT` is not a toggle, so the toggle after `FAULT NONE` is the first one.
- **AC-F1-01/02/04:** the start state is set with `SET_STATE`, which doesn't start a window.
- **AC-F1-16:** the command discarded by silence and the one rejected with `ERR HW_FAULT` are not toggles.

Each of these tests toggles at most once, or only after a reset.
