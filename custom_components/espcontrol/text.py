"""Mirror native ESPHome text settings with their validation metadata."""

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .control import EspControlControlMirror
from .mirror import async_setup_mirrors


class EspControlTextMirror(EspControlControlMirror, TextEntity):
    """A text setting that sends edits to ESPHome."""

    @property
    def native_value(self) -> str | None:
        return self.source_value

    @property
    def native_min(self) -> int:
        return self.source_attribute("min", 0)

    @property
    def native_max(self) -> int:
        return self.source_attribute("max", 255)

    @property
    def pattern(self) -> str | None:
        return self.source_attribute("pattern")

    @property
    def mode(self) -> TextMode:
        return TextMode(self.source_attribute("mode", TextMode.TEXT))

    async def async_set_value(self, value: str) -> None:
        await self.async_call_source("set_value", value=value)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_mirrors(hass, entry, "text", EspControlTextMirror, async_add_entities)
