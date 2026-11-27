from datetime import UTC, datetime, timedelta

import pytest

from custom_components.smart_heating.engine.calibration import Calibration, CalibrationError
from custom_components.smart_heating.engine.trackers import RadiatorWarmth

T0 = datetime(2026, 1, 12, 6, 0, tzinfo=UTC)


def minutes(m):
    return T0 + timedelta(minutes=m)


def test_both_states_are_needed_before_an_offset_applies():
    c = Calibration()
    c.add("bed", "cold", T0, reading=18.0, trv=18.5)
    assert c.offset("bed", 0.0) is None
    c.add("bed", "heating", T0, reading=19.0, trv=23.5)
    assert c.offset("bed", 0.0).current == -0.5
    assert c.offset("bed", 1.0).current == -4.5
    assert c.offset("bed", 0.5).current == -2.5
    assert c.offset("bed", 0.0).heating == -4.5


def test_more_entries_refine_by_median_and_clearing_forgets():
    c = Calibration()
    c.add("bed", "heating", T0, 19.0, 23.0)
    for reading in (18.0, 17.0, 18.2):
        c.add("bed", "cold", T0, reading, 18.0)
    assert c.offset("bed", 0.0).current == 0.0
    c.clear("bed")
    assert c.states("bed") == frozenset()


@pytest.mark.parametrize(("reading", "trv"), [(45.0, 40.0), (-1.0, 5.0), (2.0, 20.0)])
def test_implausible_entries_are_refused(reading, trv):
    with pytest.raises(CalibrationError):
        Calibration().add("bed", "cold", T0, reading, trv)


def test_calibration_survives_a_roundtrip_and_bad_data_is_ignored():
    c = Calibration()
    c.add("bed", "cold", T0, 18.0, 18.5)
    assert Calibration.from_dict(c.to_dict()).to_dict() == c.to_dict()
    assert Calibration.from_dict({"version": 1, "rooms": {"bed": {"cold": ["x"]}}}).states("bed") == frozenset()


def test_radiator_warmth_rises_while_heating_and_fades_after():
    w = RadiatorWarmth()
    for m in range(0, 61, 5):
        w.observe("bed", minutes(m), hot=False)
    assert (w.warmth("bed"), w.settled("bed", minutes(60))) == (0.0, "cold")
    w.observe("bed", minutes(60), hot=True)
    w.observe("bed", minutes(75), hot=True)
    assert (w.warmth("bed"), w.settled("bed", minutes(75))) == (0.5, None)
    w.observe("bed", minutes(90), hot=False)
    assert (w.warmth("bed"), w.settled("bed", minutes(90))) == (1.0, "heating")
    w.observe("bed", minutes(120), hot=False)
    assert (w.warmth("bed"), w.settled("bed", minutes(120))) == (0.5, None)


def test_radiator_state_is_unknown_right_after_a_start():
    w = RadiatorWarmth()
    w.observe("bed", T0, hot=False)
    assert w.settled("bed", minutes(30)) is None
