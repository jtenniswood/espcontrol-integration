# Catalog contract 1.0.0

Generated from `protocol/catalog-v1.json`; edit the source and run `python3 scripts/generate_contract.py`.

Wire version: 1. SHA-256: `b67fceeb7f9c9c207c1cf63585debd7b4adf655f8e5d46acb954a35f36fd0234`.

## Transport compatibility

| Transport | Query key | Version key | Default page | Maximum page | Cursor maximum |
|---|---|---|---:|---:|---:|
| native | query | protocol_version | 25 | 50 | 10000 |
| legacy_http | q | protocol | 50 | 100 | unbounded |

Sort by case-folded friendly name, then exact entity ID. Cursor is an offset, not a snapshot token. Registry changes between pages may shift results; retry from zero. next_cursor is null at the end. Native requests reject out-of-range pagination; legacy HTTP clamps page size to 1–100 and negative cursor to zero.

## Selection metadata

| Field | Type |
|---|---|
| entity_id | string |
| domain | string |
| device_id | string or null |
| name | string |
| device_name | string or null |
| area_name | string or null |
| device_class | string or null |
| icon | string or null |
| unit | string or null |
| available | boolean |
| disabled | boolean |
| hidden | boolean |
| capabilities | string[] |

Raw states, arbitrary attributes, camera URLs and credentials are excluded.

## Picker fields

| Field | Accepted HA domains |
|---|---|
| entity | Any (also the fallback for unknown fields) |
| state_entity | Any (also the fallback for unknown fields) |
| sensor | binary_sensor, input_number, sensor, text_sensor |
| binary_sensor | binary_sensor |
| text_sensor | text_sensor |
| light | light |
| fan | fan |
| climate | climate |
| cover | cover |
| lock | lock |
| alarm | alarm_control_panel |
| media_player | media_player |
| vacuum | vacuum |
| lawn_mower | lawn_mower |
| weather | weather |
| camera | camera, image |
| select | input_select, select |
| number | input_number, number |
| switch | input_boolean, switch |
| person | person |
| device_tracker | device_tracker |
| scene | scene |
| script | script |
| automation | automation |
| button | button, input_button |
| action | automation, button, input_boolean, input_button, input_number, input_select, number, scene, script, select |
