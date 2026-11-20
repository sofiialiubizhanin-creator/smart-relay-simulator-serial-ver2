# Roadmap

Every phase follows: requirements.md -> plan.md -> validation.md (before code) -> implementation -> validation results -> CHANGELOG entry.
**A phase is done when:** all of its E2E tests are green in one `python run.py` (= 5 consecutive suite runs), `validation.md` links every AC to its tests and run results, and CHANGELOG has an entry.

## Phase 1: Simulator + F1 (relay control and status) - DONE 2026-11-20
Done: `python run.py` 5/5 green (73 tests, AC-F1-01..16), validation.md complete, CHANGELOG 0.1.0, skill evals v1 -> v2.
Simulator with control API and controlled clock, `relay-host` CLI, commands ON / OFF / STATUS with error
handling and fault injection. Skill `e2e-test-conventions` v1 is in place before the first E2E test;
skill evals are run on v1 and on the refined version (`reports/skill-evals.md`); this is also required to close the phase.

## Phase 2: Change request CR-01 (toggle rate limit) - DONE 2026-11-20
Done: `python run.py` 5/5 green (91 tests, AC-F1-01..22), regression recorded, validation.md CR-01 complete, CHANGELOG 0.2.0.
A toggle (an accepted `ON`/`OFF` that changes the state) less than 2 s after the previous toggle is
rejected with `BUSY`; the exact rules are in F1 `requirements.md` section 8 (Changes, CR-01).
Regression results: `reports/regression-cr01.md`.
Before changing any F1 test, a regression run shows which F1 tests break; the F1 requirements get a
`Changes` section, and only then are the tests updated.
