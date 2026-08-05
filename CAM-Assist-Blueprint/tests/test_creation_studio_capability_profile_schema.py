"""
Schema-contract tests for CAM-A23 Creation Studio Capability Profile.

Two layers (per the CAM-A19/A20/A22 pattern):

B (always run, dependency-free): assert the schema DOCUMENT encodes the contract.
    - dialect is JSON Schema 2020-12
    - record_type const + publication_direction const are correct
    - authority is REQUIRED with five const-true flags, closed
    - capabilities: array, minItems 1, uniqueItems, closed entries requiring a
      pattern-valid capability_id
    - record_version and profile_version are semantic-version constrained
    - created_at is NOT a recognized field (deliberately omitted for determinism)

C (optional, skipped unless `jsonschema` importable): APPLY the schema and witness
    behavior.

jsonschema is NOT a project dependency; C tests use importorskip.

Agreement between the schema and the Python constants in the validator/creator is
a separate concern, covered by test_creation_studio_capability_profile_drift.py —
this file depends on nothing but the schema document.
"""

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "creation_studio_capability_profile.schema.json"

AUTHORITY_FLAGS = {
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
    "does_not_confirm_machine_readiness",
    "does_not_require_capability_use",
}
CAPABILITY_FIELDS = {
    "capability_id",
    "display_name",
    "description",
    "documentation_reference",
}
TOP_LEVEL_FIELDS = {
    "record_type",
    "record_version",
    "profile_version",
    "studio_reference",
    "publication_direction",
    "capabilities",
    "authority",
}


@pytest.fixture(scope="module")
def schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _valid_profile() -> dict:
    return {
        "record_type": "creation_studio_capability_profile",
        "record_version": "1.0.0",
        "profile_version": "1.0.0",
        "studio_reference": "cam-creation-studio",
        "publication_direction": "creation_studio_to_cam_assist",
        "capabilities": [
            {"capability_id": "strategy_visualization"},
            {
                "capability_id": "feeds_speeds_authoring",
                "display_name": "Feeds & Speeds Authoring",
            },
        ],
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
            "does_not_confirm_machine_readiness": True,
            "does_not_require_capability_use": True,
        },
    }


# ---------------------------------------------------------------------------
# B — dependency-free contract assertions
# ---------------------------------------------------------------------------

def test_schema_is_2020_12(schema):
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_record_type_const(schema):
    assert schema["properties"]["record_type"]["const"] == "creation_studio_capability_profile"


def test_publication_direction_const(schema):
    assert (
        schema["properties"]["publication_direction"]["const"]
        == "creation_studio_to_cam_assist"
    )


def test_required_top_level_fields(schema):
    assert set(schema["required"]) == TOP_LEVEL_FIELDS


def test_top_level_is_closed(schema):
    assert schema["additionalProperties"] is False


def test_authority_has_five_const_true_flags(schema):
    auth = schema["properties"]["authority"]
    assert set(auth["required"]) == AUTHORITY_FLAGS
    assert auth["additionalProperties"] is False
    for flag in AUTHORITY_FLAGS:
        assert auth["properties"][flag]["const"] is True


def test_semantic_version_fields(schema):
    # record_version tracks the record FORMAT; profile_version tracks the
    # PUBLISHED CAPABILITY SET and is owned by Creation Studio. Both are semver.
    pattern = r"^[0-9]+\.[0-9]+\.[0-9]+$"
    assert schema["properties"]["record_version"]["pattern"] == pattern
    assert schema["properties"]["profile_version"]["pattern"] == pattern


def test_capabilities_array_shape(schema):
    caps = schema["properties"]["capabilities"]
    assert caps["type"] == "array"
    assert caps["minItems"] == 1
    # uniqueItems only rejects wholly identical entries. Full capability_id
    # uniqueness cannot be expressed in vanilla JSON Schema and is enforced by
    # the structural validator instead (see test_identifier_uniqueness_* below
    # and the validator tests).
    assert caps["uniqueItems"] is True


def test_capability_entry_is_closed_and_requires_identifier(schema):
    item = schema["properties"]["capabilities"]["items"]
    assert item["type"] == "object"
    assert item["additionalProperties"] is False
    assert item["required"] == ["capability_id"]
    assert set(item["properties"].keys()) == CAPABILITY_FIELDS


def test_capability_id_is_pattern_constrained_not_enumerated(schema):
    # The vocabulary is OPEN by design: Creation Studio owns its own capability
    # evolution, so a closed enum here would couple the two repositories exactly
    # where the contract exists to keep them apart.
    cap_id = schema["properties"]["capabilities"]["items"]["properties"]["capability_id"]
    assert cap_id["pattern"] == "^[a-z][a-z0-9_]*$"
    assert "enum" not in cap_id


def test_documentation_reference_rejects_absolute_paths(schema):
    doc_ref = schema["properties"]["capabilities"]["items"]["properties"][
        "documentation_reference"
    ]
    assert doc_ref["pattern"] == "^(?![\\\\/])(?![A-Za-z]:)\\S"


def test_created_at_is_not_a_field(schema):
    # created_at is deliberately omitted so the artifact regenerates byte-identically.
    assert "created_at" not in schema["properties"]
    assert "created_at" not in schema["required"]


# ---------------------------------------------------------------------------
# C — applied schema validation (optional)
# ---------------------------------------------------------------------------

def test_applied_valid_profile_passes(schema):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator(schema).validate(_valid_profile())


def test_applied_invalid_record_type_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["record_type"] = "cam_assist_creation_studio_request"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_wrong_direction_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["publication_direction"] = "cam_assist_to_creation_studio"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_missing_authority_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    del bad["authority"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_authority_missing_fifth_flag_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    del bad["authority"]["does_not_require_capability_use"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_false_authority_flag_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["authority"]["does_not_authorize_execution"] = False
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_unknown_authority_flag_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["authority"]["authorizes_execution"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_empty_capabilities_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["capabilities"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_identical_duplicate_capability_entries_fail(schema):
    # uniqueItems catches wholly identical entries...
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["capabilities"] = [
        {"capability_id": "simulation_support"},
        {"capability_id": "simulation_support"},
    ]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_same_id_different_entries_pass_schema(schema):
    # ...but NOT two entries that share an identifier while differing elsewhere.
    # This is the documented limit of vanilla JSON Schema, and precisely why the
    # structural validator owns capability_id uniqueness. Asserting the gap here
    # keeps the split honest: if a future schema construct closes it, this test
    # fails and the division of labour gets revisited deliberately.
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_profile()
    ok["capabilities"] = [
        {"capability_id": "simulation_support"},
        {"capability_id": "simulation_support", "display_name": "Simulation Support"},
    ]
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_unknown_capability_identifier_passes(schema):
    # The vocabulary is open: an identifier this repository has never seen is
    # valid as long as it is well-shaped.
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_profile()
    ok["capabilities"] = [{"capability_id": "a_capability_invented_next_year"}]
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_malformed_capability_identifier_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    for bad_id in ("Strategy Visualization", "9_lives", "has-hyphen", "UPPER", ""):
        bad = _valid_profile()
        bad["capabilities"] = [{"capability_id": bad_id}]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_unknown_capability_field_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["capabilities"] = [{"capability_id": "simulation_support", "approved": True}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_capability_without_identifier_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["capabilities"] = [{"display_name": "Nameless"}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_blank_display_name_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["capabilities"] = [{"capability_id": "simulation_support", "display_name": "  "}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_relative_documentation_reference_passes(schema):
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_profile()
    ok["capabilities"][0]["documentation_reference"] = "docs/strategy_visualization.md"
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_absolute_documentation_reference_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    for bad_ref in ("/etc/passwd", "C:/Windows/x.md", "\\\\server\\share\\x.md"):
        bad = _valid_profile()
        bad["capabilities"][0]["documentation_reference"] = bad_ref
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_malformed_versions_fail(schema):
    jsonschema = pytest.importorskip("jsonschema")
    for field in ("record_version", "profile_version"):
        bad = _valid_profile()
        bad[field] = "1.0"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_profile_version_may_differ_from_record_version(schema):
    # The capability-set version is owned by Creation Studio and is independent
    # of the record format version (and of the CAM Assist version).
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_profile()
    ok["profile_version"] = "4.2.0"
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_blank_studio_reference_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["studio_reference"] = "   "
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_unknown_top_level_field_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["surprise"] = "x"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_created_at_is_rejected_as_unknown_field(schema):
    # created_at is not part of this contract; the closed top level rejects it.
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_profile()
    bad["created_at"] = "2026-08-02T00:00:00Z"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)
