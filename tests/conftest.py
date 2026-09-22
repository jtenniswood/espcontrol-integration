"""Run the custom integration against Home Assistant's test fixtures."""

from contextlib import ExitStack
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import mock_component


@pytest.fixture(autouse=True)
def integration_environment(hass, enable_custom_integrations, real_http, real_probe):
    """Keep network-only HTTP setup outside discovery and entity tests."""
    with ExitStack() as stack:
        if not real_http:
            mock_component(hass, "http")
            stack.enter_context(
                patch("custom_components.espcontrol.legacy.register_views")
            )
        if not real_probe:
            stack.enter_context(
                patch(
                    "custom_components.espcontrol.runtime.EspControlRuntime.async_probe",
                    return_value=True,
                )
            )
        yield


@pytest.fixture
def real_http():
    return False


@pytest.fixture
def real_probe():
    return False
