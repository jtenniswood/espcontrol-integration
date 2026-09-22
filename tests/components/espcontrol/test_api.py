"""Real HA HTTP routes, authentication, CORS and legacy/native parity."""

import json
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.espcontrol.catalog_contract import METADATA_FIELDS


@pytest.fixture
def real_http():
    return True


@pytest.fixture
async def panel(hass):
    entry = MockConfigEntry(
        domain="espcontrol",
        version=1,
        minor_version=2,
        title="Panel",
        unique_id="panel-1",
        data={"device_id": "panel-1", "host": "192.0.2.10", "web_port": 8080},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    return entry


@pytest.fixture
async def clients(panel, hass_client, hass_client_no_auth):
    return await hass_client(), await hass_client_no_auth()


async def issue(client):
    response = await client.post("/api/espcontrol/panel-1/pair")
    assert response.status == 200
    return (await response.json())["token"]


async def test_pairing_requires_ha_auth_and_redirects_to_display(clients):
    authenticated, anonymous = clients
    response = await anonymous.post("/api/espcontrol/panel-1/pair")
    assert response.status == 401
    response = await authenticated.get(
        "/api/espcontrol/panel-1/pair", allow_redirects=False
    )
    assert response.status == 302
    assert response.headers["Location"].startswith(
        "http://192.0.2.10:8080/#espcontrol-pairing="
    )
    response = await authenticated.post("/api/espcontrol/missing/pair")
    assert response.status == 404


@pytest.mark.parametrize("header", ["Authorization", "X-EspControl-Pairing-Token"])
async def test_legacy_headers_expiry_and_device_scope(hass, clients, freezer, header):
    authenticated, anonymous = clients
    token = await issue(authenticated)
    headers = {header: f"Bearer {token}" if header == "Authorization" else token}
    response = await anonymous.get("/api/espcontrol/panel-1/entities", headers=headers)
    assert response.status == 200
    assert (await response.json())["protocol"] == 1
    response = await anonymous.get("/api/espcontrol/panel-2/entities", headers=headers)
    assert response.status == 401
    freezer.tick(601)
    response = await anonymous.get("/api/espcontrol/panel-1/entities", headers=headers)
    assert response.status == 401


@pytest.mark.parametrize(
    "origin,expected",
    [
        ("http://192.0.2.10:8080", 200),
        ("http://192.0.2.10", 403),
        ("https://192.0.2.10:8080", 403),
        ("http://192.0.2.11:8080", 403),
        ("http://192.0.2.10:bad", 403),
        ("null", 403),
    ],
)
async def test_catalog_enforces_exact_display_origin(clients, origin, expected):
    authenticated, anonymous = clients
    token = await issue(authenticated)
    response = await anonymous.get(
        "/api/espcontrol/panel-1/entities",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": origin,
        },
    )
    assert response.status == expected
    if expected == 200:
        assert response.headers["Access-Control-Allow-Origin"] == origin


async def test_removing_display_revokes_grant(hass, panel, clients):
    authenticated, anonymous = clients
    token = await issue(authenticated)
    await hass.config_entries.async_remove(panel.entry_id)
    response = await anonymous.get(
        "/api/espcontrol/panel-1/entities", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status == 401


@pytest.mark.parametrize(
    "header,expected", [("Authorization", 200), ("X-EspControl-Pairing-Token", 403)]
)
async def test_legacy_browser_preflight(clients, header, expected):
    _, anonymous = clients
    response = await anonymous.options(
        "/api/espcontrol/panel-1/entities",
        headers={
            "Origin": "http://192.0.2.10:8080",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": header,
        },
    )
    assert response.status == expected
    if expected == 200:
        assert (
            response.headers["Access-Control-Allow-Origin"] == "http://192.0.2.10:8080"
        )


async def test_shared_firmware_fixture_through_both_public_transports(hass, clients):
    fixture = json.loads(
        (Path(__file__).parents[3] / "protocol/fixtures/catalog-v1.json").read_text()
    )
    for state in fixture["states"]:
        hass.states.async_set(state["entity_id"], state["state"], state["attributes"])
    authenticated, anonymous = clients
    token = await issue(authenticated)
    for case in fixture["searches"]:
        native = await hass.services.async_call(
            "espcontrol",
            "search_entities",
            case["request"],
            blocking=True,
            return_response=True,
        )
        params = {
            ("q" if key == "query" else key): str(value).lower()
            if isinstance(value, bool)
            else value
            for key, value in case["request"].items()
        }
        for key in ("include_hidden", "include_disabled"):
            if key in params:
                params[key] = "1" if case["request"][key] else "0"
        response = await anonymous.get(
            "/api/espcontrol/panel-1/entities",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status == 200
        legacy = await response.json()
        assert legacy["entities"] == native["entities"] == case["entities"]
        assert legacy["next_cursor"] == native["next_cursor"] == case["next_cursor"]
        assert all(set(record) == set(METADATA_FIELDS) for record in native["entities"])


async def test_legacy_pagination_limits_remain_compatible(hass, clients):
    authenticated, anonymous = clients
    token = await issue(authenticated)
    for index in range(110):
        hass.states.async_set(
            f"sensor.example_{index}", "secret", {"camera_url": "private"}
        )
    headers = {"Authorization": f"Bearer {token}"}
    response = await anonymous.get("/api/espcontrol/panel-1/entities", headers=headers)
    assert len((await response.json())["entities"]) == 50
    response = await anonymous.get(
        "/api/espcontrol/panel-1/entities?limit=999&cursor=-1", headers=headers
    )
    page = await response.json()
    assert len(page["entities"]) == 100 and page["next_cursor"] == 100
    assert "secret" not in json.dumps(page) and "private" not in json.dumps(page)
    response = await anonymous.get(
        "/api/espcontrol/panel-1/entities?limit=invalid", headers=headers
    )
    assert response.status == 400
