# EspControl Integration proof of concept

This directory is a local custom integration prototype. It is not a Home
Assistant Core contribution.

The integration discovers an EspControl display using the `_espcontrol._tcp`
Zeroconf service and creates a config entry keyed by the device's stable ID.
When ESPHome already owns the same MAC address, setup updates that ESPHome
device's configuration URL instead of creating a duplicate empty device. This
keeps all native ESPHome entities on the device that owns them while exposing
the EspControl web server through **Visit**.

If ESPHome has not been configured yet, the integration creates a standalone
device entry with a Visit link. Adding the ESPHome integration later will make
its native entities appear on the ESPHome device entry.

The display now uses the existing authenticated ESPHome connection to request
catalogue pages. Home Assistant exposes the read-only `espcontrol.search_entities`
action, and the firmware forwards browser searches over that connection. The
browser therefore needs no Home Assistant token or pairing URL. The HA ESPHome
device configuration must allow the device to perform Home Assistant actions.

The action returns a bounded, searchable catalogue. It combines live state with
entity, device, and area registry metadata and applies the field rules in
`const.py`. Unknown fields fall back to the all-domain rule, so a new Home
Assistant domain remains selectable while the configurator is updated. The
action accepts `query`, `field`, `limit`, and `cursor` values and returns
`protocol_version`, `entities`, and `next_cursor`.

The legacy HTTP contract remains temporarily available for older firmware:

```text
GET  /api/espcontrol/{device_id}/pair       (Home Assistant-authenticated redirect)
POST /api/espcontrol/{device_id}/pair       (Home Assistant-authenticated JSON)
GET  /api/espcontrol/{device_id}/entities  (Authorization: Bearer <grant>)
```

The browser client in `src/webserver/application/entity_catalog.ts` consumes
the local firmware endpoint and displays remembered local IDs only as a fallback
when the native catalogue is unavailable.

The intended catalogue response contains only selection metadata. Raw entity
attributes, camera URLs, and access tokens are never forwarded.
