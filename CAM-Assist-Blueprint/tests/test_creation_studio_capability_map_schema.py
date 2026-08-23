"""
Schema-contract tests for CAM-A26 Creation Studio Capability Map.

Two layers (per the CAM-A19/A20/A22/A23 pattern):

B (always run, dependency-free): assert the schema DOCUMENT encodes the contract.
    - dialect is JSON Schema 2020-12
    - record_type const is correct
    - authority is REQUIRED with five const-true flags, closed
    - mappings required; entries require request_capability, satisfied_by, rationale
    - satisfied_by is a non-empty unique array of A23-pattern strings
    - rationale is a non-blank string
    - A22 sources are NOT re-enumerated here (the request schema is authoritative)
    - created_at is NOT a recognized field

C (optional, skipped unless `jsonschema` importable): APPLY the schema and witness
    behavior.

jsonschema is NOT a project dependency; C tests use importorskip.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "creation_studio_capability_map.schema.json"
A22_SCHEMA_PATH = REPO_ROOT / "schemas" / "creation_studio_request.schema.json"

AUTHORITY_FLAGS = {
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
    "does_not_confirm_machine_readiness",
    "does_not_grant_permission",
}
MAPPING_FIELDS = {"request_capability", "satisfied_by", "rationale"}
TOP_LEVEL_FIELDS = {
    "record_type",
    "record_version",
    "map_version",
    "mappings",
    "authority",
}


@pytest.fixture(scope="module")
def schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def a22_enum() -> list[str]:
    doc = json.loads(A22_SCHEMA_PATH.read_text(encoding="utf-8"))
    return doc["properties"]["requested_capabilities"]["items"]["enum"]


def _valid_map() -> dict:
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


# ---------------------------------------------------------------------------
# B — dependency-free contract assertions
# ---------------------------------------------------------------------------


def test_schema_is_2020_12(schema):
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_record_type_const(schema):
    assert (
        schema["properties"]["record_type"]["const"]
        == "cam_assist_creation_studio_capability_map"
    )


def test_required_top_level_fields(schema):
    assert set(schema["required"]) == TOP_LEVEL_FIELDS


def test_top_level_is_closed(schema):
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == TOP_LEVEL_FIELDS


def test_versions_are_semver_and_not_interpreted(schema):
    for field in ("record_version", "map_version"):
        node = schema["properties"][field]
        assert node["type"] == "string"
        assert node["pattern"] == "^[0-9]+\\.[0-9]+\\.[0-9]+$"
        assert "never interpreted" in node["description"].lower()


def test_authority_has_five_const_true_flags(schema):
    auth = schema["properties"]["authority"]
    assert set(auth["required"]) == AUTHORITY_FLAGS
    assert auth["additionalProperties"] is False
    for flag in AUTHORITY_FLAGS:
        assert auth["properties"][flag]["const"] is True


def test_authority_does_not_grant_permission(schema):
    # The mapping-specific fifth flag. A22 uses does_not_require_gcode_generation;
    # A23 uses does_not_require_capability_use. A26 must not invent an approval flag.
    auth = schema["properties"]["authority"]["properties"]
    assert "does_not_grant_permission" in auth
    for forbidden in ("approved", "authorized", "safe", "machine_ready", "permission"):
        assert forbidden not in auth


def test_mappings_array_required(schema):
    mappings = schema["properties"]["mappings"]
    assert mappings["type"] == "array"
    assert "mappings" in schema["required"]


def test_mapping_entry_requires_source_targets_and_rationale(schema):
    entry = schema["properties"]["mappings"]["items"]
    assert set(entry["required"]) == MAPPING_FIELDS
    assert entry["additionalProperties"] is False
    assert set(entry["properties"]) == MAPPING_FIELDS


def test_satisfied_by_is_non_empty_unique_a23_pattern(schema):
    targets = schema["properties"]["mappings"]["items"]["properties"]["satisfied_by"]
    assert targets["type"] == "array"
    assert targets["minItems"] == 1
    assert targets["uniqueItems"] is True
    assert targets["items"]["pattern"] == "^[a-z][a-z0-9_]*$"


def test_rationale_is_required_and_non_blank(schema):
    rationale = schema["properties"]["mappings"]["items"]["properties"]["rationale"]
    assert rationale["type"] == "string"
    assert rationale["minLength"] == 1
    assert rationale["pattern"] == "\\S"


def test_request_capability_is_not_a_local_enum(schema):
    """A22 sources must not be re-enumerated in this schema.

    The authoritative vocabulary lives on the request schema. Duplicating it
    here would let the two contracts drift — the validator reads the A22 enum
    at runtime instead.
    """
    source = schema["properties"]["mappings"]["items"]["properties"]["request_capability"]
    assert "enum" not in source
    assert source["type"] == "string"


def test_a22_schema_still_owns_the_request_enum(a22_enum):
    assert "simulation_request" in a22_enum
    assert "unknown_request_capability" not in a22_enum


def test_created_at_is_not_a_field(schema):
    assert "created_at" not in schema["properties"]
    assert "created_at" not in schema["required"]


# ---------------------------------------------------------------------------
# C — applied schema validation (optional)
# ---------------------------------------------------------------------------


def test_applied_valid_map_passes(schema):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator(schema).validate(_valid_map())


def test_applied_empty_mappings_pass(schema):
    jsonschema = pytest.importorskip("jsonschema")
    doc = _valid_map()
    doc["mappings"] = []
    jsonschema.Draft202012Validator(schema).validate(doc)


def test_applied_invalid_record_type_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_map()
    bad["record_type"] = "not_a_map"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_missing_versions_fail(schema):
    jsonschema = pytest.importorskip("jsonschema")
    for field in ("record_version", "map_version"):
        bad = _valid_map()
        del bad[field]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_missing_mappings_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_map()
    del bad["mappings"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_missing_authority_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_map()
    del bad["authority"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_empty_satisfied_by_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_map()
    bad["mappings"][0]["satisfied_by"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_blank_rationale_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_map()
    bad["mappings"][0]["rationale"] = "   "
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_missing_request_capability_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_map()
    del bad["mappings"][0]["request_capability"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_open_a23_target_not_in_example_profile_is_structurally_valid(schema):
    jsonschema = pytest.importorskip("jsonschema")
    ok = _valid_map()
    # Syntactically legal A23 identifier that the shipped example profile
    # does not declare. Openness is the point.
    ok["mappings"][0]["satisfied_by"] = ["future_studio_capability_xyz"]
    jsonschema.Draft202012Validator(schema).validate(ok)


def test_applied_invalid_target_syntax_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_map()
    bad["mappings"][0]["satisfied_by"] = ["Not-Legal"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_unknown_top_level_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_map()
    bad["approved"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_applied_authority_false_flag_fails(schema):
    jsonschema = pytest.importorskip("jsonschema")
    bad = _valid_map()
    bad["authority"]["does_not_grant_permission"] = False
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)
