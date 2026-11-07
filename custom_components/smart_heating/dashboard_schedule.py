"""The Schedule view: per room, from what moment it is kept warm, as a plain weekly overview.

Built from the stored rooms' comfort windows, so it shows the schedule only (no Boost, vacation
or pre-heat). No Home Assistant imports.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .engine import DEFAULT_COMFORT, DEFAULT_SETBACK
from .i18n import number, tr, weekday

DAY_MINUTES = 24 * 60
STEP = 30  # one bar cell = 30 minutes
CELLS = DAY_MINUTES // STEP
WARM, COLD = "█", "·"

Intervals = tuple[tuple[int, int], ...]


def _minutes(text: str) -> int:
    hh, mm = text.split(":")[:2]
    return int(hh) * 60 + int(mm)


def week_intervals(windows: Sequence[Mapping[str, Any]]) -> list[Intervals]:
    """Warm intervals per weekday (Monday=0) in minutes; a window past midnight spills into the next day."""
    days: list[list[tuple[int, int]]] = [[] for _ in range(7)]
    for w in windows:
        start, end = _minutes(w["start"]), _minutes(w["end"])
        for d in w["days"]:
            if start < end:
                days[d].append((start, end))
            else:
                days[d].append((start, DAY_MINUTES))
                if end:
                    days[(d + 1) % 7].append((0, end))
    return [_merge(day) for day in days]


def _merge(spans: list[tuple[int, int]]) -> Intervals:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _bar(spans: Intervals) -> str:
    cells = []
    for i in range(CELLS):
        lo, hi = i * STEP, (i + 1) * STEP
        cells.append(WARM if any(s < hi and e > lo for s, e in spans) else COLD)
    return "".join(cells)


def _ruler() -> str:
    return "".join(f"{h:02d}    " for h in range(0, 24, 3))


def _groups(week: list[Intervals]) -> list[tuple[list[int], Intervals]]:
    """Runs of consecutive weekdays with the same warm times (Mon-Fri, Sat-Sun)."""
    groups: list[tuple[list[int], Intervals]] = []
    for d, spans in enumerate(week):
        if groups and groups[-1][1] == spans:
            groups[-1][0].append(d)
        else:
            groups.append(([d], spans))
    return groups


def room_schedule_markdown(room: Mapping[str, Any], lang: str) -> str:
    comfort = float(room.get("comfort", DEFAULT_COMFORT))
    setback = float(room.get("setback", DEFAULT_SETBACK))
    week = week_intervals(room.get("schedule", ()))
    t = lambda key, **p: tr(lang, key, **p)  # noqa: E731
    lines = [
        t("dash.schedule.temps", comfort=number(comfort, lang), setback=number(setback, lang)),
        "",
        f"| {t('dash.schedule.days')} | `{_ruler()}` | {t('dash.schedule.warm')} |",
        "|---|---|---|",
    ]
    for days, spans in _groups(week):
        first, last = days[0], days[-1]
        label = weekday(lang, first) if first == last else f"{weekday(lang, first)}–{weekday(lang, last)}"
        times = ", ".join(f"{_clock(s)}–{_clock(e)}" for s, e in spans) or t("dash.schedule.none")
        lines.append(f"| **{label}** | `{_bar(spans)}` | {times} |")
    return "\n".join(lines)
