# Native ESPHome entity catalog

The native catalog is the supported proof-of-concept transport between an
EspControl display and Home Assistant. The display sends the
`espcontrol.search_entities` response action through its existing ESPHome API
connection. No Home Assistant long-lived token, URL-fragment credential, or
cross-origin Home Assistant request is needed.

The ESPHome device must be allowed to perform Home Assistant actions. A native
API connection by itself is not enough: the catalog is considered ready only
after the action response is received. If the integration is absent, the
action permission is disabled, or the connection drops, the display reports a
recoverable catalog error and keeps manual entity-ID entry available.

## Contract

The action request is bounded and read-only:

```json
{
  "query": "office",
  "field": "entity",
  "area": "Office",
  "device_id": "",
  "include_hidden": false,
  "include_disabled": false,
  "limit": 50,
  "cursor": 0
}
```

The response contains `protocol_version`, `entities`, and `next_cursor`.
Each entity includes its exact Home Assistant `entity_id`, domain, friendly
name, area/device context, availability, registry visibility flags, and
normalized capability names. Raw state attributes, camera URLs, credentials,
and other private data are excluded.

The catalog is ordered by friendly name and entity ID. `cursor` is an offset;
the client follows `next_cursor` until it is `null`. Home Assistant may change
the registry between pages, so a retry starts at cursor zero. The firmware
limits request size, queue depth, response bytes, and timeout, and reports
invalid pagination, unavailable HA, cross-origin access, queue saturation, and
timeouts as distinct errors.

## Validation baseline

The hardware validation used the 7-inch P4 profile
`guition-esp32-p4-jc1060p470`, ESPHome `2026.9.0`, the EspControl firmware
native catalog branch, and EspControl Integration `0.1.1` from HACS. The
display was tested at `192.168.6.102`; the running firmware served the native
catalog endpoint and returned multiple pages of real HA metadata. Record the
Home Assistant Core version from **Settings → System → Repairs → System
information** when repeating the test, because the installed HA version is
host-specific.

## Transition

The legacy pairing HTTP endpoints remain available for older firmware during
the proof-of-concept transition. New firmware uses the display-origin native
endpoint. Once all deployed panels use the native protocol, the pairing store
and legacy endpoint can be removed in a separate breaking-change release.
