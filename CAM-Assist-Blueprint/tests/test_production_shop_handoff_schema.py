"""
Phase 1 tests for CAM-A20 Production Shop Handoff — schema contract.

Two layers (per the CAM-A19 Phase 1 pattern):

B (always run, dependency-free): assert the schema DOCUMENT encodes the contract.
    - dialect is JSON Schema 2020-12
    - record_type const + handoff_direction const are correct
    - authority is REQUIRED with four const-true flags
    - contents is required, object-shaped, closed to four known string slots
    - empty contents is allowed (no minProperties)

C (optional, skipped unless `jsonschema` importable): APPLY the schema and witness behavior.

jsonschema is NOT a project dependency; C tests use importorskip.
"""

import json
from pathlib import Path

import pytest


SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "production_shop_handoff.schema.json"

KNOWN_SLOTS = {
    "package_manifest_file",
    "strategy_file",
    "review_packet_file",
    "traceability_bundle_file",
}
AUTHORITY_FLAGS = {
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
    "does_not_confirm_machine_readiness",
}


@pytest.fixture(scope="module")
def schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _valid_handoff() -> dict:
    return {
        "record_type": "cam_assist_production_shop_handoff",
        "record_version": "1.0.0",
        "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
        "handoff_direction": "cam_assist_to_production_shop",
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
            "does_not_confirm_machine_readiness": True,
        },
        "contents": {
            "package_manifest_file": "../packages/pkg/manifest.json",
            "strategy_file": "../packages/pkg/strategy.json",
        },
    }


# ---------------------------------------------------------------------------
# B — dependency-free contract assertions
# ---------------------------------------------------------------------------

def test_schema_is_2020_12(schema):
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_record_type_const(schema):
    assert schema["properties"]["record_type"]["const"] == "cam_assist_production_shop_handoff"


def test_handoff_direction_const(schema):
    assert schema["properties"]["handoff_direction"]["const"] == "cam_assist_to_production_shop"


def test_required_top_level_fields(schema):
    assert {
        "record_type",
        "record_version",
        "package_reference",
        "handoff_direction",
        "authority",
        "contents",
    } <= set(schema["required"])


def test_authority_is_required(schema):
    assert "authority" in schema["required"]


def test_authority_has_four_const_true_flags(schema):
    auth = schema["properties"]["authority"]
    assert set(auth["required"]) == AUTHORITY_FLAGS
    for flag in AUTHORITY_FLAGS:
        assert auth["properties"][flag]["const"] is True


def test_contents_required_and_closed(schema):
    assert "contents" in schema["required"]
    contents = schema["properties"]["contents"]
    assert contents["type"] == "object"
    assert contents["additionalProperties"] is False
    assert set(contents["properties"].keys()) == KNOWN_SLOTS


def test_contents_slots_string_typed(schema):
    props = schema["properties"]["contents"]["properties"]
    for slot in KNOWN_SLOTS:
        assert props[slot]["type"] == "string"


def test_empty_contents_allowed(schema):
    # No minProperties -> {} permitted (no individual slot required).
    assert "minProperties" not in schema["properties"]["contents"]


# ---------------------------------------------------------------------------
# C — applied schema validation (optional)
# ---------------------------------------------------------------------------

def test_applied_valid_handoff_passes(schema):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator(schema).validate(_valid_handoff())


def test_applied_invalid_record_type_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_handoff()
    bad["record_type"] = "cam_assist_not_a_handoff"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_wrong_direction_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_handoff()
    bad["handoff_direction"] = "production_shop_to_cam_assist"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_missing_authority_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_handoff()
    del bad["authority"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_authority_missing_fourth_flag_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_handoff()
    del bad["authority"]["does_not_confirm_machine_readiness"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_unknown_content_slot_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_handoff()
    bad["contents"]["unknown_file"] = "x.json"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_non_object_contents_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_handoff()
    bad["contents"] = "not-an-object"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_empty_contents_passes(schema):
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_handoff()
    ok["contents"] = {}
    jsonschema.Draft202012Validator(schema).validate(ok)
