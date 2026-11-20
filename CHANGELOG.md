# Changelog

## [Unreleased] - Phase 1: Simulator + F1 (in progress)

### Added
- Project skeleton (`pyproject.toml`, console scripts `relay-sim` and `relay-host`).
- Relay simulator (`relay_sim`): `ON` / `OFF` / `STATUS` over serial-over-TCP with error replies and error
  priority, a control API (`RESET`, `SET_STATE`, `GET_STATE`, `FAULT`, `SILENCE`, `ADVANCE`), and a real or manual clock.
- `relay-host` one-shot CLI over pyserial `socket://`, with exit codes 0/1/2/3.

_Not yet validated: the E2E tests come in plan groups G4-G7._
