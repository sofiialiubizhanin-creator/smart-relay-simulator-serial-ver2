# Fixture reference

## `simulator` (session)
Launches `python -m relay_sim --port 0 --control-port 0 --clock manual --log reports/runs/simulator.log`
as a subprocess, waits (deadline, no sleep) for the stdout line `READY serial=<port> control=<port>`, yields
`SimInfo(serial_port, control_port)`. Killed at session end. One simulator per session; isolation comes from
`RESET` per test.

## `fresh_simulator` (function)
Starts a separate simulator for one test and yields `(SimInfo, ControlClient)` without sending `RESET`, so
the state is exactly the startup state. Use with `host(cmd, port=info.serial_port)`. Only for "after
startup" ACs (it costs ~0.3 s); everything else uses the shared `simulator`.

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
`host(command: str | None, *, timeout: float = 1.0, port: int | None = None) -> HostResult`
Runs `python -m relay_host --port <serial> --timeout <timeout> -- <command>` (same entry point as the
`relay-host` console script). The command is passed verbatim without a shell (empty string = empty line);
`command=None` omits it (usage error, AC-F1-15). `port`/`timeout` may be invalid on purpose (usage errors).

| `HostResult` field | Meaning |
|---|---|
| `stdout` | reply line, trailing newline stripped |
| `stderr` | stripped stderr (usage errors: usage line + `ERROR:` line) |
| `exit_code` | 0 OK/STATUS, 1 other reply, 2 connection/usage error, 3 timeout |
| `duration` | wall seconds from process start to exit - **includes Python start-up**, not for AC timing bounds |
| `sent` | `True` if the host logged a `TX` line (something reached the device) |
| `send_to_end` | seconds from the host's `TX` to its `RX`/`TIMEOUT`/`ERROR` (host log) - use for "from the command send" bounds |

The host process writes its raw `TX`/`RX`/`TIMEOUT`/`ERROR` lines into the exchange log (env `RELAY_HOST_LOG`).

## `dead_port` (function)
Binds an ephemeral port, closes it, returns the number: nothing listens there.

## `exchange_log` (function)
Path of the per-test log file. Format: `<ISO wall time ms> <SOURCE> <DIR> <repr(payload)>`.
Attached to the test row of `reports/e2e-report.html` by the `pytest_runtest_makereport` hook.

## Helpers (`tests/e2e/helpers.py`)
- `wait_until(predicate, timeout, message)` - returns as soon as `predicate()` is truthy; fails with
  `message` at the deadline. Use instead of any sleep/poll loop.
