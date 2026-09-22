# EspControl Integration proof of concept

<img src="https://raw.githubusercontent.com/jtenniswood/espcontrol-integration/main/brand/icon.png" alt="EspControl" width="128" height="128">

This directory is a local custom integration prototype. It is not a Home
Assistant Core contribution.

The integration discovers an EspControl display using the `_espcontrol._tcp`
Zeroconf service and creates a config entry keyed by the device's stable ID.
Every discovery gets an EspControl device entry with a **Visit** link. When
ESPHome already owns the same MAC address, setup updates that ESPHome device's
configuration URL as well, while native ESPHome entities remain on the ESPHome
device entry.


EspControl also creates read-only copies of enabled native ESPHome sensors for
that panel's MAC address, including binary sensors and text sensors exposed as
Home Assistant sensors. Copies follow live state changes, source renames, and
sensors added after startup. Missing, disabled, or unavailable sources make their
copies unavailable. The native ESPHome integration must remain configured; its
entities and actions continue to work independently.

After updating, restart Home Assistant to add the copies to each EspControl
device. Disabled native sensors must first be enabled on the ESPHome device's
Home Assistant page. Removing EspControl leaves the native entities in place.

The display now uses the existing authenticated ESPHome connection to request
catalogue pages. Home Assistant exposes the read-only `espcontrol.search_entities`
action, and the firmware forwards browser searches over that connection. The
browser therefore needs no Home Assistant token or pairing URL. The HA ESPHome
device configuration must allow the device to perform Home Assistant actions.

The action returns a bounded, searchable catalogue. It combines live state with
entity, device, and area registry metadata and applies the field rules in
`const.py`. Unknown fields fall back to the all-domain rule, so a new Home
Assistant domain remains selectable while the configurator is updated. The
action accepts `query`, `field`, `area`, `device_id`, `capabilities`,
`include_hidden`, `include_disabled`, `limit`, and `cursor` values and returns
`protocol_version`, `entities`, and `next_cursor`. The catalog is the union of
the entity registry and live states, so disabled registry entries and
unregistered live states are handled explicitly rather than silently dropped.

The native contract is versioned and intentionally small:

```json
{
  "query": "kitchen",
  "field": "light",
  "limit": 50,
  "cursor": 0,
  "include_hidden": false,
  "include_disabled": false
}
```

```json
{
  "protocol_version": 1,
  "entities": [{
    "entity_id": "light.kitchen",
    "domain": "light",
    "name": "Kitchen Lights",
    "area_name": "Kitchen",
    "device_name": "Kitchen Lamp",
    "available": true,
    "disabled": false,
    "hidden": false,
    "capabilities": ["brightness"]
  }],
  "next_cursor": null
}
```

Results are sorted by friendly name and entity ID. `cursor` is an offset into
that stable ordering; if the HA registry changes between pages, the next page
reflects the new catalog and the client may retry from the beginning. Limits
are bounded to 50 results per action response. A missing connection, invalid
request, timeout, or oversized response is returned as an explicit error so a
picker cannot present an empty list as a successful search.

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
