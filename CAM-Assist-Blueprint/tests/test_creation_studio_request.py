"""
Phase 3 tests for CAM-A22 Creation Studio Capability Request — structural validator.

Scope: structural validation only. The completeness-witness layer
(--check-references) is exercised in test_creation_studio_request_completeness.py.

Runs the validator as a subprocess (mirroring the A19/A20 tests) and asserts exit
codes and message content:

    0 — valid
    1 — validation failed
    2 — file/read error

Structural rules witnessed:
- record_type const / record_version
- package_reference non-empty string
- request_direction == cam_assist_to_creation_studio
- requested_capabilities: non-empty, unique, known-vocabulary array
- authority REQUIRED; five flags const-true; closed
- contents required object; five known slots only; non-empty string values
- request_context optional; known fields with correct types
- empty contents allowed (warning)
- created_at is NOT a recognized field (rejected by the closed top level)
"""

import json
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_creation_studio_request.py"


def run_validator(*args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(VALIDATE_SCRIPT)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def write_request(tmp_path: Path, data, name: str = "request.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def valid_request() -> dict:
    return {
        "record_type": "cam_assist_creation_studio_request",
        "record_version": "1.0.0",
        "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
        "request_direction": "cam_assist_to_creation_studio",
        "requested_capabilities": [
            "feeds_speeds_recommendation",
            "tooling_review",
        ],
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
            "does_not_confirm_machine_readiness": True,
            "does_not_require_gcode_generation": True,
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

def test_valid_request_passes(tmp_path):
    code, out, err = run_validator(write_request(tmp_path, valid_request()))
    assert code == 0, err
    assert "PASS" in out


def test_valid_with_all_five_slots_passes(tmp_path):
    data = valid_request()
    data["contents"]["traceability_bundle_file"] = "../traceability/pkg_bundle.json"
    data["contents"]["production_shop_handoff_file"] = "../production_shop/pkg_handoff.json"
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 0, err


def test_empty_contents_passes_with_warning(tmp_path):
    data = valid_request()
    data["contents"] = {}
    code, out, _err = run_validator(write_request(tmp_path, data))
    assert code == 0
    assert "contents is empty" in out


def test_request_context_passes(tmp_path):
    data = valid_request()
    data["request_context"] = {
        "material": "mahogany",
        "machine_profile": None,
        "operator_notes": "Review before downstream toolpath development.",
    }
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 0, err


# ---------------------------------------------------------------------------
# record_type / record_version
# ---------------------------------------------------------------------------

def test_missing_record_type_fails(tmp_path):
    data = valid_request()
    del data["record_type"]
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "record_type" in err


def test_invalid_record_type_fails(tmp_path):
    data = valid_request()
    data["record_type"] = "cam_assist_not_a_request"
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "record_type" in err


def test_bad_record_version_fails(tmp_path):
    data = valid_request()
    data["record_version"] = "1.0"
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "record_version" in err


# ---------------------------------------------------------------------------
# package_reference
# ---------------------------------------------------------------------------

def test_missing_package_reference_fails(tmp_path):
    data = valid_request()
    del data["package_reference"]
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "package_reference" in err


def test_blank_package_reference_fails(tmp_path):
    data = valid_request()
    data["package_reference"] = "  "
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "package_reference" in err


# ---------------------------------------------------------------------------
# request_direction
# ---------------------------------------------------------------------------

def test_missing_direction_fails(tmp_path):
    data = valid_request()
    del data["request_direction"]
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "request_direction" in err


def test_wrong_direction_fails(tmp_path):
    data = valid_request()
    data["request_direction"] = "creation_studio_to_cam_assist"
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "request_direction" in err


# ---------------------------------------------------------------------------
# requested_capabilities
# ---------------------------------------------------------------------------

def test_missing_capabilities_fails(tmp_path):
    data = valid_request()
    del data["requested_capabilities"]
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "requested_capabilities" in err


def test_empty_capabilities_fails(tmp_path):
    data = valid_request()
    data["requested_capabilities"] = []
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "at least one capability" in err


def test_duplicate_capabilities_fails(tmp_path):
    data = valid_request()
    data["requested_capabilities"] = ["tooling_review", "tooling_review"]
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "duplicate capability" in err


def test_unknown_capability_fails(tmp_path):
    data = valid_request()
    data["requested_capabilities"] = ["make_me_a_sandwich"]
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "unknown capability" in err


def test_non_array_capabilities_fails(tmp_path):
    data = valid_request()
    data["requested_capabilities"] = "tooling_review"
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "requested_capabilities must be an array" in err


# ---------------------------------------------------------------------------
# authority (REQUIRED, five flags)
# ---------------------------------------------------------------------------

def test_missing_authority_fails(tmp_path):
    data = valid_request()
    del data["authority"]
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "authority" in err


def test_authority_flag_false_fails(tmp_path):
    data = valid_request()
    data["authority"]["does_not_require_gcode_generation"] = False
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "does_not_require_gcode_generation" in err


def test_authority_missing_fifth_flag_fails(tmp_path):
    data = valid_request()
    del data["authority"]["does_not_require_gcode_generation"]
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "does_not_require_gcode_generation" in err


def test_unknown_authority_flag_fails(tmp_path):
    data = valid_request()
    data["authority"]["authorizes_execution"] = True
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "unknown flag" in err


# ---------------------------------------------------------------------------
# request_context types
# ---------------------------------------------------------------------------

def test_request_context_unknown_field_fails(tmp_path):
    data = valid_request()
    data["request_context"] = {"surprise": "x"}
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "request_context" in err


def test_request_context_wrong_type_fails(tmp_path):
    data = valid_request()
    data["request_context"] = {"material": 42}
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "request_context.material must be a string" in err


def test_request_context_machine_profile_null_ok(tmp_path):
    data = valid_request()
    data["request_context"] = {"machine_profile": None}
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 0, err


# ---------------------------------------------------------------------------
# Closed top-level contract; no created_at
# ---------------------------------------------------------------------------

def test_unknown_top_level_field_fails(tmp_path):
    data = valid_request()
    data["surprise"] = "x"
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "unknown top-level field" in err


def test_created_at_is_rejected(tmp_path):
    # created_at is not part of this contract; the closed top level rejects it.
    data = valid_request()
    data["created_at"] = "2026-07-11T00:00:00Z"
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "created_at" in err


# ---------------------------------------------------------------------------
# contents
# ---------------------------------------------------------------------------

def test_missing_contents_fails(tmp_path):
    data = valid_request()
    del data["contents"]
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "contents" in err


def test_non_object_contents_fails(tmp_path):
    data = valid_request()
    data["contents"] = "not-an-object"
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "contents must be an object" in err


def test_unknown_content_slot_fails(tmp_path):
    data = valid_request()
    data["contents"]["unknown_file"] = "x.json"
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 1
    assert "unknown content slot" in err


def test_content_slot_empty_string_fails(tmp_path):
    data = valid_request()
    data["contents"]["strategy_file"] = "  "
    code, _out, err = run_validator(write_request(tmp_path, data))
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
    data = valid_request()
    data["contents"] = {"strategy_file": "definitely/missing/strategy.json"}
    code, _out, err = run_validator(write_request(tmp_path, data))
    assert code == 0, err


# ---------------------------------------------------------------------------
# Committed example
# ---------------------------------------------------------------------------

def test_committed_example_is_valid():
    repo = Path(__file__).parent.parent
    example = repo / "examples" / "creation_studio" / "ltb_vcarve_synthetic_example_request.json"
    code, out, err = run_validator(example)
    assert code == 0, err + out
