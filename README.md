# Smart Relay Simulator (serial-over-TCP)

A software relay that speaks a line-based text protocol over serial-over-TCP (`socket://`), and a
one-shot host CLI `relay-host` that controls it. Built spec-first: see `specs/`.

## Run everything with one command
```
python run.py
```
Needs only Python 3.11+. This one command:
1. creates `.venv` and installs the project with its test dependencies (skipped when already up to date);
2. runs the E2E suite **5 times in a row** (the flakiness gate);
3. writes `reports/e2e-report.html` (the last run, with an AC column and a timestamped host <-> simulator exchange
   log for each test), `reports/runs/` (every run, plus the simulator log) and `reports/e2e-runs.md` (summary).

The exit code is 0 only if all 5 runs pass. Options: `python run.py --runs 1`, `python run.py -- -k f1_07`
(arguments after `--` go to pytest), `python run.py -- --reverse` (reverse order).

### View the results
```
Get-Content reports\e2e-runs.md           # summary table of the 5 runs (Linux/macOS: cat reports/e2e-runs.md)
start reports\e2e-report.html             # HTML report of the last run (Linux: xdg-open, macOS: open)
```
In the HTML report the **AC** column shows which acceptance criterion each test covers; click a test row to see
its timestamped exchange log (`CTRL` = control API, `TEST`/`HOST TX`/`HOST RX` = host calls).

## Try it by hand
Terminal 1 starts the simulator (real clock); stop it with **Ctrl+C**:
```
python run.py demo                        # waits for: READY serial=5000 control=5001
```
Terminal 2 (Linux/macOS: `.venv/bin/relay-host`):
```
.venv\Scripts\relay-host ON               # -> OK
.venv\Scripts\relay-host STATUS           # -> STATUS ON
.venv\Scripts\relay-host on               # -> ERR UNKNOWN_CMD (exit code 1)
.venv\Scripts\relay-host " ON"            # -> ERR UNKNOWN_CMD (exit code 1)
.venv\Scripts\relay-host --% ""           # -> ERR EMPTY (exit code 1); in cmd.exe/bash: relay-host ""
.venv\Scripts\relay-host OFF              # -> BUSY (exit code 1) if within 2 s of the last toggle (CR-01)
# wait at least 2 s, then:
.venv\Scripts\relay-host OFF              # -> OK
```
`$LASTEXITCODE` (PowerShell) or `echo $?` (bash) shows the exit code of the last command.
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
| `ON` / `OFF` that would toggle less than 2 s after the previous toggle (CR-01) | `BUSY` (exit code 1) |

Full specification: [specs/2026-11-20-f1-relay-control/requirements.md](specs/2026-11-20-f1-relay-control/requirements.md).

## Project layout
```
specs/                              constitution (mission, roadmap, tech-stack) + one folder per feature
  2026-11-20-f1-relay-control/      requirements.md -> plan.md -> validation.md (CR-01: section 8 "Changes")
src/relay_sim/                      simulator: device logic, clocks, serial + control-API TCP servers
src/relay_host/                     relay-host CLI (pyserial socket://)
tests/e2e/                          E2E fixtures (conftest.py, helpers.py) and tests
.claude/skills/e2e-test-conventions/  skill used for all E2E test work (SKILL.md, references, scripts, evals)
reports/                            e2e-runs.md (latest run.py summary), regression-cr01.md (+ .html: CR-01
                                    regression run), skill-evals.md (skill evals v1 -> v2)
run.py                              the one command
```
