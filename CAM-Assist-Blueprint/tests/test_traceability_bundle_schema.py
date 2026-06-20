"""
Phase 1 tests for CAM-A19 Traceability Bundle — schema contract.

Two layers, per the CAM-A19 dev order:

B (always run, dependency-free): assert the schema DOCUMENT encodes the contract.
    - dialect is JSON Schema 2020-12
    - record_type const is correct
    - bundle_contents is required and object-shaped
    - the five known reference slots are encoded (and closed: no unknown slots)
    - empty bundle_contents is allowed (no minProperties)

C (optional, skipped unless `jsonschema` is importable): APPLY the schema and
    witness actual validation behavior.
    - valid bundle passes
    - invalid record_type fails
    - non-object bundle_contents fails
    - empty bundle_contents passes

jsonschema is NOT a project dependency. The C tests use importorskip so the suite
always runs clean dependency-free; runtime validators never use jsonschema.
"""

import json
from pathlib import Path

import pytest


SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "traceability_bundle.schema.json"

KNOWN_SLOTS = {
    "assumptions_file",
    "risk_file",
    "decision_record_file",
    "annotations_file",
    "lineage_file",
}


@pytest.fixture(scope="module")
def schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _valid_bundle() -> dict:
    """A minimal structurally-valid bundle (references need not exist on disk)."""
    return {
        "record_type": "cam_assist_traceability_bundle",
        "record_version": "1.0.0",
        "package_reference": "luthiers-toolbox:vcarve:example-001",
        "bundle_contents": {
            "assumptions_file": "pkg_assumptions.json",
            "risk_file": "pkg_risk.json",
        },
    }


# ---------------------------------------------------------------------------
# B — dependency-free contract assertions (always run)
# ---------------------------------------------------------------------------

def test_schema_is_2020_12(schema):
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_schema_top_level_is_object(schema):
    assert schema["type"] == "object"


def test_record_type_const_is_correct(schema):
    assert schema["properties"]["record_type"]["const"] == "cam_assist_traceability_bundle"


def test_required_top_level_fields(schema):
    required = set(schema["required"])
    assert {
        "record_type",
        "record_version",
        "package_reference",
        "bundle_contents",
    } <= required


def test_bundle_contents_is_required(schema):
    assert "bundle_contents" in schema["required"]


def test_bundle_contents_is_object_shaped(schema):
    bc = schema["properties"]["bundle_contents"]
    assert bc["type"] == "object"


def test_bundle_contents_is_closed_to_known_slots(schema):
    bc = schema["properties"]["bundle_contents"]
    # Unknown reference kinds must be rejected structurally.
    assert bc["additionalProperties"] is False
    assert set(bc["properties"].keys()) == KNOWN_SLOTS


def test_known_slots_are_string_typed(schema):
    bc = schema["properties"]["bundle_contents"]
    for slot in KNOWN_SLOTS:
        assert bc["properties"][slot]["type"] == "string"


def test_empty_bundle_contents_is_allowed(schema):
    bc = schema["properties"]["bundle_contents"]
    # No minProperties means {} is permitted (missing sidecars are allowed).
    assert "minProperties" not in bc


def test_authority_is_optional_but_const_true_when_present(schema):
    # authority is not in the top-level required list ...
    assert "authority" not in schema["required"]
    auth = schema["properties"]["authority"]
    # ... but when present, all three flags are required and const true.
    assert set(auth["required"]) == {
        "is_informational",
        "does_not_authorize_execution",
        "does_not_bypass_human_review",
    }
    for flag in auth["required"]:
        assert auth["properties"][flag]["const"] is True


# ---------------------------------------------------------------------------
# C — applied schema validation (optional; only if jsonschema is importable)
# ---------------------------------------------------------------------------

def _validator(schema):
    jsonschema = pytest.importorskip("jsonschema")
    return jsonschema.Draft202012Validator(schema)


def test_applied_valid_bundle_passes(schema):
    jsonschema = pytest.importorskip("jsonschema")
    # Raises if invalid; passing means the good bundle validates.
    jsonschema.Draft202012Validator(schema).validate(_valid_bundle())


def test_applied_invalid_record_type_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_bundle()
    bad["record_type"] = "cam_assist_not_a_bundle"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_non_object_bundle_contents_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_bundle()
    bad["bundle_contents"] = "not-an-object"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_empty_bundle_contents_passes(schema):
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_bundle()
    ok["bundle_contents"] = {}
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_unknown_slot_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_bundle()
    bad["bundle_contents"]["unknown_file"] = "x.json"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)
