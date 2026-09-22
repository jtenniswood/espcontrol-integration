"""Per-display lifetime, web reachability and native source ownership."""

from datetime import datetime, timedelta

from aiohttp import ClientError, ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .device import webserver_url
from .tracker import NativeSourceTracker


class EspControlRuntime:
    """Owned by ConfigEntry.runtime_data; every subscription ends on unload."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, host: str, web_port: int
    ) -> None:
        self.hass = hass
        self.host = host
        self.web_port = web_port
        self.web_available: bool | None = None
        self.identity: dict | None = None
        self.sources = NativeSourceTracker(hass, entry, host, web_port)
        self._unsubscribe_probe = None

    async def async_start(self) -> None:
        self.sources.async_start()
        await self.async_probe()
        self._unsubscribe_probe = async_track_time_interval(
            self.hass, self.async_probe, timedelta(seconds=60)
        )

    @callback
    def async_stop(self) -> None:
        self.sources.async_stop()
        if self._unsubscribe_probe is not None:
            self._unsubscribe_probe()
            self._unsubscribe_probe = None

    async def async_probe(self, _now: datetime | None = None) -> bool:
        """Report current web reachability independently of native sensors."""
        self.identity = None
        self.web_available = False
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                f"{webserver_url(self.host, self.web_port)}/api/v1/identity",
                timeout=ClientTimeout(total=3),
            ) as response:
                if response.status != 200:
                    return False
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError):
            return False
        if not isinstance(payload, dict):
            return False
        self.identity = payload
        self.web_available = True
        return True
