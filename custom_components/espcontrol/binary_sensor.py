"""Mirror native ESPHome binary sensors on the EspControl device."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .mirror import EspControlMirror, async_setup_mirrors


class EspControlBinarySensorMirror(EspControlMirror, BinarySensorEntity):
    """A read-only copy of a native binary sensor's state and metadata."""

    @property
    def is_on(self) -> bool | None:
        state = self._state()
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return None
        return state.state == STATE_ON

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        state = self._state()
        value = state.attributes.get("device_class") if state else None
        try:
            return BinarySensorDeviceClass(value) if value else None
        except ValueError:
            return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_setup_mirrors(
        hass, entry, "binary_sensor", EspControlBinarySensorMirror, async_add_entities
    )
