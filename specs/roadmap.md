# Roadmap

Every phase follows: requirements.md -> plan.md -> validation.md (before code) -> implementation -> validation results -> CHANGELOG entry.
**A phase is done when:** all of its E2E tests are green in one `python run.py` (= 5 consecutive suite runs), `validation.md` links every AC to its tests and run results, and CHANGELOG has an entry.

## Phase 1: Simulator + F1 (relay control and status)
Simulator with control API and controlled clock, `relay-host` CLI, commands ON / OFF / STATUS with error
handling and fault injection. Skill `e2e-test-conventions` v1 is in place before the first E2E test;
skill evals are run on v1 and on the refined version (`reports/skill-evals.md`); this is also required to close the phase.

## Phase 2: Change request CR-01 (toggle rate limit)
A toggle (an accepted `ON`/`OFF` that changes the state) less than 2 s after the previous toggle is
rejected with `BUSY`; the exact rules are defined in the CR-01 requirements change.
Before changing any F1 test, a regression run shows which F1 tests break; the F1 requirements get a
`Changes` section, and only then are the tests updated.
