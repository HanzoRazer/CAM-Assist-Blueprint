"""
Phase 2 tests for CAM-A19 Traceability Bundle — structural validator.

Scope: structural validation only. The completeness-witness layer
(--check-references) is covered separately in
test_traceability_bundle_completeness.py.

These tests run the validator as a subprocess (mirroring test_revision_lineage.py)
and assert exit codes and message content:

    0 — valid
    1 — validation failed
    2 — file/read error

Structural rules witnessed:
- record_type / record_version
- package_reference non-empty string
- bundle_contents present and object-shaped
- known slot names only
- slot values are non-empty strings when present
- empty bundle_contents allowed (warning)
- authority const-true when present
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_traceability_bundle.py"


def run_validator(*args) -> tuple[int, str, str]:
    """Run the validator and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, str(VALIDATE_SCRIPT)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def write_bundle(tmp_path: Path, data, name: str = "bundle.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def valid_bundle() -> dict:
    return {
        "record_type": "cam_assist_traceability_bundle",
        "record_version": "1.0.0",
        "package_reference": "luthiers-toolbox:vcarve:example-001",
        "bundle_contents": {
            "assumptions_file": "pkg_assumptions.json",
            "risk_file": "pkg_risk.json",
        },
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
        },
    }


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_valid_bundle_passes(tmp_path):
    path = write_bundle(tmp_path, valid_bundle())
    code, out, err = run_validator(path)
    assert code == 0, err
    assert "PASS" in out


def test_valid_single_slot_passes(tmp_path):
    data = valid_bundle()
    data["bundle_contents"] = {"lineage_file": "pkg_lineage.json"}
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 0, err


def test_valid_without_authority_passes(tmp_path):
    data = valid_bundle()
    del data["authority"]
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 0, err


def test_empty_bundle_contents_passes_with_warning(tmp_path):
    data = valid_bundle()
    data["bundle_contents"] = {}
    path = write_bundle(tmp_path, data)
    code, out, _err = run_validator(path)
    assert code == 0
    assert "bundle_contents is empty" in out


# ---------------------------------------------------------------------------
# record_type / record_version
# ---------------------------------------------------------------------------

def test_missing_record_type_fails(tmp_path):
    data = valid_bundle()
    del data["record_type"]
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "record_type" in err


def test_invalid_record_type_fails(tmp_path):
    data = valid_bundle()
    data["record_type"] = "cam_assist_not_a_bundle"
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "record_type" in err


def test_missing_record_version_fails(tmp_path):
    data = valid_bundle()
    del data["record_version"]
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "record_version" in err


def test_bad_record_version_fails(tmp_path):
    data = valid_bundle()
    data["record_version"] = "1.0"
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "record_version" in err


# ---------------------------------------------------------------------------
# package_reference
# ---------------------------------------------------------------------------

def test_missing_package_reference_fails(tmp_path):
    data = valid_bundle()
    del data["package_reference"]
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "package_reference" in err


def test_empty_package_reference_fails(tmp_path):
    data = valid_bundle()
    data["package_reference"] = "  "
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "package_reference" in err


# ---------------------------------------------------------------------------
# bundle_contents
# ---------------------------------------------------------------------------

def test_missing_bundle_contents_fails(tmp_path):
    data = valid_bundle()
    del data["bundle_contents"]
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "bundle_contents" in err


def test_non_object_bundle_contents_fails(tmp_path):
    data = valid_bundle()
    data["bundle_contents"] = "not-an-object"
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "bundle_contents must be an object" in err


def test_unknown_slot_fails(tmp_path):
    data = valid_bundle()
    data["bundle_contents"]["unknown_file"] = "x.json"
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "unknown reference slot" in err


def test_slot_value_non_string_fails(tmp_path):
    data = valid_bundle()
    data["bundle_contents"]["risk_file"] = 123
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "risk_file" in err


def test_slot_value_empty_string_fails(tmp_path):
    data = valid_bundle()
    data["bundle_contents"]["risk_file"] = "  "
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "risk_file" in err


# ---------------------------------------------------------------------------
# authority
# ---------------------------------------------------------------------------

def test_authority_flag_false_fails(tmp_path):
    data = valid_bundle()
    data["authority"]["does_not_authorize_execution"] = False
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "does_not_authorize_execution" in err


def test_authority_flag_missing_fails(tmp_path):
    data = valid_bundle()
    del data["authority"]["is_informational"]
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 1
    assert "is_informational" in err


# ---------------------------------------------------------------------------
# File / read errors
# ---------------------------------------------------------------------------

def test_missing_file_returns_2(tmp_path):
    code, _out, err = run_validator(tmp_path / "does_not_exist.json")
    assert code == 2
    assert "not found" in err.lower()


def test_invalid_json_returns_1(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ not valid json", encoding="utf-8")
    code, _out, err = run_validator(path)
    assert code == 1
    assert "parse error" in err.lower()


def test_non_object_root_returns_1(tmp_path):
    path = tmp_path / "arr.json"
    path.write_text("[]", encoding="utf-8")
    code, _out, err = run_validator(path)
    assert code == 1
    assert "object" in err.lower()


# ---------------------------------------------------------------------------
# Structural layer is filesystem-free: references need not exist
# ---------------------------------------------------------------------------

def test_structural_pass_with_nonexistent_references(tmp_path):
    """Declared references that do not exist on disk are fine structurally;
    existence is a completeness concern, surfaced only under --check-references."""
    data = valid_bundle()
    data["bundle_contents"] = {"assumptions_file": "definitely/missing/file.json"}
    path = write_bundle(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 0, err
