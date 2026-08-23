"""
Validator tests for CAM-A26 Creation Studio Capability Map.

Witnesses the structural layer (filesystem-free):

Positive:
- a valid map passes
- empty mappings array is an explicit "no bridges" declaration
- an A23 identifier the shipped profile has never seen is a legal target
- map_version may differ from record_version

Negative:
- unknown A22 source identifier
- duplicate source mapping entries
- duplicate target inside one satisfied_by list
- blank / missing rationale
- empty satisfied_by
- invalid record_type / versions
- invalid authority (false, missing, unknown flag)
- unknown top-level / mapping fields
- illegal A23 target syntax

The same target may appear in mappings for different request identifiers.

The CLI is exercised as a subprocess. The committed canonical registry is
validated as a regression, and every source in it is checked against the
authoritative A22 enum extracted from the request schema.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate_creation_studio_capability_map.py"
A22_SCHEMA = REPO_ROOT / "schemas" / "creation_studio_request.schema.json"
CANONICAL_MAP = REPO_ROOT / "contracts" / "creation_studio_capability_map.json"
EXAMPLE_PROFILE = REPO_ROOT / "examples" / "creation_studio" / "capability_profile.json"

SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _shared.creation_studio_capability_map import (  # noqa: E402
    CapabilityMapContractError,
    CapabilityMapInputError,
    build_mapping_index,
    load_a22_request_enum,
    load_capability_map,
    validate_map,
)


def run_validate(*args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(VALIDATE_SCRIPT)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def valid_map() -> dict:
    return {
        "record_type": "cam_assist_creation_studio_capability_map",
        "record_version": "1.0.0",
        "map_version": "1.0.0",
        "mappings": [
            {
                "request_capability": "simulation_request",
                "satisfied_by": ["simulation_support"],
                "rationale": "Explicit correspondence for compatibility reporting.",
            }
        ],
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
            "does_not_confirm_machine_readiness": True,
            "does_not_grant_permission": True,
        },
    }


def write_map(tmp_path: Path, data, name: str = "capability_map.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def a22_enum() -> list[str]:
    return load_a22_request_enum(A22_SCHEMA)


# ---------------------------------------------------------------------------
# A22 source authority
# ---------------------------------------------------------------------------


def test_a22_enum_is_read_from_the_request_schema_not_copied():
    enum = a22_enum()
    schema = json.loads(A22_SCHEMA.read_text(encoding="utf-8"))
    assert enum == schema["properties"]["requested_capabilities"]["items"]["enum"]
    assert "feeds_speeds_recommendation" in enum
    assert "unknown_request_capability" not in enum


def test_unknown_request_capability_is_rejected():
    doc = valid_map()
    doc["mappings"][0]["request_capability"] = "unknown_request_capability"
    result = validate_map(doc)
    assert not result.valid
    assert any("unknown_request_capability" in error for error in result.errors)
    assert any("A22" in error for error in result.errors)


def test_every_legal_a22_identifier_is_accepted_as_a_source():
    for identifier in a22_enum():
        doc = valid_map()
        doc["mappings"][0]["request_capability"] = identifier
        result = validate_map(doc)
        assert result.valid, (identifier, result.errors)


# ---------------------------------------------------------------------------
# open A23 targets
# ---------------------------------------------------------------------------


def test_open_target_not_in_example_profile_is_structurally_valid():
    example = json.loads(EXAMPLE_PROFILE.read_text(encoding="utf-8"))
    declared = {entry["capability_id"] for entry in example["capabilities"]}
    novel = "future_studio_capability_xyz"
    assert novel not in declared

    doc = valid_map()
    doc["mappings"][0]["satisfied_by"] = [novel]
    result = validate_map(doc)
    assert result.valid, result.errors


def test_illegal_target_syntax_is_rejected():
    doc = valid_map()
    doc["mappings"][0]["satisfied_by"] = ["Not-Legal"]
    result = validate_map(doc)
    assert not result.valid
    assert any("Not-Legal" in error for error in result.errors)


# ---------------------------------------------------------------------------
# duplicates
# ---------------------------------------------------------------------------


def test_duplicate_source_entries_are_rejected():
    doc = valid_map()
    doc["mappings"] = [
        {
            "request_capability": "simulation_request",
            "satisfied_by": ["simulation_support"],
            "rationale": "first",
        },
        {
            "request_capability": "simulation_request",
            "satisfied_by": ["feeds_speeds_authoring"],
            "rationale": "second",
        },
    ]
    result = validate_map(doc)
    assert not result.valid
    assert any("duplicate request_capability" in error for error in result.errors)


def test_duplicate_target_inside_one_mapping_is_rejected():
    doc = valid_map()
    doc["mappings"][0]["satisfied_by"] = ["simulation_support", "simulation_support"]
    result = validate_map(doc)
    assert not result.valid
    assert any("duplicate target" in error for error in result.errors)


def test_same_target_may_satisfy_different_requests():
    doc = valid_map()
    doc["mappings"] = [
        {
            "request_capability": "simulation_request",
            "satisfied_by": ["simulation_support"],
            "rationale": "simulation correspondence",
        },
        {
            "request_capability": "gcode_explanation",
            "satisfied_by": ["simulation_support"],
            "rationale": "shared target is permitted across mappings",
        },
    ]
    result = validate_map(doc)
    assert result.valid, result.errors


# ---------------------------------------------------------------------------
# structural positives and negatives
# ---------------------------------------------------------------------------


def test_valid_map_passes():
    assert validate_map(valid_map()).valid


def test_empty_mappings_pass():
    doc = valid_map()
    doc["mappings"] = []
    assert validate_map(doc).valid


def test_blank_rationale_is_rejected():
    doc = valid_map()
    doc["mappings"][0]["rationale"] = "   "
    result = validate_map(doc)
    assert not result.valid
    assert any("rationale" in error for error in result.errors)


def test_missing_rationale_is_rejected():
    doc = valid_map()
    del doc["mappings"][0]["rationale"]
    result = validate_map(doc)
    assert not result.valid


def test_empty_satisfied_by_is_rejected():
    doc = valid_map()
    doc["mappings"][0]["satisfied_by"] = []
    result = validate_map(doc)
    assert not result.valid


def test_wrong_record_type_is_rejected():
    doc = valid_map()
    doc["record_type"] = "creation_studio_capability_profile"
    result = validate_map(doc)
    assert not result.valid


def test_malformed_versions_are_rejected():
    for field in ("record_version", "map_version"):
        doc = valid_map()
        doc[field] = "v1"
        result = validate_map(doc)
        assert not result.valid, field


def test_map_version_may_differ_from_record_version():
    doc = valid_map()
    doc["record_version"] = "1.0.0"
    doc["map_version"] = "2.3.1"
    assert validate_map(doc).valid


def test_authority_false_flag_is_rejected():
    doc = valid_map()
    doc["authority"]["does_not_grant_permission"] = False
    result = validate_map(doc)
    assert not result.valid


def test_unknown_authority_flag_is_rejected():
    doc = valid_map()
    doc["authority"]["approved"] = True
    result = validate_map(doc)
    assert not result.valid
    assert any("unknown flag" in error for error in result.errors)


def test_unknown_top_level_field_is_rejected():
    doc = valid_map()
    doc["execution_allowed"] = False
    result = validate_map(doc)
    assert not result.valid


def test_build_mapping_index_sorts_targets_and_ignores_array_order():
    doc = valid_map()
    doc["mappings"] = [
        {
            "request_capability": "gcode_explanation",
            "satisfied_by": ["post_processor_education", "gcode_tutorial_generation"],
            "rationale": "any_of",
        }
    ]
    index = build_mapping_index(doc)
    assert index["gcode_explanation"] == [
        "gcode_tutorial_generation",
        "post_processor_education",
    ]


# ---------------------------------------------------------------------------
# canonical registry
# ---------------------------------------------------------------------------


def test_canonical_map_is_structurally_valid():
    code, stdout, stderr = run_validate(CANONICAL_MAP)
    assert code == 0, stderr
    assert "PASS" in stdout


def test_canonical_sources_are_all_in_the_a22_enum():
    doc = json.loads(CANONICAL_MAP.read_text(encoding="utf-8"))
    enum = set(a22_enum())
    sources = [entry["request_capability"] for entry in doc["mappings"]]
    assert sources
    assert set(sources) <= enum
    assert len(sources) == len(set(sources))


def test_canonical_map_does_not_claim_unmapped_a22_identifiers():
    """Conservative initial registry: unmapped A22 ids stay unmapped.

    The remaining request identifiers have no honest A23 correspondence in the
    shipped profile. Recording them would be inference.
    """
    doc = json.loads(CANONICAL_MAP.read_text(encoding="utf-8"))
    sources = {entry["request_capability"] for entry in doc["mappings"]}
    assert sources == {
        "feeds_speeds_recommendation",
        "gcode_explanation",
        "simulation_request",
    }
    unmapped = set(a22_enum()) - sources
    assert unmapped == {
        "tooling_review",
        "operation_sequence_analysis",
        "cycle_time_estimation",
        "toolpath_development_request",
        "workholding_review",
    }


def test_canonical_rationales_are_non_blank():
    doc = json.loads(CANONICAL_MAP.read_text(encoding="utf-8"))
    for entry in doc["mappings"]:
        assert entry["rationale"].strip()


def test_load_capability_map_returns_index_and_identity():
    doc, index, identity = load_capability_map(CANONICAL_MAP)
    assert doc["record_type"] == "cam_assist_creation_studio_capability_map"
    assert identity.record_version == "1.0.0"
    assert identity.map_version == "1.0.0"
    assert index["simulation_request"] == ["simulation_support"]
    assert "gcode_tutorial_generation" in index["gcode_explanation"]


def test_load_capability_map_rejects_unknown_source(tmp_path: Path):
    doc = valid_map()
    doc["mappings"][0]["request_capability"] = "unknown_request_capability"
    path = write_map(tmp_path, doc)
    with pytest.raises(CapabilityMapContractError, match="unknown_request_capability"):
        load_capability_map(path)


def test_build_mapping_index_rejects_malformed_rows():
    with pytest.raises(CapabilityMapContractError, match="must be an object"):
        build_mapping_index({"mappings": ["not-an-object"]})
    with pytest.raises(CapabilityMapContractError, match="request_capability"):
        build_mapping_index({"mappings": [{"satisfied_by": ["simulation_support"]}]})
    with pytest.raises(CapabilityMapContractError, match="satisfied_by"):
        build_mapping_index(
            {"mappings": [{"request_capability": "simulation_request", "satisfied_by": "x"}]}
        )
    with pytest.raises(CapabilityMapContractError, match="non-blank string"):
        build_mapping_index(
            {
                "mappings": [
                    {"request_capability": "simulation_request", "satisfied_by": [""]}
                ]
            }
        )
    with pytest.raises(CapabilityMapContractError, match="non-blank string"):
        build_mapping_index(
            {
                "mappings": [
                    {"request_capability": "simulation_request", "satisfied_by": [1]}
                ]
            }
        )


def test_missing_a22_schema_is_an_input_error(tmp_path: Path):
    with pytest.raises(CapabilityMapInputError, match="not found"):
        load_a22_request_enum(tmp_path / "missing_schema.json")


def test_malformed_a22_schema_is_an_input_error(tmp_path: Path):
    bad = tmp_path / "bad_schema.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(CapabilityMapInputError, match="not valid JSON"):
        load_a22_request_enum(bad)


def test_structurally_changed_a22_schema_is_an_input_error(tmp_path: Path):
    bad = tmp_path / "changed.json"
    bad.write_text(json.dumps({"properties": {}}), encoding="utf-8")
    with pytest.raises(CapabilityMapInputError, match="requested_capabilities"):
        load_a22_request_enum(bad)


def test_validator_cli_missing_schema_exits_2_without_traceback(
    tmp_path: Path, monkeypatch, capsys
):
    import _shared.creation_studio_capability_map as shared
    import validate_creation_studio_capability_map as validator

    monkeypatch.setattr(shared, "default_a22_schema_path", lambda: tmp_path / "nope.json")
    path = write_map(tmp_path, valid_map())
    monkeypatch.setattr(sys, "argv", ["validate_creation_studio_capability_map.py", str(path)])
    code = validator.main()
    captured = capsys.readouterr()
    assert code == 2
    assert "Traceback (most recent call last)" not in captured.err
    assert "A22 request schema" in captured.err


def test_validator_cli_malformed_schema_exits_2_without_traceback(
    tmp_path: Path, monkeypatch, capsys
):
    import _shared.creation_studio_capability_map as shared
    import validate_creation_studio_capability_map as validator

    schema = tmp_path / "schema.json"
    schema.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(shared, "default_a22_schema_path", lambda: schema)
    path = write_map(tmp_path, valid_map())
    monkeypatch.setattr(sys, "argv", ["validate_creation_studio_capability_map.py", str(path)])
    code = validator.main()
    captured = capsys.readouterr()
    assert code == 2
    assert "Traceback (most recent call last)" not in captured.err
    assert captured.out.strip() == ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_pass_and_fail(tmp_path: Path):
    good = write_map(tmp_path, valid_map(), "good.json")
    code, stdout, stderr = run_validate(good)
    assert code == 0, stderr
    assert "PASS" in stdout

    bad_doc = valid_map()
    bad_doc["mappings"][0]["request_capability"] = "unknown_request_capability"
    bad = write_map(tmp_path, bad_doc, "bad.json")
    code, stdout, stderr = run_validate(bad)
    assert code == 1
    assert "FAIL" in stderr
    assert stdout.strip() == "" or "PASS" not in stdout


def test_cli_missing_file_exits_2(tmp_path: Path):
    code, stdout, stderr = run_validate(tmp_path / "nope.json")
    assert code == 2
    assert "File not found" in stderr
