"""All problems of one Room combined into a likely cause. No Home Assistant imports."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .models import Alert

# Alert code -> likely cause, most explanatory first: a dead valve also leaves a Room cold.
_CAUSES: tuple[tuple[str, str], ...] = (
    ("boiler_outage", "boiler_outage"),
    ("frost_risk", "frost_risk"),
    ("trv_offline", "valve_unreachable"),
    ("trv_off", "valve_off"),
    ("trv_write_failed", "valve_rejects"),
    ("not_warming", "no_heat"),
    ("target_not_reached", "too_cold"),
    ("low_battery", "battery"),
    ("sensor_stale", "sensor"),
)
URGENT = frozenset({"boiler_outage", "frost_risk"})


@dataclass(frozen=True)
class Diagnosis:
    room: str | None
    cause: str
    codes: tuple[str, ...]  # every symptom, in order of how much it explains

    @property
    def urgent(self) -> bool:
        return self.cause in URGENT


def diagnose(alerts: Sequence[Alert]) -> tuple[Diagnosis, ...]:
    """One diagnosis per Room (and one for the system), urgent ones first."""
    rank = {code: i for i, (code, _) in enumerate(_CAUSES)}
    cause = dict(_CAUSES)
    by_room: dict[str | None, set[str]] = {}
    for alert in alerts:
        if alert.code in rank:
            by_room.setdefault(alert.room, set()).add(alert.code)
    found = [
        Diagnosis(room, cause[codes[0]], codes)
        for room, symptoms in by_room.items()
        for codes in [tuple(sorted(symptoms, key=rank.__getitem__))]
    ]
    return tuple(sorted(found, key=lambda d: rank[d.codes[0]]))
