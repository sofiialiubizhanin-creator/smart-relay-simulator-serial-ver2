# Test patterns

## Positive command
```python
@pytest.mark.ac("AC-F1-01")
def test_ac_f1_01_on_from_off_replies_ok(host, control):
    control.set_state("OFF")
    r = host("ON")
    assert (r.stdout, r.exit_code) == ("OK", 0)
    assert control.get_state() == "ON"
```

## Negative: error reply and state unchanged (parametrize inputs)
```python
@pytest.mark.ac("AC-F1-06")
@pytest.mark.parametrize("cmd", ["on", "Off", "status"])
@pytest.mark.parametrize("initial", ["OFF", "ON"])
def test_ac_f1_06_non_uppercase_rejected(host, control, cmd, initial):
    control.set_state(initial)
    r = host(cmd)
    assert (r.stdout, r.exit_code) == ("ERR UNKNOWN_CMD", 1)
    assert control.get_state() == initial
```

## Fault injection
```python
control.fault("HW_FAULT")
r = host("ON")
assert (r.stdout, r.exit_code) == ("ERR HW_FAULT", 1)
control.fault("NONE")   # recovery is part of the AC - assert it too
```

## Timeout (device silent): bound from the command send, exact text, discarded command
```python
@pytest.mark.ac("AC-F1-11")
def test_ac_f1_11_silent_device_times_out(host, control):
    control.set_state("OFF")
    control.silence(True)
    r = host("ON", timeout=0.5)
    assert (r.stdout, r.exit_code) == ("", 3)
    assert r.stderr == "ERROR: no response from device within 0.5s"
    assert r.sent and r.send_to_end <= 0.5 + 0.5   # NOT r.duration: that includes Python start-up
    assert control.get_state() == "OFF"            # the command was discarded
    control.silence(False)
    assert host("STATUS").stdout == "STATUS OFF"   # recovery
```

## Usage error: nothing is sent
```python
r = host(None)                                     # COMMAND omitted
assert r.exit_code == 2 and not r.sent
```

## After startup (no RESET)
```python
info, fresh_control = fresh_simulator
assert host("STATUS", port=info.serial_port).stdout == "STATUS OFF"
```

## Time-dependent behavior (controlled clock): boundary pairs
```python
@pytest.mark.parametrize("elapsed, expected", [(1.999, "BUSY"), (2.000, "OK")], ids=["just-under", "at-boundary"])
def test_ac_xx_nn_rate_limit_boundary(host, control, elapsed, expected):
    assert host("ON").stdout == "OK"
    control.advance(elapsed)        # never sleep; exact decimals
    assert host("OFF").stdout == expected
```

## Anti-patterns
- `time.sleep(2)` - use `control.advance(2)`.
- Asserting only `STATUS` to prove state - also use `control.get_state()`.
- Test B relies on state left by test A.
- Importing `relay_sim.device` to call the parser directly (that is a unit test).
- Timing bounds on `r.duration` when the AC counts from the command send; widening a bound, retries, `flaky`.
- Writing tests for an AC that is not (yet) in `requirements.md`; a change request in a new spec folder
  instead of a `Changes` section in the affected feature's `requirements.md`.
- A second test file for the same feature, or repeating a scenario that already exists.
