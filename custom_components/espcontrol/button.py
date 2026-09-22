"""Mirror native ESPHome buttons, including wake, restart and firmware actions."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .control import EspControlControlMirror
from .mirror import async_setup_mirrors


class EspControlButtonMirror(EspControlControlMirror, ButtonEntity):
    """A button that presses its native source."""

    @property
    def device_class(self) -> str | None:
        return self.source_attribute("device_class")

    async def async_press(self) -> None:
        await self.async_call_source("press")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_mirrors(
        hass, entry, "button", EspControlButtonMirror, async_add_entities
    )
