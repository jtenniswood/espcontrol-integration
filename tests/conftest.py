"""Run the custom integration against Home Assistant's test fixtures."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import mock_component


@pytest.fixture(autouse=True)
def integration_environment(hass, enable_custom_integrations):
    """Keep network-only HTTP setup outside discovery and entity tests."""
    mock_component(hass, "http")
    with (
        patch("custom_components.espcontrol.register_views"),
        patch(
            "custom_components.espcontrol.device.EspControlRuntime.async_probe",
            return_value=True,
        ),
    ):
        yield
