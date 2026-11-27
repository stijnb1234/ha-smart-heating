"""What the administrator can do with advice, and how it reads. No Home Assistant imports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any

from .engine.advice import KEEP, Advice, AdviceLog
from .i18n import DEFAULT_LANGUAGE, number, tr, weekday

SNOOZE = timedelta(weeks=4)
UNDO_KEEP = timedelta(weeks=4)
EFFECT_AFTER = timedelta(days=7)
_CHANGED_KEYS = ("schedule", "presence_entities")


@dataclass
class AdviceState:
    hidden: dict[str, str] = field(default_factory=dict)  # advice key -> hidden until (ISO)
    applied: list[dict[str, Any]] = field(default_factory=list)  # oldest first, for undo and effect
    cost_per_hour: float | None = None  # money per boiler hour, from the last digest
    currency: str = "EUR"

    def hide(self, key: str, now: datetime, how_long: timedelta = SNOOZE) -> None:
        self.hidden[key] = (now + how_long).isoformat()

    def visible(self, advice: Sequence[Advice], now: datetime) -> list[Advice]:
        self.hidden = {k: v for k, v in self.hidden.items() if datetime.fromisoformat(v) > now}
        return [a for a in advice if a.key not in self.hidden]

    def prune(self, now: datetime) -> None:
        self.applied = [r for r in self.applied if now - datetime.fromisoformat(r["at"]) <= UNDO_KEEP]

    def to_dict(self) -> dict[str, Any]:
        return {"hidden": self.hidden, "applied": self.applied, "cost_per_hour": self.cost_per_hour, "currency": self.currency}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> AdviceState:
        if not data:
            return cls()
        return cls(
            hidden=dict(data.get("hidden", {})),
            applied=[dict(r) for r in data.get("applied", [])],
            cost_per_hour=data.get("cost_per_hour"),
            currency=data.get("currency", "EUR"),
        )


def _clock(at: time) -> str:
    return at.strftime("%H:%M")


def apply_advice(
    rooms: Sequence[Mapping[str, Any]],
    advice: Advice,
    *,
    duration: timedelta,
    people: Sequence[str] = (),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """(stored Rooms with the change made, what the changed settings were before).

    Raises ValueError when the Room or the schedule window is no longer as the advice saw it.
    `duration`: length of an added comfort time. `people`: the chosen Room occupants.
    """
    room = next((r for r in rooms if r["name"] == advice.room), None)
    if room is None or not advice.applicable:
        raise ValueError("nothing to apply")
    changed = dict(room)
    schedule = [dict(w) for w in room.get("schedule", ())]
    if advice.kind == "trim_schedule":
        change = advice.change
        assert change is not None
        old = (_clock(change.window.start), _clock(change.window.end))
        index = next(
            (
                i
                for i, w in enumerate(schedule)
                if (w["start"][:5], w["end"][:5]) == old and set(change.days) <= set(w["days"])
            ),
            None,
        )
        if index is None:
            raise ValueError("schedule changed since")
        window = schedule.pop(index)
        rest = sorted(set(window["days"]) - set(change.days))
        new = [{**window, "days": rest}] if rest else []
        if change.start is not None and change.end is not None:
            new.append({"days": list(change.days), "start": _clock(change.start), "end": _clock(change.end)})
        schedule[index:index] = new
        changed["schedule"] = schedule
    elif advice.kind == "add_time":
        assert advice.start is not None
        end = (datetime.combine(datetime.min, advice.start) + duration).time()
        schedule.append({"days": list(advice.days), "start": _clock(advice.start), "end": _clock(end)})
        changed["schedule"] = schedule
    else:
        if not people:
            raise ValueError("nobody chosen")
        changed["presence_entities"] = list(people)
    before = {k: room.get(k) for k in _CHANGED_KEYS if changed.get(k) != room.get(k)}
    return [changed if r is room else dict(r) for r in rooms], before


def undo_advice(rooms: Sequence[Mapping[str, Any]], record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Stored Rooms with the settings of one applied advice put back."""
    result = []
    for room in rooms:
        room = dict(room)
        if room.get("id") == record["room_id"]:
            for key, value in record["before"].items():
                if value is None:
                    room.pop(key, None)
                else:
                    room[key] = value
        result.append(room)
    return result


def effects(state: AdviceState, log: AdviceLog, now: datetime) -> list[tuple[str, float, float]]:
    """(Room, boiler hours per week before, since) for advice applied at least a week ago."""
    found = []
    for record in state.applied:
        at = datetime.fromisoformat(record["at"])
        if now - at < EFFECT_AFTER or record.get("hours_before") is None:
            continue
        after = log.hours_per_week(
            record["room"], "sole", at.date() + timedelta(days=1), min(now.date(), at.date() + KEEP)
        )
        if after is not None:
            found.append((record["room"], record["hours_before"], after))
    return found


def _days(days: Sequence[int], lang: str) -> str:
    return ", ".join(weekday(lang, d) for d in days)


def advice_title(advice: Advice, lang: str = DEFAULT_LANGUAGE) -> str:
    key = f"advice.{advice.kind}.title"
    if advice.kind == "fault":
        key = f"diagnosis.{advice.cause}.title"
    return tr(lang, key, room=advice.room)


def advice_text(
    advice: Advice,
    lang: str = DEFAULT_LANGUAGE,
    cost_per_hour: float | None = None,
    names: Mapping[str, str] | None = None,
    currency: str = "EUR",
) -> str:
    """The advice as plain sentences, with what it saves. `names`: friendly names of people."""
    names = names or {}
    if advice.kind == "fault":
        text = tr(lang, f"diagnosis.{advice.cause}", room=advice.room) + " " + tr(lang, "advice.fault.count", count=advice.count)
    else:
        if advice.kind == "trim_schedule":
            change = advice.change
            assert change is not None
            what = (
                tr(lang, "advice.trim.drop")
                if advice.start is None or advice.end is None
                else tr(lang, "advice.trim.change", start=_clock(advice.start), end=_clock(advice.end))
            )
            values = {
                "days": _days(advice.days, lang), "what": what,
                "old": f"{_clock(change.window.start)}–{_clock(change.window.end)}",
            }
        elif advice.kind == "add_time":
            assert advice.start is not None
            values = {"days": _days(advice.days, lang), "time": _clock(advice.start)}
        else:
            values = {
                "hours": number(advice.saving_hours, lang),
                "people": ", ".join(names.get(p, p) for p in advice.people),
                "preheat": advice.cause.replace(".", "," if lang == "nl" else "."),
            }
        key = f"advice.{advice.kind}"
        text = tr(lang, key, room=advice.room, count=advice.count, **values)
        if advice.probably:
            text = tr(lang, "advice.probably") + " " + text
        if advice.cause == "sun" and advice.kind == "leak":
            text += " " + tr(lang, "advice.leak.sun")
    if advice.saving_hours >= 0.5:
        if cost_per_hour:
            text += " " + tr(
                lang, "advice.saving_cost", hours=number(advice.saving_hours, lang),
                cost=f"{advice.saving_hours * cost_per_hour:.0f}", currency=currency,
            )
        else:
            text += " " + tr(lang, "advice.saving", hours=number(advice.saving_hours, lang))
    return text
