"""
Phase 8 tests for CAM-A22 — product boundary (dev-order "Product Boundary" matrix).

Witnesses that the contract and its documentation keep the CAM Assist <->
CAM-Creation-Studio boundary explicit:

- documentation states the repositories remain separate
- documentation states the merger is not decided
- the request does not grant execution authority (schema + doc)
- the request does not claim CAM-Creation-Studio supports any capability (doc)
- the request does not require G-code generation (schema + doc)
- the Production Shop handoff remains a separate artifact (doc)

Documentation assertions are whitespace-normalized so line wrapping is irrelevant.
"""

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "creation_studio_request.schema.json"
INTEGRATION_DOC = REPO_ROOT / "docs" / "integration" / "CAM_CREATION_STUDIO_REQUEST.md"


def _norm(text: str) -> str:
    """Lowercase with runs of whitespace collapsed to single spaces."""
    return re.sub(r"\s+", " ", text).lower()


def _doc() -> str:
    return _norm(INTEGRATION_DOC.read_text(encoding="utf-8"))


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Documentation boundary statements
# ---------------------------------------------------------------------------

def test_doc_states_repositories_remain_separate():
    assert "remain separate" in _doc()


def test_doc_states_merger_not_decided():
    assert "not decided" in _doc()


def test_doc_states_no_execution_authority():
    assert "does not grant execution authority" in _doc()


def test_doc_states_no_consumer_support_claim():
    assert "does not guarantee that cam-creation-studio supports" in _doc()


def test_doc_states_no_gcode_requirement():
    assert "does not require g-code" in _doc()


def test_doc_states_production_shop_handoff_separate():
    doc = _doc()
    assert "production shop handoff" in doc
    assert "remains a **separate**" in doc or "remains a separate" in doc


# ---------------------------------------------------------------------------
# Schema-enforced authority invariants
# ---------------------------------------------------------------------------

def test_schema_forbids_execution_authority():
    auth = _schema()["properties"]["authority"]["properties"]
    assert auth["does_not_authorize_execution"]["const"] is True


def test_schema_forbids_gcode_requirement():
    auth = _schema()["properties"]["authority"]["properties"]
    assert auth["does_not_require_gcode_generation"]["const"] is True


def test_schema_direction_is_outbound_only():
    assert _schema()["properties"]["request_direction"]["const"] == "cam_assist_to_creation_studio"
