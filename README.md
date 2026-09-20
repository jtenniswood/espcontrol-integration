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
When the same display is already configured through ESPHome, the integration
reuses that ESPHome device entry so its native entities stay together and adds
the EspControl web server as the device's **Visit** link. If ESPHome has not
been configured yet, it creates a standalone device entry with the Visit link
until ESPHome is added.

The integration also offers a short-lived pairing grant. The grant is
deliberately scoped to one device and is never a Home Assistant long-lived
access token. The device **Visit** action performs this pairing automatically:
Home Assistant issues a ten-minute grant and redirects the browser to the
device with the grant in its URL fragment. A manual pairing service remains
available for installations without a configured Home Assistant internal or
external URL.

If an earlier POC version created a separate empty EspControl device, remove
that old EspControl config entry once after upgrading. The ESPHome device entry
and its entities are retained; the updated integration adds the Visit link to
that entry instead of creating another device.

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
Home Assistant restart revokes them. Before a production implementation, the
native API transport must deliver the grant to the display over an authenticated
physical pairing flow. The browser client in `src/webserver/application/entity_catalog.ts`
consumes the catalogue and keeps a local fallback to the existing remembered
entity suggestions.

The intended catalogue response contains only selection metadata. Raw entity
attributes, camera URLs, and access tokens are never forwarded.
