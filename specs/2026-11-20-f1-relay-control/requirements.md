# F1: Relay control and status: requirements

Status: approved 2026-11-20 (review fixes applied 2026-11-20) | Phase 1

## 1. Scope
- The relay simulator: what it models, its states and its control API.
- The line protocol for the commands `ON`, `OFF` and `STATUS` and its error responses.
- The `relay-host` one-shot CLI: sending a command, printing the reply, exit codes, and how it handles timeouts and connection failures.

## 2. Simulator

### 2.1 What it models
- A single relay with state `OFF` or `ON`. The state is `OFF` at startup and after `RESET`.
- A serial port exposed as a TCP server (serial-over-TCP). Each host call opens a new connection.
  **Relay state is kept across connections.**
- A hardware fault (`HW_FAULT`): the relay cannot switch.
- Silence (simulates a hung device): the device reads command lines but **discards** them: no reply
  and no state change.
- A clock: `real` (monotonic wall time) for manual use, or `manual` for tests. A manual clock starts at
  0 and moves only on `ADVANCE`. F1 has no time-dependent behavior; the clock exists for CR-01.
- An exchange log: every received line and every reply, with a timestamp (ms), to stderr or to a file.

### 2.2 What it does not model
Electrical behavior, contact bounce, baud rate, parity, framing, flow control, noise or partial bytes,
keeping state after a simulator restart, several relays or channels, several clients at the same time,
and authentication.

### 2.3 Control API (tests only, separate TCP port)
Line-based text protocol, ASCII, each line ends with `\n`; leading/trailing whitespace is ignored.
Every command replies `OK` unless stated otherwise. An invalid command or argument has no effect and
replies `ERR UNKNOWN_CONTROL_CMD`, `ERR BAD_ARG` (e.g. `ADVANCE` with a negative, NaN or infinite value)
or `ERR NOT_MANUAL_CLOCK` (`ADVANCE` on a real clock).

| Command | Effect |
|---|---|
| `RESET` | State `OFF`, faults and silence cleared, manual clock back to 0 |
| `SET_STATE ON` / `SET_STATE OFF` | Forces the relay state (a "set a value" operation; does not count as a toggle) |
| `FAULT HW_FAULT` / `FAULT NONE` | Turns the hardware fault on or off |
| `SILENCE ON` / `SILENCE OFF` | Turns the "device not responding" mode on or off |
| `ADVANCE <seconds>` | Moves the manual clock forward (finite decimal number, >= 0) |
| `GET_STATE` | Replies `STATE ON` or `STATE OFF` |

### 2.4 Launch
`relay-sim [--host H] [--port P] [--control-port P] [--clock real|manual] [--log FILE]`.
Defaults: `localhost` (listens on both 127.0.0.1 and ::1), `5000`, `5001`, `real`, log to stderr.
Port `0` picks a free port. Once both ports listen, it prints `READY serial=<p> control=<p>` to stdout.
If a port cannot be opened, it prints one `ERROR:` line to stderr and exits with code 1.

## 3. Device protocol
- ASCII. A command is one line ending with `\n`. A response is one line ending with `\n`.
- The line is matched **exactly**: commands are uppercase only, with no leading, trailing or inner
  whitespace and no other characters (`\r` counts as an extra character).
- The maximum command length is 32 bytes. The length is everything before the terminating `\n`, which
  is not counted. Every other byte counts, including `\r`, spaces and tabs (`"ON\r"` is 3 bytes).
- Exactly one response for each command line (except in silence mode).
- **Error priority.** When a line breaks several rules, only the first matching rule applies:
  1. Silence mode active: the line is discarded (no response, no state change).
  2. Empty line: `ERR EMPTY`.
  3. Longer than 32 bytes: `ERR TOO_LONG` (the content is not checked).
  4. Not an exact command (lowercase, whitespace, unknown): `ERR UNKNOWN_CMD`.
  5. A valid `ON` or `OFF` while `HW_FAULT` is active: `ERR HW_FAULT`. `STATUS` is never affected.

| Request | Response | Effect |
|---|---|---|
| `ON` | `OK` | State becomes `ON` (if it is already `ON`: no change) |
| `OFF` | `OK` | State becomes `OFF` (if it is already `OFF`: no change) |
| `STATUS` | `STATUS ON` / `STATUS OFF` | None |
| empty line | `ERR EMPTY` | None |
| longer than 32 bytes | `ERR TOO_LONG` | None |
| any other line (lowercase, whitespace, unknown) | `ERR UNKNOWN_CMD` | None |
| `ON` / `OFF` while `HW_FAULT` is active | `ERR HW_FAULT` | None |

## 4. Host CLI `relay-host`
- Usage: `relay-host [--host H] [--port P] [--timeout S] COMMAND`. Defaults: `localhost`, `5000`, `1.0` s.
  `--port` must be 1-65535 and `--timeout` > 0; IPv6 addresses (e.g. `::1`) are accepted for `--host`.
- The host is a thin transport. It sends `COMMAND` (UTF-8) + `\n` **exactly as given** and does not
  check the command, so device errors are visible through the host. `relay-host ""` sends an empty line
  (some shells, e.g. Windows PowerShell 5.1, drop an empty argument; that call is then a usage error).
- It prints the response line (without `\n`) to stdout.
- Exit codes: `0` = `OK` or `STATUS ...`; `1` = any other reply (`ERR ...`, or `BUSY` reserved for CR-01);
  `2` = cannot connect, connection closed before a reply, or wrong CLI usage; `3` = no response within `--timeout`.
- On exit code 2 or 3 it prints a single error line to stderr:
  `ERROR: cannot connect to device: <reason>`, `ERROR: connection lost: <reason>` or
  `ERROR: no response from device within <timeout>s`.
  **Exception (usage errors):** when `COMMAND` is missing or an option is invalid, nothing is sent and
  stderr gets the usage line followed by one `ERROR: <reason>` line; exit code 2.
- Test support: if the environment variable `RELAY_HOST_LOG` is set, the host appends timestamped (ms)
  `HOST TX/RX/TIMEOUT/ERROR` lines to that file. A logging failure never changes the output or exit code.

## 5. Acceptance Criteria

| ID | Given / When / Then |
|---|---|
| AC-F1-01 | Given the relay is `OFF`, when the host sends `ON`, then the reply is `OK`, the exit code is 0 and the state is `ON`. |
| AC-F1-02 | Given the relay is `ON`, when the host sends `OFF`, then the reply is `OK`, the exit code is 0 and the state is `OFF`. |
| AC-F1-03 | When the host sends `STATUS`, the reply is `STATUS ON` or `STATUS OFF` matching the current state (`STATUS OFF` after startup or reset), the exit code is 0, and the state is unchanged. |
| AC-F1-04 | Sending `ON` while already `ON`, or `OFF` while already `OFF`, replies `OK` with exit code 0, and the state is unchanged. |
| AC-F1-05 | An unknown command (for example `TOGGLE`) replies `ERR UNKNOWN_CMD` with exit code 1, and the state is unchanged. |
| AC-F1-06 | A lowercase or mixed-case command (`on`, `Off`, `status`) replies `ERR UNKNOWN_CMD` with exit code 1, and the state is unchanged. |
| AC-F1-07 | An empty line replies `ERR EMPTY` with exit code 1, and the state is unchanged. |
| AC-F1-08 | A command with any whitespace or extra character (`" ON"`, `"ON "`, `"O N"`, `"ON\t"`, `"ON\r"`, `"   "`) replies `ERR UNKNOWN_CMD` with exit code 1, and the state is unchanged. |
| AC-F1-09 | A command longer than 32 bytes replies `ERR TOO_LONG` with exit code 1; a 32-byte unknown command still replies `ERR UNKNOWN_CMD`. A 33-byte lowercase or whitespace-containing command replies `ERR TOO_LONG` (length is checked before content). |
| AC-F1-10 | Given `HW_FAULT` is active, `ON` and `OFF` reply `ERR HW_FAULT` with exit code 1 and the state is unchanged (also when the relay is already in the requested state), while `STATUS` still works. Invalid lines (for example `on`, empty) still get their own error (`ERR UNKNOWN_CMD`, `ERR EMPTY`), not `ERR HW_FAULT`. After `FAULT NONE`, commands work normally again. |
| AC-F1-11 | Given the device is silent, a command gets no reply and does not change the state; the host exits with code 3 and `ERROR: no response from device within <timeout>s` on stderr, no later than `--timeout` + 0.5 s **counted from the moment the host sent the command** (host exchange log timestamps). After `SILENCE OFF`, commands work normally again. |
| AC-F1-12 | Given no simulator is listening on the target port, the host exits with code 2 and stderr starts with `ERROR: cannot connect`. |
| AC-F1-13 | The state stays the same across separate host calls: `ON` in one call, then `STATUS` in another, replies `STATUS ON`. |
| AC-F1-14 | A quick sequence of four separate host calls with no clock advance, `ON`, `OFF`, `ON`, `STATUS`, replies `OK`, `OK`, `OK`, `STATUS ON`. *(Expected to be affected by CR-01.)* |
| AC-F1-15 | A usage error (`COMMAND` missing, `--port` outside 1-65535, or `--timeout` <= 0) exits with code 2, prints the usage line plus one `ERROR:` line on stderr, and sends nothing to the device. |
| AC-F1-16 | Given both `HW_FAULT` and silence are active, silence wins (error priority rule 1): `ON` gets no reply, the host exits with code 3 and the state is unchanged. After `SILENCE OFF` the fault is still active: `ON` replies `ERR HW_FAULT` with exit code 1. |

## 6. Edge cases (where each is covered)
- Repeated `ON` or `OFF` (AC-F1-04). Commands right after a reset (AC-F1-03).
- A line of only spaces is not empty: it replies `ERR UNKNOWN_CMD` (AC-F1-08).
- The length limit at exactly 32 and at 33 bytes; `\r` and whitespace count toward the length (AC-F1-09).
- A line that breaks several rules follows the error priority in section 3 (AC-F1-09, AC-F1-10, AC-F1-16).
- `HW_FAULT` together with repeated commands: a fault always wins over "already in that state" (AC-F1-10).
- A silent device does not leave the host hanging, and a command sent to it is discarded (AC-F1-11).
  The simulator is down (AC-F1-12). Wrong host usage sends nothing (AC-F1-15).

## 7. Out of scope
Persistent configuration, several relays, concurrent clients, an interactive host shell, non-ASCII or
binary payloads beyond rejecting them, security, and real serial hardware.

## 8. Changes

### CR-01: Toggle rate limit (Phase 2)
Status: approved 2026-11-20 | Source: change request "relay can't be toggled faster than
every 2 s; a second toggle within 2 s returns `BUSY`; tests use controlled simulator time".
Sections 1-7 above are kept as written; this section adds rules and states which of their items it supersedes.

**Definitions**
- **Toggle:** an `ON` or `OFF` that is accepted and **changes** the relay state (`OFF -> ON` or `ON -> OFF`).
- **Window:** the 2.000 s after the last toggle, measured on the simulator clock (manual clock in tests,
  monotonic wall time in `real` mode) and compared in whole milliseconds.

**Rules**
1. A toggle requested less than 2.000 s after the previous toggle is rejected: reply `BUSY`, state unchanged,
   host exit code 1. At 2.000 s or later it is accepted (`OK`).
2. These never get `BUSY` and never start or restart the window: `STATUS`; `ON` while `ON` / `OFF` while `OFF`
   (still `OK`, no change); any rejected command (`BUSY`, `ERR ...`).
3. The first toggle after startup or `RESET` is always allowed; `RESET` clears the window.
4. `SET_STATE` (control API) neither starts nor clears the window.
5. Error priority (section 3) gets rule 6 after `ERR HW_FAULT`: a toggle inside the window -> `BUSY`.
   Silence, empty, too long, unknown and `HW_FAULT` keep priority over `BUSY`.

**Supersedes in sections 1-7**
- Section 2.1 "F1 has no time-dependent behavior": the clock now drives the window.
- Section 3: the table gains the row "`ON`/`OFF` that would toggle inside the window -> `BUSY`, no effect".
- Section 4: `BUSY` is no longer "reserved"; it is the reply of rule 1 (exit code 1, as already defined).
- **AC-F1-14** (new expectation): the quick sequence `ON`, `OFF`, `ON`, `STATUS` with no clock advance
  replies `OK`, `BUSY`, `OK`, `STATUS ON` (the second call is a toggle 0 s after the first; the third is a
  no-op because the relay is still `ON`); final state `ON`.
- Any other F1 AC whose test toggles twice within 2 s is listed by the regression run
  (`reports/regression-cr01.md`) and updated here before its test is changed.

**New acceptance criteria**

| ID | Given / When / Then |
|---|---|
| AC-F1-17 | Given a toggle at clock t, a toggle at t + 0 s and at t + 1.999 s replies `BUSY` with exit code 1, and the state is unchanged. |
| AC-F1-18 | Given a toggle at clock t, a toggle at exactly t + 2.000 s, or later, replies `OK` with exit code 0 and the state changes. |
| AC-F1-19 | A `BUSY` reply does not restart the window: toggle at t, `BUSY` at t + 1.5 s, then a toggle at t + 2.0 s replies `OK`. |
| AC-F1-20 | Inside the window, `STATUS` and a no-op `ON`/`OFF` reply as in F1 (`STATUS ...` / `OK`, exit 0) and do not restart the window: a toggle at t + 2.0 s replies `OK`. |
| AC-F1-21 | The first toggle after `RESET` is allowed even if a toggle happened less than 2 s before the reset; `SET_STATE` does not start a window (a toggle right after it replies `OK`). |
| AC-F1-22 | Priority: with `HW_FAULT` active inside the window, a toggle replies `ERR HW_FAULT`; invalid lines keep their own errors (`ERR EMPTY`, `ERR TOO_LONG`, `ERR UNKNOWN_CMD`), never `BUSY`. |

**Edge cases:** the boundary pair 1.999 s / 2.000 s (AC-F1-17/18); a window reached in several `ADVANCE`
steps (AC-F1-18); both directions `OFF -> ON` and `ON -> OFF` (AC-F1-17/18).
