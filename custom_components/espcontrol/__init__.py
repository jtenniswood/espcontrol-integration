"""EspControl integration proof of concept."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import register_views
from .const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_WEB_PORT,
    DOMAIN,
    SERVICE_CREATE_PAIRING_TOKEN,
)
from .pairing import PairingStore
from .device import (
    EspControlRuntime,
    find_esphome_device,
    mac_from_entry,
    pairing_url,
    remove_empty_legacy_device,
    webserver_url,
)

type EspControlConfigEntry = ConfigEntry[EspControlRuntime]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration and its authenticated pairing API."""

    pairing = PairingStore()
    hass.data[DOMAIN] = {"pairing": pairing}
    register_views(hass, pairing)

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
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EspControlConfigEntry) -> bool:
    """Set up one discovered display."""

    device_id = entry.data[CONF_DEVICE_ID]
    host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
    web_port = entry.options.get(CONF_WEB_PORT, entry.data.get(CONF_WEB_PORT, 80))
    # The authenticated HA redirect issues a short-lived grant before sending
    # the browser to the display. If HA URLs are not configured, retain the
    # direct Visit link and the manual pairing service remains available.
    configuration_url = pairing_url(hass, device_id) or webserver_url(host, web_port)
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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EspControlConfigEntry) -> bool:
    """Unload one display runtime."""

    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
