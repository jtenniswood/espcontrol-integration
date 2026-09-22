"""Mirror native ESPHome sensors on the EspControl device."""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfInformation,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .mirror import EspControlMirror, async_setup_mirrors


class EspControlSensorMirror(EspControlMirror, SensorEntity):
    """A read-only native sensor copy, including text and timestamp sensors."""

    @property
    def suggested_display_precision(self) -> int | None:
        """Show percentages and byte counts as integers without losing history."""
        if self.native_unit_of_measurement in {PERCENTAGE, UnitOfInformation.BYTES}:
            return 0
        return None

    @callback
    def _source_updated(self, event: Event) -> None:
        # A source may publish its unit after setup. HA normally initializes
        # suggested precision when the registry entry is added or updated.
        self.async_registry_entry_updated()
        super()._source_updated(event)

    @property
    def native_value(self) -> str | float | date | datetime | None:
        state = self._state()
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return None
        if self.device_class == SensorDeviceClass.TIMESTAMP:
            return dt_util.parse_datetime(state.state)
        if self.device_class == SensorDeviceClass.DATE:
            return dt_util.parse_date(state.state)
        # HA exposes the source's display value in its display unit. Leave
        # numeric conversion to SensorEntity so text sensors keep their text.
        return state.state

    @property
    def native_unit_of_measurement(self) -> str | None:
        state = self._state()
        return state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) if state else None

    @property
    def device_class(self) -> SensorDeviceClass | None:
        state = self._state()
        value = state.attributes.get(ATTR_DEVICE_CLASS) if state else None
        try:
            return SensorDeviceClass(value) if value else None
        except ValueError:
            return None

    @property
    def state_class(self) -> SensorStateClass | None:
        state = self._state()
        value = state.attributes.get("state_class") if state else None
        try:
            return SensorStateClass(value) if value else None
        except ValueError:
            return None

    @property
    def last_reset(self) -> datetime | None:
        state = self._state()
        value = state.attributes.get("last_reset") if state else None
        return dt_util.parse_datetime(value) if isinstance(value, str) else None

    @property
    def options(self) -> list[str] | None:
        state = self._state()
        return state.attributes.get("options") if state else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_setup_mirrors(
        hass, entry, "sensor", EspControlSensorMirror, async_add_entities
    )
