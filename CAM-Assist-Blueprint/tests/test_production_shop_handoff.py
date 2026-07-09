"""
Phase 2 tests for CAM-A20 Production Shop Handoff — structural validator.

Scope: structural validation only. The completeness-witness layer
(--check-references) is NOT implemented yet and is not tested here.

Runs the validator as a subprocess (mirroring the A19 bundle tests) and asserts
exit codes and message content:

    0 — valid
    1 — validation failed
    2 — file/read error

Structural rules witnessed:
- record_type const / record_version
- package_reference non-empty string
- handoff_direction == cam_assist_to_production_shop
- authority REQUIRED; four flags const-true
- contents required object; known slots only; non-empty string values
- empty contents allowed (warning)
"""

import json
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_production_shop_handoff.py"


def run_validator(*args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(VALIDATE_SCRIPT)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def write_handoff(tmp_path: Path, data, name: str = "handoff.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def valid_handoff() -> dict:
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
            "review_packet_file": "../packages/pkg/review_packet.md",
        },
    }


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_valid_handoff_passes(tmp_path):
    path = write_handoff(tmp_path, valid_handoff())
    code, out, err = run_validator(path)
    assert code == 0, err
    assert "PASS" in out


def test_valid_with_bundle_slot_passes(tmp_path):
    data = valid_handoff()
    data["contents"]["traceability_bundle_file"] = "../traceability/pkg_bundle.json"
    path = write_handoff(tmp_path, data)
    code, _out, err = run_validator(path)
    assert code == 0, err


def test_empty_contents_passes_with_warning(tmp_path):
    data = valid_handoff()
    data["contents"] = {}
    path = write_handoff(tmp_path, data)
    code, out, _err = run_validator(path)
    assert code == 0
    assert "contents is empty" in out


# ---------------------------------------------------------------------------
# record_type / record_version
# ---------------------------------------------------------------------------

def test_missing_record_type_fails(tmp_path):
    data = valid_handoff()
    del data["record_type"]
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "record_type" in err


def test_invalid_record_type_fails(tmp_path):
    data = valid_handoff()
    data["record_type"] = "cam_assist_not_a_handoff"
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "record_type" in err


def test_bad_record_version_fails(tmp_path):
    data = valid_handoff()
    data["record_version"] = "1.0"
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "record_version" in err


# ---------------------------------------------------------------------------
# package_reference
# ---------------------------------------------------------------------------

def test_missing_package_reference_fails(tmp_path):
    data = valid_handoff()
    del data["package_reference"]
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "package_reference" in err


def test_empty_package_reference_fails(tmp_path):
    data = valid_handoff()
    data["package_reference"] = "  "
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "package_reference" in err


# ---------------------------------------------------------------------------
# handoff_direction
# ---------------------------------------------------------------------------

def test_missing_direction_fails(tmp_path):
    data = valid_handoff()
    del data["handoff_direction"]
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "handoff_direction" in err


def test_wrong_direction_fails(tmp_path):
    data = valid_handoff()
    data["handoff_direction"] = "production_shop_to_cam_assist"
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "handoff_direction" in err


# ---------------------------------------------------------------------------
# authority (REQUIRED, four flags)
# ---------------------------------------------------------------------------

def test_missing_authority_fails(tmp_path):
    data = valid_handoff()
    del data["authority"]
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "authority" in err


def test_authority_flag_false_fails(tmp_path):
    data = valid_handoff()
    data["authority"]["does_not_authorize_execution"] = False
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "does_not_authorize_execution" in err


def test_authority_missing_fourth_flag_fails(tmp_path):
    data = valid_handoff()
    del data["authority"]["does_not_confirm_machine_readiness"]
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "does_not_confirm_machine_readiness" in err


def test_unknown_authority_flag_fails(tmp_path):
    # A contradictory/undeclared flag must not ride along on the non-execution block.
    data = valid_handoff()
    data["authority"]["authorizes_execution"] = True
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "unknown flag" in err


# ---------------------------------------------------------------------------
# Closed top-level contract
# ---------------------------------------------------------------------------

def test_unknown_top_level_field_fails(tmp_path):
    data = valid_handoff()
    data["surprise"] = "x"
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "unknown top-level field" in err


def test_created_at_accepted_at_top_level(tmp_path):
    # created_at is the one optional top-level field; it must still pass.
    data = valid_handoff()
    data["created_at"] = "2026-07-09T00:00:00Z"
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 0, err


# ---------------------------------------------------------------------------
# contents
# ---------------------------------------------------------------------------

def test_missing_contents_fails(tmp_path):
    data = valid_handoff()
    del data["contents"]
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "contents" in err


def test_non_object_contents_fails(tmp_path):
    data = valid_handoff()
    data["contents"] = "not-an-object"
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "contents must be an object" in err


def test_unknown_content_slot_fails(tmp_path):
    data = valid_handoff()
    data["contents"]["unknown_file"] = "x.json"
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "unknown content slot" in err


def test_content_slot_non_string_fails(tmp_path):
    data = valid_handoff()
    data["contents"]["strategy_file"] = 123
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "strategy_file" in err


def test_content_slot_empty_string_fails(tmp_path):
    data = valid_handoff()
    data["contents"]["strategy_file"] = "  "
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 1
    assert "strategy_file" in err


# ---------------------------------------------------------------------------
# File / read errors
# ---------------------------------------------------------------------------

def test_missing_file_returns_2(tmp_path):
    code, _out, err = run_validator(tmp_path / "nope.json")
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
    data = valid_handoff()
    data["contents"] = {"strategy_file": "definitely/missing/strategy.json"}
    code, _out, err = run_validator(write_handoff(tmp_path, data))
    assert code == 0, err
