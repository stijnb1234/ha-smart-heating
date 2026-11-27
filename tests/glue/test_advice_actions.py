from datetime import UTC, datetime, time, timedelta

import pytest

from custom_components.smart_heating.advice_actions import (
    AdviceState,
    advice_text,
    advice_title,
    apply_advice,
    effects,
    undo_advice,
)
from custom_components.smart_heating.engine import ScheduleWindow
from custom_components.smart_heating.engine.advice import Advice, AdviceLog, ScheduleChange

NOW = datetime(2026, 1, 20, 8, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)
ROOMS = [{"id": "study", "name": "Study", "schedule": [{"days": [0, 1], "start": "09:00", "end": "17:00"}]}]
WINDOW = ScheduleWindow(frozenset({0, 1}), time(9), time(17))


def trim(start, end, days=(0,)):
    return Advice(
        "k", "trim_schedule", "Study", 2.0, days, start, end, change=ScheduleChange(WINDOW, days, start, end)
    )


def test_trimming_one_day_splits_the_window_and_undo_puts_it_back():
    rooms, before = apply_advice(ROOMS, trim(time(11), time(17)), duration=HOUR)
    assert rooms[0]["schedule"] == [
        {"days": [1], "start": "09:00", "end": "17:00"},
        {"days": [0], "start": "11:00", "end": "17:00"},
    ]
    assert undo_advice(rooms, {"room_id": "study", "before": before}) == ROOMS


def test_dropping_every_day_removes_the_window():
    rooms, _ = apply_advice(ROOMS, trim(None, None, (0, 1)), duration=HOUR)
    assert rooms[0]["schedule"] == []


def test_a_schedule_edited_since_is_left_alone():
    edited = [{**ROOMS[0], "schedule": [{"days": [0], "start": "10:00", "end": "17:00"}]}]
    with pytest.raises(ValueError):
        apply_advice(edited, trim(time(11), time(17)), duration=HOUR)


def test_adding_time_and_linking_people():
    add = Advice("a", "add_time", "Study", days=(2,), start=time(7), count=3)
    rooms, _ = apply_advice(ROOMS, add, duration=HOUR)
    assert rooms[0]["schedule"][-1] == {"days": [2], "start": "07:00", "end": "08:00"}
    link = Advice("o", "occupants", "Study", people=("person.sam",))
    rooms, before = apply_advice(ROOMS, link, duration=HOUR, people=["person.sam"])
    assert rooms[0]["presence_entities"] == ["person.sam"]
    assert "presence_entities" not in undo_advice(rooms, {"room_id": "study", "before": before})[0]
    with pytest.raises(ValueError):
        apply_advice(ROOMS, link, duration=HOUR)


def test_snoozed_advice_returns_after_four_weeks():
    state, advice = AdviceState(), [Advice("k", "add_sensor", "Study")]
    state.hide("k", NOW)
    assert state.visible(advice, NOW + timedelta(weeks=3)) == []
    assert state.visible(advice, NOW + timedelta(weeks=5)) == advice
    assert AdviceState.from_dict(state.to_dict()) == state


def test_effect_compares_boiler_hours_before_and_since():
    log = AdviceLog()
    log.days["Study"] = {f"2026-01-{d:02d}": {"sole": 30.0} for d in range(12, 20)}
    state = AdviceState(applied=[{"at": (NOW - timedelta(days=9)).isoformat(), "room": "Study", "hours_before": 6.0}])
    assert effects(state, log, NOW) == [("Study", 6.0, 3.5)]


@pytest.mark.parametrize("lang", ["en", "nl"])
def test_every_kind_reads_as_a_sentence_in_both_languages(lang):
    advice = [
        trim(time(11), time(17)),
        trim(None, None),
        Advice("a", "add_time", "Study", days=(2,), start=time(7), count=3),
        Advice("o", "occupants", "Study", people=("person.sam",)),
        Advice("l", "leak", "Study", count=4, cause="sun", probably=True),
        Advice("s", "sole_caller", "Study", 12.5),
        Advice("p", "long_preheat", "Study", count=3, cause="4.5"),
        Advice("t", "late", "Study", count=3),
        Advice("n", "add_sensor", "Study"),
        Advice("f", "fault", "Study", count=3, cause="valve_rejects"),
    ]
    for item in advice:
        text = advice_text(item, lang, 0.9, {"person.sam": "Sam"})
        assert "{" not in text and "advice." not in text and "diagnosis." not in text
        assert "Study" in advice_title(item, lang)
    assert "GBP" in advice_text(advice[0], lang, 0.9, currency="GBP")
