"""Coverage for the complete Home Assistant entity catalog."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from custom_components.espcontrol.catalog import build_entity_catalog


def _state(entity_id: str, value: str = "on", **attributes: object) -> SimpleNamespace:
    return SimpleNamespace(entity_id=entity_id, state=value, attributes=attributes)


def _entry(
    *,
    name: str | None = None,
    device_id: str | None = None,
    area_id: str | None = None,
    disabled_by: str | None = None,
    hidden_by: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        original_name=None,
        device_id=device_id,
        area_id=area_id,
        disabled_by=disabled_by,
        hidden_by=hidden_by,
    )


def _hass() -> SimpleNamespace:
    entries = {
        "light.kitchen": _entry(name="Kitchen Lights", device_id="lamp-1", area_id="kitchen"),
        "light.hidden": _entry(name="Hidden Light", hidden_by="user"),
        "switch.disabled": _entry(name="Disabled Switch", disabled_by="user"),
        "number.level": _entry(name="Level", device_id="lamp-1", area_id="kitchen"),
    }
    devices = {
        "lamp-1": SimpleNamespace(name="Kitchen Lamp", name_by_user=None, area_id="kitchen"),
    }
    areas = {
        "kitchen": SimpleNamespace(name="Kitchen"),
    }
    hass = SimpleNamespace(
        states=SimpleNamespace(
            async_all=lambda: [
                _state("light.kitchen", brightness=255),
                _state("light.hidden"),
                _state("sensor.unregistered", "unavailable", friendly_name="Garage Air"),
                _state("number.level", "42", min=0, max=100),
            ]
        )
    )
    return hass, entries, devices, areas


def _catalog(hass: SimpleNamespace, entries: dict, devices: dict, areas: dict, **kwargs):
    with (
        patch("custom_components.espcontrol.catalog.er.async_get", return_value=SimpleNamespace(
            entities=entries,
            async_get=lambda entity_id: entries.get(entity_id),
        )),
        patch("custom_components.espcontrol.catalog.dr.async_get", return_value=SimpleNamespace(
            async_get=lambda device_id: devices.get(device_id),
        )),
        patch("custom_components.espcontrol.catalog.ar.async_get", return_value=SimpleNamespace(
            async_get_area=lambda area_id: areas.get(area_id),
        )),
    ):
        return build_entity_catalog(hass, **kwargs)


def test_catalog_unions_states_and_registry_and_applies_visibility_defaults() -> None:
    hass, entries, devices, areas = _hass()

    records, next_cursor = _catalog(hass, entries, devices, areas, limit=20)

    assert next_cursor is None
    assert [record["entity_id"] for record in records] == [
        "sensor.unregistered",
        "light.kitchen",
        "number.level",
    ]
    assert records[1]["area_name"] == "Kitchen"
    assert records[1]["device_name"] == "Kitchen Lamp"
    assert records[0]["available"] is False


def test_catalog_can_include_hidden_and_disabled_registry_entities() -> None:
    hass, entries, devices, areas = _hass()

    records, _ = _catalog(
        hass,
        entries,
        devices,
        areas,
        include_hidden=True,
        include_disabled=True,
        limit=20,
    )

    assert {record["entity_id"] for record in records} == {
        "light.kitchen",
        "light.hidden",
        "sensor.unregistered",
        "number.level",
        "switch.disabled",
    }
    disabled = next(record for record in records if record["entity_id"] == "switch.disabled")
    assert disabled["disabled"] is True
    assert disabled["available"] is False


def test_catalog_searches_entity_name_area_and_device_and_paginates() -> None:
    hass, entries, devices, areas = _hass()

    records, next_cursor = _catalog(
        hass, entries, devices, areas, query="kitchen", limit=1
    )
    assert [record["entity_id"] for record in records] == ["light.kitchen"]
    assert next_cursor == 1

    records, next_cursor = _catalog(
        hass, entries, devices, areas, query="lamp", limit=1
    )
    assert [record["entity_id"] for record in records] == ["light.kitchen"]
    assert next_cursor == 1

    records, next_cursor = _catalog(
        hass, entries, devices, areas, query="kitchen", limit=1, cursor=1
    )
    assert [record["entity_id"] for record in records] == ["number.level"]
    assert next_cursor is None


def test_catalog_applies_field_and_capability_filters() -> None:
    hass, entries, devices, areas = _hass()

    records, _ = _catalog(
        hass,
        entries,
        devices,
        areas,
        field="light",
        capabilities=["brightness"],
        limit=20,
    )

    assert [record["entity_id"] for record in records] == ["light.kitchen"]
