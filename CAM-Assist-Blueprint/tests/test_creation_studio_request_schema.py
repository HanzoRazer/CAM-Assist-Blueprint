"""
Phase 2 tests for CAM-A22 Creation Studio Capability Request — schema contract.

Two layers (per the CAM-A19/A20 Phase 1 pattern):

B (always run, dependency-free): assert the schema DOCUMENT encodes the contract.
    - dialect is JSON Schema 2020-12
    - record_type const + request_direction const are correct
    - authority is REQUIRED with five const-true flags, closed
    - requested_capabilities: array, minItems 1, uniqueItems, enum-constrained
    - contents is required, object-shaped, closed to five known string slots
    - request_context is optional and closed
    - created_at is NOT a recognized field (deliberately omitted for determinism)

C (optional, skipped unless `jsonschema` importable): APPLY the schema and witness
    behavior.

jsonschema is NOT a project dependency; C tests use importorskip.
"""

import json
from pathlib import Path

import pytest


SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "creation_studio_request.schema.json"

CONTENT_SLOTS = {
    "package_manifest_file",
    "strategy_file",
    "review_packet_file",
    "traceability_bundle_file",
    "production_shop_handoff_file",
}
AUTHORITY_FLAGS = {
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
    "does_not_confirm_machine_readiness",
    "does_not_require_gcode_generation",
}
CAPABILITY_VOCABULARY = {
    "feeds_speeds_recommendation",
    "tooling_review",
    "operation_sequence_analysis",
    "cycle_time_estimation",
    "simulation_request",
    "gcode_explanation",
    "toolpath_development_request",
    "workholding_review",
}


@pytest.fixture(scope="module")
def schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _valid_request() -> dict:
    return {
        "record_type": "cam_assist_creation_studio_request",
        "record_version": "1.0.0",
        "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
        "request_direction": "cam_assist_to_creation_studio",
        "requested_capabilities": [
            "feeds_speeds_recommendation",
            "tooling_review",
            "operation_sequence_analysis",
        ],
        "contents": {
            "package_manifest_file": "../packages/pkg/manifest.json",
            "strategy_file": "../packages/pkg/strategy.json",
            "review_packet_file": "../packages/pkg/review_packet.md",
        },
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
            "does_not_confirm_machine_readiness": True,
            "does_not_require_gcode_generation": True,
        },
    }


# ---------------------------------------------------------------------------
# B — dependency-free contract assertions
# ---------------------------------------------------------------------------

def test_schema_is_2020_12(schema):
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_record_type_const(schema):
    assert schema["properties"]["record_type"]["const"] == "cam_assist_creation_studio_request"


def test_request_direction_const(schema):
    assert schema["properties"]["request_direction"]["const"] == "cam_assist_to_creation_studio"


def test_required_top_level_fields(schema):
    assert set(schema["required"]) == {
        "record_type",
        "record_version",
        "package_reference",
        "request_direction",
        "requested_capabilities",
        "contents",
        "authority",
    }


def test_authority_has_five_const_true_flags(schema):
    auth = schema["properties"]["authority"]
    assert set(auth["required"]) == AUTHORITY_FLAGS
    assert auth["additionalProperties"] is False
    for flag in AUTHORITY_FLAGS:
        assert auth["properties"][flag]["const"] is True


def test_requested_capabilities_shape(schema):
    caps = schema["properties"]["requested_capabilities"]
    assert caps["type"] == "array"
    assert caps["minItems"] == 1
    assert caps["uniqueItems"] is True
    assert set(caps["items"]["enum"]) == CAPABILITY_VOCABULARY


def test_contents_required_and_closed(schema):
    assert "contents" in schema["required"]
    contents = schema["properties"]["contents"]
    assert contents["type"] == "object"
    assert contents["additionalProperties"] is False
    assert set(contents["properties"].keys()) == CONTENT_SLOTS


def test_contents_slots_string_typed(schema):
    props = schema["properties"]["contents"]["properties"]
    for slot in CONTENT_SLOTS:
        assert props[slot]["type"] == "string"


def test_request_context_optional_and_closed(schema):
    assert "request_context" not in schema["required"]
    ctx = schema["properties"]["request_context"]
    assert ctx["type"] == "object"
    assert ctx["additionalProperties"] is False
    assert set(ctx["properties"].keys()) == {"material", "machine_profile", "operator_notes"}


def test_top_level_is_closed(schema):
    assert schema["additionalProperties"] is False


def test_created_at_is_not_a_field(schema):
    # created_at is deliberately omitted so the artifact regenerates byte-identically.
    assert "created_at" not in schema["properties"]
    assert "created_at" not in schema["required"]


# ---------------------------------------------------------------------------
# C — applied schema validation (optional)
# ---------------------------------------------------------------------------

def test_applied_valid_request_passes(schema):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator(schema).validate(_valid_request())


def test_applied_invalid_record_type_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["record_type"] = "cam_assist_not_a_request"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_wrong_direction_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["request_direction"] = "creation_studio_to_cam_assist"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_missing_authority_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    del bad["authority"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_authority_missing_fifth_flag_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    del bad["authority"]["does_not_require_gcode_generation"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_false_authority_flag_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["authority"]["does_not_authorize_execution"] = False
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_empty_capabilities_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["requested_capabilities"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_duplicate_capabilities_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["requested_capabilities"] = ["tooling_review", "tooling_review"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_unknown_capability_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["requested_capabilities"] = ["make_me_a_sandwich"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_empty_contents_passes(schema):
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_request()
    ok["contents"] = {}
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_all_five_content_slots_pass(schema):
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_request()
    ok["contents"]["traceability_bundle_file"] = "../traceability/pkg_bundle.json"
    ok["contents"]["production_shop_handoff_file"] = "../production_shop/pkg_handoff.json"
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_unknown_content_slot_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["contents"]["unknown_file"] = "x.json"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_unknown_authority_flag_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["authority"]["authorizes_execution"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_unknown_top_level_field_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["surprise"] = "x"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_created_at_is_rejected_as_unknown_field(schema):
    # created_at is not part of this contract; the closed top level rejects it.
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["created_at"] = "2026-07-11T00:00:00Z"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_request_context_passes(schema):
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_request()
    ok["request_context"] = {
        "material": "mahogany",
        "machine_profile": None,
        "operator_notes": "Review before downstream toolpath development.",
    }
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_request_context_unknown_field_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_request()
    bad["request_context"] = {"surprise": "x"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)
