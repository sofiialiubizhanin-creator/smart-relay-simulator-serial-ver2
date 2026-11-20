---
name: e2e-test-conventions
description: Conventions for writing and changing pytest E2E tests of the Smart Relay Simulator (tests/e2e/). Use whenever you create, modify, review or fix an E2E test, conftest, fixture or test helper under tests/e2e/, or turn an Acceptance Criterion (AC-*) from requirements.md / validation.md into a test. Do NOT use for unit tests of src/ modules, for production code changes without test changes, or for docs-only edits.
---

# E2E test conventions (Smart Relay Simulator)

## When to use
- Writing a new E2E test for an AC from `specs/*/requirements.md` / `validation.md`.
- Changing, fixing or reviewing existing tests, `tests/e2e/conftest.py` or helpers.
- Updating tests after a requirements change (e.g. a change request).

## When NOT to use
- Unit tests of internal modules (`src/relay_sim/*`, `src/relay_host/*`) - those are not E2E.
- Production code changes that do not touch tests; README/CHANGELOG/spec-only edits.

## Golden rules
1. **Source of truth is the spec, not the code.** Read the AC in `requirements.md` and the matching row in
   `validation.md` first. Do not open `src/` to decide what a test should expect.
2. **Drive the product only through the host CLI** via the `host` fixture. Set up / inspect the simulator
   only through the `control` fixture (control API). Never import `relay_sim` or `relay_host` in E2E tests.
3. **No `time.sleep`, ever.** Time-dependent behavior: `control.advance(seconds)` on the manual clock.
   Waiting for a condition: `wait_until(predicate, timeout=..., message=...)` from `tests/e2e/helpers.py`.
4. **Independent tests.** Each test starts from a reset simulator (autouse fixture does `RESET`). Never rely
   on another test's state; set preconditions explicitly with `control.set_state(...)`.
5. **Every test references its AC**: name `test_ac_<feature>_<nn>_<behavior>` and marker
   `@pytest.mark.ac("AC-F1-01")` (several IDs allowed). Tests without a valid marker fail at collection.
6. **Assert the full contract**: reply text (`r.stdout`), exit code (`r.exit_code`) and, for anything that
   could change state, the real state via `control.get_state()` - not only via `STATUS`.
7. **Never weaken, skip, xfail or delete a test to make it pass.** If the expected behavior is wrong,
   stop and ask for a `requirements.md` change first.
8. The exchange log is automatic (fixtures record it into the HTML report); do not print it manually.

## Fixtures (tests/e2e/conftest.py)
| Fixture | Scope | Purpose |
|---|---|---|
| `simulator` | session | Starts `python -m relay_sim --clock manual` on free ports; yields ports |
| `control` | function, autouse | Control API client; `RESET` before each test |
| `host` | function | `host(command, timeout=1.0, port=None) -> HostResult(stdout, stderr, exit_code, duration)` |
| `dead_port` | function | A local TCP port with nothing listening |
| `exchange_log` | function | Per-test timestamped log (host TX/RX + control calls), attached to report |

`control` methods: `reset()`, `set_state("ON"|"OFF")`, `get_state() -> "ON"|"OFF"`,
`fault("HW_FAULT"|"NONE")`, `silence(True|False)`, `advance(seconds)`.

Details and copy-ready patterns: `references/fixtures.md`, `references/patterns.md`.

## Checklist before finishing
- [ ] Each AC touched has >= 1 test with the right marker; run `python .claude/skills/e2e-test-conventions/scripts/ac_coverage.py`.
- [ ] Negative/edge cases from requirements "Edge cases" are covered.
- [ ] No `sleep`, no `src` imports, no hard-coded ports, no order dependence.
- [ ] `python run.py` (5 consecutive runs) is green; update the AC <> test table in `validation.md`.
