"""Thin Home Assistant Store wrapper persisting TRV calibration (keyed by Room id)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .engine.calibration import SCHEMA_VERSION, Calibration
from .rooms import RoomKeys

STORAGE_KEY = "smart_heating.calibration"
SECTIONS = ("rooms",)


class CalibrationStore:
    def __init__(self, hass: HomeAssistant, keys: RoomKeys) -> None:
        self._store: Store = Store(hass, SCHEMA_VERSION, STORAGE_KEY)
        self._keys = keys

    async def async_load(self) -> Calibration:
        return Calibration.from_dict(self._keys.sections_to_names(await self._store.async_load(), SECTIONS))

    async def async_save(self, calibration: Calibration) -> None:
        await self._store.async_save(self._keys.sections_to_ids(calibration.to_dict(), SECTIONS))
