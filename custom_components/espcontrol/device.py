"""Device registry helpers and HTTP probe for the EspControl web API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientSession, ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import format_mac

from .const import CONF_DEVICE_ID, CONF_MAC, DOMAIN

ESPHOME_DOMAIN = "esphome"


def mac_from_entry(entry: ConfigEntry[Any]) -> str | None:
    """Return the device MAC, including for advertisements without ``mac``."""

    value = entry.data.get(CONF_MAC) or entry.data.get(CONF_DEVICE_ID)
    if not isinstance(value, str):
        return None
    mac = format_mac(value)
    parts = mac.split(":")
    if len(parts) != 6 or any(len(part) != 2 for part in parts):
        return None
    try:
        if any(int(part, 16) > 255 for part in parts):
            return None
    except ValueError:
        return None
    return mac


def webserver_url(host: str, port: int) -> str:
    """Build the URL shown by Home Assistant's device Visit action."""

    display_host = host
    if ":" in display_host and not display_host.startswith("["):
        display_host = f"[{display_host}]"
    port_suffix = "" if port == 80 else f":{port}"
    return f"http://{display_host}{port_suffix}"


def find_esphome_device(hass: HomeAssistant, mac: str) -> dr.DeviceEntry | None:
    """Find the existing ESPHome device for this physical panel, if present."""

    registry = dr.async_get(hass)
    for device in registry.async_get_devices(
        connections={(dr.CONNECTION_NETWORK_MAC, mac)}
    ):
        config_entry = hass.config_entries.async_get_entry(device.config_entry_id)
        if config_entry and config_entry.domain == ESPHOME_DOMAIN:
            return device
    return None


def remove_empty_legacy_device(
    hass: HomeAssistant,
    entry: ConfigEntry[Any],
    device_id: str,
    keep_device_id: str,
) -> None:
    """Remove the empty duplicate created by the first POC implementation."""

    registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    for device in registry.async_get_devices(
        identifiers={(DOMAIN, device_id)},
        config_entry_id=entry.entry_id,
    ):
        if device.id == keep_device_id:
            continue
        if not er.async_entries_for_device(entity_registry, device.id):
            registry.async_remove_device(device.id)


@dataclass(slots=True)
class EspControlRuntime:
    """Runtime state kept per config entry."""

    host: str
    web_port: int = 80
    available: bool = False
    identity: dict[str, object] | None = None

    async def async_probe(self, session: ClientSession) -> bool:
        """Probe identity without failing setup when the display is offline."""

        url = f"http://{self.host}:{self.web_port}/api/v1/identity"
        try:
            async with session.get(url, timeout=ClientTimeout(total=3)) as response:
                if response.status != 200:
                    self.available = False
                    return False
                payload = await response.json(content_type=None)
        except Exception:  # noqa: BLE001 - an offline LAN device is expected.
            self.available = False
            return False
        if not isinstance(payload, dict):
            self.available = False
            return False
        self.identity = payload
        self.available = True
        return True
