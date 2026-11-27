from datetime import UTC, datetime, time, timedelta

from custom_components.smart_heating.engine import RoomConfig, ScheduleWindow
from custom_components.smart_heating.engine.advice import AdviceLog, Observation, detect
from custom_components.smart_heating.engine.diagnosis import diagnose
from custom_components.smart_heating.engine.insights import Suggestion
from custom_components.smart_heating.engine.models import Alert
from custom_components.smart_heating.engine.trackers import FrostTracker, LeakTracker

START = datetime(2026, 1, 5, tzinfo=UTC)  # a Monday
ROOM = RoomConfig(
    name="study", id="study", schedule=(ScheduleWindow(frozenset({0}), time(9), time(17)),)
)


def record(log, days, make, *, step=5):
    """Observe every `step` minutes for `days` days; `make(at)` gives the Room's flags."""
    for m in range(0, days * 24 * 60, step):
        at = START + timedelta(minutes=m)
        flags = {"scheduled": False, "away": False, "lowered": False, "calling": False, "sole": False}
        flags |= make(at)
        log.observe(at, flags["calling"], [Observation(room="study", **flags)])
    return START + timedelta(days=days)


def kinds(found):
    return [a.kind for a in found]


def test_a_quiet_room_gives_no_advice():
    log = AdviceLog()
    now = record(log, 28, lambda at: {})
    assert detect(log, (ROOM,), now) == []


def _away_mornings(at):
    """Mondays: pre-heated from 07:00, but nobody is there until 11:00."""
    if at.weekday() != 0:
        return {}
    scheduled = 9 <= at.hour < 17
    away = 9 <= at.hour < 11
    calling = 7 <= at.hour < 9 or (11 <= at.hour < 13)
    return {"scheduled": scheduled, "away": away, "calling": calling, "sole": calling}


def test_a_start_that_is_repeatedly_for_nobody_is_moved_and_counts_the_preheat():
    log = AdviceLog()
    now = record(log, 28, _away_mornings)
    (advice,) = [a for a in detect(log, (ROOM,), now) if a.kind == "trim_schedule"]
    assert (advice.days, advice.start, advice.end) == ((0,), time(11), time(17))
    assert advice.saving_hours == 2.0
    assert advice.applicable


def test_two_weeks_of_evidence_is_not_enough():
    log = AdviceLog()
    now = record(log, 14, _away_mornings)
    assert "trim_schedule" not in kinds(detect(log, (ROOM,), now))


def test_a_room_that_alone_keeps_the_boiler_on():
    log = AdviceLog()
    now = record(log, 8, lambda at: {"calling": at.hour < 4, "sole": at.hour < 4})
    (advice,) = detect(log, (ROOM,), now)
    assert advice.kind == "sole_caller" and round(advice.saving_hours) == 28


def test_leaks_come_first_and_mention_the_sun_only_when_seen_in_daytime():
    log = AdviceLog()
    now = record(log, 8, lambda at: {"leaked": at.hour == 12 and at.minute == 0, "calling": at.hour < 4, "sole": at.hour < 4})
    leak = detect(log, (ROOM,), now)[0]
    assert (leak.kind, leak.cause, leak.probably) == ("leak", "sun", False)


def test_a_room_without_a_sensor_only_gets_leak_and_sensor_advice():
    log = AdviceLog()
    now = record(log, 8, lambda at: {"leaked": at.hour == 2 and at.minute == 0, "calling": at.hour < 4, "sole": at.hour < 4})
    suggestion = Suggestion("study", (1,), time(7), 3)
    found = detect(log, (ROOM,), now, sensorless={"study"}, suggestions=[suggestion])
    assert kinds(found) == ["leak", "add_sensor"]
    assert found[0].probably


def test_recurring_diagnoses_become_advice():
    log = AdviceLog()
    for day in range(2):
        log.record_fault("study", "valve_rejects", START + timedelta(days=day))
    assert detect(log, (ROOM,), START + timedelta(days=3)) == []
    log.record_fault("study", "valve_rejects", START + timedelta(days=2))
    (advice,) = detect(log, (ROOM,), START + timedelta(days=3))
    assert (advice.kind, advice.cause, advice.count) == ("fault", "valve_rejects", 3)


def test_occupants_are_suggested_from_who_was_away_when_the_valve_went_down():
    log = AdviceLog()
    now = record(
        log, 8,
        lambda at: {"scheduled": True, "lowered": at.hour == 10, "people_away": ("person.sam",)},
    )
    found = detect(log, (ROOM,), now, without_occupants={"study"})
    assert [a.people for a in found if a.kind == "occupants"] == [("person.sam",)]


def test_old_evidence_is_forgotten_and_the_log_survives_a_roundtrip():
    log = AdviceLog()
    record(log, 2, _away_mornings)
    log.record_fault("study", "battery", START)
    assert AdviceLog.from_dict(log.to_dict()).to_dict() == log.to_dict()
    log.prune((START + timedelta(days=40)).date())
    assert not log.boiler and not log.days["study"] and not log.faults["study"]


def test_one_diagnosis_per_room_names_the_cause_that_explains_most():
    alerts = [
        Alert("low_battery", "study"), Alert("target_not_reached", "study"), Alert("trv_offline", "study"),
        Alert("not_warming", "hall"), Alert("boiler_outage"),
    ]
    found = diagnose(alerts)
    assert [(d.room, d.cause, d.urgent) for d in found] == [
        (None, "boiler_outage", True), ("study", "valve_unreachable", False), ("hall", "no_heat", False)
    ]
    assert found[1].codes == ("trv_offline", "target_not_reached", "low_battery")


def test_frost_risk_after_an_hour_near_frost_hold_without_warming():
    t = FrostTracker()
    for m in range(0, 61, 10):
        t.observe("shed", START + timedelta(minutes=m), 8.5, 8.0)
    assert t.at_risk() == {"shed"}
    t.observe("shed", START + timedelta(minutes=70), 8.9, 8.0)  # warming
    assert t.at_risk() == frozenset()


def test_leak_is_a_rise_on_others_calls_reported_once():
    t = LeakTracker()
    seen = [
        t.observe("shed", START + timedelta(minutes=m), 15.0 + m * 0.1, 12.0, calling=False, boiler_on=True)
        for m in range(0, 31, 5)
    ]
    assert seen.count(True) == 1


def test_no_leak_while_the_boiler_is_off_or_just_after_the_rooms_own_call():
    t = LeakTracker()
    assert not any(
        t.observe("shed", START + timedelta(minutes=m), 15.0 + m * 0.1, 12.0, calling=False, boiler_on=False)
        for m in range(0, 31, 5)
    )
    t.observe("shed", START + timedelta(minutes=31), 15.0, 12.0, calling=True, boiler_on=True)
    assert not any(
        t.observe("shed", START + timedelta(minutes=m), 15.0 + m * 0.1, 12.0, calling=False, boiler_on=True)
        for m in range(32, 60, 5)
    )
