"""Stable display identity, address formatting and native device association."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import format_mac

from .const import CONF_DEVICE_ID, CONF_MAC

ESPHOME_DOMAIN = "esphome"


def mac_from_entry(entry: ConfigEntry[Any]) -> str | None:
    """Return the device MAC, including for advertisements without ``mac``."""

    value = entry.data.get(CONF_MAC) or entry.data.get(CONF_DEVICE_ID)
    return parse_mac(value)


def parse_mac(value: object) -> str | None:
    """Validate MAC addresses independently of opaque stable device IDs."""
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
    return f"http://{display_host}:{port}"


def pairing_url(hass: HomeAssistant, device_id: str) -> str | None:
    """Return the authenticated HA redirect used by the device Visit action."""

    base_url = hass.config.internal_url or hass.config.external_url
    if not base_url:
        return None
    return f"{base_url.rstrip('/')}/api/espcontrol/{quote(device_id, safe='')}/pair"


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


def normalize_device_id(value: str) -> str:
    """Normalize MAC identities without changing opaque future device IDs."""
    return parse_mac(value.strip()) or value.strip()
