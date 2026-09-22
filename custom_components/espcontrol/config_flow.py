"""Discover displays and maintain their network addresses."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    CONF_DEVICE_ID,
    CONF_MAC,
    CONF_MODEL,
    CONF_PROTOCOL,
    CONF_WEB_PORT,
    DEFAULT_PORT,
    DOMAIN,
    PROTOCOL_VERSION,
)
from .device import normalize_device_id, parse_mac
from .migrations import CONFIG_MINOR_VERSION, CONFIG_VERSION


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)


class EspControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle user and Zeroconf setup."""

    VERSION = CONFIG_VERSION
    MINOR_VERSION = CONFIG_MINOR_VERSION

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    @callback
    def _entry_for_identity(self, device_id: str) -> config_entries.ConfigEntry | None:
        """Include disabled legacy entries whose migration has not run yet."""
        return next(
            (
                entry
                for entry in self._async_current_entries()
                if normalize_device_id(entry.unique_id or entry.data[CONF_DEVICE_ID])
                == device_id
            ),
            None,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return EspControlOptionsFlow()

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        properties = {
            _text(key): _text(value) for key, value in discovery_info.properties.items()
        }
        if properties.get(CONF_PROTOCOL, "") != str(PROTOCOL_VERSION):
            return self.async_abort(reason="unsupported_protocol")
        mac = properties.get(CONF_MAC)
        if mac:
            mac = parse_mac(mac)
            if mac is None:
                return self.async_abort(reason="invalid_device")
        device_id = mac or properties.get(CONF_DEVICE_ID)
        if not device_id:
            return self.async_abort(reason="missing_device_id")
        device_id = normalize_device_id(device_id)
        if not device_id:
            return self.async_abort(reason="missing_device_id")
        try:
            web_port = cv.port(properties.get(CONF_WEB_PORT, "80"))
        except (ValueError, vol.Invalid):
            return self.async_abort(reason="invalid_device")
        await self.async_set_unique_id(device_id)
        if existing := self._entry_for_identity(device_id):
            self.hass.config_entries.async_update_entry(
                existing,
                data={
                    **existing.data,
                    CONF_HOST: discovery_info.host,
                    CONF_WEB_PORT: web_port,
                },
            )
            return self.async_abort(reason="already_configured")
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: discovery_info.host, CONF_WEB_PORT: web_port}
        )
        self._data = {
            CONF_DEVICE_ID: device_id,
            CONF_HOST: discovery_info.host,
            CONF_PORT: discovery_info.port or DEFAULT_PORT,
            CONF_WEB_PORT: web_port,
            CONF_MODEL: properties.get(CONF_MODEL),
            CONF_PROTOCOL: PROTOCOL_VERSION,
            CONF_MAC: mac,
        }
        self.context["title_placeholders"] = {
            "name": properties.get(
                "name", discovery_info.hostname.removesuffix(".local.")
            )
        }
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=self.context["title_placeholders"]["name"], data=self._data
            )
        return self.async_show_form(step_id="confirm")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input = {
                **user_input,
                CONF_DEVICE_ID: normalize_device_id(user_input[CONF_DEVICE_ID]),
            }
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            if self._entry_for_identity(user_input[CONF_DEVICE_ID]):
                return self.async_abort(reason="already_configured")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_DEVICE_ID],
                data={**user_input, CONF_PROTOCOL: PROTOCOL_VERSION, CONF_WEB_PORT: 80},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): vol.All(
                        str, vol.Strip, vol.Length(min=1)
                    ),
                    vol.Required(CONF_HOST): vol.All(str, vol.Strip, vol.Length(min=1)),
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                }
            ),
        )


class EspControlOptionsFlow(config_entries.OptionsFlow):
    """Allow a user to change the display address after DHCP changes."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): vol.All(
                            str, vol.Strip, vol.Length(min=1)
                        ),
                        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                        vol.Optional(CONF_WEB_PORT, default=80): cv.port,
                    }
                ),
                {**self.config_entry.data, **self.config_entry.options},
            ),
        )
