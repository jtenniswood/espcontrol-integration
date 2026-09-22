"""Compatibility boundary for firmware predating the native catalog bridge."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError

from .api import register_views
from .const import CONF_DEVICE_ID, DOMAIN, SERVICE_CREATE_PAIRING_TOKEN
from .pairing import PairingStore


class LegacyCatalogAdapter:
    """Own every legacy grant and endpoint; native code needs no credentials."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.pairing = PairingStore()

    @callback
    def async_setup(self) -> None:
        register_views(self.hass, self.pairing)

        async def create_pairing_token(call: ServiceCall) -> dict:
            device_id = call.data[CONF_DEVICE_ID]
            if not any(
                entry.data.get(CONF_DEVICE_ID) == device_id
                and entry.state is ConfigEntryState.LOADED
                for entry in self.hass.config_entries.async_entries(DOMAIN)
            ):
                raise ServiceValidationError("The EspControl display is not configured")
            grant = self.pairing.issue(device_id)
            return {
                "device_id": device_id,
                "token": grant.token,
                "expires_at": grant.expires_at,
            }

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_CREATE_PAIRING_TOKEN,
            create_pairing_token,
            schema=vol.Schema({vol.Required(CONF_DEVICE_ID): str}),
            supports_response=SupportsResponse.ONLY,
        )

    @callback
    def async_revoke(self, device_id: str) -> None:
        self.pairing.revoke(device_id)
