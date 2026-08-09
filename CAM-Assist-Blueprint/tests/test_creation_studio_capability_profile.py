"""
Validator tests for CAM-A23 Creation Studio Capability Profile.

Witnesses the structural layer (filesystem-free) and the opt-in existence
witness:

Positive:
- a valid capability profile passes
- optional capability fields (display_name, description, documentation_reference)
- an identifier the vocabulary has never seen passes (OPEN vocabulary)
- profile_version may differ from record_version

Negative:
- duplicate capability ids            - invalid record_type
- blank / malformed identifiers       - malformed versions
- invalid authority (false, missing, unknown flag)
- wrong publication_direction         - unknown top-level / capability fields
- absolute documentation references

Existence witness (--check-references):
- unresolved declared references warn but do not fail
- --fail-on-reference-warnings promotes them to errors
- structural validity is never affected either way
- the witness never opens a referenced file

The CLI is exercised as a subprocess, matching the other sidecar validators.

Every profile here is built in tmp_path: this file depends on the validator alone,
never on the committed example. Validating the committed example is the
example-regression suite's job
(test_creation_studio_capability_profile_example.py).
"""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate_creation_studio_capability_profile.py"


def run_validate(*args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(VALIDATE_SCRIPT)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def valid_profile() -> dict:
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


def write_profile(tmp_path: Path, data, name: str = "capability_profile.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------

def test_valid_profile_passes(tmp_path):
    path = write_profile(tmp_path, valid_profile())
    code, out, err = run_validate(path)
    assert code == 0, err
    assert "structurally valid" in out


def test_all_optional_capability_fields_pass(tmp_path):
    data = valid_profile()
    data["capabilities"] = [
        {
            "capability_id": "simulation_support",
            "display_name": "Simulation Support",
            "description": "Plays back a simulated tool motion for teaching purposes.",
            "documentation_reference": "docs/simulation.md",
        }
    ]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 0, err


def test_unknown_identifier_passes_open_vocabulary(tmp_path):
    # Creation Studio owns its capability evolution: a well-shaped identifier this
    # repository has never seen must validate without a schema change here.
    data = valid_profile()
    data["capabilities"] = [{"capability_id": "a_capability_invented_next_year"}]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 0, err


def test_profile_version_independent_of_record_version(tmp_path):
    data = valid_profile()
    data["profile_version"] = "7.3.1"
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 0, err


# ---------------------------------------------------------------------------
# Negative — record identity
# ---------------------------------------------------------------------------

def test_invalid_record_type_fails(tmp_path):
    data = valid_profile()
    data["record_type"] = "cam_assist_creation_studio_request"
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "record_type" in err


def test_missing_record_type_fails(tmp_path):
    data = valid_profile()
    del data["record_type"]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "record_type" in err


def test_wrong_publication_direction_fails(tmp_path):
    # An inbound-only contract must never be re-pointed outbound.
    data = valid_profile()
    data["publication_direction"] = "cam_assist_to_creation_studio"
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "publication_direction" in err


def test_missing_studio_reference_fails(tmp_path):
    data = valid_profile()
    del data["studio_reference"]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "studio_reference" in err


def test_blank_studio_reference_fails(tmp_path):
    data = valid_profile()
    data["studio_reference"] = "   "
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "studio_reference" in err


# ---------------------------------------------------------------------------
# Negative — versions
# ---------------------------------------------------------------------------

def test_malformed_record_version_fails(tmp_path):
    data = valid_profile()
    data["record_version"] = "1.0"
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "record_version" in err


def test_malformed_profile_version_fails(tmp_path):
    data = valid_profile()
    data["profile_version"] = "v1"
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "profile_version" in err


def test_non_string_profile_version_fails(tmp_path):
    data = valid_profile()
    data["profile_version"] = 1
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "profile_version" in err


def test_missing_profile_version_fails(tmp_path):
    data = valid_profile()
    del data["profile_version"]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "profile_version" in err


# ---------------------------------------------------------------------------
# Negative — capabilities
# ---------------------------------------------------------------------------

def test_duplicate_capability_ids_fail(tmp_path):
    # Uniqueness is the validator's job: vanilla JSON Schema cannot express
    # uniqueness by object property, so two entries sharing an id while differing
    # elsewhere slip past uniqueItems.
    data = valid_profile()
    data["capabilities"] = [
        {"capability_id": "simulation_support"},
        {"capability_id": "simulation_support", "display_name": "Simulation Support"},
    ]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "duplicate capability_id" in err
    assert "simulation_support" in err


def test_empty_capabilities_fail(tmp_path):
    data = valid_profile()
    data["capabilities"] = []
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "at least one capability" in err


def test_missing_capabilities_fails(tmp_path):
    data = valid_profile()
    del data["capabilities"]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "capabilities" in err


def test_capabilities_not_an_array_fails(tmp_path):
    data = valid_profile()
    data["capabilities"] = {"capability_id": "simulation_support"}
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "capabilities must be an array" in err


def test_capability_entry_not_an_object_fails(tmp_path):
    data = valid_profile()
    data["capabilities"] = ["simulation_support"]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "must be an object" in err


def test_blank_capability_identifier_fails(tmp_path):
    data = valid_profile()
    data["capabilities"] = [{"capability_id": "   "}]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "capability_id" in err


def test_missing_capability_identifier_fails(tmp_path):
    data = valid_profile()
    data["capabilities"] = [{"display_name": "Nameless"}]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "capability_id is required" in err


def test_malformed_capability_identifiers_fail(tmp_path):
    for bad_id in ("Strategy Visualization", "9_lives", "has-hyphen", "UPPER", "_leading"):
        data = valid_profile()
        data["capabilities"] = [{"capability_id": bad_id}]
        path = write_profile(tmp_path, data, name=f"{abs(hash(bad_id))}.json")
        code, _out, err = run_validate(path)
        assert code == 1, bad_id
        assert "capability_id" in err


def test_non_string_capability_identifier_fails(tmp_path):
    data = valid_profile()
    data["capabilities"] = [{"capability_id": 42}]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "capability_id" in err


def test_unknown_capability_field_fails(tmp_path):
    # A profile declares capability, never approval. An 'approved' flag riding
    # along on a capability entry is exactly the confusion the closed entry
    # contract exists to prevent.
    data = valid_profile()
    data["capabilities"] = [{"capability_id": "simulation_support", "approved": True}]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "unknown field" in err


def test_blank_display_name_fails(tmp_path):
    data = valid_profile()
    data["capabilities"] = [{"capability_id": "simulation_support", "display_name": "  "}]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "display_name" in err


def test_blank_description_fails(tmp_path):
    data = valid_profile()
    data["capabilities"] = [{"capability_id": "simulation_support", "description": ""}]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "description" in err


def test_absolute_documentation_reference_fails(tmp_path):
    for bad_ref in ("/etc/passwd", "C:/Windows/x.md", "\\\\server\\share\\x.md"):
        data = valid_profile()
        data["capabilities"] = [
            {"capability_id": "simulation_support", "documentation_reference": bad_ref}
        ]
        path = write_profile(tmp_path, data, name=f"abs_{abs(hash(bad_ref))}.json")
        code, _out, err = run_validate(path)
        assert code == 1, bad_ref
        assert "relative path" in err


def test_blank_documentation_reference_fails(tmp_path):
    data = valid_profile()
    data["capabilities"] = [
        {"capability_id": "simulation_support", "documentation_reference": "  "}
    ]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "documentation_reference" in err


# ---------------------------------------------------------------------------
# Negative — authority
# ---------------------------------------------------------------------------

def test_missing_authority_fails(tmp_path):
    data = valid_profile()
    del data["authority"]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "authority" in err


def test_false_authority_flag_fails(tmp_path):
    data = valid_profile()
    data["authority"]["does_not_authorize_execution"] = False
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "does_not_authorize_execution" in err


def test_missing_authority_flag_fails(tmp_path):
    data = valid_profile()
    del data["authority"]["does_not_require_capability_use"]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "does_not_require_capability_use" in err


def test_unknown_authority_flag_fails(tmp_path):
    # The non-authority declaration is closed so a contradictory flag cannot ride
    # along beside the five true ones.
    data = valid_profile()
    data["authority"]["authorizes_execution"] = True
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "unknown flag" in err


def test_authority_not_an_object_fails(tmp_path):
    data = valid_profile()
    data["authority"] = True
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "authority must be an object" in err


# ---------------------------------------------------------------------------
# Negative — closed top level and malformed documents
# ---------------------------------------------------------------------------

def test_unknown_top_level_field_fails(tmp_path):
    data = valid_profile()
    data["execution_authority"] = True
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "unknown top-level field" in err


def test_created_at_rejected_as_unknown_field(tmp_path):
    data = valid_profile()
    data["created_at"] = "2026-08-02T00:00:00Z"
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path)
    assert code == 1
    assert "created_at" in err


def test_non_object_root_fails(tmp_path):
    path = write_profile(tmp_path, ["not", "an", "object"])
    code, _out, err = run_validate(path)
    assert code == 1
    assert "must be a JSON object" in err


def test_parse_error_fails(tmp_path):
    path = tmp_path / "capability_profile.json"
    path.write_text("{not json", encoding="utf-8")
    code, _out, err = run_validate(path)
    assert code == 1
    assert "parse error" in err.lower()


def test_missing_file_returns_2(tmp_path):
    code, _out, err = run_validate(tmp_path / "nope.json")
    assert code == 2
    assert "not found" in err.lower()


# ---------------------------------------------------------------------------
# Existence witness (--check-references)
# ---------------------------------------------------------------------------

def test_structural_layer_ignores_unresolved_references(tmp_path):
    # The default layer is filesystem-free: a profile whose references do not
    # exist is still structurally valid.
    data = valid_profile()
    data["capabilities"] = [
        {"capability_id": "simulation_support", "documentation_reference": "docs/nope.md"}
    ]
    path = write_profile(tmp_path, data)
    code, out, err = run_validate(path)
    assert code == 0, err
    assert "does not resolve" not in out


def test_check_references_warns_but_passes(tmp_path):
    data = valid_profile()
    data["capabilities"] = [
        {"capability_id": "simulation_support", "documentation_reference": "docs/nope.md"}
    ]
    path = write_profile(tmp_path, data)
    code, out, _err = run_validate(path, "--check-references")
    assert code == 0
    assert "does not resolve" in out
    assert "simulation_support" in out


def test_check_references_clean_when_reference_exists(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "simulation.md").write_text("# Simulation\n", encoding="utf-8")
    data = valid_profile()
    data["capabilities"] = [
        {"capability_id": "simulation_support", "documentation_reference": "docs/simulation.md"}
    ]
    path = write_profile(tmp_path, data)
    code, out, _err = run_validate(path, "--check-references")
    assert code == 0
    assert "does not resolve" not in out


def test_check_references_silent_when_no_reference_declared(tmp_path):
    # An omitted documentation reference is allowed and silent — the witness
    # reports unresolved references, never absent ones.
    path = write_profile(tmp_path, valid_profile())
    code, out, _err = run_validate(path, "--check-references")
    assert code == 0
    assert "[WARN]" not in out


def test_fail_on_reference_warnings_promotes_to_error(tmp_path):
    data = valid_profile()
    data["capabilities"] = [
        {"capability_id": "simulation_support", "documentation_reference": "docs/nope.md"}
    ]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path, "--check-references", "--fail-on-reference-warnings")
    assert code == 1
    assert "does not resolve" in err


def test_fail_on_reference_warnings_is_inert_without_check_references(tmp_path):
    data = valid_profile()
    data["capabilities"] = [
        {"capability_id": "simulation_support", "documentation_reference": "docs/nope.md"}
    ]
    path = write_profile(tmp_path, data)
    code, _out, err = run_validate(path, "--fail-on-reference-warnings")
    assert code == 0, err


def test_witness_does_not_open_referenced_file(tmp_path):
    # Existence only: an unreadable/garbage referenced file must not affect the
    # result. The witness stats, it never parses.
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "broken.md").write_bytes(b"\x00\xff\xfe not text at all")
    data = valid_profile()
    data["capabilities"] = [
        {"capability_id": "simulation_support", "documentation_reference": "docs/broken.md"}
    ]
    path = write_profile(tmp_path, data)
    code, out, err = run_validate(path, "--check-references")
    assert code == 0, err
    assert "does not resolve" not in out


def test_check_references_does_not_mutate(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "simulation.md").write_text("# Simulation\n", encoding="utf-8")
    data = valid_profile()
    data["capabilities"] = [
        {"capability_id": "simulation_support", "documentation_reference": "docs/simulation.md"},
        {"capability_id": "strategy_visualization", "documentation_reference": "docs/nope.md"},
    ]
    path = write_profile(tmp_path, data)
    before = {p.relative_to(tmp_path).as_posix(): p.read_bytes()
              for p in tmp_path.rglob("*") if p.is_file()}
    run_validate(path)
    run_validate(path, "--check-references")
    after = {p.relative_to(tmp_path).as_posix(): p.read_bytes()
             for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_quiet_suppresses_success_output(tmp_path):
    path = write_profile(tmp_path, valid_profile())
    code, out, _err = run_validate(path, "--quiet")
    assert code == 0
    assert out.strip() == ""
