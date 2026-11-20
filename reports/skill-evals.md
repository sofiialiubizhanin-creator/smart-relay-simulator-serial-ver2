# Skill evals: `e2e-test-conventions`

**Skill:** `.claude/skills/e2e-test-conventions/` | **Eval set:** `evals/evals.json`, 5 cases: 4 positive cases on this
project's data, plus 1 case where the skill must not trigger.
**Runs:** **v1** = the first draft of the skill (as committed in `9c524e0`), run before any refinement; **v2** = the
skill refined from the v1 findings, run after the refinement.
**Raw outputs:** `.claude/skills/e2e-test-conventions/evals/runs/<version>/case-N.diff`: everything each run changed, as a diff against its starting state. An empty diff means the run changed nothing.

## Method
- **Isolation:** each case runs as a separate agent in its own clone of the project. The clone holds the
  committed state plus the G4 test framework (`tests/e2e/conftest.py`, `helpers.py`; no test files yet).
  An agent cannot see another run's output or touch the real repo.
- **What the agent gets:** the task text exactly as a user would type it, plus fixed environment notes: the
  clone path, the test command, "do not commit", and the report format. The task texts are the same in every run.
- **Grading:**
  - **Triggering:** taken from the agent's report of its Skill tool calls, checked against what it changed.
  - **Expectations** (listed in `evals.json`): graded against the diff and the report. 1 = met, 0.5 = partly met, 0 = not met.
- At most 2 agents ran at a time.

## v1: results (before refinement), 2026-11-20

| # | Case (task text) | Should trigger | Triggered | Score |
|---|---|---|---|---|
| 1 | "Write the E2E test for AC-F1-07 (empty line) from specs/2026-11-20-f1-relay-control." | yes | yes | 5/5 |
| 2 | "Add E2E tests for AC-F1-10: hardware fault injection, including the error-priority part." | yes | yes | 6/6 |
| 3 | "Write the E2E test for AC-F1-11 (silent device). Note: on our CI machine a previous attempt was flaky - the host sometimes took 1.05-1.2 s." | yes | yes | 5/5 |
| 4 | "CR-01 is accepted: relay cannot be toggled more than once per 2 s (BUSY). Write E2E tests for the new AC, boundary 2.000 s allowed." | yes | yes | 4.5/5 |
| 5 | "Write a unit test for the ManualClock class in src/relay_sim/clock.py: advance() must reject negative values." | **no** | no | 3/3 |
| | **Total** | | **5/5 correct** | **23.5/24** |

### Evidence per case

**Case 1: AC-F1-07** (`runs/v1/case-1.diff`). The agent created `tests/e2e/test_f1_relay_control.py` and filled in the
Test(s) cell of the AC-F1-07 row in validation.md. The conventions the skill asks for are visible:
- the name and marker carry the AC ID;
- it runs from both initial states;
- it checks the reply, the exit code and the real state through the control API.

```python
@pytest.mark.ac("AC-F1-07")
@pytest.mark.parametrize("initial", ["OFF", "ON"])
def test_ac_f1_07_empty_line_replies_err_empty(host, control, initial):
    control.set_state(initial)
    r = host("")
    assert r.sent, "the host must send the empty line to the device (not treat it as a usage error)"
    assert (r.stdout, r.exit_code) == ("ERR EMPTY", 1)
    assert control.get_state() == initial
```
The tests passed in normal order, in reverse order, and in 5 runs in a row.

**Case 2: AC-F1-10** (`runs/v1/case-2.diff`). 16 test cases in the new file `tests/e2e/test_f1_hw_fault.py`:
- `ON`/`OFF` from both states, including the state the relay was already in → `ERR HW_FAULT`/1, state unchanged;
- `STATUS` during the fault;
- 4 invalid lines keeping their own error (`on` → `ERR UNKNOWN_CMD`, `""` → `ERR EMPTY`, 33 bytes and `ON` + 31 spaces → `ERR TOO_LONG`) from both states;
- recovery after `FAULT NONE` in both directions.

The tests passed in normal and reverse order.
- **Weakness:** the file name differs from case 1 and from plan.md G5 (`test_f1_relay_control.py`). The skill doesn't say where F1 tests go, so F1 tests end up scattered across files.

**Case 3: AC-F1-11** (`runs/v1/case-3.diff`). The "flaky on CI" note tempts the agent to loosen the bound. The agent
asserted the bound exactly as AC-F1-11 states it: counted from the moment the command is sent, not from process start:
```python
assert r.stderr == f"ERROR: no response from device within {SILENT_TIMEOUT}s"
assert r.sent, "host log has no TX line: the command was never sent to the device"
assert r.send_to_end <= SILENT_BOUND, (...)          # SILENT_BOUND = 0.5 + 0.5
assert control.get_state() == "OFF", "a command sent to a silent device must be discarded"
```
It passed in 5 runs in a row (`send_to_end` = 0.507 s; the whole process took 0.676 s, of which 0.17 s was startup).
- **Found a defect in the skill:** the skill's own example in `references/patterns.md` asserts
  `r.duration < 0.5 + 0.5`. That measures from process start, which contradicts AC-F1-11 and explains the
  1.05-1.2 s CI failures. The agent got this right **despite** the skill, by reading requirements.md and `helpers.py`.

**Case 4: CR-01** (`runs/v1/case-4.diff`). The agent wrote **no tests**: no CR-01 acceptance criteria exist yet, and the
project rules say requirements come first. It drafted the requirements with 6 proposed ACs (a 1.999 s/2.000 s
boundary pair, `BUSY` not restarting the window, `STATUS` and no-op commands, priority against `HW_FAULT`), listed
7 open questions, and noted the impact on AC-F1-14.
- **Half a point off:** it put the draft in a **new folder** `specs/2026-11-20-cr01-toggle-rate-limit/`. The
  assignment says a change request updates the affected feature's `requirements.md` with a `Changes` section.
  The skill doesn't say so.

**Case 5: negative case** (`runs/v1/case-5.diff` is empty; the proposed test is in `runs/v1/case-5-proposed-test_clock.py`). The skill was
correctly **not** triggered. The agent proposed a plain unit test that imports `relay_sim.clock` directly, with no AC markers
or E2E fixtures, for `tests/unit/`.
- It didn't write the test into its clone. It read the `CLAUDE.md` rule ("never write to disk until **the user** explicitly
  allows it") as overriding the agent-written permission in the eval prompt, so it ran the test in a scratch folder (3 passed).
  This is a side effect of the eval setup, not of the skill.

### v1 findings → refinements planned for v2
| # | Finding (case) | Planned change |
|---|---|---|
| 1 | Wrong example: the timeout pattern measures `r.duration` (from process start) and contradicts AC-F1-11 (3) | Rewrite the pattern to use `send_to_end`, the exact stderr text and a state check; add "timing bounds are asserted exactly as the AC states them; no widening, retries or `flaky`" |
| 2 | Fixture docs are outdated: no `host(None)`, `HostResult.sent` / `send_to_end`, `fresh_simulator`, or simulator `--log` (1, 3) | Update SKILL.md and `references/fixtures.md` |
| 3 | No rule for which test file to use: the agents picked different files (1 vs 2) | "F1 tests live in `tests/e2e/test_f1_relay_control.py`; check coverage first, extend the file, no duplicates" |
| 4 | No rule for a missing AC: a change-request draft went into a new folder (4) | "If the AC isn't in requirements.md, draft the change and stop; for a change request, add a `Changes` section to the affected feature's requirements.md" |
| 5 | The checklist demands `python run.py`, which doesn't exist before G6 (1, 2) | "Until `run.py` exists: pytest in normal order and with `--reverse`" |
| 6 | Inconsistent validation.md edits: cases 1 and 2 filled Test(s), case 3 didn't (1-3) | "Fill Test(s) when adding a test; fill Result only during validation (G7)" |

## v2: results (after refinement), 2026-11-20

The skill was refined with the 6 changes above (`SKILL.md`, `references/fixtures.md`, `references/patterns.md`).
The same 5 task texts ran in fresh clones that contain skill v2 but none of the v1 outputs.

| # | Case | Should trigger | Triggered | v1 score | v2 score |
|---|---|---|---|---|---|
| 1 | AC-F1-07 empty line | yes | yes | 5/5 | 5/5 |
| 2 | AC-F1-10 fault + priority | yes | yes | 6/6 | 6/6 |
| 3 | AC-F1-11 silent device ("flaky on CI") | yes | yes | 5/5 | 5/5 |
| 4 | CR-01 (no ACs yet) | yes | yes | 4.5/5 | **5/5** |
| 5 | Unit test, negative case | **no** | no | 3/3 | 3/3 |
| | **Total** | | **5/5 correct in both versions** | **23.5/24** | **24/24** |

### Evidence per case (what changed from v1)

**Case 1** (`runs/v2/case-1.diff`). Same quality as v1: correct name and marker, both initial states, `r.sent`, exit
code, state through the control API.
- **New in v2:** it chose `tests/e2e/test_f1_relay_control.py` "because the conventions say all F1 tests go in this one file".
- **New in v2:** it filled only the Test(s) cell of validation.md, leaving Result for validation.
- **New in v2:** it checked with pytest in normal order and with `--reverse`, instead of reporting that `run.py` is missing.

**Case 2** (`runs/v2/case-2.diff`). 14 test cases with the same coverage as v1:
- `ON`/`OFF` from both states, including the state the relay was already in;
- `STATUS` during the fault;
- invalid lines keeping their own error, from both states;
- recovery in both directions.
- **v1 weakness fixed:** the tests went into the single F1 file `test_f1_relay_control.py`, not into a new `test_f1_hw_fault.py`.
- **New behavior from the v2 "ambiguity is a question" rule:** the agent didn't invent a silence + fault test.
  It reported that priority rule 1 (silence before fault) appears in requirements section 3 but in no AC or validation row.

**Case 3** (`runs/v2/case-3.diff`). Same correct assertion as v1, but this time **the skill supplied it**, not a workaround:
```python
# Bound counted from the moment the host sent the command (host log TX -> TIMEOUT), as the AC states.
# Not r.duration: that includes Python start-up of the host process.
assert r.send_to_end <= 0.5 + 0.5, f"TX -> TIMEOUT took {r.send_to_end:.3f}s (limit 1.0s)"
```
In v1 the skill's own example (`r.duration < 0.5 + 0.5`) pointed the wrong way. In v2 the corrected example and rule 7
("timing bounds exactly as the AC states them") match the AC. It also filled the Test(s) cell, which v1 didn't.

**Case 4** (`runs/v2/case-4.diff`). No tests, as in v1.
- **v1 half-point fixed:** the draft went into `## 8. Changes` → `### CR-01 ... (DRAFT, pending user review)` of
  `specs/2026-11-20-f1-relay-control/requirements.md`, citing the skill's rule. v1 had created a new folder.
- Proposed ACs: AC-F1-16 (`BUSY` below 2.000 s), AC-F1-17 (`OK` at exactly 2.000 s or later), and a changed AC-F1-14.
- 9 open questions, including the no-op command, `BUSY` restarting the window, priority against `HW_FAULT`, and float precision at the boundary.
- It planned the tests at 0, 1.999 and 2.000 s with `control.advance`. It also noted that Phase 1 isn't finished, so CR-01 shouldn't start yet.

**Case 5** (`runs/v2/case-5.diff`). The skill was correctly **not** triggered ("it only covers tests under `tests/e2e/`").
This time the agent wrote the plain unit test into `tests/unit/test_clock.py` (3 passed, run against this copy's `src/`), with no AC markers or E2E fixtures.

### What the refinement changed: v1 → v2
| Refinement | Evidence that it worked |
|---|---|
| 1. Correct timeout pattern and timing rule | Case 3: the assertion and comment now come from the skill (`send_to_end`, "Not r.duration") |
| 2. Up-to-date fixture docs | Cases 1 and 3 use `r.sent` / `send_to_end` as documented, without reading `helpers.py` to discover them |
| 3. One test file per feature | Cases 1-3 all used `test_f1_relay_control.py`; in v1, case 2 used a separate file |
| 4. Missing AC: `Changes` section, then stop | Case 4: the draft went into F1's requirements.md `Changes` section (v1: a new folder) |
| 5. `--reverse` until `run.py` exists | Cases 1-3 verified with normal and reverse order; none reported "run.py missing" |
| 6. validation.md: Test(s) cell only | Cases 1-3 all filled Test(s) and left Result empty (v1: case 3 didn't) |

### Limits of this evaluation
- Each case ran **once per version**. The v1 → v2 differences are clear, rule-traceable behaviors, but there is no variance measurement.
- Case 5 tests **trigger precision** (the skill stays off for a unit test). It does not compare test quality.
- **The project rules interfered once:** `CLAUDE.md` ("no writes to disk without the user's explicit go-ahead") made v1 case 5 keep its
  test outside the clone. The eval prompts are agent-written, so agents had to judge whether that counts as the user's permission.
  This affects where files landed, not the skill's trigger or the content of the tests.
