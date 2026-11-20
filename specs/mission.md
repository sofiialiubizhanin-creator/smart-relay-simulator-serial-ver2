# Mission

**What:** Smart Relay Simulator: a software relay that speaks a line-based text protocol over
serial-over-TCP (`socket://`), plus a one-shot host CLI (`relay-host`) that controls it from a terminal.
**For whom:** developers and QA who need to test relay-control logic without hardware, using a
spec-driven (SDD) workflow where E2E tests come from requirements.

## Quality principles
1. Every Acceptance Criterion (AC) has an ID and is covered by at least one E2E test; every test references its AC ID.
2. E2E tests are written from `requirements.md` and `validation.md`, never from implementation code.
3. Every feature includes negative and edge scenarios, including fault injection.
4. Any behavior change starts with a change to `requirements.md`.
5. The agent must not change, weaken, skip or delete a test to make it pass unless `requirements.md` was changed first.
6. The E2E suite passes 5 runs in a row with zero failures (no flaky tests).
