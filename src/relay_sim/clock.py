"""Clocks for the simulator: real (monotonic wall time) or manual (moved only by the control API)."""
import math
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
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError(f"advance needs a finite value >= 0, got {seconds}")
        self._now += seconds

    def reset(self) -> None:
        self._now = 0.0
