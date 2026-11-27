"""Thin HA glue: per Room without a room sensor, a box to enter what a thermometer reads there.

Entering a value records one calibration entry (see engine/calibration.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTemperature

from .const import DOMAIN
from .dashboard import entity_id
from .engine import RoomConfig
from .engine.calibration import MAX_READING, MIN_READING
from .i18n import tr
from .rooms import calibratable_rooms

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


class ThermometerReading(NumberEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = MIN_READING
    _attr_native_max_value = MAX_READING
    _attr_native_step = 0.1
    _attr_mode = NumberMode.BOX
    _attr_native_value: float | None = None

    def __init__(self, entry_id: str, room: RoomConfig, state: dict) -> None:
        self._room, self._state = room.name, state
        self._attr_name = tr(state["lang"], "entity.thermometer", room=room.name)
        self._attr_unique_id = f"{entry_id}_thermometer_{room.id}"
        self.entity_id = entity_id("number", room.id, "thermometer")

    async def async_set_native_value(self, value: float) -> None:
        await self._state["coordinator"].async_calibrate(self._room, value)
        self._attr_native_value = value
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    state = hass.data[DOMAIN][entry.entry_id]
    names = calibratable_rooms(state["rooms"], state["sensor_entities"], state["coordinator"].trv_devices)
    async_add_entities(ThermometerReading(entry.entry_id, r, state) for r in state["rooms"] if r.name in names)
