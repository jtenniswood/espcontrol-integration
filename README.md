# EspControl Integration

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
Its Visit link points directly to the display's local HTTP server. When the
same hardware is also configured through ESPHome, EspControl mirrors the
ESPHome sensor and binary-sensor states onto its own device entry.

Mirrors are read-only copies of enabled native ESPHome sensors for the same
panel MAC address, including text sensors exposed by ESPHome as Home Assistant
sensors. They follow state changes, source renames, and sensors added after
startup. Missing, disabled, or unavailable sources make their copies unavailable.
The native ESPHome integration must remain configured; its entities and actions
continue to work independently. Removing EspControl leaves them in place.

After installing or updating the integration, restart Home Assistant. The copies
appear under the matching EspControl device automatically. Disabled native
sensors must first be enabled in ESPHome's Home Assistant device page.

## Development tests

Use Python 3.14 and install `requirements-test.txt` in a virtual environment, then
run `python -m pytest tests/components/espcontrol`. Tests use Home Assistant's
registries and entity platforms with device HTTP access mocked out.

The integration also offers a short-lived pairing grant. The grant is
deliberately scoped to one device and is never a Home Assistant long-lived
access token.

After pairing, the entity endpoint returns a bounded, searchable catalogue. It
combines live state with entity, device, and area registry metadata and applies
the field rules in `const.py`. Unknown fields fall back to the all-domain rule,
so a new Home Assistant domain remains selectable while the configurator is
updated.

The HTTP contract is:

```text
POST /api/espcontrol/{device_id}/pair       (Home Assistant-authenticated)
GET  /api/espcontrol/{device_id}/entities  (X-EspControl-Pairing-Token)
```

Pairing grants expire after ten minutes and are held in memory in this POC; a
Home Assistant restart revokes them. Before a production implementation, the
native API transport must deliver the grant to the display over an authenticated
physical pairing flow. The browser client in `src/webserver/application/entity_catalog.ts`
consumes the catalogue and keeps a local fallback to the existing remembered
entity suggestions.

The intended catalogue response contains only selection metadata. Raw entity
attributes, camera URLs, and access tokens are never forwarded.
