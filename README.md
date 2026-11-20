# Smart Relay Simulator (serial-over-TCP)

A software relay that speaks a line-based text protocol over serial-over-TCP (`socket://`), and a
one-shot host CLI `relay-host` that controls it. Built spec-first: see `specs/`.

> Status: minimal program (plan groups G0-G3) and the E2E test framework (G4, `tests/e2e/`). The test cases
> and the single command `python run.py` come in later groups.

## Setup (once)
```
python -m venv .venv
.venv\Scripts\python -m pip install -e .          # Linux/macOS: .venv/bin/python -m pip install -e .
```

## Run
```
.venv\Scripts\relay-sim                   # terminal 1: simulator, serial port 5000, control API 5001
.venv\Scripts\relay-host ON               # terminal 2 -> OK
.venv\Scripts\relay-host STATUS           # -> STATUS ON
.venv\Scripts\relay-host on               # -> ERR UNKNOWN_CMD (exit code 1)
.venv\Scripts\relay-host ""               # -> ERR EMPTY (exit code 1), see the PowerShell note below
```
`relay-host [--host H] [--port P] [--timeout S] COMMAND`. Exit codes: 0 `OK`/`STATUS`, 1 any other reply
(`ERR ...`), 2 cannot connect or wrong usage, 3 no response within the timeout.

`relay-sim [--host H] [--port P] [--control-port P] [--clock real|manual] [--log FILE]` prints
`READY serial=<p> control=<p>` once it is listening. `localhost` (default) listens on 127.0.0.1 and ::1.
Every exchange is logged with timestamps to stderr, or to `--log FILE`.

**Windows PowerShell 5.1:** it drops an empty `""` argument, so `relay-host ""` becomes a usage error.
Send an empty line with ``relay-host `"`"`` or `relay-host --% ""` (cmd.exe, bash and PowerShell 7.3+ pass `""` as is).

**Control API** (for tests, port 5001): `RESET`, `SET_STATE ON|OFF`, `GET_STATE`, `FAULT HW_FAULT|NONE`,
`SILENCE ON|OFF`, `ADVANCE <seconds>` (manual clock only). See requirements section 2.3.

## Protocol (summary)
| Request | Reply |
|---|---|
| `ON` / `OFF` | `OK` (also when the relay is already in that state) |
| `STATUS` | `STATUS ON` / `STATUS OFF` |
| empty line / longer than 32 bytes / anything else | `ERR EMPTY` / `ERR TOO_LONG` / `ERR UNKNOWN_CMD` |
| `ON` / `OFF` during an injected hardware fault | `ERR HW_FAULT` |

Full specification: [specs/2026-11-20-f1-relay-control/requirements.md](specs/2026-11-20-f1-relay-control/requirements.md).
