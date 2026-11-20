# Fixture reference

## `simulator` (session)
Launches `python -m relay_sim --port 0 --control-port 0 --clock manual` as a subprocess, waits (deadline,
no sleep) for the stdout line `READY serial=<port> control=<port>`, yields `SimInfo(serial_port, control_port)`.
Killed at session end. One simulator per session; isolation comes from `RESET` per test.

## `control` (function, autouse)
TCP client to the control port. Calls `reset()` before every test. Every call is logged as
`CTRL > <cmd>` / `CTRL < <reply>` in the exchange log. Raises `AssertionError` if the reply is not as expected.

| Method | Control API line |
|---|---|
| `reset()` | `RESET` |
| `set_state(s)` | `SET_STATE ON|OFF` |
| `get_state()` | `GET_STATE` -> returns `"ON"`/`"OFF"` |
| `fault(kind)` | `FAULT HW_FAULT|NONE` |
| `silence(on)` | `SILENCE ON|OFF` |
| `advance(sec)` | `ADVANCE <sec>` |

## `host` (function)
`host(command: str, *, timeout: float = 1.0, port: int | None = None) -> HostResult`
Runs `python -m relay_host --port <serial> --timeout <timeout> <command>` (same entry point as the
`relay-host` console script). The command is passed verbatim (empty string = empty line).
`HostResult`: `stdout` (stripped of trailing newline), `stderr`, `exit_code`, `duration` (seconds, wall).
The host process writes its raw `TX`/`RX`/`TIMEOUT` lines into the exchange log (env `RELAY_HOST_LOG`).

## `dead_port` (function)
Binds an ephemeral port, closes it, returns the number: nothing listens there.

## `exchange_log` (function)
Path of the per-test log file. Format: `<ISO wall time ms> <SOURCE> <DIR> <repr(payload)>`.
Attached to the test row of `reports/e2e-report.html` by the `pytest_runtest_makereport` hook.

## Helpers (`tests/e2e/helpers.py`)
- `wait_until(predicate, timeout, message)` - returns as soon as `predicate()` is truthy; fails with
  `message` at the deadline. Use instead of any sleep/poll loop.
