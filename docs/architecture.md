# Architecture and maintenance

ESPHome owns native device communication, actions, and source entities. EspControl
owns its config entry, device record, catalog, sensor copies, and control proxies.

| Owner | Files | Boundary |
|---|---|---|
| Catalog contract | `protocol/catalog-v1.json`, `scripts/generate_contract.py` | Versioned metadata, field rules, picker mappings, transport limits and bridge budgets |
| Generated consumers | `catalog_contract.py`, `protocol/generated/` | Committed, reproducible artifacts; never hand-edited |
| Catalog engine | `catalog.py`, `catalog_model.py` | Registry/state union, metadata allowlist, filtering and ordering |
| Native adapter | `services.py` | HA service schema and ESPHome string/list normalization |
| Legacy adapter | `legacy.py`, `api.py`, `pairing.py` | Pairing, HTTP, origins, expiration, revocation |
| Display lifetime | `runtime.py`, `device.py`, `config_flow.py` | Effective address, timer, identity and source tracker, stored in `ConfigEntry.runtime_data` |
| Native source tracker | `tracker.py` | One device/entity listener pair per display, shared by all mirror platforms |
| Entity presentation | `mirror.py`, `sensor.py`, `binary_sensor.py` | State subscriptions, short names, value/metadata conversion and sensor display precision |
| Control forwarding | `control.py`, `light.py`, `button.py`, `switch.py`, `select.py`, `number.py`, `text.py` | Typed HA controls preserve native capabilities and forward actions to the exact source with the caller's context |
| Saved compatibility | `migrations.py` | Additive entry migration and deferred, idempotent legacy mirror migration |

The tracker filters registry events by the associated ESPHome device and remembered
source entity IDs. Disabled and removed sources update existing mirrors; mirror
registry events and unrelated devices do not trigger scans. Late ESPHome startup
is handled through registry events and one final HA startup reconciliation.
Source state subscriptions remain on entities so state updates do not scan registries.

Controls use the same tracker and stable identities as sensors. Their actions call
the source domain's Home Assistant service with the current source entity ID;
no second ESPHome connection is created. Source availability and registry identity
are checked before forwarding, and native errors propagate to the caller.
The registry's short entity name drives device-page labels. Sensor display precision
is presentation metadata, so rounding does not discard recorded measurements.

Each mirror records `source_entity_id` as a HA attribute. Wire v1 stays unchanged:
its selection metadata does not expose extra state attributes or remove duplicate
choices. A future picker can consume explicit lineage through a separately
versioned extension without invalidating saved mirror references.

Web reachability is refreshed independently of native source state. Runtime
cleanup cancels its timer and tracker; entity unload cancels state subscriptions.
Changing options or discovery address data reloads the entry, recreates the
runtime, refreshes Visit links, and revokes any old-origin pairing grants.

Config version 1/minor 2 retains the stored `device_id` verbatim because it is
part of device, mirror and pairing identities. Only the config-entry unique ID
is normalized for MAC discovery deduplication. A collision with another saved
entry fails migration instead of merging or deleting user data. The previous
empty-device deletion path is removed: emptiness cannot distinguish a legacy
record from a valid display without native sensors.

## Updating the contract

1. Change the JSON contract with a compatible contract-version increment, or a
   new wire version for breaking metadata or request changes.
2. Regenerate Python constants, TypeScript types, C++ constants and reference docs.
3. Update independent protocol fixtures and run both HA environments.
4. Commit the integration artifacts. In the firmware checkout, run
   `python3 scripts/sync_ha_catalog_contract.py --source-checkout /path/to/espcontrol-integration`.
5. Commit the firmware lock file and artifacts together. Its check validates
   the exact upstream revision and SHA-256 of every vendored artifact and fixture.
6. Run firmware catalog unit tests, typechecking and the contract gate before release.

Keep filtering handwritten. Avoid adding a registry cache or another ESPHome
connection until measurements show a need. Compatibility checks live at public
interfaces and saved identities so implementations can change without changing
what users retain across upgrades.
