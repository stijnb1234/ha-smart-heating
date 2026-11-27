"""Guided calibration of a TRV's sensor against a thermometer held in the room. No HA imports.

A sensor on the radiator valve reads about right with a cold radiator and several degrees high
with a hot one, so entries are kept apart per radiator state and both are needed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Any, Literal

SCHEMA_VERSION = 1
MAX_ENTRIES = 5  # newest kept per Room and state
MIN_READING, MAX_READING = 0.0, 40.0
MAX_DIFFERENCE = 15.0  # a larger gap between thermometer and TRV is taken for a typo

RadiatorState = Literal["cold", "heating"]
STATES: tuple[RadiatorState, ...] = ("cold", "heating")


class CalibrationError(ValueError):
    """Why an entry was refused; `key` names the user-facing message."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


@dataclass(frozen=True)
class Offset:
    """Degrees to add to the TRV reading: for the radiator as it is now, and when fully hot."""

    current: float
    heating: float


class Calibration:
    def __init__(self) -> None:
        # room -> state -> (when, thermometer minus TRV), oldest first
        self._entries: dict[str, dict[RadiatorState, list[tuple[datetime, float]]]] = {}

    def add(self, room: str, state: RadiatorState, at: datetime, reading: float, trv: float) -> None:
        if not MIN_READING <= reading <= MAX_READING or abs(reading - trv) > MAX_DIFFERENCE:
            raise CalibrationError("calibration_implausible")
        entries = self._entries.setdefault(room, {}).setdefault(state, [])
        entries.append((at, reading - trv))
        del entries[:-MAX_ENTRIES]

    def clear(self, room: str) -> None:
        self._entries.pop(room, None)

    def states(self, room: str) -> frozenset[RadiatorState]:
        return frozenset(self._entries.get(room, {}))

    def offset(self, room: str, warmth: float) -> Offset | None:
        """None until both states have an entry. `warmth`: 0 (cold radiator) to 1 (hot)."""
        entries = self._entries.get(room, {})
        if any(state not in entries for state in STATES):
            return None
        cold, hot = (median(d for _, d in entries[state]) for state in STATES)
        return Offset(cold + (hot - cold) * warmth, hot)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SCHEMA_VERSION,
            "rooms": {
                room: {state: [[at.isoformat(), d] for at, d in found] for state, found in states.items()}
                for room, states in self._entries.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> Calibration:
        calibration = cls()
        if not data or data.get("version") != SCHEMA_VERSION:
            return calibration
        try:
            for room, states in data.get("rooms", {}).items():
                calibration._entries[room] = {
                    state: [(datetime.fromisoformat(at), float(d)) for at, d in states[state]]
                    for state in STATES
                    if states.get(state)
                }
        except (TypeError, ValueError, AttributeError):
            return cls()
        return calibration
