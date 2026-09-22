# Legacy catalog compatibility

New firmware uses the native ESPHome response action. Older pairing-based
firmware can continue using these endpoints through `LegacyCatalogAdapter`:

| Endpoint | Authentication | Result |
|---|---|---|
| `GET /api/espcontrol/{device_id}/pair` | HA session/token | Redirect to the display with a temporary grant |
| `POST /api/espcontrol/{device_id}/pair` | HA session/token | Grant and pairing URI as JSON |
| `GET /api/espcontrol/{device_id}/entities` | `Authorization: Bearer <grant>` | Catalog page |

`espcontrol.create_pairing_token` is also retained. Grants are random, scoped to
one configured display, stored as hashes, and expire after ten minutes. Issuing
a new grant replaces the previous grant. Unload, removal, and HA restart revoke
existing grants. The endpoints cannot invoke arbitrary Home Assistant actions.

Browser requests must originate from the display's exact HTTP host and web port.
Home Assistant owns CORS response headers and preflight. The historical
`X-EspControl-Pairing-Token` header is still accepted for direct non-browser
clients; HA's standard CORS allowlist does not permit that header in browser
preflight. Browser clients must use `Authorization`.

The legacy transport retains `q`, response key `protocol`, a default page size
of 50, and a maximum of 100. Negative cursors clamp to zero. See the
[generated reference](catalog-contract.md) for the complete contract.
Both transports call the same catalog engine; shared fixtures exercise them
through actual HA service and HTTP interfaces.

## Removal gate

Keep this adapter until every deployed panel has been verified to use the native
catalog bridge. Record the firmware revision and device profile, test a fresh
browser without pairing storage, verify pagination and unavailable-HA fallback,
and record a usable firmware rollback version. A successful identity HTTP request
alone does not prove native catalog support.

No complete installed-firmware inventory is available in this repository. The
adapter therefore remains enabled. Removing it requires an announced breaking
release after that inventory and the firmware tests pass; it is not part of
this migration.
