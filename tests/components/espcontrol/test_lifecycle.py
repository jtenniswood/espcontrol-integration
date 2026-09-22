"""Saved identity, address changes, source ownership and unload regressions."""

import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF, ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_config_flow import _discovery_info
from test_mirror import add_native, add_source

from custom_components.espcontrol.migrations import async_migrate_entry


def panel_entry(hass, **kwargs):
    entry = MockConfigEntry(
        domain="espcontrol",
        title="Panel",
        version=1,
        minor_version=2,
        unique_id="aa:bb:cc:dd:ee:ff",
        data={"device_id": "aa:bb:cc:dd:ee:ff", "host": "192.0.2.10"},
        **kwargs,
    )
    entry.add_to_hass(hass)
    return entry


async def test_empty_device_survives_reload_and_options_change(hass):
    native = add_native(hass)
    entry = panel_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    registry = dr.async_get(hass)
    device = registry.async_get_devices(
        config_entry_id=entry.entry_id,
        identifiers={("espcontrol", entry.data["device_id"])},
    )[0]
    for _ in range(2):
        assert await hass.config_entries.async_reload(entry.entry_id)
    assert (
        registry.async_get_devices(
            config_entry_id=entry.entry_id,
            identifiers={("espcontrol", entry.data["device_id"])},
        )[0].id
        == device.id
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "host": "2001:db8::10",
            "port": 6053,
            "web_port": 8080,
        },
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.host == "2001:db8::10"
    assert (
        registry.async_get(device.id).configuration_url == "http://[2001:db8::10]:8080"
    )
    assert (
        registry.async_get(native[1].id).configuration_url
        == "http://[2001:db8::10]:8080"
    )


async def test_discovery_updates_runtime_without_changing_identity(hass):
    entry = panel_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    info = _discovery_info()
    info.properties["web_port"] = "8081"
    result = await hass.config_entries.flow.async_init(
        "espcontrol", context={"source": SOURCE_ZEROCONF}, data=info
    )
    assert result["reason"] == "already_configured"
    await hass.async_block_till_done()
    assert entry.runtime_data.host == info.host
    assert entry.runtime_data.web_port == 8081


async def test_manual_mac_matches_discovered_mac(hass):
    result = await hass.config_entries.flow.async_init(
        "espcontrol", context={"source": SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "device_id": "AABBCCDDEEFF",
            "host": "192.0.2.10",
            "port": 6053,
        },
    )
    result = await hass.config_entries.flow.async_init(
        "espcontrol", context={"source": SOURCE_ZEROCONF}, data=_discovery_info()
    )
    assert result["reason"] == "already_configured"


async def test_v1_migration_retains_device_and_mirror_identifiers(hass):
    fixture = json.loads(
        (Path(__file__).parents[2] / "fixtures/config-entry-v1.json").read_text()
    )
    entry = MockConfigEntry(domain="espcontrol", **fixture)
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("espcontrol", entry.data["device_id"])},
    )
    assert await async_migrate_entry(hass, entry)
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 1 and entry.minor_version == 2
    assert entry.unique_id == "aa:bb:cc:dd:ee:ff"
    assert entry.data["device_id"] == "AA:BB:CC:DD:EE:FF"
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert (
        dr.async_get(hass)
        .async_get_devices(
            config_entry_id=entry.entry_id,
            identifiers={("espcontrol", entry.data["device_id"])},
        )[0]
        .id
        == device.id
    )


async def test_tracker_ignores_unrelated_registry_events_and_cleans_up(hass):
    entries = [panel_entry(hass)]
    native = add_native(hass)
    source = add_source(hass, native)
    hass.states.async_set(source.entity_id, "10")
    for index in range(2):
        mac = f"22:33:44:55:66:{index:02x}"
        entry = MockConfigEntry(
            domain="espcontrol",
            title=f"Panel {index}",
            unique_id=mac,
            data={"device_id": mac, "host": f"192.0.2.{index + 20}"},
        )
        entry.add_to_hass(hass)
        entries.append(entry)
        add_source(hass, add_native(hass, mac), name=f"panel{index}")
    assert await hass.config_entries.async_setup(entries[0].entry_id)
    await hass.async_block_till_done()
    assert all(entry.state is ConfigEntryState.LOADED for entry in entries)
    tracker = entries[0].runtime_data.sources
    with ExitStack() as stack:
        reconciles = [
            stack.enter_context(
                patch.object(
                    entry.runtime_data.sources,
                    "async_reconcile",
                    wraps=entry.runtime_data.sources.async_reconcile,
                )
            )
            for entry in entries
        ]
        for index in range(20):
            other = add_source(
                hass,
                add_native(hass, f"11:22:33:44:55:{index:02x}"),
                name=f"other{index}",
            )
            er.async_get(hass).async_update_entity(other.entity_id, name="Unrelated")
        await hass.async_block_till_done()
        assert [reconcile.call_count for reconcile in reconciles] == [0, 0, 0]
        er.async_get(hass).async_update_entity(
            source.entity_id, new_entity_id="sensor.renamed"
        )
        await hass.async_block_till_done()
        assert [reconcile.call_count for reconcile in reconciles] == [1, 0, 0]
    assert await hass.config_entries.async_unload(entries[0].entry_id)
    assert not tracker._listeners and not tracker._unsubscribers
    assert (
        hass.states.get(source.entity_id).state == "10"
    )  # Mirrors never remove native states
    assert er.async_get(hass).async_get("sensor.renamed") is not None


async def test_migration_collision_keeps_both_entries_untouched(hass):
    other = panel_entry(hass)
    original = MockConfigEntry(
        domain="espcontrol",
        version=1,
        minor_version=1,
        unique_id="AA:BB:CC:DD:EE:FF",
        data={"device_id": "AA:BB:CC:DD:EE:FF", "host": "192.0.2.11"},
    )
    original.add_to_hass(hass)
    assert not await async_migrate_entry(hass, original)
    assert original.unique_id == "AA:BB:CC:DD:EE:FF" and original.minor_version == 1
    assert hass.config_entries.async_get_entry(other.entry_id) is other
