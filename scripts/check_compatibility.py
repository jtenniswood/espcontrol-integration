"""Verify the tested HA version, contract outputs, fixtures and release metadata."""

import argparse
import json
from importlib.metadata import version
from pathlib import Path

import yaml
from generate_contract import outputs

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ha-version", required=True)
    parser.add_argument("--release-tag")
    args = parser.parse_args()
    matrix = json.loads((ROOT / "protocol/compatibility.json").read_text())
    contract = json.loads((ROOT / "protocol/catalog-v1.json").read_text())
    assert version("homeassistant") == args.ha_version, (
        "Installed HA differs from the declared test environment"
    )
    assert args.ha_version in {item["version"] for item in matrix["home_assistant"]}
    assert matrix["contract_version"] == contract["version"]
    workflow = yaml.safe_load((ROOT / ".github/workflows/test.yml").read_text())
    assert workflow["jobs"]["test"]["strategy"]["matrix"]["include"] == [
        {"ha": item["version"], "requirements": item["requirements"]}
        for item in matrix["home_assistant"]
    ], "CI matrix must match the documented compatibility matrix"
    assert (
        json.loads((ROOT / "hacs.json").read_text())["homeassistant"]
        == matrix["home_assistant"][0]["version"]
    )
    for path, expected in outputs().items():
        assert path.read_text() == expected, f"Stale generated contract: {path}"
    for firmware in matrix["firmware"]:
        fixture = json.loads((ROOT / firmware["fixture"]).read_text())
        assert fixture["provenance"]["firmware_revision"] == firmware["revision"]
        assert firmware["wire_version"] == contract["wire_version"]
    if args.release_tag:
        manifest = json.loads(
            (ROOT / "custom_components/espcontrol/manifest.json").read_text()
        )
        assert args.release_tag.removeprefix("v") == manifest["version"], (
            "Release tag and integration version differ"
        )
    print(
        f"Contract {contract['version']} and Home Assistant {args.ha_version} compatibility verified"
    )


if __name__ == "__main__":
    main()
