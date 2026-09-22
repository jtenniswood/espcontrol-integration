"""Separate web reachability from availability of native sensor sources."""

from homeassistant.components import system_health
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    @callback
    def info() -> dict[str, object]:
        runtimes = [
            entry.runtime_data
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]
        return {
            "configured_displays": len(runtimes),
            "web_reachable_displays": sum(
                runtime.web_available is True for runtime in runtimes
            ),
            "native_linked_displays": sum(
                runtime.sources.device_id is not None for runtime in runtimes
            ),
            "available_native_sources": sum(
                runtime.sources.available_sources for runtime in runtimes
            ),
            "legacy_pairing": "supported during firmware transition",
        }

    register.async_register_info(info)
