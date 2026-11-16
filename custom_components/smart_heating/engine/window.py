"""Open-window detection: a rate-of-fall rule over Room temperature history."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from .models import EPSILON, EngineInput, RoomConfig, SensorReading

MIN_PAUSE = timedelta(minutes=15)
MAX_PAUSE = timedelta(minutes=30)
# The TRV sensor sits on the radiator and swings by degrees without the room changing. A TRV that
# reports its valve is judged by that. Otherwise, with a room sensor on top, a fast fall there must show in the room too: at least this share of the
# threshold (two steps of a sensor that reports in 0.5 K steps), but not less than MIN_CORROBORATION K.
CORROBORATION = 0.75
MIN_CORROBORATION = 0.3


def recent_drop(
    history: Sequence[SensorReading],
    now: datetime,
    period: timedelta,
    ceiling: float | None = None,
) -> float | None:
    """How far the latest reading is below the highest one within `period` (None: too few).

    With a `ceiling` (the room's comfort temperature) the highest reading counts at most as the ceiling: a room
    that overshot its comfort temperature and settles back is not a window, only a fall below it is."""
    cutoff = now - period
    recent = [r.value for r in history if cutoff <= r.at <= now]
    if len(recent) < 2:
        return None
    peak = max(recent)
    if ceiling is not None:
        peak = min(peak, ceiling)
    return peak - recent[-1]


def drop_threshold(room: RoomConfig, inp: EngineInput) -> float:
    """The configured drop is the ceiling; a learned, lower value fits the Room's own noise."""
    return min(room.window_drop, inp.window_thresholds.get(room.name, room.window_drop))


def window_history(room: RoomConfig, inp: EngineInput) -> Sequence[SensorReading]:
    """Readings to judge a fast fall by: the TRV-first history, but only the external sensor
    while the radiator cools down (none when the Room has no external sensor)."""
    if room.name in inp.cooling_rooms:
        return inp.external_history.get(room.name, ())
    return inp.temp_history.get(room.name, ())


def _fast_fall(room: RoomConfig, inp: EngineInput, ceiling: float) -> bool:
    threshold = drop_threshold(room, inp)
    drop = recent_drop(window_history(room, inp), inp.now, room.window_period, ceiling)
    if drop is None or drop < threshold - EPSILON:
        return False
    if room.name in inp.cooling_rooms or room.name in inp.valve_known:
        return True  # judged by the room sensor alone, or the valve state already explains the TRV sensor
    room_drop = recent_drop(inp.external_history.get(room.name, ()), inp.now, room.window_period, ceiling)
    if room_drop is None:
        return True  # no room sensor to check against
    return room_drop >= max(threshold * CORROBORATION, MIN_CORROBORATION) - EPSILON


def window_pauses(inp: EngineInput) -> dict[str, datetime]:
    """Rooms currently paused, mapped to when their pause ends."""
    paused: dict[str, datetime] = {}
    for room in inp.config.rooms:
        if not room.window_detection:
            continue
        until = inp.last_commands.window_paused_until.get(room.name)
        if until is not None and inp.now < until:
            paused[room.name] = until
        elif _fast_fall(room, inp, room.comfort):
            length = min(max(room.window_pause, MIN_PAUSE), MAX_PAUSE)
            paused[room.name] = inp.now + length
    return paused
