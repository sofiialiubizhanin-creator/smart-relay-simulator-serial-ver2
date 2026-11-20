# Smart Relay Simulator (serial-over-TCP)

A software relay that speaks a line-based text protocol over serial-over-TCP (`socket://`), and a
one-shot host CLI `relay-host` that controls it. Built spec-first: see `specs/`.

> Status: minimal program (plan groups G0-G3). The single command `python run.py` and the E2E tests come in later groups.

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
.venv\Scripts\relay-host ""               # -> ERR EMPTY (exit code 1)
```
`relay-host [--host H] [--port P] [--timeout S] COMMAND`. Exit codes: 0 `OK`/`STATUS`, 1 `ERR`/`BUSY`,
2 cannot connect or wrong usage, 3 no response within the timeout.
`relay-sim [--host H] [--port P] [--control-port P] [--clock real|manual]` prints `READY serial=<p> control=<p>`
once it is listening. The simulator logs every exchange to stderr with timestamps.

## Protocol (summary)
| Request | Reply |
|---|---|
| `ON` / `OFF` | `OK` (also when the relay is already in that state) |
| `STATUS` | `STATUS ON` / `STATUS OFF` |
| empty line / longer than 32 bytes / anything else | `ERR EMPTY` / `ERR TOO_LONG` / `ERR UNKNOWN_CMD` |
| `ON` / `OFF` during an injected hardware fault | `ERR HW_FAULT` |

Full specification: [specs/2026-11-20-f1-relay-control/requirements.md](specs/2026-11-20-f1-relay-control/requirements.md).
