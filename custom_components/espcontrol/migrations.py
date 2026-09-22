"""Idempotent saved-entry and deferred legacy mirror migrations."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import CONF_DEVICE_ID, CONF_MAC, DOMAIN
from .device import mac_from_entry, normalize_device_id

CONFIG_VERSION = 1
CONFIG_MINOR_VERSION = 2


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Retain registry identities, including valid empty EspControl devices."""
    if entry.version > CONFIG_VERSION:
        return False
    if entry.version == 1 and entry.minor_version < CONFIG_MINOR_VERSION:
        data = dict(entry.data)
        if mac := mac_from_entry(entry):
            data[CONF_MAC] = mac
        unique_id = normalize_device_id(entry.unique_id or data[CONF_DEVICE_ID])
        if any(
            other.entry_id != entry.entry_id and other.unique_id == unique_id
            for other in hass.config_entries.async_entries(DOMAIN)
        ):
            return False
        # Keep device_id byte-for-byte: it is part of existing device and mirror
        # identifiers and saved legacy pairing URLs. Only discovery dedup changes.
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            unique_id=unique_id,
            version=CONFIG_VERSION,
            minor_version=CONFIG_MINOR_VERSION,
        )
    return True


@callback
def async_migrate_mirror(
    registry: er.EntityRegistry,
    entry: ConfigEntry,
    source: er.RegistryEntry,
    unique_id: str,
) -> None:
    """Migrate draft IDs when their native source becomes known (even later)."""
    if registry.async_get_entity_id(source.domain, DOMAIN, unique_id) is not None:
        return
    legacy_id = registry.async_get_entity_id(
        source.domain, DOMAIN, f"{entry.data[CONF_DEVICE_ID]}_{source.entity_id}"
    )
    if legacy_id and registry.async_get(legacy_id).config_entry_id == entry.entry_id:
        registry.async_update_entity(legacy_id, new_unique_id=unique_id)
