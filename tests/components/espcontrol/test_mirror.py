"""Exercise mirrored sensors through real HA platforms and registries."""

import pytest
from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.espcontrol.const import DOMAIN
from custom_components.espcontrol.mirror import mirror_unique_id

MAC = "aa:bb:cc:dd:ee:ff"


@pytest.fixture
def panel(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Kitchen",
        unique_id=MAC,
        data={"device_id": MAC, "host": "192.0.2.10", "mac": MAC},
    )
    entry.add_to_hass(hass)
    return entry


def add_native(hass, mac=MAC):
    entry = MockConfigEntry(domain="esphome", title="Native panel")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, mac)},
        name="Native panel",
    )
    return entry, device


def add_source(hass, native, domain="sensor", name="temperature", **kwargs):
    entry, device = native
    return er.async_get(hass).async_get_or_create(
        domain,
        "esphome",
        name,
        config_entry=entry,
        device_id=device.id,
        original_name=name,
        **kwargs,
    )


def copy_id(hass, panel, source):
    return er.async_get(hass).async_get_entity_id(
        source.domain, DOMAIN, mirror_unique_id(panel, source)
    )


async def test_mirrors_values_metadata_and_device_ownership(hass, panel):
    native = add_native(hass)
    source = add_source(hass, native, entity_category=EntityCategory.DIAGNOSTIC)
    attributes = {
        "friendly_name": "Kitchen Temperature",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "icon": "mdi:thermometer",
    }
    hass.states.async_set(source.entity_id, "21.5", attributes)
    binary = add_source(hass, native, "binary_sensor", "connected")
    hass.states.async_set(binary.entity_id, "on", {"device_class": "connectivity"})
    foreign = add_source(hass, add_native(hass, "11:22:33:44:55:66"), name="foreign")
    disabled = add_source(
        hass, native, name="disabled", disabled_by=er.RegistryEntryDisabler.USER
    )

    assert await hass.config_entries.async_setup(panel.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    mirror_id = copy_id(hass, panel, source)
    state = hass.states.get(mirror_id)
    assert state.state == "21.5"
    for key, value in attributes.items():
        assert state.attributes[key] == value
    mirror = registry.async_get(mirror_id)
    assert mirror.entity_category == EntityCategory.DIAGNOSTIC
    assert mirror.config_entry_id == panel.entry_id
    assert mirror.device_id != native[1].id
    assert (DOMAIN, MAC) in dr.async_get(hass).async_get(mirror.device_id).identifiers
    assert hass.states.get(copy_id(hass, panel, binary)).state == "on"
    assert copy_id(hass, panel, foreign) is None
    assert copy_id(hass, panel, disabled) is None
    assert registry.async_get(source.entity_id).config_entry_id == native[0].entry_id

    hass.states.async_set(source.entity_id, "22.0", attributes)
    hass.states.async_set(binary.entity_id, "off", {"device_class": "connectivity"})
    await hass.async_block_till_done()
    assert float(hass.states.get(mirror_id).state) == 22
    assert hass.states.get(copy_id(hass, panel, binary)).state == "off"


@pytest.mark.parametrize("domain", ["sensor", "binary_sensor"])
async def test_late_discovery_rename_disable_remove_and_reenable(hass, panel, domain):
    assert await hass.config_entries.async_setup(panel.entry_id)
    native = add_native(hass)
    source = add_source(hass, native, domain)
    hass.states.async_set(source.entity_id, "on" if domain == "binary_sensor" else "10")
    await hass.async_block_till_done()
    mirror_id = copy_id(hass, panel, source)
    assert mirror_id is not None

    registry = er.async_get(hass)
    renamed = registry.async_update_entity(
        source.entity_id, new_entity_id=f"{domain}.renamed"
    )
    hass.states.async_remove(source.entity_id)
    hass.states.async_set(
        renamed.entity_id, "off" if domain == "binary_sensor" else "20"
    )
    await hass.async_block_till_done()
    assert copy_id(hass, panel, renamed) == mirror_id
    assert hass.states.get(mirror_id).state == (
        "off" if domain == "binary_sensor" else "20"
    )

    for state in ("unknown", "unavailable"):
        hass.states.async_set(renamed.entity_id, state)
        await hass.async_block_till_done()
        assert hass.states.get(mirror_id).state == state

    registry.async_update_entity(
        renamed.entity_id, disabled_by=er.RegistryEntryDisabler.USER
    )
    hass.states.async_set(
        renamed.entity_id, "on" if domain == "binary_sensor" else "30"
    )
    await hass.async_block_till_done()
    assert hass.states.get(mirror_id).state == "unavailable"
    registry.async_update_entity(renamed.entity_id, disabled_by=None)
    await hass.async_block_till_done()
    assert hass.states.get(mirror_id).state == (
        "on" if domain == "binary_sensor" else "30"
    )
    registry.async_remove(renamed.entity_id)
    await hass.async_block_till_done()
    assert hass.states.get(mirror_id).state == "unavailable"
    assert len(er.async_entries_for_config_entry(registry, panel.entry_id)) == 1


@pytest.mark.parametrize(
    ("value", "attributes"),
    [
        ("192.0.2.10", {}),
        ("2026-09-22T10:00:00+00:00", {"device_class": "timestamp"}),
        ("2026-09-22", {"device_class": "date"}),
        ("ready", {"device_class": "enum", "options": ["ready", "busy"]}),
        (
            "12.5",
            {
                "device_class": "energy",
                "unit_of_measurement": "kWh",
                "state_class": "total_increasing",
            },
        ),
    ],
)
async def test_text_timestamp_and_statistics_metadata(hass, panel, value, attributes):
    source = add_source(hass, add_native(hass))
    hass.states.async_set(source.entity_id, value, attributes)
    assert await hass.config_entries.async_setup(panel.entry_id)
    await hass.async_block_till_done()
    mirror = hass.states.get(copy_id(hass, panel, source))
    assert mirror.state == value
    for key, expected in attributes.items():
        assert mirror.attributes[key] == expected


async def test_legacy_mirror_migrates_in_place_and_reload_does_not_duplicate(
    hass, panel
):
    source = add_source(hass, add_native(hass))
    hass.states.async_set(source.entity_id, "10")
    registry = er.async_get(hass)
    legacy = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{MAC}_{source.entity_id}",
        config_entry=panel,
        suggested_object_id="existing_mirror",
    )
    assert await hass.config_entries.async_setup(panel.entry_id)
    await hass.async_block_till_done()
    assert copy_id(hass, panel, source) == legacy.entity_id
    assert await hass.config_entries.async_unload(panel.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set(source.entity_id, "25")
    assert await hass.config_entries.async_setup(panel.entry_id)
    await hass.async_block_till_done()
    assert copy_id(hass, panel, source) == legacy.entity_id
    assert hass.states.get(legacy.entity_id).state == "25"
    assert len(er.async_entries_for_config_entry(registry, panel.entry_id)) == 1
    assert hass.states.get(source.entity_id).state == "25"


async def test_registry_source_before_state_recovers_with_metadata(hass, panel):
    source = add_source(hass, add_native(hass))
    assert await hass.config_entries.async_setup(panel.entry_id)
    await hass.async_block_till_done()
    mirror_id = copy_id(hass, panel, source)
    assert hass.states.get(mirror_id).state == "unavailable"
    attributes = {
        "device_class": "temperature",
        "unit_of_measurement": "°F",
        "state_class": "measurement",
    }
    hass.states.async_set(source.entity_id, "72", attributes)
    await hass.async_block_till_done()
    state = hass.states.get(mirror_id)
    # SensorEntity applies HA's display-unit preferences to the copied value.
    assert float(state.state) == pytest.approx((72 - 32) * 5 / 9)
    assert state.attributes["unit_of_measurement"] == "°C"
    for key, value in attributes.items():
        if key != "unit_of_measurement":
            assert state.attributes[key] == value
    hass.states.async_remove(source.entity_id)
    await hass.async_block_till_done()
    assert hass.states.get(mirror_id).state == "unavailable"


async def test_enabling_previously_disabled_source_creates_one_copy(hass, panel):
    source = add_source(
        hass, add_native(hass), disabled_by=er.RegistryEntryDisabler.INTEGRATION
    )
    assert await hass.config_entries.async_setup(panel.entry_id)
    await hass.async_block_till_done()
    assert copy_id(hass, panel, source) is None
    registry = er.async_get(hass)
    registry.async_update_entity(source.entity_id, disabled_by=None)
    hass.states.async_set(source.entity_id, "10")
    await hass.async_block_till_done()
    assert hass.states.get(copy_id(hass, panel, source)).state == "10"
    assert len(er.async_entries_for_config_entry(registry, panel.entry_id)) == 1
