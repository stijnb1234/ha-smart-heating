from datetime import UTC, datetime, time, timedelta

import pytest

from custom_components.smart_heating.engine import (
    Commands,
    EngineConfig,
    EngineInput,
    RoomConfig,
    SensorConfig,
    SensorReading,
    decide,
)
from custom_components.smart_heating.engine.boiler import demand_rooms
from custom_components.smart_heating.engine.insights import RoomInsights
from custom_components.smart_heating.engine.sensors import select_temperature
from custom_components.smart_heating.engine.trackers import CoastTracker, StallTracker

T0 = datetime(2026, 1, 12, 12, 0, tzinfo=UTC)


def minutes(n):
    return T0 + timedelta(minutes=n)


# --- learned open-window threshold -------------------------------------------------

def test_window_threshold_needs_data_and_never_exceeds_the_configured_drop():
    ins = RoomInsights()
    assert ins.window_threshold("bed", 1.5) is None
    for _ in range(40):
        ins.record_drop("bed", 0.1)
    assert ins.window_threshold("bed", 1.5) == 0.5  # quiet room: 0.1 + 0.4 margin, floor 0.5
    assert ins.window_threshold("bed", 0.5) == 0.5


def test_noisy_room_learns_a_higher_threshold():
    ins = RoomInsights()
    for i in range(100):
        ins.record_drop("bed", 0.6 if i % 4 == 0 else 0.1)
    assert 0.9 <= ins.window_threshold("bed", 1.5) <= 1.1


def test_learned_threshold_beats_a_stale_stored_drop(clock):
    room = RoomConfig(name="bed", window_drop=1.5)
    inp = EngineInput(
        config=EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0),
        now=minutes(0), anyone_home=True, learned={}, last_commands=Commands(),
        trv_temps={"bed": SensorReading(18.0, minutes(0))},
        temp_history={"bed": (SensorReading(19.0, minutes(-8)), SensorReading(18.0, minutes(0)))},
    )
    assert "bed" not in decide(inp).window_paused_until
    import dataclasses

    learned = dataclasses.replace(inp, window_thresholds={"bed": 0.7})
    assert "bed" in decide(learned).window_paused_until


# --- coast: end the call early -------------------------------------------------------

def test_coast_tracker_measures_the_rise_after_the_call_ends():
    t = CoastTracker()
    assert t.observe("bed", minutes(0), 19.0, calling=True) is None
    assert t.observe("bed", minutes(1), 19.3, calling=False) is None  # call just ended here
    assert t.observe("bed", minutes(5), 19.8, calling=False) is None
    assert t.observe("bed", minutes(9), 19.9, calling=False) is None
    assert t.observe("bed", minutes(12), 19.7, calling=False) == pytest_approx(0.6)


def test_coast_tracker_ignores_calls_ended_by_something_else():
    t = CoastTracker()
    t.observe("bed", minutes(0), 19.0, calling=True)
    t.observe("bed", minutes(1), 19.3, calling=False, valid=False)  # window pause
    assert t.observe("bed", minutes(20), 18.0, calling=False) is None


def test_learned_coast_widens_the_demand_margin():
    room = RoomConfig(name="bed", comfort=19.5)
    cfg = EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0)
    temps, targets = {"bed": 19.0}, {"bed": 19.5}
    assert demand_rooms(cfg, targets, temps) == ("bed",)  # 0.5 below target, hysteresis 0.3
    assert demand_rooms(cfg, targets, temps, coast={"bed": 0.6}) == ()  # it will coast the rest


def test_coast_needs_three_observations_and_is_capped():
    ins = RoomInsights()
    ins.record_coast("bed", 5.0)
    ins.record_coast("bed", 5.0)
    assert ins.coast("bed") is None
    ins.record_coast("bed", 5.0)
    assert ins.coast("bed") == 1.0


# --- sensor offset ----------------------------------------------------------------------

def test_learned_offset_fixes_the_trv_fallback_unless_one_is_configured():
    cfg = SensorConfig()
    trv = {"bed": SensorReading(18.0, minutes(0))}
    plain = RoomConfig(name="bed")
    assert select_temperature(plain, {}, trv, minutes(1), cfg)[0] == 18.0
    assert select_temperature(plain, {}, trv, minutes(1), cfg, {"bed": 1.2})[0] == 19.2
    manual = RoomConfig(name="bed", trv_offset=-0.5)
    assert select_temperature(manual, {}, trv, minutes(1), cfg, {"bed": 1.2})[0] == 17.5


def test_offset_is_the_median_of_enough_samples():
    ins = RoomInsights()
    for _ in range(23):
        ins.record_offset("bed", 1.0)
    assert ins.offset("bed") is None
    ins.record_offset("bed", 9.0)
    assert ins.offset("bed") == 1.0


# --- stall ------------------------------------------------------------------------------

def test_stall_after_45_minutes_of_calling_without_warming_up():
    s = StallTracker()
    for m in range(0, 46, 5):
        s.observe("bed", minutes(m), 18.0 + (0.1 if m else 0), calling=True)
    assert s.stalled() == frozenset({"bed"})


def test_progress_or_stopping_resets_the_stall():
    s = StallTracker()
    for m in range(0, 40, 5):
        s.observe("bed", minutes(m), 18.0, calling=True)
    s.observe("bed", minutes(40), 18.4, calling=True)  # real warming
    assert s.stalled() == frozenset()
    s.observe("bed", minutes(60), 18.4, calling=False)
    assert s.stalled() == frozenset()


def test_stalled_room_rests_then_tries_again_and_stays_stalled():
    s = StallTracker()
    for m in range(0, 46, 5):
        s.observe("bed", minutes(m), 18.0, calling=True)
    assert s.resting(minutes(46)) == {"bed"}
    s.observe("bed", minutes(60), 18.0, calling=False)  # resting is not recovering
    assert s.resting(minutes(224)) == {"bed"}
    assert s.resting(minutes(225)) == frozenset()
    assert s.stalled() == {"bed"}
    for m in range(225, 271, 5):
        s.observe("bed", minutes(m), 18.0, calling=True)
    assert s.resting(minutes(271)) == {"bed"}


@pytest.mark.parametrize(("temp", "unmet"), [(17.9, True), (18.0, False)])
def test_warming_up_or_no_longer_needing_heat_ends_the_stall(temp, unmet):
    s = StallTracker()
    for m in range(0, 46, 5):
        s.observe("bed", minutes(m), 18.0, calling=True)
    s.observe("bed", minutes(50), 17.5, calling=False)  # cools further while resting
    s.observe("bed", minutes(90), temp, calling=False, unmet=unmet)
    assert s.stalled() == frozenset()


def test_no_stall_while_calls_do_not_reach_the_boiler():
    s = StallTracker()
    for m in range(0, 91, 5):
        s.observe("bed", minutes(m), 18.0, calling=True, heated=False)
    assert s.stalled() == frozenset()


def test_resting_room_does_not_call():
    cfg = EngineConfig(rooms=(RoomConfig(name="bed"),), boiler_low=10.0, boiler_high=22.0)
    assert demand_rooms(cfg, {"bed": 19.5}, {"bed": 17.0}, resting=frozenset({"bed"})) == ()


def test_stalled_room_raises_an_alert():
    room = RoomConfig(name="bed")
    inp = EngineInput(
        config=EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0),
        now=minutes(0), anyone_home=True, learned={}, last_commands=Commands(),
        trv_temps={"bed": SensorReading(18.0, minutes(0))}, stalled=frozenset({"bed"}),
    )
    assert [(a.code, a.room) for a in decide(inp).alerts] == [("not_warming", "bed")]


# --- schedule suggestions ---------------------------------------------------------------

def _never_covered(room, at):
    return False


def test_three_days_of_morning_boosts_become_a_suggestion():
    ins = RoomInsights()
    for day in (0, 1, 3):  # Mon, Tue, Thu
        ins.record_event("study", datetime(2026, 1, 12 + day, 7, 10 + day, tzinfo=UTC))
    (s,) = ins.suggestions(datetime(2026, 1, 16, tzinfo=UTC), _never_covered)
    assert (s.room, s.days, s.start, s.events) == ("study", (0, 1, 3), time(7, 10), 3)


def test_two_days_or_covered_moments_are_not_suggested():
    ins = RoomInsights()
    for day in (0, 1):
        ins.record_event("study", datetime(2026, 1, 12 + day, 7, 0, tzinfo=UTC))
    assert ins.suggestions(datetime(2026, 1, 16, tzinfo=UTC), _never_covered) == []
    ins.record_event("study", datetime(2026, 1, 14, 7, 0, tzinfo=UTC))
    assert ins.suggestions(datetime(2026, 1, 16, tzinfo=UTC), lambda r, at: True) == []


def test_old_events_expire():
    ins = RoomInsights()
    for day in (0, 1, 2):
        ins.record_event("study", datetime(2026, 1, 12 + day, 7, 0, tzinfo=UTC))
    assert ins.suggestions(datetime(2026, 3, 1, tzinfo=UTC), _never_covered) == []


def test_insights_survive_a_roundtrip_and_bad_data_is_ignored():
    ins = RoomInsights()
    for _ in range(40):
        ins.record_drop("bed", 0.2)
    ins.record_event("bed", T0)
    again = RoomInsights.from_dict(ins.to_dict())
    assert again.window_threshold("bed", 1.5) == ins.window_threshold("bed", 1.5)
    assert again.to_dict() == ins.to_dict()
    assert RoomInsights.from_dict({"version": 99}).to_dict() == RoomInsights().to_dict()
    assert RoomInsights.from_dict({"version": 1, "drops": {"bed": ["x"]}}).to_dict() == RoomInsights().to_dict()


def pytest_approx(value):
    import pytest

    return pytest.approx(value)


# --- settling: no restart while the radiator's stored heat is still arriving ----------------

def test_settling_room_does_not_call_again_until_it_is_really_cold():
    room = RoomConfig(name="bed", comfort=19.5)
    cfg = EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0)
    targets = {"bed": 19.5}
    settling = frozenset({"bed"})
    assert demand_rooms(cfg, targets, {"bed": 19.1}) == ("bed",)
    assert demand_rooms(cfg, targets, {"bed": 19.1}, settling=settling) == ()
    assert demand_rooms(cfg, targets, {"bed": 18.5}, settling=settling) == ("bed",)  # genuinely cold


def test_coast_tracker_settles_until_the_peak_plateaus():
    t = CoastTracker()
    t.observe("bed", minutes(0), 19.0, calling=True)
    t.observe("bed", minutes(1), 19.0, calling=False)
    assert t.settling() == {"bed"}
    t.observe("bed", minutes(10), 19.5, calling=False)  # 0.5 K sensor step, no fall ever shows
    assert t.settling() == {"bed"}
    assert t.observe("bed", minutes(31), 19.5, calling=False) == pytest_approx(0.5)
    assert t.settling() == frozenset()


def test_room_hysteresis_overrides_the_global_one():
    room = RoomConfig(name="bed", comfort=19.5, demand_hysteresis=0.5)
    cfg = EngineConfig(rooms=(room,), boiler_low=10.0, boiler_high=22.0)
    assert demand_rooms(cfg, {"bed": 19.5}, {"bed": 19.1}) == ()
    assert demand_rooms(cfg, {"bed": 19.5}, {"bed": 18.9}) == ("bed",)


def test_coast_follows_the_upper_quartile():
    ins = RoomInsights()
    for rise in (0.1, 0.1, 0.1, 0.1, 0.6, 0.6, 0.7, 0.7):
        ins.record_coast("bed", rise)
    assert ins.coast("bed") == pytest_approx(0.7)


# --- stall: crawlers whose target stays out of reach -------------------------------------

def _warm(tracker, start, rate, target, *, until, begin=0, step=0.1, calling=True):
    """Feed a Room warming at `rate` K/h, read by a sensor with `step` K resolution."""
    for m in range(begin, until + 1, 5):
        temp = start + int(rate * (m - begin) / 60 / step + 1e-9) * step
        tracker.observe("bed", minutes(m), temp, calling=calling, target=target)


def test_crawling_room_with_target_out_of_reach_is_stalled():
    s = StallTracker()
    _warm(s, 10.0, 0.45, 15.0, until=115)
    assert s.stalled() == frozenset()  # not judged on a short stretch
    _warm(s, 10.9, 0.45, 15.0, begin=120, until=125)
    assert s.resting(minutes(126)) == {"bed"}


@pytest.mark.parametrize(("rate", "target"), [(1.0, 16.0), (0.4, 12.0)])
def test_room_that_arrives_in_time_is_not_stalled(rate, target):
    s = StallTracker()
    _warm(s, 10.0 if target > 15 else 10.5, rate, target, until=240 if rate < 0.5 else 200)
    assert s.stalled() == frozenset()


def test_coarse_sensor_does_not_look_like_a_crawler():
    s = StallTracker()
    _warm(s, 15.0, 0.75, 19.5, until=300, step=0.5)
    assert s.stalled() == frozenset()


def test_creeping_does_not_end_a_stall_but_real_warming_does():
    s = StallTracker()
    _warm(s, 10.0, 0.45, 15.0, until=125)
    _warm(s, 10.9, 0.45, 15.0, begin=130, until=290, calling=False)  # heated by others, slowly
    assert s.stalled() == {"bed"}
    _warm(s, 12.1, 2.0, 15.0, begin=295, until=355, calling=False)
    assert s.stalled() == frozenset()


def test_without_a_target_only_a_flat_temperature_stalls():
    s = StallTracker()
    _warm(s, 10.0, 0.45, None, until=300)  # floor heating
    assert s.stalled() == frozenset()
