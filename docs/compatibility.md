# Compatibility and validation

The machine-readable matrix is [protocol/compatibility.json](../protocol/compatibility.json).
Catalog contract **1.0.0** preserves native and legacy wire version **1**.

| Environment | Pinned test dependency | Coverage |
|---|---|---|
| Home Assistant 2026.8.0, Python 3.14 | pytest-homeassistant-custom-component 0.13.354 | Minimum supported version |
| Home Assistant 2026.9.3, Python 3.14 | pytest-homeassistant-custom-component 0.13.366 | Current validated version |
| ESPHome 2026.9.0, EspControl native catalog branch `c525e016ecaa5118d791fcc047bb43ffde32b1c6` | Shared `protocol/fixtures/catalog-v1.json` | Automated protocol fixtures; not a published firmware release or fresh hardware qualification |

The firmware consumer's contract adoption is a separate change based on
[EspControl PR #2023](https://github.com/jtenniswood/espcontrol/pull/2023).
It pins an integration commit and vendors its artifacts and fixtures. The
existing native firmware remains compatible with wire v1 before adopting the pin.
No released firmware is claimed to contain these changes until that release is built.

The suite covers public native action validation, metadata privacy, pagination,
legacy HTTP authentication and CORS, token expiration/removal, saved-entry and
mirror migrations, source changes, repeated reloads, address changes, IPv6,
offline recovery, and subscription cleanup. Real HA registries and entity
platforms are exercised; device identity HTTP responses are simulated in tests.

## Hardware acceptance before broad rollout

Record the actual HA version, firmware commit, ESPHome version and display profile.
Test one native catalog panel and any panel still requiring legacy pairing:

1. Open Visit in a fresh browser; search and paginate without importing a HA token.
2. Disable the device's HA action permission; verify an explicit recoverable error
   and manual entity-ID entry, then restore the permission and retry.
3. Rename and disable a native sensor; verify its mirror follows and retains its
   entity ID, then re-enable it. Existing dashboard references must still work.
4. Change the panel address/web port; verify both Visit links and source association.
5. Reload and restart HA; verify no duplicate device or sensor IDs and recovery
   after the panel was offline during startup.
6. Verify any older firmware's pairing flow before retiring the adapter.

The documented panel at `192.168.6.102` answered a read-only identity request on
2026-09-22, but its response exposed names/address only, without firmware version
or catalog capabilities. This does not establish a complete firmware inventory
or satisfy the removal gate. No firmware was flashed during this implementation.

Use the release workflow to run both environments against the same tagged commit
before publication. When raising the minimum or updating current HA, update the
matrix, pinned requirements, HACS minimum, and tests together.
