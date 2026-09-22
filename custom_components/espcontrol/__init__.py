"""Home Assistant companion to ESPHome displays."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_DEVICE_ID, CONF_HOST, CONF_WEB_PORT, DOMAIN, MIRROR_PLATFORMS
from .device import mac_from_entry, webserver_url
from .legacy import LegacyCatalogAdapter
from .migrations import async_migrate_entry  # noqa: F401 -- HA lifecycle entry point
from .runtime import EspControlRuntime
from .services import async_register_catalog_action

type EspControlConfigEntry = ConfigEntry[EspControlRuntime]

PLATFORMS = MIRROR_PLATFORMS


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register the native action and the contained legacy compatibility API."""
    legacy = LegacyCatalogAdapter(hass)
    hass.data[DOMAIN] = legacy
    legacy.async_setup()
    async_register_catalog_action(hass)
    return True


async def _async_update_entry(
    hass: HomeAssistant, entry: EspControlConfigEntry
) -> None:
    """Apply discovery and options changes to the runtime and both Visit links."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: EspControlConfigEntry) -> bool:
    host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
    web_port = entry.options.get(CONF_WEB_PORT, entry.data.get(CONF_WEB_PORT, 80))
    mac = mac_from_entry(entry)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.data[CONF_DEVICE_ID])},
        configuration_url=webserver_url(host, web_port),
        name=entry.title,
        manufacturer="EspControl",
        model=entry.data.get("model"),
        connections={(dr.CONNECTION_NETWORK_MAC, mac)} if mac else set(),
    )
    entry.runtime_data = runtime = EspControlRuntime(hass, entry, host, web_port)
    entry.async_on_unload(runtime.async_stop)
    await runtime.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EspControlConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].async_revoke(entry.data[CONF_DEVICE_ID])
        return True
    return False


async def async_remove_entry(hass: HomeAssistant, entry: EspControlConfigEntry) -> None:
    if legacy := hass.data.get(DOMAIN):
        legacy.async_revoke(entry.data[CONF_DEVICE_ID])
