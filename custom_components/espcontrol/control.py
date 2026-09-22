"""Forward control actions through the existing native ESPHome entities."""

from typing import Any

from homeassistant.const import ATTR_ENTITY_ID, STATE_ON
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .mirror import EspControlMirror


class EspControlControlMirror(EspControlMirror):
    """Keep native ESPHome as the sole owner of device commands."""

    async def async_call_source(self, service: str, **data: Any) -> None:
        source = self._source
        current = (
            er.async_get(self.hass).async_get(source.entity_id) if source else None
        )
        if (
            source is None
            or current is None
            or current.id != source.id
            or current.disabled
            or not self.available
        ):
            raise HomeAssistantError("The native ESPHome control is unavailable")
        await self.hass.services.async_call(
            source.domain,
            service,
            {**data, ATTR_ENTITY_ID: source.entity_id},
            blocking=True,
            context=self._context,
        )


class EspControlToggleMirror(EspControlControlMirror):
    """Shared on/off state and actions for switches and lights."""

    @property
    def is_on(self) -> bool | None:
        value = self.source_value
        return value == STATE_ON if value is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_call_source("turn_on", **kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_call_source("turn_off", **kwargs)
