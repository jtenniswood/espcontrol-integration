"""Mirror native ESPHome numeric settings with their units and limits."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .control import EspControlControlMirror
from .mirror import async_setup_mirrors


class EspControlNumberMirror(EspControlControlMirror, NumberEntity):
    """Forward numeric settings in the source's exposed Home Assistant unit."""

    @property
    def native_value(self) -> float | None:
        value = self.source_value
        return float(value) if value is not None else None

    @property
    def native_min_value(self) -> float:
        return self.source_attribute("min", 0)

    @property
    def native_max_value(self) -> float:
        return self.source_attribute("max", 100)

    @property
    def native_step(self) -> float | None:
        return self.source_attribute("step")

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.source_attribute("unit_of_measurement")

    @property
    def device_class(self) -> str | None:
        return self.source_attribute("device_class")

    @property
    def mode(self) -> NumberMode:
        return NumberMode(self.source_attribute("mode", NumberMode.AUTO))

    async def async_set_native_value(self, value: float) -> None:
        await self.async_call_source("set_value", value=value)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_mirrors(
        hass, entry, "number", EspControlNumberMirror, async_add_entities
    )
