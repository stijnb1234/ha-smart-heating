"""Pure trackers of short-lived Room behaviour that feed the learned insights and alerts."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

from .calibration import RadiatorState
from .models import EPSILON

COAST_MAX_WAIT = timedelta(minutes=60)
COAST_FALL = 0.1  # K below the peak that ends the coast observation
# No new peak for this long ends it too: a sensor that moves in 0.5 K steps never shows a fall.
COAST_PLATEAU = timedelta(minutes=20)
STALL_AFTER = timedelta(minutes=45)
# Floor heating responds slowly: it gets as long as its default pre-heat lead time.
STALL_AFTER_FLOOR = timedelta(hours=3)
STALL_RISE = 0.3  # K of warming that counts as progress
STALL_REST = timedelta(hours=3)  # how long a stalled Room stops calling before it tries again
# A Room that would need longer than this to reach its target is stalled even though it creeps up.
STALL_REACH = timedelta(hours=6)
# The rise rate is measured over this long, so one step of a coarse sensor says little.
STALL_RATE_WINDOW = timedelta(hours=2)


class CoastTracker:
    """After a Room stops calling for heat, how much further does it rise before it peaks."""

    def __init__(self) -> None:
        self._calling: dict[str, bool] = {}
        # room -> (stopped_at, temp when it stopped, peak so far, when the peak was reached)
        self._stopped: dict[str, tuple[datetime, float, float, datetime]] = {}

    def observe(
        self, room: str, now: datetime, temp: float | None, calling: bool, valid: bool = True
    ) -> float | None:
        """The finished coast (K) once the Room peaked, else None.

        `valid` is False while something other than the schedule steers the Room (window pause,
        boost, away), which would make the observation meaningless.
        """
        was_calling = self._calling.get(room, False)
        self._calling[room] = calling
        if temp is None or calling or not valid:
            self._stopped.pop(room, None)
            return None
        if was_calling:
            self._stopped[room] = (now, temp, temp, now)
            return None
        stopped = self._stopped.get(room)
        if stopped is None:
            return None
        at, start, peak, peaked_at = stopped
        if temp > peak:
            peak, peaked_at = temp, now
        if temp < peak - COAST_FALL or now - peaked_at >= COAST_PLATEAU or now - at >= COAST_MAX_WAIT:
            del self._stopped[room]
            return peak - start
        self._stopped[room] = (at, start, peak, peaked_at)
        return None

    def settling(self) -> frozenset[str]:
        """Rooms whose call ended and whose temperature has not peaked yet."""
        return frozenset(self._stopped)


class StallTracker:
    """Rooms that keep calling for heat without getting anywhere (stuck valve, open window):
    flat, or rising so slowly that the target stays out of reach.

    Such a Room cannot be helped by the boiler, so it rests: it stops calling for `STALL_REST`,
    then gets another try. It stays stalled until it warms up fast enough (also on other Rooms'
    calls) or no longer needs heat.
    """

    def __init__(self) -> None:
        self._since: dict[str, tuple[datetime, float]] = {}  # running try: (started, temp then)
        self._stalled: dict[str, datetime] = {}  # stalled room -> resting until
        # Readings of a running try, or since it stalled: the last STALL_RATE_WINDOW and one before.
        self._readings: dict[str, deque[tuple[datetime, float]]] = {}

    def observe(
        self,
        room: str,
        now: datetime,
        temp: float | None,
        calling: bool,
        *,
        unmet: bool = True,
        heated: bool = True,
        after: timedelta = STALL_AFTER,
        target: float | None = None,
    ) -> None:
        """`unmet`: the Room is still colder than a target it may call for. `heated`: a call
        actually reaches the boiler, so a Room that does not warm up is the Room's own fault.
        `target`: also judge whether the Room reaches it within STALL_REACH; None (floor
        heating, slow by nature) only judges whether it warms at all."""
        if temp is None or not unmet:
            self.reset(room)
            return
        if room not in self._stalled and not (calling and heated):
            self.reset(room)
            return
        readings = self._readings.setdefault(room, deque())
        readings.append((now, temp))
        while len(readings) > 1 and now - readings[1][0] >= STALL_RATE_WINDOW:
            readings.popleft()
        if room in self._stalled and self._recovered(readings, temp, target):
            del self._stalled[room]
            self._since.pop(room, None)
        if not (calling and heated):
            self._since.pop(room, None)
            return
        started = self._since.get(room)
        if started is None or temp >= started[1] + STALL_RISE - EPSILON:
            started = self._since[room] = (now, temp)
        flat = now - started[0] >= after
        then, before = readings[0]
        crawling = (
            target is not None
            and now - then >= STALL_RATE_WINDOW
            and not self._reaches(temp - before, now - then, target - temp)
        )
        if flat or crawling:
            # Start over: what counts from here on is how the Room does after giving up.
            self._since.pop(room, None)
            self._stalled[room] = now + STALL_REST
            self._readings[room] = deque([(now, temp)])

    @staticmethod
    def _reaches(rise: float, over: timedelta, shortfall: float) -> bool:
        return rise * (STALL_REACH / over) >= shortfall - EPSILON

    def _recovered(
        self, readings: deque[tuple[datetime, float]], temp: float, target: float | None
    ) -> bool:
        rise = temp - min(value for _, value in readings)
        if rise < STALL_RISE - EPSILON:
            return False
        return target is None or self._reaches(rise, STALL_RATE_WINDOW, target - temp)

    def reset(self, room: str) -> None:
        self._since.pop(room, None)
        self._stalled.pop(room, None)
        self._readings.pop(room, None)

    def stalled(self) -> frozenset[str]:
        return frozenset(self._stalled)

    def resting(self, now: datetime) -> frozenset[str]:
        """Stalled Rooms that do not call for heat right now."""
        return frozenset(r for r, until in self._stalled.items() if now < until)


RADIATOR_WARMUP = timedelta(minutes=30)
# Warmth above this counts as a hot radiator for calibration entries.
WARM_ENOUGH = 0.8


class RadiatorWarmth:
    """How warm each radiator is, from 0 (cold) to 1 (hot), from when it was being heated."""

    def __init__(self) -> None:
        # room -> (first seen, last seen, heated then, warmth)
        self._state: dict[str, tuple[datetime, datetime, bool, float]] = {}

    def observe(self, room: str, now: datetime, hot: bool) -> None:
        first, last, was_hot, warmth = self._state.get(room, (now, now, hot, 0.0))
        step = (now - last) / (RADIATOR_WARMUP if was_hot else RADIATOR_COOLDOWN)
        warmth = min(max(warmth + (step if was_hot else -step), 0.0), 1.0)
        self._state[room] = (first, now, hot, warmth)

    def warmth(self, room: str) -> float:
        return self._state[room][3] if room in self._state else 0.0

    def settled(self, room: str, now: datetime) -> RadiatorState | None:
        """The radiator's state when it is clearly cold or hot. Unknown shortly after a start:
        what the radiator did before then was not seen."""
        if room not in self._state or now - self._state[room][0] < RADIATOR_COOLDOWN:
            return None
        _, _, hot, warmth = self._state[room]
        if warmth >= WARM_ENOUGH:
            return "heating"
        return "cold" if not hot and warmth <= EPSILON else None


# A Room within this much of frost-hold that has not warmed for FROST_AFTER is at risk.
FROST_BAND = 1.0
FROST_AFTER = timedelta(hours=1)


class FrostTracker:
    """Rooms near frost-hold that are not getting warmer."""

    def __init__(self) -> None:
        self._since: dict[str, tuple[datetime, float]] = {}  # (since, lowest temp seen)
        self._at_risk: set[str] = set()

    def observe(self, room: str, now: datetime, temp: float | None, frost_hold: float) -> None:
        if temp is None or temp > frost_hold + FROST_BAND:
            self._since.pop(room, None)
            self._at_risk.discard(room)
            return
        since, low = self._since.get(room, (now, temp))
        if temp >= low + STALL_RISE - EPSILON:
            since, low = now, temp
            self._at_risk.discard(room)
        self._since[room] = (since, min(low, temp))
        if now - since >= FROST_AFTER:
            self._at_risk.add(room)

    def at_risk(self) -> frozenset[str]:
        return frozenset(self._at_risk)


LEAK_RISE = 1.0  # K within LEAK_PERIOD
LEAK_PERIOD = timedelta(minutes=30)
LEAK_MARGIN = 0.5  # this far above the valve's setpoint it should be shut
LEAK_QUIET = timedelta(hours=1)  # after the Room's own call its radiator is still warm


class LeakTracker:
    """Rooms that warm up on other Rooms' calls although their valve should be closed."""

    def __init__(self) -> None:
        self._readings: dict[str, deque[tuple[datetime, float]]] = {}
        self._own_call: dict[str, datetime] = {}
        self._reported: set[str] = set()

    def observe(
        self, room: str, now: datetime, temp: float | None, setpoint: float, calling: bool, boiler_on: bool
    ) -> bool:
        """True once per stretch in which the Room warmed up while it should not."""
        if calling:
            self._own_call[room] = now
        quiet = room not in self._own_call or now - self._own_call[room] >= LEAK_QUIET
        if temp is None or not boiler_on or not quiet or temp <= setpoint + LEAK_MARGIN:
            self._readings.pop(room, None)
            self._reported.discard(room)
            return False
        readings = self._readings.setdefault(room, deque())
        readings.append((now, temp))
        while now - readings[0][0] > LEAK_PERIOD:
            readings.popleft()
        if room in self._reported or temp - min(t for _, t in readings) < LEAK_RISE - EPSILON:
            return False
        self._reported.add(room)
        return True


# Long enough for the remaining fall to stay below the lowest learned window threshold (0.5 K).
RADIATOR_COOLDOWN = timedelta(minutes=60)


class RadiatorCooldown:
    """Rooms whose radiator was hot until recently and is now cooling down.

    A radiator is hot while the boiler runs and its Room is below target (the valve is open).
    For `RADIATOR_COOLDOWN` after that ends the TRV's own sensor, mounted on the valve, keeps
    falling although the Room does not cool: open-window detection must not trust it then.
    """

    def __init__(self) -> None:
        self._hot: dict[str, bool] = {}
        self._cooling_since: dict[str, datetime] = {}

    def observe(self, room: str, now: datetime, hot: bool) -> None:
        if hot:
            self._cooling_since.pop(room, None)
        elif self._hot.get(room, False):
            self._cooling_since[room] = now
        self._hot[room] = hot

    def cooling(self, now: datetime) -> frozenset[str]:
        return frozenset(r for r, since in self._cooling_since.items() if now - since < RADIATOR_COOLDOWN)
