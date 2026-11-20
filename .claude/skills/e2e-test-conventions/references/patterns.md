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

## Timeout (device silent)
```python
control.silence(True)
r = host("STATUS", timeout=0.5)
assert r.exit_code == 3 and "no response" in r.stderr
assert r.duration < 0.5 + 0.5
```

## Time-dependent behavior (controlled clock)
```python
r1 = host("ON")
control.advance(1.999)          # never sleep
r2 = host("OFF")
```

## Anti-patterns
- `time.sleep(2)` - use `control.advance(2)`.
- Asserting only `STATUS` to prove state - also use `control.get_state()`.
- Test B relies on state left by test A.
- Importing `relay_sim.device` to call the parser directly (that is a unit test).
