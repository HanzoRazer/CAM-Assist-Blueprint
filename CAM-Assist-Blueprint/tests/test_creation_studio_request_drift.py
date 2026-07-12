"""
Drift guard for CAM-A22 Creation Studio Capability Request.

The contract is encoded in three places by design (JSON Schema, structural
validator, creator). Reviews flagged the maintenance risk that these can drift
apart — a capability added to one but not the others, a slot renamed in the
schema but not the validator, etc. These tests pin the schema as the reference
and assert the Python constants agree with it, so a one-sided edit fails loudly.
"""

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "creation_studio_request.schema.json"
SCRIPTS_DIR = REPO_ROOT / "scripts"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_creation_studio_request.py"
CREATE_SCRIPT = SCRIPTS_DIR / "create_creation_studio_request.py"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _validator():
    return _load_module("_validate_csr_drift", VALIDATE_SCRIPT)


def _creator():
    return _load_module("_create_csr_drift", CREATE_SCRIPT)


# ---------------------------------------------------------------------------
# Capability vocabulary: schema == validator == creator
# ---------------------------------------------------------------------------

def test_capability_vocabulary_matches_across_layers():
    schema_caps = _schema()["properties"]["requested_capabilities"]["items"]["enum"]
    assert schema_caps == _validator().CAPABILITY_VOCABULARY
    assert schema_caps == _creator().CAPABILITY_VOCABULARY


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
# Content slots and context fields: schema properties == validator constants
# ---------------------------------------------------------------------------

def test_content_slots_match_schema():
    schema_slots = list(_schema()["properties"]["contents"]["properties"].keys())
    assert schema_slots == _validator().CONTENT_SLOTS


def test_context_fields_match_schema():
    schema_fields = list(_schema()["properties"]["request_context"]["properties"].keys())
    assert schema_fields == _validator().CONTEXT_FIELDS


# ---------------------------------------------------------------------------
# Top-level key set: schema (required + request_context) == validator known set
# ---------------------------------------------------------------------------

def test_top_level_keys_match_schema():
    schema = _schema()
    schema_top = set(schema["properties"].keys())
    assert schema_top == set(_validator().KNOWN_TOP_LEVEL)
    # required is a subset of the known keys; request_context is the sole optional.
    assert set(schema["required"]) == schema_top - {"request_context"}


# ---------------------------------------------------------------------------
# record_type / record_version / direction consts agree
# ---------------------------------------------------------------------------

def test_record_and_direction_consts_match():
    schema = _schema()
    validator = _validator()
    creator = _creator()
    rt = schema["properties"]["record_type"]["const"]
    rd = schema["properties"]["request_direction"]["const"]
    assert rt == validator.RECORD_TYPE == creator.RECORD_TYPE
    assert rd == validator.REQUEST_DIRECTION == creator.REQUEST_DIRECTION
