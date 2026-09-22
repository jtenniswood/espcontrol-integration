"""Native ESPHome catalog action; transport validation stays at this boundary."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.helpers import config_validation as cv

from .catalog import build_entity_catalog
from .catalog_contract import CATALOG_PROTOCOL_VERSION, REQUEST_LIMITS, TRANSPORTS
from .const import DOMAIN, SERVICE_SEARCH_ENTITIES

NATIVE = TRANSPORTS["native"]


def _capabilities(value: object) -> list[str]:
    """ESPHome can send a comma-separated string; HA callers can send a list."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return cv.ensure_list(value)


SEARCH_SCHEMA = vol.Schema(
    {
        **{
            vol.Optional(key, default="entity" if key == "field" else ""): vol.All(
                str, vol.Length(max=REQUEST_LIMITS[key])
            )
            for key in ("query", "field", "area", "device_id")
        },
        vol.Optional("include_hidden", default=False): cv.boolean,
        vol.Optional("include_disabled", default=False): cv.boolean,
        vol.Optional("capabilities", default=[]): vol.All(
            _capabilities, [vol.All(str, vol.Length(max=REQUEST_LIMITS["capability"]))]
        ),
        vol.Optional("limit", default=NATIVE["default_limit"]): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=NATIVE["max_limit"])
        ),
        vol.Optional("cursor", default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=NATIVE["max_cursor"])
        ),
    }
)


@callback
def async_register_catalog_action(hass: HomeAssistant) -> None:
    """Expose the versioned catalog through the existing ESPHome connection."""

    async def search_entities(call: ServiceCall) -> dict:
        values = dict(call.data)
        values["area"] = values["area"] or None
        values["device_id"] = values["device_id"] or None
        entities, cursor = build_entity_catalog(hass, **values)
        return {
            NATIVE["version_key"]: CATALOG_PROTOCOL_VERSION,
            "entities": entities,
            "next_cursor": cursor,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_ENTITIES,
        search_entities,
        schema=SEARCH_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
