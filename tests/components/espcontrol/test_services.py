"""Exercise the public native action, including its firmware-facing schema."""

import json

import pytest
import voluptuous as vol
from homeassistant.setup import async_setup_component

from custom_components.espcontrol.catalog_contract import METADATA_FIELDS


@pytest.fixture
async def catalog_action(hass):
    assert await async_setup_component(hass, "espcontrol", {})

    async def call(**data):
        return await hass.services.async_call(
            "espcontrol", "search_entities", data, blocking=True, return_response=True
        )

    return call


async def test_public_action_paginates_safe_metadata(hass, catalog_action):
    for index in range(60):
        hass.states.async_set(
            f"light.test_{index:02}",
            "on",
            {
                "friendly_name": f"Light {index:02}",
                "brightness": 100,
                "camera_url": "https://private",
                "access_token": "secret",
            },
        )
    page = await catalog_action()
    assert page["protocol_version"] == 1
    assert len(page["entities"]) == 25
    assert page["next_cursor"] == 25
    assert all(set(record) == set(METADATA_FIELDS) for record in page["entities"])
    assert "secret" not in json.dumps(page) and "https://private" not in json.dumps(
        page
    )
    page = await catalog_action(cursor=25, limit=50)
    assert len(page["entities"]) == 35 and page["next_cursor"] is None


@pytest.mark.parametrize(
    "data",
    [
        {"limit": 0},
        {"limit": 51},
        {"cursor": -1},
        {"cursor": 10001},
        {"query": "x" * 121},
        {"field": "x" * 41},
        {"area": "x" * 121},
        {"device_id": "x" * 121},
        {"capabilities": ["x" * 81]},
        {"unknown": True},
    ],
)
async def test_public_action_rejects_invalid_requests(catalog_action, data):
    with pytest.raises(vol.Invalid):
        await catalog_action(**data)


@pytest.mark.parametrize(
    "capabilities", ["brightness, effect", ["brightness", "effect"]]
)
async def test_firmware_csv_and_ha_list_capabilities(
    hass, catalog_action, capabilities
):
    hass.states.async_set("light.full", "on", {"brightness": 1, "effect": "none"})
    hass.states.async_set("light.partial", "on", {"brightness": 1})
    page = await catalog_action(capabilities=capabilities, include_disabled="false")
    assert [record["entity_id"] for record in page["entities"]] == ["light.full"]


async def test_unknown_field_keeps_future_domains_selectable(hass, catalog_action):
    hass.states.async_set("future_domain.example", "ready")
    page = await catalog_action(field="future_field")
    assert page["entities"][0]["entity_id"] == "future_domain.example"
