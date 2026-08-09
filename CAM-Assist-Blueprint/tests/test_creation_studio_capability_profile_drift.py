"""
Drift guard for CAM-A23 Creation Studio Capability Profile.

The contract is encoded in three places by design (JSON Schema, structural
validator, creator). The same maintenance risk CAM-A22 flagged applies here:
these can drift apart — an authority flag renamed in the schema but not the
validator, a capability field added to one layer only, an identifier pattern
loosened in one place. These tests pin the schema as the reference and assert the
Python constants agree with it, so a one-sided edit fails loudly.

This lives in its own file rather than beside the schema-document tests because
it imports the validator and creator: the schema test file must stay dependent on
nothing but the schema document.
"""

import importlib.util
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "creation_studio_capability_profile.schema.json"
SCRIPTS_DIR = REPO_ROOT / "scripts"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_creation_studio_capability_profile.py"
CREATE_SCRIPT = SCRIPTS_DIR / "create_creation_studio_capability_profile.py"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _validator():
    return _load_module("_validate_cscp_drift", VALIDATE_SCRIPT)


def _creator():
    return _load_module("_create_cscp_drift", CREATE_SCRIPT)


# ---------------------------------------------------------------------------
# Authority flags: schema required == validator flags == creator emitted keys
# ---------------------------------------------------------------------------

def test_authority_flags_match_across_layers():
    schema_flags = _schema()["properties"]["authority"]["required"]
    validator = _validator()
    creator = _creator()
    assert schema_flags == validator.AUTHORITY_FLAGS
    assert set(schema_flags) == set(creator.AUTHORITY.keys())
    # The creator emits every flag as literal True.
    assert all(creator.AUTHORITY[f] is True for f in schema_flags)


# ---------------------------------------------------------------------------
# Capability entry fields and top-level key set: schema == validator constants
# ---------------------------------------------------------------------------

def test_capability_fields_match_schema():
    schema_fields = list(
        _schema()["properties"]["capabilities"]["items"]["properties"].keys()
    )
    assert schema_fields == _validator().CAPABILITY_FIELDS


def test_top_level_keys_match_schema():
    schema = _schema()
    schema_top = set(schema["properties"].keys())
    assert schema_top == set(_validator().KNOWN_TOP_LEVEL)
    # Every top-level key is required; the profile has no optional top-level field.
    assert set(schema["required"]) == schema_top


# ---------------------------------------------------------------------------
# Identifier pattern and record/direction consts agree
# ---------------------------------------------------------------------------

def test_capability_id_pattern_matches_across_layers():
    pattern = _schema()["properties"]["capabilities"]["items"]["properties"][
        "capability_id"
    ]["pattern"]
    assert _validator().CAPABILITY_ID_PATTERN.pattern == pattern
    assert _creator().CAPABILITY_ID_PATTERN.pattern == pattern


def test_record_and_direction_consts_match():
    schema = _schema()
    validator = _validator()
    creator = _creator()
    rt = schema["properties"]["record_type"]["const"]
    pd = schema["properties"]["publication_direction"]["const"]
    assert rt == validator.RECORD_TYPE == creator.RECORD_TYPE
    assert pd == validator.PUBLICATION_DIRECTION == creator.PUBLICATION_DIRECTION


def test_semantic_version_pattern_matches_across_layers():
    schema = _schema()
    validator = _validator()
    creator = _creator()
    pattern = schema["properties"]["record_version"]["pattern"]
    assert schema["properties"]["profile_version"]["pattern"] == pattern
    assert validator.VERSION_PATTERN.pattern == pattern
    assert creator.VERSION_PATTERN.pattern == pattern


def test_creator_record_version_satisfies_schema():
    schema = _schema()
    creator = _creator()
    assert re.fullmatch(schema["properties"]["record_version"]["pattern"], creator.RECORD_VERSION)
