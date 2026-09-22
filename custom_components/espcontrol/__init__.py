"""EspControl integration proof of concept."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import (
    Event,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .api import register_views
from .const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_WEB_PORT,
    DOMAIN,
    SIGNAL_ESPHOME_ENTITIES_UPDATED,
    CATALOG_PROTOCOL_VERSION,
    SERVICE_CREATE_PAIRING_TOKEN,
    SERVICE_SEARCH_ENTITIES,
)
from .pairing import PairingStore
from .device import (
    EspControlRuntime,
    find_esphome_device,
    mac_from_entry,
    remove_empty_legacy_device,
    webserver_url,
)

type EspControlConfigEntry = ConfigEntry[EspControlRuntime]

PLATFORMS = ("sensor", "binary_sensor")


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration and its authenticated pairing API."""

    pairing = PairingStore()
    hass.data[DOMAIN] = {"pairing": pairing}
    register_views(hass, pairing)

    @callback
    def _async_home_assistant_started(_event: Event) -> None:
        # ESPHome may finish loading after this config entry. A final startup
        # scan ensures the mirrors see entities regardless of setup order.
        async_dispatcher_send(hass, SIGNAL_ESPHOME_ENTITIES_UPDATED)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _async_home_assistant_started)

    async def create_pairing_token(call: ServiceCall) -> ServiceResponse:
        device_id = call.data[CONF_DEVICE_ID]
        entry = next(
            (
                candidate
                for candidate in hass.config_entries.async_entries(DOMAIN)
                if candidate.data.get(CONF_DEVICE_ID) == device_id
                and candidate.state is ConfigEntryState.LOADED
            ),
            None,
        )
        if entry is None:
            raise ServiceValidationError("The EspControl display is not configured")
        grant = pairing.issue(device_id)
        return {"device_id": device_id, "token": grant.token, "expires_at": grant.expires_at}

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_PAIRING_TOKEN,
        create_pairing_token,
        schema=vol.Schema({vol.Required(CONF_DEVICE_ID): str}),
        supports_response=SupportsResponse.ONLY,
    )

    async def search_entities(call: ServiceCall) -> ServiceResponse:
        """Return one bounded page of entity metadata to an ESPHome display."""

        from .catalog import build_entity_catalog

        raw_capabilities = call.data.get("capabilities", ())
        if isinstance(raw_capabilities, str):
            capabilities = tuple(
                value.strip() for value in raw_capabilities.split(",") if value.strip()
            )
        else:
            capabilities = tuple(raw_capabilities)
        entities, next_cursor = build_entity_catalog(
            hass,
            query=call.data.get("query", ""),
            field=call.data.get("field", "entity"),
            area=call.data.get("area") or None,
            device_id=call.data.get("device_id") or None,
            include_hidden=call.data.get("include_hidden", False),
            include_disabled=call.data.get("include_disabled", False),
            capabilities=capabilities,
            limit=call.data.get("limit", 25),
            cursor=call.data.get("cursor", 0),
        )
        return {
            "protocol_version": CATALOG_PROTOCOL_VERSION,
            "entities": entities,
            "next_cursor": next_cursor,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_ENTITIES,
        search_entities,
        schema=vol.Schema(
            {
                vol.Optional("query", default=""): vol.All(str, vol.Length(max=120)),
                vol.Optional("field", default="entity"): vol.All(str, vol.Length(max=40)),
                vol.Optional("area", default=""): vol.All(str, vol.Length(max=120)),
                vol.Optional("device_id", default=""): vol.All(str, vol.Length(max=120)),
                vol.Optional("include_hidden", default=False): cv.boolean,
                vol.Optional("include_disabled", default=False): cv.boolean,
                vol.Optional("capabilities", default=[]): vol.All(
                    cv.ensure_list, [vol.All(str, vol.Length(max=80))]
                ),
                vol.Optional("limit", default=25): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
                vol.Optional("cursor", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=10000)),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EspControlConfigEntry) -> bool:
    """Set up one discovered display."""

    device_id = entry.data[CONF_DEVICE_ID]
    host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
    web_port = entry.options.get(CONF_WEB_PORT, entry.data.get(CONF_WEB_PORT, 80))
    # The display serves the catalog bridge over its own web server. Visit must
    # therefore open that origin directly; no browser-held HA credential is
    # needed for entity searches.
    configuration_url = webserver_url(host, web_port)
    device_registry = dr.async_get(hass)
    if (mac := mac_from_entry(entry)) and (
        esphome_device := find_esphome_device(hass, mac)
    ):
        # ESPHome owns the native entities. Keep its device entry and Visit
        # link intact, while also creating an EspControl-owned registry entry
        # so every discovery appears under this integration.
        device_registry.async_update_device(
            esphome_device.id,
            configuration_url=configuration_url,
        )
        remove_empty_legacy_device(hass, entry, device_id, esphome_device.id)
    # Keep a useful device entry for every discovery. When ESPHome is present,
    # its native entities remain on the ESPHome-owned device entry because a
    # Home Assistant device can only belong to one config entry.
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, device_id)},
        configuration_url=configuration_url,
        name=entry.title,
        manufacturer="EspControl",
        model=entry.data.get("model"),
        connections={(dr.CONNECTION_NETWORK_MAC, mac)} if mac else set(),
    )
    runtime = EspControlRuntime(
        host=host,
        web_port=web_port,
    )
    hass.data[DOMAIN][entry.entry_id] = runtime
    await runtime.async_probe(async_get_clientsession(hass))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # The ESPHome entry is normally loaded first, but discovery order is not a
    # contract. This lets the mirror platforms rescan after both entries load.
    async_dispatcher_send(hass, SIGNAL_ESPHOME_ENTITIES_UPDATED)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EspControlConfigEntry) -> bool:
    """Unload one display runtime."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
