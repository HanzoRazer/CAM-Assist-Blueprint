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


def test_authority_is_closed(schema):
    # The non-execution block rejects undeclared flags.
    assert schema["properties"]["authority"]["additionalProperties"] is False


def test_top_level_is_closed(schema):
    # Unrecognized top-level fields are rejected.
    assert schema["additionalProperties"] is False


def test_created_at_is_declared_optional(schema):
    # created_at is a recognized optional field (declared, not required).
    assert schema["properties"]["created_at"]["type"] == "string"
    assert "created_at" not in schema["required"]


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


def test_applied_unknown_authority_flag_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_handoff()
    bad["authority"]["authorizes_execution"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_unknown_top_level_field_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_handoff()
    bad["surprise"] = "x"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_created_at_allowed(schema):
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_handoff()
    ok["created_at"] = "2026-07-09T00:00:00Z"
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_empty_created_at_fails(schema):
    # minLength:1 keeps the schema in step with the hand validator, which rejects
    # an empty created_at. Without it the schema would accept "" (format is an
    # annotation, not an assertion, under Draft202012Validator) while the
    # structural validator rejected it — the very schema/validator drift this
    # field's check exists to close.
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_handoff()
    bad["created_at"] = ""
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_whitespace_created_at_fails(schema):
    # The hand validator rejects a whitespace-only created_at via .strip();
    # pattern "\\S" makes the schema agree. minLength:1 alone would let "   "
    # through, reopening the drift in the opposite direction. Belt-and-suspenders
    # with the empty-string case above: together they fully close it.
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_handoff()
    bad["created_at"] = "   "
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_missing_created_at_allowed(schema):
    # created_at is optional (not in the schema's required list); the hand
    # validator only constrains it "when present". Lock that: a record with no
    # created_at at all must validate, so the non-empty checks above cannot be
    # misread as making the field mandatory.
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_handoff()
    ok.pop("created_at", None)
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_malformed_created_at_passes_without_format_checker(schema):
    # Documents a deliberately-unenforced boundary: `format: date-time` is an
    # annotation, not an assertion, under a bare Draft202012Validator, so a
    # non-empty but non-ISO-8601 string passes. This is the schema's actual
    # contract today (non-blank, not well-formed). If the project ever wants the
    # shape enforced, wire a FormatChecker into the validation path AND the
    # hand validator together — changing only this test would resurface drift.
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_handoff()
    ok["created_at"] = "not-a-timestamp"
    jsonschema.Draft202012Validator(schema).validate(ok)
