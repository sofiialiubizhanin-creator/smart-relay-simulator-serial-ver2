"""Unit tests for relay_sim.clock.ManualClock."""
import pytest

from relay_sim.clock import ManualClock


@pytest.mark.parametrize("seconds", [-1.0, -0.001, -1e9])
def test_advance_rejects_negative_values(seconds):
    clock = ManualClock()
    clock.advance(5.0)

    with pytest.raises(ValueError, match="advance needs a finite value >= 0"):
        clock.advance(seconds)

    assert clock.now() == 5.0  # time is unchanged after a rejected advance
