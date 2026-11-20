"""E2E tests for F1: relay control and status.

Source: specs/2026-11-20-f1-relay-control/requirements.md section 5 (AC-F1-xx) and validation.md (how to verify).
Conventions: skill e2e-test-conventions. Every test starts from a reset simulator: state OFF, no fault, no silence, clock 0.
"""
import pytest

STATES = ["OFF", "ON"]
OPPOSITE = {"OFF": "ON", "ON": "OFF"}


# ---------- AC-F1-01 / 02: switching ----------
@pytest.mark.ac("AC-F1-01")
def test_ac_f1_01_on_from_off_replies_ok(host, control):
    control.set_state("OFF")
    r = host("ON")
    assert (r.stdout, r.exit_code) == ("OK", 0)
    assert control.get_state() == "ON"


@pytest.mark.ac("AC-F1-02")
def test_ac_f1_02_off_from_on_replies_ok(host, control):
    control.set_state("ON")
    r = host("OFF")
    assert (r.stdout, r.exit_code) == ("OK", 0)
    assert control.get_state() == "OFF"


# ---------- AC-F1-03: STATUS ----------
@pytest.mark.ac("AC-F1-03")
def test_ac_f1_03_status_off_after_startup(host, fresh_simulator):
    info, fresh_control = fresh_simulator
    r = host("STATUS", port=info.serial_port)
    assert (r.stdout, r.exit_code) == ("STATUS OFF", 0)
    assert fresh_control.get_state() == "OFF"


@pytest.mark.ac("AC-F1-03")
def test_ac_f1_03_status_off_after_reset(host, control):
    control.set_state("ON")
    control.reset()
    r = host("STATUS")
    assert (r.stdout, r.exit_code) == ("STATUS OFF", 0)
    assert control.get_state() == "OFF"


@pytest.mark.ac("AC-F1-03")
@pytest.mark.parametrize("state", STATES)
def test_ac_f1_03_status_reports_current_state(host, control, state):
    control.set_state(state)
    r = host("STATUS")
    assert (r.stdout, r.exit_code) == (f"STATUS {state}", 0)
    assert control.get_state() == state


# ---------- AC-F1-04: repeated command is a no-op ----------
@pytest.mark.ac("AC-F1-04")
@pytest.mark.parametrize("state", STATES)
def test_ac_f1_04_repeated_command_replies_ok_without_change(host, control, state):
    control.set_state(state)
    r = host(state)
    assert (r.stdout, r.exit_code) == ("OK", 0)
    assert control.get_state() == state


# ---------- AC-F1-05 .. 08: invalid lines ----------
@pytest.mark.ac("AC-F1-05")
@pytest.mark.parametrize("initial", STATES)
@pytest.mark.parametrize("cmd", ["TOGGLE", "RESET", "X"])
def test_ac_f1_05_unknown_command_rejected(host, control, cmd, initial):
    control.set_state(initial)
    r = host(cmd)
    assert (r.stdout, r.exit_code) == ("ERR UNKNOWN_CMD", 1)
    assert control.get_state() == initial


@pytest.mark.ac("AC-F1-06")
@pytest.mark.parametrize("initial", STATES)
@pytest.mark.parametrize("cmd", ["on", "off", "Off", "oN", "status"])
def test_ac_f1_06_non_uppercase_command_rejected(host, control, cmd, initial):
    control.set_state(initial)
    r = host(cmd)
    assert (r.stdout, r.exit_code) == ("ERR UNKNOWN_CMD", 1)
    assert control.get_state() == initial


@pytest.mark.ac("AC-F1-07")
@pytest.mark.parametrize("initial", STATES)
def test_ac_f1_07_empty_line_replies_err_empty(host, control, initial):
    control.set_state(initial)
    r = host("")
    assert r.sent, "the empty line must reach the device (not become a usage error)"
    assert (r.stdout, r.exit_code) == ("ERR EMPTY", 1)
    assert control.get_state() == initial


@pytest.mark.ac("AC-F1-08")
@pytest.mark.parametrize("initial", STATES)
@pytest.mark.parametrize("cmd", [" ON", "ON ", "O N", "ON\t", "ON\r", "   "],
                         ids=["leading-space", "trailing-space", "inner-space", "tab", "cr", "only-spaces"])
def test_ac_f1_08_whitespace_or_extra_char_rejected(host, control, cmd, initial):
    control.set_state(initial)
    r = host(cmd)
    assert (r.stdout, r.exit_code) == ("ERR UNKNOWN_CMD", 1)
    assert control.get_state() == initial


# ---------- AC-F1-09: length limit and error priority ----------
@pytest.mark.ac("AC-F1-09")
@pytest.mark.parametrize("initial", STATES)
@pytest.mark.parametrize("cmd, expected", [
    ("A" * 32, "ERR UNKNOWN_CMD"),
    ("A" * 33, "ERR TOO_LONG"),
    ("A" * 31 + "\r", "ERR UNKNOWN_CMD"),
    ("A" * 32 + "\r", "ERR TOO_LONG"),
    ("o" * 33, "ERR TOO_LONG"),
    ("ON" + " " * 31, "ERR TOO_LONG"),
], ids=["32B-unknown", "33B", "32B-with-cr", "33B-with-cr", "33B-lowercase", "33B-whitespace"])
def test_ac_f1_09_length_limit(host, control, cmd, expected, initial):
    control.set_state(initial)
    r = host(cmd)
    assert (r.stdout, r.exit_code) == (expected, 1)
    assert control.get_state() == initial


# ---------- AC-F1-10: hardware fault, priority, recovery ----------
@pytest.mark.ac("AC-F1-10")
@pytest.mark.parametrize("initial", STATES)
@pytest.mark.parametrize("cmd", ["ON", "OFF"])
def test_ac_f1_10_hw_fault_blocks_on_off(host, control, cmd, initial):
    """Includes the command for the current state: the fault wins over "already in that state"."""
    control.set_state(initial)
    control.fault("HW_FAULT")
    r = host(cmd)
    assert (r.stdout, r.exit_code) == ("ERR HW_FAULT", 1)
    assert control.get_state() == initial


@pytest.mark.ac("AC-F1-10")
@pytest.mark.parametrize("state", STATES)
def test_ac_f1_10_hw_fault_status_still_works(host, control, state):
    control.set_state(state)
    control.fault("HW_FAULT")
    r = host("STATUS")
    assert (r.stdout, r.exit_code) == (f"STATUS {state}", 0)
    assert control.get_state() == state


@pytest.mark.ac("AC-F1-10")
@pytest.mark.parametrize("initial", STATES)
@pytest.mark.parametrize("cmd, expected", [
    ("on", "ERR UNKNOWN_CMD"), ("", "ERR EMPTY"), ("A" * 33, "ERR TOO_LONG"),
], ids=["lowercase", "empty", "33B"])
def test_ac_f1_10_hw_fault_invalid_line_keeps_own_error(host, control, cmd, expected, initial):
    control.set_state(initial)
    control.fault("HW_FAULT")
    r = host(cmd)
    assert (r.stdout, r.exit_code) == (expected, 1)
    assert control.get_state() == initial


@pytest.mark.ac("AC-F1-10")
@pytest.mark.parametrize("initial", STATES)
def test_ac_f1_10_recovers_after_fault_cleared(host, control, initial):
    target = OPPOSITE[initial]
    control.set_state(initial)
    control.fault("HW_FAULT")
    assert host(target).stdout == "ERR HW_FAULT"
    control.fault("NONE")
    r = host(target)
    assert (r.stdout, r.exit_code) == ("OK", 0)
    assert control.get_state() == target


# ---------- AC-F1-11: silent device ----------
@pytest.mark.ac("AC-F1-11")
def test_ac_f1_11_silent_device_times_out_and_discards_command(host, control):
    control.set_state("OFF")
    control.silence(True)
    r = host("ON", timeout=0.5)
    assert (r.stdout, r.exit_code) == ("", 3)
    assert r.stderr == "ERROR: no response from device within 0.5s"
    # Bound counted from the command send (host log TX -> TIMEOUT), as the AC states; not r.duration.
    assert r.sent and r.send_to_end is not None
    assert r.send_to_end <= 0.5 + 0.5, f"TX -> TIMEOUT took {r.send_to_end:.3f}s"
    assert control.get_state() == "OFF", "a command sent to a silent device must be discarded"


@pytest.mark.ac("AC-F1-11")
def test_ac_f1_11_recovers_after_silence_off(host, control):
    control.silence(True)
    assert host("STATUS", timeout=0.5).exit_code == 3
    control.silence(False)
    r = host("STATUS")
    assert (r.stdout, r.exit_code) == ("STATUS OFF", 0)


# ---------- AC-F1-12: simulator unreachable ----------
@pytest.mark.ac("AC-F1-12")
def test_ac_f1_12_unreachable_device_connection_error(host, dead_port):
    r = host("STATUS", port=dead_port)
    assert (r.stdout, r.exit_code) == ("", 2)
    assert r.stderr.startswith("ERROR: cannot connect"), r.stderr
    assert r.duration < 6, f"host took {r.duration:.3f}s"


# ---------- AC-F1-13: state persists across connections ----------
@pytest.mark.ac("AC-F1-13")
def test_ac_f1_13_state_persists_across_host_calls(host, control):
    assert host("ON").stdout == "OK"
    assert host("STATUS").stdout == "STATUS ON"
    assert host("OFF").stdout == "OK"
    assert host("STATUS").stdout == "STATUS OFF"
    assert control.get_state() == "OFF"


# ---------- AC-F1-14: quick sequence (expected to be affected by CR-01) ----------
@pytest.mark.ac("AC-F1-14")
def test_ac_f1_14_quick_sequence_without_clock_advance(host, control):
    replies = [host(cmd).stdout for cmd in ("ON", "OFF", "ON", "STATUS")]
    assert replies == ["OK", "OK", "OK", "STATUS ON"]
    assert control.get_state() == "ON"


# ---------- AC-F1-15: usage error sends nothing ----------
@pytest.mark.ac("AC-F1-15")
@pytest.mark.parametrize("kwargs", [
    {"command": None}, {"command": "ON", "port": 70000}, {"command": "ON", "timeout": 0},
], ids=["no-command", "port-out-of-range", "timeout-zero"])
def test_ac_f1_15_usage_error_sends_nothing(host, control, kwargs):
    command = kwargs.pop("command")
    r = host(command, **kwargs)
    assert (r.stdout, r.exit_code) == ("", 2)
    lines = r.stderr.splitlines()
    assert len(lines) == 2 and lines[0].startswith("usage:") and lines[1].startswith("ERROR:"), r.stderr
    assert not r.sent, "a usage error must not send anything to the device"
    assert control.get_state() == "OFF"


# ---------- AC-F1-16: silence wins over HW fault (error priority rule 1 before rule 5) ----------
@pytest.mark.ac("AC-F1-16")
def test_ac_f1_16_silence_wins_over_hw_fault(host, control):
    control.set_state("OFF")
    control.fault("HW_FAULT")
    control.silence(True)
    r = host("ON", timeout=0.5)
    assert (r.stdout, r.exit_code) == ("", 3)
    assert control.get_state() == "OFF"
    control.silence(False)
    r = host("ON")
    assert (r.stdout, r.exit_code) == ("ERR HW_FAULT", 1)
    assert control.get_state() == "OFF"
