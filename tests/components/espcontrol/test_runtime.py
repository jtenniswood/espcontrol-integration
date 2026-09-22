"""Web health recovery is independent of native source availability."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.espcontrol.runtime import EspControlRuntime


@pytest.fixture
def real_probe():
    return True


async def test_ipv6_probe_recovers_and_clears_stale_identity(hass):
    entry = MockConfigEntry(
        domain="espcontrol", data={"device_id": "panel", "host": "2001:db8::10"}
    )
    runtime = EspControlRuntime(hass, entry, "2001:db8::10", 8080)
    replies = [
        TimeoutError(),
        {"device_id": "panel"},
        ["invalid"],
        {"device_id": "panel"},
    ]
    urls = []

    @asynccontextmanager
    async def get(url, **kwargs):
        urls.append(url)
        result = replies.pop(0)
        if isinstance(result, Exception):
            raise result
        yield SimpleNamespace(status=200, json=AsyncMock(return_value=result))

    with patch(
        "custom_components.espcontrol.runtime.async_get_clientsession",
        return_value=SimpleNamespace(get=get),
    ):
        assert not await runtime.async_probe()
        assert runtime.web_available is False
        assert await runtime.async_probe()
        assert runtime.identity == {"device_id": "panel"}
        assert not await runtime.async_probe()
        assert runtime.identity is None
        assert await runtime.async_probe()
    assert urls == ["http://[2001:db8::10]:8080/api/v1/identity"] * 4
    assert runtime.sources.device_id is None


async def test_offline_startup_recovers_on_timer_and_stops_on_unload(hass, freezer):
    entry = MockConfigEntry(
        domain="espcontrol",
        title="Panel",
        data={"device_id": "panel", "host": "192.0.2.10"},
    )
    entry.add_to_hass(hass)
    calls = []

    @asynccontextmanager
    async def get(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            raise TimeoutError
        yield SimpleNamespace(
            status=200, json=AsyncMock(return_value={"device_id": "panel"})
        )

    with patch(
        "custom_components.espcontrol.runtime.async_get_clientsession",
        return_value=SimpleNamespace(get=get),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        assert entry.runtime_data.web_available is False
        freezer.tick(61)
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
        assert entry.runtime_data.web_available is True
        assert await hass.config_entries.async_unload(entry.entry_id)
        freezer.tick(61)
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
        assert len(calls) == 2
