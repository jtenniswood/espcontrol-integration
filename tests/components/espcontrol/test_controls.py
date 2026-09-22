"""Control copies route HA actions to their matching native ESPHome source."""

from unittest.mock import patch

import pytest
from homeassistant.const import EntityCategory
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from test_mirror import add_native, add_source, copy_id
from test_mirror import panel as panel  # noqa: PLC0414 -- pytest fixture re-export

CASES = [
    ("button", "unknown", {"device_class": "restart"}, "press", {}),
    ("switch", "off", {}, "turn_on", {}),
    ("switch", "on", {}, "turn_off", {}),
    (
        "light",
        "on",
        {
            "supported_color_modes": ["brightness"],
            "color_mode": "brightness",
            "brightness": 200,
            "supported_features": 32,
        },
        "turn_on",
        {"brightness": 123, "transition": 1.0},
    ),
    (
        "light",
        "on",
        {"supported_color_modes": ["onoff"], "color_mode": "onoff"},
        "turn_off",
        {},
    ),
    (
        "select",
        "Daily",
        {"options": ["Daily", "Weekly"]},
        "select_option",
        {"option": "Weekly"},
    ),
    (
        "number",
        "40",
        {"min": 10, "max": 90, "step": 5, "mode": "slider", "unit_of_measurement": "%"},
        "set_value",
        {"value": 55.0},
    ),
    (
        "text",
        "wake",
        {"min": 1, "max": 20, "mode": "text", "pattern": "[a-z]+"},
        "set_value",
        {"value": "hello"},
    ),
]


@pytest.mark.parametrize(("domain", "value", "attributes", "service", "data"), CASES)
async def test_control_metadata_actions_and_renames(
    hass, panel, domain, value, attributes, service, data
):
    native = add_native(hass)
    source = add_source(
        hass,
        native,
        domain,
        name="Setting",
        has_entity_name=True,
        entity_category=EntityCategory.CONFIG,
    )
    hass.states.async_set(source.entity_id, value, attributes)
    foreign = add_source(
        hass, add_native(hass, "11:22:33:44:55:66"), domain, name="Other"
    )
    hass.states.async_set(foreign.entity_id, value, attributes)
    assert await hass.config_entries.async_setup(panel.entry_id)
    await hass.async_block_till_done()
    mirror_id = copy_id(hass, panel, source)
    state = hass.states.get(mirror_id)
    if domain == "number":
        assert float(state.state) == float(value)
    else:
        assert state.state == value
    for key, expected in attributes.items():
        assert state.attributes[key] == expected
    registry = er.async_get(hass)
    mirror = registry.async_get(mirror_id)
    assert mirror.has_entity_name and mirror.original_name == "Setting"
    assert mirror.entity_category == EntityCategory.CONFIG
    assert mirror.device_id != native[1].id
    assert copy_id(hass, panel, foreign) is None

    # Exercise the real HA mirror service handler; intercept only its outgoing
    # native call so tests never issue commands to a physical device.
    call_service = hass.services.async_call
    calls = []
    context = Context()

    async def dispatch(call_domain, call_service_name, service_data=None, **kwargs):
        if service_data and service_data.get("entity_id") == mirror_id:
            return await call_service(
                call_domain, call_service_name, service_data, **kwargs
            )
        calls.append((call_domain, call_service_name, service_data, kwargs))

    with patch.object(type(hass.services), "async_call", side_effect=dispatch):
        await hass.services.async_call(
            domain,
            service,
            {"entity_id": mirror_id, **data},
            blocking=True,
            context=context,
        )
        assert calls == [
            (
                domain,
                service,
                {"entity_id": source.entity_id, **data},
                {"blocking": True, "context": context},
            )
        ]
        calls.clear()
        renamed = registry.async_update_entity(
            source.entity_id, new_entity_id=f"{domain}.renamed_native"
        )
        hass.states.async_remove(source.entity_id)
        hass.states.async_set(renamed.entity_id, value, attributes)
        await hass.async_block_till_done()
        await hass.services.async_call(
            domain,
            service,
            {"entity_id": mirror_id, **data},
            blocking=True,
            context=context,
        )
        assert calls[0][2]["entity_id"] == renamed.entity_id
        assert copy_id(hass, panel, renamed) == mirror_id
        calls.clear()

        registry.async_update_entity(
            renamed.entity_id, disabled_by=er.RegistryEntryDisabler.USER
        )
        # A queued action must also be rejected before the tracker has consumed
        # the disable event and marked the copy unavailable.
        with pytest.raises(
            HomeAssistantError, match="native ESPHome control is unavailable"
        ):
            await (
                hass.data[domain]
                .get_entity(mirror_id)
                .async_call_source(service, **data)
            )
        await hass.async_block_till_done()
        assert hass.states.get(mirror_id).state == "unavailable"
        # HA ignores unavailable service targets; no native call should escape.
        await hass.services.async_call(
            domain, service, {"entity_id": mirror_id, **data}, blocking=True
        )
        assert not calls

    assert await hass.config_entries.async_unload(panel.entry_id)
    assert hass.states.get(renamed.entity_id).state == value
    assert await hass.config_entries.async_setup(panel.entry_id)
    registry.async_update_entity(renamed.entity_id, disabled_by=None)
    await hass.async_block_till_done()
    assert copy_id(hass, panel, renamed) == mirror_id
    assert len(er.async_entries_for_config_entry(registry, panel.entry_id)) == 1


@pytest.mark.parametrize(
    ("domain", "value", "attributes", "service", "data"),
    [
        (
            "select",
            "Daily",
            {"options": ["Daily", "Weekly"]},
            "select_option",
            {"option": "Never"},
        ),
        (
            "number",
            "40",
            {"min": 10, "max": 90, "step": 5},
            "set_value",
            {"value": 100},
        ),
        (
            "text",
            "wake",
            {"min": 1, "max": 20, "pattern": "[a-z]+"},
            "set_value",
            {"value": "123"},
        ),
    ],
)
async def test_native_limits_are_enforced_before_forwarding(
    hass, panel, domain, value, attributes, service, data
):
    source = add_source(hass, add_native(hass), domain)
    hass.states.async_set(source.entity_id, value, attributes)
    assert await hass.config_entries.async_setup(panel.entry_id)
    await hass.async_block_till_done()
    with patch(
        "custom_components.espcontrol.control.EspControlControlMirror.async_call_source"
    ) as forward:
        with pytest.raises((ServiceValidationError, ValueError)):
            await hass.services.async_call(
                domain,
                service,
                {"entity_id": copy_id(hass, panel, source), **data},
                blocking=True,
            )
        forward.assert_not_called()


async def test_late_control_capabilities_and_native_failure(hass, panel):
    assert await hass.config_entries.async_setup(panel.entry_id)
    source = add_source(hass, add_native(hass), "light")
    await hass.async_block_till_done()
    mirror_id = copy_id(hass, panel, source)
    assert hass.states.get(mirror_id).state == "unavailable"
    attributes = {
        "supported_color_modes": ["brightness"],
        "color_mode": "brightness",
        "brightness": 50,
    }
    hass.states.async_set(source.entity_id, "on", attributes)
    await hass.async_block_till_done()
    assert hass.states.get(mirror_id).attributes["supported_color_modes"] == [
        "brightness"
    ]
    assert hass.states.get(mirror_id).attributes["brightness"] == 50
    call_service = hass.services.async_call

    async def fail_native(domain, service, service_data=None, **kwargs):
        if service_data and service_data.get("entity_id") == source.entity_id:
            raise HomeAssistantError("Native connection failed")
        return await call_service(domain, service, service_data, **kwargs)

    with (
        patch.object(type(hass.services), "async_call", side_effect=fail_native),
        pytest.raises(HomeAssistantError, match="Native connection failed"),
    ):
        await hass.services.async_call(
            "light", "turn_off", {"entity_id": mirror_id}, blocking=True
        )
    assert hass.states.get(mirror_id).state == "on"
    hass.states.async_set(source.entity_id, "unavailable")
    await hass.async_block_till_done()
    assert hass.states.get(mirror_id).state == "unavailable"
