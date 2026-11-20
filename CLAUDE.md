# Project rules for the coding agent

- Follow `specs/mission.md`, `specs/roadmap.md` and `specs/tech-stack.md` at every stage.
- SDD cycle per feature or change request: requirements.md -> plan.md -> validation.md (before code) -> implementation -> validation results -> CHANGELOG.
  Stop for user review after requirements.md and after plan.md + validation.md.
- **Before writing or changing anything in `tests/e2e/` (tests, conftest, fixtures, helpers), invoke the skill `e2e-test-conventions`.**
- Never change, weaken, skip or delete a test to make it pass unless `requirements.md` was changed first.
