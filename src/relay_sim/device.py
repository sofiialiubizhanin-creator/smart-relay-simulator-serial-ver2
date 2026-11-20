"""Relay device logic: pure, no I/O. Implements the protocol from specs/*-f1-relay-control/requirements.md."""
from .clock import Clock

MAX_LINE_LEN = 32  # bytes, excluding the terminating \n
COMMANDS = (b"ON", b"OFF", b"STATUS")


class RelayDevice:
    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.reset()

    # ---- control operations (used by the control API) ----
    def reset(self) -> None:
        self.state = "OFF"
        self.hw_fault = False
        self.silent = False
        self.clock.reset()

    def set_state(self, state: str) -> None:
        if state not in ("ON", "OFF"):
            raise ValueError(state)
        self.state = state

    def set_fault(self, active: bool) -> None:
        self.hw_fault = active

    def set_silent(self, active: bool) -> None:
        self.silent = active

    # ---- device protocol ----
    def handle_line(self, line: bytes, overflow: bool = False) -> bytes | None:
        """Handle one command line (without the trailing \\n).

        `overflow=True` means the line was longer than MAX_LINE_LEN and its content was discarded.
        Returns the reply line (without \\n), or None when the device is silent (line discarded, no effect).
        Error priority (requirements section 3): silence > empty > too long > unknown > HW fault.
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
        self.state = line.decode()
        return b"OK"
