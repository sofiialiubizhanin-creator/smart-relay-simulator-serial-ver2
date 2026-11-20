# Project rules for the coding agent

- **Never commit any changes until the user explicitly allows it.**
- **Never write anything to disk (create, edit, delete or revert files) until the user explicitly allows it.**
  Propose the change and wait for a clear go-ahead; a remark or opinion from the user is not permission.

- Follow `specs/mission.md`, `specs/roadmap.md` and `specs/tech-stack.md` at every stage.
- SDD cycle per feature or change request: requirements.md -> plan.md -> validation.md (before code) -> implementation -> validation results -> CHANGELOG.
  Stop for user review after requirements.md and after plan.md + validation.md.
- One commit per SDD stage: requirements (incl. new ACs), then plan + validation rows, are committed **separately and
  before** the code or tests they justify; never mix a requirements change with its implementation in one commit.
- **Before writing or changing anything in `tests/e2e/` (tests, conftest, fixtures, helpers), invoke the skill `e2e-test-conventions`.**
- Never change, weaken, skip or delete a test to make it pass unless `requirements.md` was changed first.
