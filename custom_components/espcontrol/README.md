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

The integration also offers a short-lived pairing grant. The grant is
deliberately scoped to one device and is never a Home Assistant long-lived
access token. The device **Visit** action opens an authenticated Home Assistant
redirect, issues the grant, and then opens the display with the grant in its
URL fragment.

After pairing, the entity endpoint returns a bounded, searchable catalogue. It
combines live state with entity, device, and area registry metadata and applies
the field rules in `const.py`. Unknown fields fall back to the all-domain rule,
so a new Home Assistant domain remains selectable while the configurator is
updated.

The HTTP contract is:

```text
GET  /api/espcontrol/{device_id}/pair       (Home Assistant-authenticated redirect)
POST /api/espcontrol/{device_id}/pair       (Home Assistant-authenticated JSON)
GET  /api/espcontrol/{device_id}/entities  (Authorization: Bearer <grant>)
```

Pairing grants expire after ten minutes and are held in memory in this POC; a
Home Assistant restart revokes them. Before a production implementation, the
native API transport must deliver the grant to the display over an authenticated
physical pairing flow. The browser client in `src/webserver/application/entity_catalog.ts`
consumes the catalogue and keeps a local fallback to the existing remembered
entity suggestions.

The intended catalogue response contains only selection metadata. Raw entity
attributes, camera URLs, and access tokens are never forwarded.
