"""Patterns that waste gas, found in four weeks of compact observations. No Home Assistant imports.

`AdviceLog` collects per Room and day what happened (in half-hour slots where the time of day
matters); `detect` turns it into `Advice`. Nothing here changes anything.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from statistics import median
from typing import Any

from .insights import Suggestion
from .models import RoomConfig, ScheduleWindow

SCHEMA_VERSION = 1
KEEP = timedelta(days=28)
SLOT_MINUTES = 30
SLOTS = 24 * 60 // SLOT_MINUTES
MAX_GAP = timedelta(minutes=5)  # longer between observations is downtime, not observed time

MIN_OCCURRENCES = 3
MIN_SHARE = 0.75
MIN_SAVING_H = 1.0  # boiler hours per week before a schedule change is worth proposing
MIN_DAYS = 7  # of data before weekly totals mean anything
SOLE_HOURS = 10.0  # per week, and
SOLE_SHARE = 0.4  # of all boiler hours: a Room that alone keeps the boiler on
LONG_PREHEAT_MIN = 180.0
LONG_PREHEAT_FLOOR_MIN = 300.0
PREHEAT_LOOKBACK = 8  # slots before a window start that its pre-heat may fall in
DAYTIME = range(9, 17)

# Slot counters: minutes observed, people away, valve turned down, boiler called by this Room alone.
OBSERVED, AWAY, LOWERED, SOLE = range(4)


@dataclass(frozen=True)
class Observation:
    room: str
    scheduled: bool  # inside a comfort window (pre-heat not included)
    away: bool  # the Room's people, or everyone, are away
    lowered: bool  # valve turned below comfort by hand during a comfort window
    calling: bool
    sole: bool  # the only Room calling
    preheating: bool = False
    late: bool = False  # a comfort window just started with the Room still clearly cold
    leaked: bool = False  # warmed up while its valve should have been closed
    people_away: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScheduleChange:
    """Replace `days` of one comfort window by `start`-`end` (None: drop those days)."""

    window: ScheduleWindow
    days: tuple[int, ...]
    start: time | None
    end: time | None


@dataclass(frozen=True)
class Advice:
    key: str  # stable while the same pattern lasts
    kind: str
    room: str
    saving_hours: float = 0.0  # boiler hours per week
    days: tuple[int, ...] = ()
    start: time | None = None
    end: time | None = None
    count: int = 0
    cause: str = ""  # fault: the diagnosis; leak: "sun" when only seen in daytime
    probably: bool = False  # judged by a TRV sensor next to the radiator
    change: ScheduleChange | None = None
    people: tuple[str, ...] = ()  # suggested Room occupants

    @property
    def applicable(self) -> bool:
        return self.kind in ("trim_schedule", "add_time", "occupants")


@dataclass
class AdviceLog:
    # room -> day (ISO) -> slot -> counters
    slots: dict[str, dict[str, dict[int, list[float]]]] = field(default_factory=dict)
    # room -> day -> totals
    days: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    faults: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    # room -> day -> people away when the valve was turned down
    lowered_by: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    boiler: dict[str, float] = field(default_factory=dict)  # day -> minutes called
    _last: datetime | None = None

    def observe(self, now: datetime, boiler_on: bool, rooms: Sequence[Observation]) -> None:
        gap = timedelta(0) if self._last is None else now - self._last
        self._last = now
        minutes = gap.total_seconds() / 60 if timedelta(0) < gap <= MAX_GAP else 0.0
        day = now.date().isoformat()
        slot = (now.hour * 60 + now.minute) // SLOT_MINUTES
        if boiler_on:
            self.boiler[day] = self.boiler.get(day, 0.0) + minutes
        for o in rooms:
            counters = self.slots.setdefault(o.room, {}).setdefault(day, {}).setdefault(slot, [0.0] * 4)
            counters[OBSERVED] += minutes
            counters[AWAY] += minutes if o.away and o.scheduled else 0.0
            counters[LOWERED] += minutes if o.lowered else 0.0
            counters[SOLE] += minutes if o.sole else 0.0
            totals = self.days.setdefault(o.room, {}).setdefault(day, {})
            for key, amount in (
                ("calling", minutes if o.calling else 0.0),
                ("sole", minutes if o.sole else 0.0),
                ("preheat", minutes if o.preheating else 0.0),
            ):
                totals[key] = totals.get(key, 0.0) + amount
            if o.late:
                totals["late"] = 1
            if o.leaked:
                totals["leak"] = totals.get("leak", 0) + 1
                if now.hour not in DAYTIME:
                    totals["leak_night"] = 1
            if o.lowered:
                found = self.lowered_by.setdefault(o.room, {}).get(day, [])
                self.lowered_by[o.room][day] = sorted({*found, *o.people_away})

    def record_fault(self, room: str, cause: str, now: datetime) -> None:
        causes = self.faults.setdefault(room, {}).setdefault(now.date().isoformat(), [])
        if cause not in causes:
            causes.append(cause)

    def prune(self, today: date) -> None:
        oldest = (today - KEEP).isoformat()
        for store in (self.slots, self.days, self.faults, self.lowered_by):
            for by_day in store.values():
                for day in [d for d in by_day if d < oldest]:
                    del by_day[day]
        for day in [d for d in self.boiler if d < oldest]:
            del self.boiler[day]

    def hours_per_week(self, room: str, key: str, since: date, until: date) -> float | None:
        """Average of a daily total over the observed days in [since, until)."""
        found = [
            t.get(key, 0.0)
            for d, t in self.days.get(room, {}).items()
            if since.isoformat() <= d < until.isoformat()
        ]
        return sum(found) / len(found) * 7 / 60 if found else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SCHEMA_VERSION,
            "slots": {
                r: {d: {str(s): c for s, c in slots.items()} for d, slots in days.items()}
                for r, days in self.slots.items()
            },
            "days": self.days,
            "faults": self.faults,
            "lowered_by": self.lowered_by,
            "boiler": self.boiler,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> AdviceLog:
        if not data or data.get("version") != SCHEMA_VERSION:
            return cls()
        try:
            return cls(
                slots={
                    r: {
                        d: {int(s): [float(x) for x in c] for s, c in slots.items()}
                        for d, slots in days.items()
                    }
                    for r, days in data.get("slots", {}).items()
                },
                days={r: {d: dict(t) for d, t in v.items()} for r, v in data.get("days", {}).items()},
                faults={r: {d: list(c) for d, c in v.items()} for r, v in data.get("faults", {}).items()},
                lowered_by={r: {d: list(c) for d, c in v.items()} for r, v in data.get("lowered_by", {}).items()},
                boiler={d: float(m) for d, m in data.get("boiler", {}).items()},
            )
        except (TypeError, ValueError, AttributeError):
            return cls()


def _time(slot: int) -> time:
    minutes = slot % SLOTS * SLOT_MINUTES
    return time(minutes // 60, minutes % 60)


def _slot(at: time) -> int:
    return (at.hour * 60 + at.minute) // SLOT_MINUTES


def _wasted_slots(by_day: Mapping[str, Mapping[int, Sequence[float]]], weekday: int, slots: range) -> set[int]:
    """Slots of a weekday in which comfort was, time and again, for nobody."""
    wasted = set()
    for slot in slots:
        seen = [
            c
            for d, found in by_day.items()
            if date.fromisoformat(d).weekday() == weekday
            and (c := found.get(slot)) is not None
            and c[OBSERVED] >= SLOT_MINUTES / 2
        ]
        hits = [c for c in seen if max(c[AWAY], c[LOWERED]) >= c[OBSERVED] / 2]
        if len(hits) >= MIN_OCCURRENCES and len(hits) >= MIN_SHARE * len(seen):
            wasted.add(slot)
    return wasted


def _saved_hours(by_day: Mapping[str, Mapping[int, Sequence[float]]], days: Collection[int], slots: range) -> float:
    """Boiler hours per week this Room alone caused in `slots` of those weekdays."""
    total = 0.0
    for weekday in days:
        found = [v for d, v in by_day.items() if date.fromisoformat(d).weekday() == weekday]
        if found:
            total += sum(v[s][SOLE] for v in found for s in slots if s in v) / len(found)
    return total / 60


def _trims(room: RoomConfig, by_day: Mapping[str, Mapping[int, Sequence[float]]]) -> list[Advice]:
    advice = []
    for window in room.schedule:
        if window.end <= window.start:
            continue  # past midnight: left to the user
        first, last = _slot(window.start), _slot(window.end)
        span = range(first, last)
        groups: dict[tuple[str, int], list[int]] = {}
        for weekday in sorted(window.days):
            wasted = _wasted_slots(by_day, weekday, span)
            if not wasted:
                continue
            if len(wasted) == len(span):
                groups.setdefault(("drop", 0), []).append(weekday)
                continue
            head = next(s for s in span if s not in wasted)
            tail = next(s for s in reversed(span) if s not in wasted) + 1
            if head > first:
                groups.setdefault(("start", head), []).append(weekday)
            if tail < last:
                groups.setdefault(("end", tail), []).append(weekday)
        for (edge, slot), days in groups.items():
            # Starting later (or not at all) also saves the pre-heat before the old start.
            lead = max(first - PREHEAT_LOOKBACK, 0)
            saved = _saved_hours(
                by_day,
                days,
                range(lead, last) if edge == "drop" else range(lead, slot) if edge == "start" else range(slot, last),
            )
            if saved < MIN_SAVING_H:
                continue
            start = None if edge == "drop" else _time(slot) if edge == "start" else window.start
            end = None if edge == "drop" else _time(slot) if edge == "end" else window.end
            change = ScheduleChange(window, tuple(days), start, end)
            advice.append(
                Advice(
                    f"trim_schedule_{room.id}_{edge}_{window.start:%H%M}_{window.end:%H%M}",
                    "trim_schedule", room.name, saved, tuple(days), start, end, change=change,
                )
            )
    return advice


def detect(
    log: AdviceLog,
    rooms: Sequence[RoomConfig],
    now: datetime,
    *,
    sensorless: Collection[str] = (),
    without_occupants: Collection[str] = (),
    suggestions: Sequence[Suggestion] = (),
) -> list[Advice]:
    """Everything worth telling right now: leaks first, then by boiler hours to be saved."""
    today = now.date()
    week = today - timedelta(days=7)
    boiler_week = [m for d, m in log.boiler.items() if d >= week.isoformat()]
    boiler_hours = sum(boiler_week) / 60
    found: list[Advice] = []
    for room in rooms:
        name = room.name
        daily = log.days.get(name, {})
        slots = log.slots.get(name, {})
        guessed = name in sensorless
        sole = log.hours_per_week(name, "sole", week, today + timedelta(days=1)) or 0.0

        leaks = [t for t in daily.values() if t.get("leak")]
        if len(leaks) >= MIN_OCCURRENCES:
            found.append(
                Advice(
                    f"leak_{room.id}", "leak", name, count=int(sum(t["leak"] for t in leaks)),
                    cause="" if any(t.get("leak_night") for t in leaks) else "sun", probably=guessed,
                )
            )
        for cause in sorted({c for causes in log.faults.get(name, {}).values() for c in causes}):
            count = sum(cause in causes for causes in log.faults[name].values())
            if count >= MIN_OCCURRENCES:
                found.append(Advice(f"fault_{room.id}_{cause}", "fault", name, count=count, cause=cause))
        if guessed:
            if len(daily) >= MIN_DAYS and (log.hours_per_week(name, "calling", week, today + timedelta(days=1)) or 0) >= MIN_SAVING_H:
                found.append(Advice(f"add_sensor_{room.id}", "add_sensor", name))
            continue  # temperature and schedule advice need a real room temperature

        if len(daily) >= MIN_DAYS and sole >= SOLE_HOURS and sole >= SOLE_SHARE * boiler_hours:
            found.append(Advice(f"sole_caller_{room.id}", "sole_caller", name, sole))
        limit = LONG_PREHEAT_FLOOR_MIN if room.floor_heating else LONG_PREHEAT_MIN
        long = [t["preheat"] for t in daily.values() if t.get("preheat", 0) > limit]
        late = sum(bool(t.get("late")) for t in daily.values())
        if len(long) >= MIN_OCCURRENCES:
            found.append(
                Advice(f"long_preheat_{room.id}", "long_preheat", name, count=len(long), cause=f"{median(long) / 60:.1f}")
            )
        if late >= MIN_OCCURRENCES and late >= MIN_SHARE * len(daily):
            found.append(Advice(f"late_{room.id}", "late", name, count=late))
        found += _trims(room, slots)

        if name in without_occupants:
            events = log.lowered_by.get(name, {})
            people = sorted(
                p
                for p in {p for away in events.values() for p in away}
                if sum(p in away for away in events.values()) >= max(MIN_OCCURRENCES, MIN_SHARE * len(events))
            )
            if people:
                found.append(Advice(f"occupants_{room.id}", "occupants", name, people=tuple(people)))
    by_name = {r.name: r for r in rooms}
    for s in suggestions:
        if (room_config := by_name.get(s.room)) is not None and s.room not in sensorless:
            found.append(
                Advice(
                    f"add_time_{room_config.id}_{s.start:%H%M}", "add_time", s.room,
                    days=s.days, start=s.start, count=s.events,
                )
            )
    return sorted(found, key=lambda a: (a.kind != "leak", -a.saving_hours, a.key))
