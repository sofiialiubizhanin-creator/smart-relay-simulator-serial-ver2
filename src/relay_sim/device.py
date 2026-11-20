"""Relay device logic: pure, no I/O. Implements the protocol from specs/*-f1-relay-control/requirements.md
(sections 1-7 and section 8, CR-01 toggle rate limit)."""
from .clock import Clock

MAX_LINE_LEN = 32  # bytes, excluding the terminating \n
COMMANDS = (b"ON", b"OFF", b"STATUS")
TOGGLE_WINDOW_MS = 2000  # CR-01: minimum time between two toggles


class RelayDevice:
    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.reset()

    # ---- control operations (used by the control API) ----
    def reset(self) -> None:
        self.state = "OFF"
        self.hw_fault = False
        self.silent = False
        self.last_toggle_ms: int | None = None  # CR-01 rule 3: RESET clears the window
        self.clock.reset()

    def set_state(self, state: str) -> None:
        """Force the state (test setup). CR-01 rule 4: neither starts nor clears the toggle window."""
        if state not in ("ON", "OFF"):
            raise ValueError(state)
        self.state = state

    def set_fault(self, active: bool) -> None:
        self.hw_fault = active

    def set_silent(self, active: bool) -> None:
        self.silent = active

    # ---- device protocol ----
    def _now_ms(self) -> int:
        """Clock time in whole milliseconds, so e.g. 1.999 + 0.001 s is exactly 2000 ms."""
        return round(self.clock.now() * 1000)

    def handle_line(self, line: bytes, overflow: bool = False) -> bytes | None:
        """Handle one command line (without the trailing \\n).

        `overflow=True` means the line was longer than MAX_LINE_LEN and its content was discarded.
        Returns the reply line (without \\n), or None when the device is silent (line discarded, no effect).
        Error priority (requirements sections 3 and 8): silence > empty > too long > unknown > HW fault >
        toggle inside the 2 s window (BUSY).
        """
        if self.silent:
            return None
        if not overflow and line == b"":
            return b"ERR EMPTY"
        if overflow or len(line) > MAX_LINE_LEN:
            return b"ERR TOO_LONG"
        if line not in COMMANDS:
            return b"ERR UNKNOWN_CMD"
        if line == b"STATUS":
            return b"STATUS " + self.state.encode()
        if self.hw_fault:
            return b"ERR HW_FAULT"
        target = line.decode()
        if target == self.state:  # no-op: not a toggle, never BUSY, window untouched (CR-01 rule 2)
            return b"OK"
        now_ms = self._now_ms()
        if self.last_toggle_ms is not None and now_ms - self.last_toggle_ms < TOGGLE_WINDOW_MS:
            return b"BUSY"  # CR-01 rule 1: rejected, state and window unchanged
        self.state = target
        self.last_toggle_ms = now_ms
        return b"OK"
