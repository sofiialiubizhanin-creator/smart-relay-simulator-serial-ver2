# F1: Relay control and status: requirements

Status: draft for review | Phase 1 | Date: 2026-11-20

## 1. Scope
- The relay simulator: what it models, its states and its control API.
- The line protocol for the commands `ON`, `OFF` and `STATUS` and its error responses.
- The `relay-host` one-shot CLI: sending a command, printing the reply, exit codes, and how it handles timeouts and connection failures.

## 2. Simulator

### 2.1 What it models
- A single relay with state `OFF` or `ON`. The state is `OFF` at startup and after `RESET`.
- A serial port exposed as a TCP server (serial-over-TCP). One client at a time; each host call opens a
  new connection. **Relay state is kept across connections.**
- A hardware fault (`HW_FAULT`): the relay cannot switch.
- Silence: the device receives commands but never replies (simulates a hung device).
- A clock: `real` (monotonic wall time) for manual use, or `manual` for tests. A manual clock starts at
  0 and moves only on `ADVANCE`. F1 has no time-dependent behavior; the clock exists for CR-01.

### 2.2 What it does not model
Electrical behavior, contact bounce, baud rate, parity, framing, flow control, noise or partial bytes,
keeping state after a simulator restart, several relays or channels, several clients at the same time,
and authentication.

### 2.3 Control API (tests only, separate TCP port)
Line-based text protocol, ASCII, each line ends with `\n`. Every command replies `OK` unless stated otherwise.

| Command | Effect |
|---|---|
| `RESET` | State `OFF`, faults and silence cleared, manual clock back to 0 |
| `SET_STATE ON` / `SET_STATE OFF` | Forces the relay state (a "set a value" operation; does not count as a toggle) |
| `FAULT HW_FAULT` / `FAULT NONE` | Turns the hardware fault on or off |
| `SILENCE ON` / `SILENCE OFF` | Turns the "device not responding" mode on or off |
| `ADVANCE <seconds>` | Moves the manual clock forward (decimal number, >= 0) |
| `GET_STATE` | Replies `STATE ON` or `STATE OFF` |

## 3. Device protocol
- ASCII. A command is one line ending with `\n`. A response is one line ending with `\n`.
- The line is matched **exactly**: commands are uppercase only, with no leading, trailing or inner
  whitespace and no other characters (`\r` counts as an extra character).
- The maximum command length is 32 bytes. The length is everything before the terminating `\n`, which
  is not counted. Every other byte counts, including `\r`, spaces and tabs (`"ON\r"` is 3 bytes).
- Exactly one response for each command line (except in silence mode).
- **Error priority.** When a line breaks several rules, only the first matching rule applies:
  1. Silence mode active: no response at all.
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
- The host is a thin transport. It sends `COMMAND` + `\n` **exactly as given** and does not check the
  command, so device errors are visible through the host. `relay-host ""` sends an empty line.
- It prints the response line (without `\n`) to stdout.
- Exit codes: `0` = `OK` or `STATUS ...`; `1` = device replied `ERR ...` or `BUSY`;
  `2` = cannot connect, or wrong CLI usage; `3` = no response within `--timeout`.
- On exit code 2 or 3 it prints a single error line to stderr, for example `ERROR: no response from device within 1.0s`.

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
| AC-F1-08 | A command with any whitespace or extra character (`" ON"`, `"ON "`, `"O N"`, `"ON\t"`) replies `ERR UNKNOWN_CMD` with exit code 1, and the state is unchanged. |
| AC-F1-09 | A command longer than 32 bytes replies `ERR TOO_LONG` with exit code 1; a 32-byte unknown command still replies `ERR UNKNOWN_CMD`. A 33-byte lowercase or whitespace-containing command replies `ERR TOO_LONG` (length is checked before content). |
| AC-F1-10 | Given `HW_FAULT` is active, `ON` and `OFF` reply `ERR HW_FAULT` with exit code 1 and the state is unchanged, while `STATUS` still works. Invalid lines (for example `on`, empty) still get their own error (`ERR UNKNOWN_CMD`, `ERR EMPTY`), not `ERR HW_FAULT`. After `FAULT NONE`, commands work normally again. |
| AC-F1-11 | Given the device is silent, the host exits with code 3 and a timeout error on stderr no later than `--timeout` + 0.5 s. After `SILENCE OFF`, commands work normally again. |
| AC-F1-12 | Given no simulator is listening on the target port, the host exits with code 2 and a connection error on stderr. |
| AC-F1-13 | The state stays the same across separate host calls: `ON` in one call, then `STATUS` in another, replies `STATUS ON`. |
| AC-F1-14 | A quick sequence with no clock advance, `ON`, `OFF`, `ON`, `STATUS`, replies `OK`, `OK`, `OK`, `STATUS ON`. *(Expected to be affected by CR-01.)* |

## 6. Edge cases (where each is covered)
- Repeated `ON` or `OFF` (AC-F1-04). Commands right after a reset (AC-F1-03).
- A line of only spaces is not empty: it replies `ERR UNKNOWN_CMD` (AC-F1-08).
- The length limit at exactly 32 and at 33 bytes; `\r` and whitespace count toward the length (AC-F1-09).
- A line that breaks several rules follows the error priority in section 3 (AC-F1-09, AC-F1-10).
- `HW_FAULT` together with repeated commands: a fault always wins over "already in that state" (AC-F1-10).
- A silent device does not leave the host hanging (AC-F1-11). The simulator is down (AC-F1-12).

## 7. Out of scope
Persistent configuration, several relays, concurrent clients, an interactive host shell, non-ASCII or
binary payloads beyond rejecting them, security, and real serial hardware.
