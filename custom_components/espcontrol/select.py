"""Mirror native ESPHome selectors and their allowed options."""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .control import EspControlControlMirror
from .mirror import async_setup_mirrors


class EspControlSelectMirror(EspControlControlMirror, SelectEntity):
    """A selector whose options and current selection come from ESPHome."""

    @property
    def current_option(self) -> str | None:
        return self.source_value

    @property
    def options(self) -> list[str]:
        return self.source_attribute("options", [])

    async def async_select_option(self, option: str) -> None:
        await self.async_call_source("select_option", option=option)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_mirrors(
        hass, entry, "select", EspControlSelectMirror, async_add_entities
    )
