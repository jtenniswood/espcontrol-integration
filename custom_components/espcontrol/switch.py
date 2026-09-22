"""Mirror native ESPHome switches."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .control import EspControlToggleMirror
from .mirror import async_setup_mirrors


class EspControlSwitchMirror(EspControlToggleMirror, SwitchEntity):
    """A switch that follows its native source."""

    @property
    def device_class(self) -> str | None:
        return self.source_attribute("device_class")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_mirrors(
        hass, entry, "switch", EspControlSwitchMirror, async_add_entities
    )
