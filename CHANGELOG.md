# Changelog

## [Unreleased] - Phase 1: Simulator + F1 (in progress)

### Added
- Project skeleton (`pyproject.toml`, console scripts `relay-sim` and `relay-host`).
- Relay simulator (`relay_sim`): `ON` / `OFF` / `STATUS` over serial-over-TCP with error replies and error
  priority, a control API (`RESET`, `SET_STATE`, `GET_STATE`, `FAULT`, `SILENCE`, `ADVANCE`), and a real or manual clock.
- `relay-host` one-shot CLI over pyserial `socket://`, with exit codes 0/1/2/3.

### Changed (after the G0-G3 spec and code review)
- Specs: silence discards commands; AC-F1-11 time counted from command send; AC-F1-12 error text and
  6 s bound; new AC-F1-15 (usage errors, the one exception to the single-stderr-line rule); control-API
  errors, simulator launch, host encoding, exit codes and `RELAY_HOST_LOG` documented; "5 runs" and
  CR-01 "toggle" wording unified.
- Simulator: `--log FILE`; `ADVANCE` rejects NaN/infinite values; no tracebacks on control-port
  disconnects; one-line error for a busy port.
- Host: `--port`/`--timeout` validated as usage errors; IPv6 hosts supported; a broken `RELAY_HOST_LOG`
  path no longer crashes the host. pyserial pinned to `<4`.

_Not yet validated: the E2E tests come in plan groups G4-G7._
