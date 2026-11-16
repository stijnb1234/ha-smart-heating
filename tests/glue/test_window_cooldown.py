"""Open-window detection versus a radiator cooling down (simulation).

The TRV's own sensor sits on the valve, a hand's width from the radiator. While the radiator
is hot it reads several degrees above the room; when the boiler call ends the radiator cools
and that reading falls fast although the room itself does not cool. These tests model that
with an exponential decay and check it is not taken for an open window.
"""

import math
from datetime import timedelta

from custom_components.smart_heating.engine import Commands

from .test_controller import T0, make, snap

START = T0 + timedelta(hours=6)  # Monday 09:00, inside the room's comfort window (20 degC)
TRV_EXCESS = 3.5  # K the TRV sensor reads above the room while the radiator is hot
TAU = 35.0  # minutes: cooling time constant of a cast-iron radiator


def _run(c, minutes, room, trv, start):
    reasons = []
    for m in range(minutes):
        now = start + timedelta(minutes=m)
        cycle = c.step(snap(now, temp=trv(m), ext=room(m)))
        c.confirm(cycle, dict(cycle.decision.trv_setpoints), Commands())
        reasons.append(cycle.decision.reasons["work"])
    return reasons


def _heat_then_stop(c):
    """Heat for 30 min (room 19.5, below the demand band: the boiler is called), then stop."""
    _run(c, 30, room=lambda m: 19.5, trv=lambda m: 19.5 + TRV_EXCESS, start=START)
    return START + timedelta(minutes=30)


def test_radiator_cooling_after_the_call_is_not_an_open_window():
    c = make()
    stopped = _heat_then_stop(c)

    # Room reached comfort: the call ends; the room stays at 20 while the radiator cools.
    reasons = _run(
        c, 45, room=lambda m: 20.0, trv=lambda m: 20.0 + TRV_EXCESS * math.exp(-m / TAU), start=stopped
    )

    assert "window" not in reasons


def test_without_the_cooldown_rule_the_same_curve_would_look_like_an_open_window():
    # The TRV falls 1.2 K in the first 15 min: above the default 0.8 K drop. This is the
    # false trigger the cooldown rule exists for.
    drop = TRV_EXCESS * (1 - math.exp(-15 / TAU))
    assert drop > 0.8


def test_open_window_during_cooldown_is_still_seen_by_the_room_sensor():
    c = make()
    stopped = _heat_then_stop(c)

    # The fall counts from the room's comfort temperature down, so a TRV reading above it
    # (hot radiator) delays the catch a few minutes; it must still come within 20.
    reasons = _run(
        c,
        20,
        room=lambda m: 20.0 - 0.3 * m,  # the room air cools fast: a real open window
        trv=lambda m: 20.0 + TRV_EXCESS * math.exp(-m / TAU) - 0.3 * m,
        start=stopped,
    )

    assert "window" in reasons


def test_open_window_after_cooldown_is_seen_by_the_trv_sensor():
    c = make()
    stopped = _heat_then_stop(c)
    cooled = 20.0 + TRV_EXCESS * math.exp(-90 / TAU)
    quiet = _run(c, 90, room=lambda m: 20.0, trv=lambda m: 20.0 + TRV_EXCESS * math.exp(-m / TAU), start=stopped)
    assert "window" not in quiet

    reasons = _run(
        c, 10, room=lambda m: 20.0 - 0.07 * m, trv=lambda m: cooled - 0.3 * m, start=stopped + timedelta(minutes=90)
    )  # the TRV sensor reacts first, the room sensor follows

    assert "window" in reasons


def test_a_closing_valve_starts_the_cooldown_without_any_boiler_call():
    c = make()
    for m in range(20):  # valve open, but the boiler is not calling (room within its band)
        now = START + timedelta(minutes=m)
        cycle = c.step(snap(now, temp=23.0, ext=19.95, valve_open=frozenset({"work"})))
        c.confirm(cycle, dict(cycle.decision.trv_setpoints), Commands())
    reasons = []
    for m in range(20, 50):  # valve shut: the TRV sensor falls fast, the room does not
        now = START + timedelta(minutes=m)
        cycle = c.step(snap(now, temp=23.0 - 0.2 * (m - 20), ext=19.95))
        c.confirm(cycle, dict(cycle.decision.trv_setpoints), Commands())
        reasons.append(cycle.decision.reasons["work"])

    assert "window" not in reasons


def test_a_value_after_a_long_silence_is_not_a_fast_fall():
    from custom_components.smart_heating.engine import SensorReading

    c = make()
    reported = START
    for m in range(61):  # the TRV reports once an hour: 20.0, then 19.0
        now = START + timedelta(minutes=m)
        if m == 60:
            reported = now
        value = 19.0 if m == 60 else 20.0
        s = snap(now)
        s = type(s)(**{**s.__dict__, "trv": {"work": SensorReading(value, START if m < 60 else reported)}})
        cycle = c.step(s)
        c.confirm(cycle, dict(cycle.decision.trv_setpoints), Commands())

    assert cycle.decision.reasons["work"] != "window"
