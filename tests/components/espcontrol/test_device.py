"""Tests for device identity and Home Assistant device links."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.espcontrol.device import mac_from_entry, webserver_url


def test_mac_from_entry_falls_back_to_device_id() -> None:
    """The firmware's device_id is the stable MAC when mac is not advertised."""

    entry = SimpleNamespace(data={"device_id": "80:F1:B2:D0:7D:48"})

    assert mac_from_entry(entry) == "80:f1:b2:d0:7d:48"


def test_mac_from_entry_rejects_non_mac_stable_ids() -> None:
    """Future non-MAC identifiers must not be used as network connections."""

    entry = SimpleNamespace(data={"device_id": "panel-kitchen"})

    assert mac_from_entry(entry) is None


def test_webserver_url_handles_ipv4_and_ipv6_hosts() -> None:
    """Visit links use valid HTTP URLs for both address families."""

    assert webserver_url("192.0.2.10", 80) == "http://192.0.2.10"
    assert webserver_url("2001:db8::10", 8080) == "http://[2001:db8::10]:8080"
