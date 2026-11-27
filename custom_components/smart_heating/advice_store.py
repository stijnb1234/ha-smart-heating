"""Thin Home Assistant Store wrapper persisting advice evidence and choices (Rooms keyed by id)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .advice_actions import AdviceState
from .engine.advice import SCHEMA_VERSION, AdviceLog
from .rooms import RoomKeys

STORAGE_KEY = "smart_heating.advice"
SECTIONS = ("slots", "days", "faults", "lowered_by")


class AdviceStore:
    def __init__(self, hass: HomeAssistant, keys: RoomKeys) -> None:
        self._store: Store = Store(hass, SCHEMA_VERSION, STORAGE_KEY)
        self._keys = keys

    async def async_load(self) -> tuple[AdviceLog, AdviceState]:
        data = await self._store.async_load() or {}
        log = AdviceLog.from_dict(self._keys.sections_to_names(data.get("log"), SECTIONS))
        return log, AdviceState.from_dict(data.get("state"))

    async def async_save(self, log: AdviceLog, state: AdviceState) -> None:
        await self._store.async_save(
            {"log": self._keys.sections_to_ids(log.to_dict(), SECTIONS), "state": state.to_dict()}
        )
