"""
CAM-A27 shared capability-map module.

Filesystem-light tests of the import-stable module. No CLI argument parsing
and no executable side effects. The module must be importable when scripts/
is on sys.path, independently of either CLI adapter.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
CANONICAL_MAP = REPO_ROOT / "contracts" / "creation_studio_capability_map.json"

sys.path.insert(0, str(SCRIPTS))

from _shared.creation_studio_capability_map import (  # noqa: E402
    CapabilityMapContractError,
    CapabilityMapInputError,
    build_mapping_index,
    load_a22_request_enum,
    load_capability_map,
    load_capability_map_document,
    normalize_provenance_path,
    validate_capability_map_document,
)


CANONICAL_INDEX = {
    "feeds_speeds_recommendation": ["feeds_speeds_authoring"],
    "gcode_explanation": ["gcode_tutorial_generation", "post_processor_education"],
    "simulation_request": ["simulation_support"],
}


def test_importing_the_shared_module_has_no_cli_side_effects(capsys):
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert callable(load_capability_map)
    assert callable(build_mapping_index)


def test_scripts_do_not_import_one_another():
    validator = (SCRIPTS / "validate_creation_studio_capability_map.py").read_text(
        encoding="utf-8"
    )
    reconciler = (SCRIPTS / "reconcile_creation_studio_capabilities.py").read_text(
        encoding="utf-8"
    )
    assert "from validate_creation_studio_capability_map import" not in reconciler
    assert "import validate_creation_studio_capability_map" not in reconciler
    assert "from reconcile_creation_studio_capabilities import" not in validator
    assert "import reconcile_creation_studio_capabilities" not in validator
    assert "from _shared.creation_studio_capability_map import" in validator
    assert "from _shared.creation_studio_capability_map import" in reconciler


def test_canonical_map_index_is_deterministic():
    doc, index, identity = load_capability_map(CANONICAL_MAP)
    assert index == CANONICAL_INDEX
    assert identity.record_version == "1.0.0"
    assert identity.map_version == "1.0.0"
    again = build_mapping_index(doc)
    assert again == CANONICAL_INDEX
    assert json.dumps(index, sort_keys=True) == json.dumps(CANONICAL_INDEX, sort_keys=True)


def test_canonical_mapping_rows_are_unchanged():
    doc = json.loads(CANONICAL_MAP.read_text(encoding="utf-8"))
    rows = {
        entry["request_capability"]: entry["satisfied_by"]
        for entry in doc["mappings"]
    }
    assert rows == {
        "feeds_speeds_recommendation": ["feeds_speeds_authoring"],
        "gcode_explanation": ["gcode_tutorial_generation", "post_processor_education"],
        "simulation_request": ["simulation_support"],
    }


def test_normalize_provenance_path_collapses_equivalent_relative_spellings():
    assert normalize_provenance_path("./contracts/creation_studio_capability_map.json") == (
        "contracts/creation_studio_capability_map.json"
    )
    assert normalize_provenance_path(
        "contracts/../contracts/creation_studio_capability_map.json"
    ) == "contracts/creation_studio_capability_map.json"
    assert normalize_provenance_path(
        Path("contracts") / ".." / "contracts" / "creation_studio_capability_map.json"
    ) == "contracts/creation_studio_capability_map.json"


def test_normalize_provenance_path_does_not_absolutize_a_relative_input():
    raw = "contracts/creation_studio_capability_map.json"
    normalized = normalize_provenance_path(raw)
    assert not Path(normalized).is_absolute()
    assert "\\" not in normalized


def test_missing_schema_is_typed_input_error(tmp_path: Path):
    with pytest.raises(CapabilityMapInputError):
        load_a22_request_enum(tmp_path / "absent.json")


def test_build_mapping_index_does_not_silently_skip(tmp_path: Path):
    with pytest.raises(CapabilityMapContractError):
        build_mapping_index({"mappings": [{"request_capability": "   ", "satisfied_by": ["x"]}]})


def test_load_capability_map_document_missing_file(tmp_path: Path):
    with pytest.raises(CapabilityMapInputError, match="not found"):
        load_capability_map_document(tmp_path / "nope.json")


def test_validate_document_accepts_a_supplied_enum(tmp_path: Path):
    # Supplying the enum avoids touching the on-disk schema.
    result = validate_capability_map_document(
        {
            "record_type": "cam_assist_creation_studio_capability_map",
            "record_version": "1.0.0",
            "map_version": "1.0.0",
            "mappings": [],
            "authority": {
                "is_informational": True,
                "does_not_authorize_execution": True,
                "does_not_bypass_human_review": True,
                "does_not_confirm_machine_readiness": True,
                "does_not_grant_permission": True,
            },
        },
        a22_enum=["simulation_request"],
    )
    assert result.valid
