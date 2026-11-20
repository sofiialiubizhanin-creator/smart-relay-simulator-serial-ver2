"""Clocks for the simulator: real (monotonic wall time) or manual (moved only by the control API)."""
import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float: ...
    def reset(self) -> None: ...


class RealClock:
    """Monotonic wall time. Cannot be advanced or reset."""

    def now(self) -> float:
        return time.monotonic()

    def reset(self) -> None:
        pass


class ManualClock:
    """Simulated time: starts at 0.0 and moves only via advance()."""

    def __init__(self) -> None:
        self._now = 0.0

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("cannot advance by a negative amount")
        self._now += seconds

    def reset(self) -> None:
        self._now = 0.0
