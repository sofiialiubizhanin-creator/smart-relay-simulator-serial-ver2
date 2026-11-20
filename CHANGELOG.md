# Changelog

## [0.1.0] - 2026-11-20 - Phase 1: Simulator + F1 (relay control and status)

**Spec:** `specs/2026-11-20-f1-relay-control/` (requirements -> plan -> validation).
**Result:** all 16 acceptance criteria pass; `python run.py` 5/5 runs green, 73/73 tests each.

### Added
- Project skeleton (`pyproject.toml`, console scripts `relay-sim` and `relay-host`).
- Relay simulator (`relay_sim`): `ON` / `OFF` / `STATUS` over serial-over-TCP with error replies and error
  priority, a control API (`RESET`, `SET_STATE`, `GET_STATE`, `FAULT`, `SILENCE`, `ADVANCE`), a real or manual
  clock, and a timestamped exchange log (`--log FILE`).
- `relay-host` one-shot CLI over pyserial `socket://`, with exit codes 0/1/2/3 and `RELAY_HOST_LOG` for tests.
- E2E framework (`tests/e2e/conftest.py`, `helpers.py`): simulator/control/host fixtures, mandatory AC markers,
  `--reverse`, exchange log and AC column in `reports/e2e-report.html`, timing measured from the command send.
- E2E tests for AC-F1-01..16 (73 cases) in `tests/e2e/test_f1_relay_control.py`.
- `python run.py`: one command that sets up `.venv`, installs, runs the suite 5 times in a row and writes the
  reports; `python run.py demo` for manual use.
- Skill `e2e-test-conventions`: v1, evals, then v2 refined from the findings (`reports/skill-evals.md`: trigger
  correct 5/5 in both versions, expectations 23.5/24 -> 24/24).

### Changed (after the G0-G3 spec and code review)
- Specs: silence discards commands; AC-F1-11 time counted from command send; AC-F1-12 error text and
  6 s bound; new AC-F1-15 (usage errors, the one exception to the single-stderr-line rule); control-API
  errors, simulator launch, host encoding, exit codes and `RELAY_HOST_LOG` documented; "5 runs" and
  CR-01 "toggle" wording unified.
- Simulator: `ADVANCE` rejects NaN/infinite values; no tracebacks on control-port disconnects; one-line
  error for a busy port.
- Host: `--port`/`--timeout` validated as usage errors; IPv6 hosts supported; a broken `RELAY_HOST_LOG`
  path no longer crashes the host. pyserial pinned to `<4`.
- New AC-F1-16: silence wins over the hardware fault (error priority rule 1 before rule 5).

### Validation
`specs/2026-11-20-f1-relay-control/validation.md`: every AC linked to its tests with a result. Non-functional
checks pass: exchange log in the report, no sleep, reverse order and single-test runs, AC coverage, and the
AC-marker rule enforced.

### Notes
- pyserial's `socket://` handler sleeps 0.3 s in `close()`; the host uses a subclass without that pause.
- On Windows a refused loopback connection takes ~2 s per address (TCP retries), so AC-F1-12 allows up to 6 s.
- Windows PowerShell 5.1 drops an empty `""` argument; use `relay-host --% ""` there (see README).
