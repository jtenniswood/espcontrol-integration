# EspControl Integration

<img src="https://raw.githubusercontent.com/jtenniswood/espcontrol-integration/main/brand/icon.png" alt="EspControl" width="128" height="128">

This repository contains the experimental EspControl integration. It is a HACS-installable
custom integration and is not a Home Assistant Core contribution.

## Install with HACS

In HACS, open **Custom repositories**, add this GitHub repository, choose
**Integration**, and install EspControl. Restart Home Assistant, then add the
EspControl integration from **Settings → Devices & services**.

The device firmware must also advertise the `_espcontrol._tcp` service. The
experimental firmware changes live in the main [EspControl repository](https://github.com/jtenniswood/espcontrol).

The integration discovers an EspControl display using the `_espcontrol._tcp`
Zeroconf service and creates a config entry keyed by the device's stable ID.
Every discovery gets an EspControl device entry with the device's **Visit**
link. When the same display is also configured through ESPHome, the integration
updates the ESPHome device's Visit link too, while native ESPHome entities stay
owned by the ESPHome device entry.


EspControl also creates read-only copies of enabled native ESPHome sensors for
that panel's MAC address, including binary sensors and text sensors exposed as
Home Assistant sensors. Copies follow live state changes, source renames, and
sensors added after startup. Missing, disabled, or unavailable sources make their
copies unavailable. The native ESPHome integration must remain configured; its
entities and actions continue to work independently.

After updating, restart Home Assistant to add the copies to each EspControl
device. Disabled native sensors must first be enabled on the ESPHome device's
Home Assistant page. Removing EspControl leaves the native entities in place.

The native ESPHome connection is the primary catalog transport. The display
requests the read-only `espcontrol.search_entities` response action, so a
fresh browser needs no Home Assistant token, URL-fragment credential, or
special pairing link. The device must be allowed to perform Home Assistant
actions. See [the native catalog contract](docs/native-entity-catalog.md).

The short-lived pairing grant remains temporarily available for older firmware.
It is scoped to one device, expires after ten minutes, and is never a Home
Assistant long-lived access token. It will be removed after the native
protocol transition is complete.

If an earlier POC version created a separate empty EspControl device, remove
that old entry once after upgrading. The updated integration recreates the
EspControl-owned device entry when the display is discovered again; the ESPHome
device entry and its entities are retained separately.

After pairing, the entity endpoint returns a bounded, searchable catalogue. It
combines live state with entity, device, and area registry metadata and applies
the field rules in `const.py`. Unknown fields fall back to the all-domain rule,
so a new Home Assistant domain remains selectable while the configurator is
updated.

The HTTP contract is:

```text
GET  /api/espcontrol/{device_id}/pair       (Home Assistant-authenticated redirect)
POST /api/espcontrol/{device_id}/pair       (Home Assistant-authenticated JSON)
GET  /api/espcontrol/{device_id}/entities  (X-EspControl-Pairing-Token)
```

Pairing grants expire after ten minutes and are held in memory in this POC; a
Home Assistant restart revokes them. The browser client in
`src/webserver/application/entity_catalog.ts` consumes the native display
endpoint and keeps a local fallback to remembered entity suggestions.

The intended catalogue response contains only selection metadata. Raw entity
attributes, camera URLs, and access tokens are never forwarded.

## Development tests

Use Python 3.14 and install `requirements-test.txt` in a virtual environment, then
run `python -m pytest tests/components/espcontrol`. Tests use Home Assistant's
registries and entity platforms with device HTTP access mocked out.
