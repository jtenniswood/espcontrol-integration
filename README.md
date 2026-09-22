# EspControl Integration

<img src="https://raw.githubusercontent.com/jtenniswood/espcontrol-integration/main/brand/icon.png" alt="EspControl" width="128" height="128">

A HACS custom integration that connects EspControl displays to Home Assistant.
It discovers displays, opens their configurator through **Visit**, supplies safe
entity-selection metadata over the existing ESPHome connection, and mirrors the
display's native ESPHome sensors and controls. This is an experimental companion integration,
not a Home Assistant Core integration or a replacement for ESPHome.

## Install and connect

1. In HACS, add `jtenniswood/espcontrol-integration` as a custom **Integration** repository.
2. Install it, restart Home Assistant, and add **EspControl** under **Settings → Devices & services**.
3. Use firmware advertising `_espcontrol._tcp` protocol `1`. Confirm the discovered display,
   or enter its stable device ID and host manually. MAC IDs are normalized to prevent duplicate entries.
4. Keep the same display configured in ESPHome and allow it to perform Home Assistant actions.
5. Open **Visit** on the display's device page. Native catalog firmware requests
   `espcontrol.search_entities` through ESPHome; the browser needs no Home Assistant token.

Home Assistant **2026.8.0 or later** is required. The native catalog firmware is
currently the `show-ha-entity-catalog` feature branch in the
[firmware repository](https://github.com/jtenniswood/espcontrol/pull/2023).
See [verified combinations and limitations](docs/compatibility.md) before upgrading.

The configurator can retain remembered suggestions and manual entity-ID entry
when catalog access fails. It must report a transport error separately from an
empty successful search. Firmware owns this browser behavior.

## Devices, sensors and controls

EspControl and ESPHome retain separate device records for the same physical
panel. EspControl creates read-only copies of enabled native sensor and binary
sensor entities matching the panel's MAC, including text sensors represented by
Home Assistant's sensor domain. It also mirrors lights (including display backlight),
buttons, switches, selectors, numbers, and text settings. Control actions target
the matching native entity through Home Assistant; ESPHome keeps ownership of
device communication. Configuration categories, options, and limits are preserved.

Device pages show short entity labels without repeating the panel name.
Percentage (`%`) and byte (`B`) sensors display whole numbers while retaining
the original measurements for history. Explicit display-precision overrides
and custom names on the EspControl entities are preserved.

Copies follow source state, metadata, renames, and entities added after startup.
Missing, disabled, or unavailable sources make copies unavailable. Each copy
exposes `source_entity_id` so its origin is inspectable. Both source and copy
remain selectable in catalog v1; existing selections are never rewritten.
Enable a disabled source on the ESPHome device page to create its copy.

Discovered address and web-port changes reload the display runtime. Options
provide a manual address override; that override takes precedence over discovery.
Both device Visit links update. The integration checks web reachability every
60 seconds and reports it separately from the native source association and
available source count. An offline display does not prevent setup.

## Upgrade and removal

Existing device IDs, mirror IDs, customizations, and history are retained. The
config-entry migration is additive (version 1, minor version 2). Old mirror IDs
are migrated in place when their source is discovered, including after startup.
Empty EspControl device records are valid and are preserved on reload; do not
remove them as an upgrade step.

Removing or unloading EspControl revokes its legacy pairing grants and stops its
subscriptions and health timer. Native ESPHome entities are left in place.
Back up Home Assistant before testing a release. An integration rollback can use
the previous HACS version; no destructive registry migration is performed.

## Catalog and older firmware

The canonical definitions are in [catalog-v1.json](protocol/catalog-v1.json).
See the [generated contract reference](docs/catalog-contract.md) for field rules,
metadata, transport limits, and pagination. Raw state values, arbitrary attributes,
camera URLs, and credentials are excluded from catalog responses.

[Native transport behavior](docs/native-entity-catalog.md) is the supported path.
The [legacy compatibility adapter](docs/legacy-catalog.md) remains available for
older panels until deployed firmware compatibility has been established. Its
short-lived grants are not Home Assistant access tokens.

## Development and releases

Use Python 3.14 in an isolated environment:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python scripts/check_compatibility.py --ha-version 2026.9.3
.venv/bin/python -m pytest -q tests/components/espcontrol
```

Repeat in a separate environment with `requirements-test-min.txt` and
`--ha-version 2026.8.0`. Tests use real HA services, HTTP routing, registries, and
entity platforms, with device networking simulated explicitly.

After changing `protocol/catalog-v1.json`, run
`python3 scripts/generate_contract.py`. CI rejects stale generated Python, TypeScript,
C++ and documentation. Keep shared fixture expectations independently reviewed.
Firmware vendors the generated files and fixtures from an exact integration commit;
its contract check rejects edits to the vendored files.

The **Release verified integration** workflow accepts an existing version tag,
pins its commit, runs both compatibility environments, checks the tag matches the
manifest version, and only then publishes the tagged package. Creating a release
manually bypasses these checks; use the workflow. No release is published by an
ordinary push or pull request.

See [architecture and maintenance](docs/architecture.md) for ownership boundaries
and [compatibility](docs/compatibility.md) for the test matrix and hardware checks.
