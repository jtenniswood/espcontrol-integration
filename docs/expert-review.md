# Expert review after sensor mirroring

Updated 22 September 2026 against implementation commit
`525292c7b4e1132d19ca50800d663de3b7eff818` in
[PR #10](https://github.com/jtenniswood/espcontrol-integration/pull/10).
The PR was open when this review was prepared; implementation here does not
mean the change has been merged, released, or validated on a live display.

The integration now has a clearer division of responsibility and meaningful
runtime tests. Native ESPHome owns the original entities and device actions;
the HACS integration adds EspControl device entries, read-only sensor copies,
and the native catalogue action. The next priority is proving upgrades and
recovery on supported installations, rather than replacing this architecture.

This document revises the earlier expert-reset review from the development
task. It records the subsequent product decision to duplicate native sensors
and accounts for the native catalogue work incorporated from main.

## Requirements to preserve

- Keep Home Assistant's built-in ESPHome support and HACS installation support.
  Here, native support means the built-in ESPHome integration; shipping
  EspControl itself in Home Assistant Core is a separate, uncommitted goal.
- Show read-only copies of enabled native sensors and binary sensors under the
  matching EspControl device. This is an intentional product feature. The
  earlier recommendation to make mirroring optional is superseded.
- Keep the original ESPHome entities, actions, entity IDs, and automations
  working. HACS adds features without becoming a replacement action transport.
- Retain the local configurator and manual entity-ID entry when catalogue
  enhancements are unavailable.
- Preserve existing mirror entity IDs and history during upgrades wherever a
  previous mirror can be identified. Never automatically delete copies merely
  because their native source is temporarily missing.

## What changed since the earlier review

| Earlier concern | Current assessment |
| --- | --- |
| Unclear ownership and duplicated platform logic | Addressed in the implementation: originals stay with ESPHome; shared source tracking lives in `EspControlMirror`, with separate sensor and binary-sensor adapters. Copies are required product behavior. |
| Mirror IDs depend on editable entity names | Addressed for new mirrors: identity uses the native unique ID. Tests cover renames and migration of matching draft mirrors in place. A source renamed before upgrading an old draft still needs migration coverage. |
| Mirrors only discovered at setup; missing availability handling | Addressed in automated tests: registry events discover late sources; copies follow state updates, renames, disabling, removal, and recovery. |
| Runtime discarded even when unload fails | Code corrected: runtime is removed only after successful platform unload. Failed-unload behavior still needs an explicit regression test. |
| Browser pairing is the main catalogue workflow | Superseded by the native `espcontrol.search_entities` action incorporated from main. Pairing endpoints are now legacy compatibility code. |
| Catalogue excludes registry entities without live states | Addressed by the catalogue work incorporated from main: results combine the entity registry and live states. |
| No documented versioned catalogue contract | Partly addressed: [the native contract](native-entity-catalog.md) now documents protocol, pagination, and fallback behavior. Executable cross-repository compatibility fixtures remain useful. |
| CI only validates HACS packaging | Addressed in configuration: a pinned test environment and a self-hosted test workflow now exist. The merged branch passed 24 local tests; completed GitHub checks were not yet verified for this revision. |

Evidence: [mirror lifecycle](../custom_components/espcontrol/mirror.py),
[sensor adapter](../custom_components/espcontrol/sensor.py),
[binary-sensor adapter](../custom_components/espcontrol/binary_sensor.py),
[mirror tests](../tests/components/espcontrol/test_mirror.py), and
[test workflow](../.github/workflows/test.yml).

## Ranked recommendations

### 1. Prove coexistence and upgrade safety on supported installations

- **Importance:** High.
- **Recommendation strength:** Strong.
- **Why it matters:** Both device entries and existing automations must survive
  upgrades, reloads, and removal of the HACS integration. Passing registry tests
  is useful evidence, but it does not prove behavior with a physical panel.
- **Evidence:** [Mirror tests](../tests/components/espcontrol/test_mirror.py)
  exercise real HA registries and entity platforms. The
  [test harness](../tests/conftest.py) mocks HTTP registration and the identity
  probe. Tests were run with HA 2026.9.3; the
  [HACS metadata](../hacs.json) does not declare a minimum HA version.
- **User experience impact:** Preserve both sets of entities and the existing
  native controls; avoid unexpected entity recreation or history loss.
- **Migration approach:** Capture fixtures from an existing HACS installation,
  including renamed sources and user-customized mirror IDs, before changing
  identity or cleanup logic further.
- **Risk management:** Check restart order, reload, HACS removal, source loss,
  catalogue action permission, and Visit links on a real display. Test the
  oldest supported HA version as well as the current supported release. Add a
  failed-platform-unload regression test. Do not treat mirror tests as proof
  of native action delivery or legacy HTTP authentication.
- **Work required:** Medium: a supported-version decision, fixtures, and a
  focused physical-device test session.
- **Suggested first step:** Complete PR #10's manual test steps and record the
  HA version, firmware version, and results before release.

### 2. Make address changes and health status recover automatically

- **Importance:** High.
- **Recommendation strength:** Strong.
- **Why it matters:** Discovery and options can update an address while the
  running runtime and Visit links still reflect setup-time values. A single
  startup HTTP probe also cannot represent ongoing device availability.
- **Evidence:** [Config flow](../custom_components/espcontrol/config_flow.py)
  updates the saved host and exposes host/web-port options, but setup registers
  no options-update listener. [Setup](../custom_components/espcontrol/__init__.py)
  probes once and [system health](../custom_components/espcontrol/system_health.py)
  reads that runtime flag. The probe in
  [device.py](../custom_components/espcontrol/device.py) constructs its own URL
  rather than using the IPv6-aware URL helper.
- **User experience impact:** Address changes and HTTP recovery should update
  configuration links and health reporting. Native sensor availability should
  continue to follow ESPHome, independently of this HTTP probe.
- **Migration approach:** Preserve config-entry IDs and saved settings. First
  centralize address resolution, then add controlled reload/recovery behavior.
- **Risk management:** Test DHCP rediscovery, manual options, IPv6, offline
  startup, recovery, and failed unloads. Define whether a manual address
  override takes precedence over discovery before changing that behavior.
- **Work required:** Medium: lifecycle handling and targeted network tests.
- **Suggested first step:** Add a test that changes host and web port through
  options and verifies that runtime configuration and Visit links refresh.

### 3. Turn the native catalogue contract into compatibility tests

- **Importance:** Medium.
- **Recommendation strength:** Strong.
- **Why it matters:** HACS and firmware can be updated independently. A written
  protocol is a useful foundation, but both ends must agree on pagination,
  capabilities, supported fields, and error behavior across versions.
- **Evidence:** [Native contract](native-entity-catalog.md),
  [service schema](../custom_components/espcontrol/__init__.py),
  [field rules](../custom_components/espcontrol/const.py), and
  [catalogue tests](../tests/components/espcontrol/test_catalog.py).
  The service caps pages at 50 while the shared catalogue builder permits 100
  for the legacy HTTP path; adapters need explicitly tested limits.
- **User experience impact:** Preserve complete entity selection and manual
  fallback when the integration, permission, or transport is unavailable.
- **Migration approach:** Keep protocol version 1 and introduce request/response
  fixtures before changing formats. Accept supported additive fields without
  requiring every panel to upgrade simultaneously.
- **Risk management:** Validate old/new firmware and integration combinations,
  multi-page results, disabled entries, capability filtering, action permission
  failures, and unknown versions. Keep legacy compatibility removal separate.
- **Work required:** Medium: shared fixtures and checks in both repositories.
- **Suggested first step:** Run one multi-page catalogue fixture through the HA
  action and firmware consumer and compare the resulting entity IDs.

### 4. Bound the legacy pairing lifecycle while older firmware uses it

- **Importance:** Medium.
- **Recommendation strength:** Strong.
- **Why it matters:** Moving new firmware to the native catalogue reduces the
  role of browser grants, but older deployments still need predictable access
  revocation and a documented transition.
- **Evidence:** [HTTP views](../custom_components/espcontrol/api.py) validate
  catalogue grants without requiring a currently loaded matching config entry.
  [PairingStore](../custom_components/espcontrol/pairing.py) supports revocation,
  but unload does not invoke it. Origin matching compares the hostname rather
  than the complete origin. The current test harness bypasses HTTP registration.
- **User experience impact:** Keep supported older firmware usable while making
  unload/removal terminate its catalogue grant predictably.
- **Migration approach:** Retain the legacy endpoints until deployed firmware
  compatibility is established. Centralize entry eligibility and revoke grants
  at the appropriate lifecycle boundary.
- **Risk management:** Test actual HTTP authentication, grant expiry and
  revocation, allowed/rejected origins, and preflight behavior. Preserve the
  documented transition instead of deleting endpoints as incidental cleanup.
- **Work required:** Medium: lifecycle changes and real HTTP-view tests.
- **Suggested first step:** Add a test that issues a grant, unloads its entry,
  and confirms that the same grant can no longer retrieve catalogue data.

### 5. Measure mirror discovery costs before optimizing them

- **Importance:** Low.
- **Recommendation strength:** Moderate.
- **Why it matters:** The current shared implementation is easy to follow, but
  each sensor platform rescans on every entity/device registry event. Larger
  installations may benefit from filtering or combining those scans.
- **Evidence:** `async_setup_mirrors` in
  [mirror.py](../custom_components/espcontrol/mirror.py) registers listeners per
  platform and resolves the matching ESPHome device during each reconciliation.
- **User experience impact:** Preserve all automatic discovery and rename
  behavior; this is a potential internal efficiency improvement.
- **Migration approach:** Keep the source-to-copy identity scheme. Introduce
  event filtering or a shared per-display coordinator only if measurements
  justify it.
- **Risk management:** Measure with multiple panels and unrelated registry
  updates; retain the late-discovery, disable/enable, and reload regression tests.
- **Work required:** Small to measure; medium only if refactoring is justified.
- **Suggested first step:** Count reconciliation calls during a representative
  HA startup and unrelated registry update batch. No performance defect has
  been demonstrated in this review.

## Quick wins

- Keep the README link to this review current as recommendations are completed.
- Record physical-test results and the supported HA version range alongside
  the existing reproducible Python test setup.
- Keep new-firmware instructions centered on the native catalogue; label the
  remaining HTTP pairing instructions as legacy compatibility guidance.

## Not recommended right now

- Removing, disabling by default, or making sensor mirroring optional merely
  to avoid duplicate values. The copies are the requested user experience.
- Moving original ESPHome entities to EspControl or adding a second action
  transport. Preserve native ownership and existing automations.
- Treating HACS support and native ESPHome support as competing architectures.
  They serve complementary roles in the same installation.
- A wholesale firmware rewrite, a large schema generator, or a mandatory Core
  submission before the current behavior has been validated on devices.
- Deleting unavailable mirror registry entries or legacy pairing endpoints
  without a deliberate compatibility and migration decision.

## Checks and evidence

- Reviewed the post-merge implementation at `525292c`, including native
  catalogue service registration, mirror platforms, source discovery, config
  flow, pairing, runtime health, tests, and workflows.
- Earlier validation on that implementation: Python 3.14.4 and HA 2026.9.3,
  `python -m pytest -q -p no:cacheprovider tests/components/espcontrol
  --timeout=30 --timeout-method=thread`: **24 passed**.
- Targeted Ruff and formatting checks passed for the new mirror code and test
  harness. Two stale catalogue assertions were reproduced on untouched main
  and corrected when enabling the complete suite in CI.
- GitHub test/HACS checks had not all completed when this review was prepared.
  Local success is not a claim that remote CI or live-device validation passed.
- The native catalogue document records earlier hardware testing on its own
  firmware/integration baseline. That does not validate the new mirror feature.
- This update changes documentation only. Code tests were not rerun; Markdown
  links and whitespace are checked before publication. No new firmware build,
  device flash, or live Home Assistant session was performed for this review.
