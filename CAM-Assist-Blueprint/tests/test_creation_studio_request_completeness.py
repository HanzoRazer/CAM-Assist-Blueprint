"""
Phase 6 tests for CAM-A22 Creation Studio Capability Request — completeness witness.

Witnesses the opt-in --check-references EXISTENCE layer of
scripts/validate_creation_studio_request.py:

- a valid request whose declared references all exist -> PASS, no warnings
- a declared reference that does not resolve -> WARNING only, validity and exit
  code unchanged
- a structurally invalid request + --check-references -> FAIL (structure dominates)
- a referenced file that exists but is garbage -> PASS (existence only, never parsed)
- references resolve relative to the request file's directory, independent of cwd
- default mode (no flag) remains filesystem-free: missing refs do not warn
- --fail-on-reference-warnings promotes unresolved refs to errors (exit 1)
- the witness mutates nothing

The witness is existence-only: it never parses referenced content, never
cross-checks package_reference, and emits no absent-slot/omission findings.
"""

import json
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_creation_studio_request.py"

ALL_REFS = {
    "package_manifest_file": "../packages/pkg/manifest.json",
    "strategy_file": "../packages/pkg/strategy.json",
    "review_packet_file": "../packages/pkg/review_packet.md",
    "traceability_bundle_file": "../traceability/pkg_bundle.json",
    "production_shop_handoff_file": "../production_shop/pkg_handoff.json",
}


def run_validator(*args, cwd: Path | None = None) -> tuple[int, str, str]:
    cmd = [sys.executable, str(VALIDATE_SCRIPT)] + [str(a) for a in args]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(cwd) if cwd else None
    )
    return result.returncode, result.stdout, result.stderr


def valid_request(contents: dict) -> dict:
    return {
        "record_type": "cam_assist_creation_studio_request",
        "record_version": "1.0.0",
        "package_reference": "luthiers-toolbox:vcarve:example",
        "request_direction": "cam_assist_to_creation_studio",
        "requested_capabilities": ["tooling_review"],
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
            "does_not_confirm_machine_readiness": True,
            "does_not_require_gcode_generation": True,
        },
        "contents": contents,
    }


def scaffold(root: Path, present: set[str], contents: dict | None = None) -> Path:
    """Lay out a request at root/creation_studio/r.json with sibling referenced
    files, creating only those in `present`. Returns the request path.

    File content for the referenced files is intentionally garbage-ish — the
    witness must care only about existence, never content.
    """
    request_dir = root / "creation_studio"
    request_dir.mkdir(parents=True, exist_ok=True)
    pkg = root / "packages" / "pkg"
    trace = root / "traceability"
    prod = root / "production_shop"
    for d in (pkg, trace, prod):
        d.mkdir(parents=True, exist_ok=True)

    targets = {
        "package_manifest_file": pkg / "manifest.json",
        "strategy_file": pkg / "strategy.json",
        "review_packet_file": pkg / "review_packet.md",
        "traceability_bundle_file": trace / "pkg_bundle.json",
        "production_shop_handoff_file": prod / "pkg_handoff.json",
    }
    for slot, target in targets.items():
        if slot in present:
            target.write_text("{}", encoding="utf-8")

    request_path = request_dir / "r.json"
    request_path.write_text(
        json.dumps(valid_request(contents if contents is not None else dict(ALL_REFS))),
        encoding="utf-8",
    )
    return request_path


def snapshot(d: Path) -> dict:
    return {
        p.relative_to(d).as_posix(): p.read_bytes()
        for p in d.rglob("*")
        if p.is_file()
    }


# ---------------------------------------------------------------------------
# All references present
# ---------------------------------------------------------------------------

def test_all_refs_present_passes_no_warnings(tmp_path):
    request = scaffold(tmp_path, present=set(ALL_REFS.keys()))
    code, out, _err = run_validator(request, "--check-references")
    assert code == 0
    assert "PASS" in out
    assert "[WARN]" not in out


def test_committed_example_check_references_clean():
    repo = Path(__file__).parent.parent
    example = repo / "examples" / "creation_studio" / "ltb_vcarve_synthetic_example_request.json"
    code, out, _err = run_validator(example, "--check-references")
    assert code == 0
    assert "[WARN]" not in out


# ---------------------------------------------------------------------------
# Missing references -> warning only, exit code unchanged
# ---------------------------------------------------------------------------

def test_missing_handoff_warns_only(tmp_path):
    request = scaffold(tmp_path, present=set(ALL_REFS) - {"production_shop_handoff_file"})
    code, out, _err = run_validator(request, "--check-references")
    assert code == 0
    assert "PASS" in out
    assert "production_shop_handoff_file reference does not resolve" in out


def test_missing_bundle_warns_only(tmp_path):
    request = scaffold(tmp_path, present=set(ALL_REFS) - {"traceability_bundle_file"})
    code, out, _err = run_validator(request, "--check-references")
    assert code == 0
    assert "traceability_bundle_file reference does not resolve" in out


def test_all_five_refs_missing_warn_none_fatal(tmp_path):
    request = scaffold(tmp_path, present=set())
    code, out, _err = run_validator(request, "--check-references")
    assert code == 0
    assert out.count("[WARN]") == 5


# ---------------------------------------------------------------------------
# Structure dominates; existence-only; omissions silent
# ---------------------------------------------------------------------------

def test_structural_invalidity_dominates(tmp_path):
    request_dir = tmp_path / "creation_studio"
    request_dir.mkdir(parents=True)
    bad = valid_request(dict(ALL_REFS))
    bad["record_type"] = "not_a_request"
    request = request_dir / "r.json"
    request.write_text(json.dumps(bad), encoding="utf-8")
    code, _out, err = run_validator(request, "--check-references")
    assert code == 1
    assert "FAIL" in err


def test_existing_garbage_file_passes_existence_only(tmp_path):
    request = scaffold(tmp_path, present=set(ALL_REFS.keys()))
    (tmp_path / "packages" / "pkg" / "manifest.json").write_text(
        "this is not json at all !!!", encoding="utf-8"
    )
    code, out, _err = run_validator(request, "--check-references")
    assert code == 0
    assert "[WARN]" not in out


def test_omitted_slot_is_silent(tmp_path):
    contents = {k: v for k, v in ALL_REFS.items() if k != "production_shop_handoff_file"}
    request = scaffold(tmp_path, present=set(contents.keys()), contents=contents)
    code, out, _err = run_validator(request, "--check-references")
    assert code == 0
    assert "[WARN]" not in out


# ---------------------------------------------------------------------------
# Resolution relative to request dir; default mode fs-free
# ---------------------------------------------------------------------------

def test_resolution_relative_to_request_dir_independent_of_cwd(tmp_path):
    request = scaffold(tmp_path, present=set(ALL_REFS.keys()))
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    code, out, _err = run_validator(request, "--check-references", cwd=other_cwd)
    assert code == 0
    assert "[WARN]" not in out


def test_default_mode_is_filesystem_free(tmp_path):
    request = scaffold(tmp_path, present=set())
    code, out, _err = run_validator(request)
    assert code == 0
    assert "does not resolve" not in out


# ---------------------------------------------------------------------------
# Strict enforcement: --fail-on-reference-warnings (opt-in, additive)
# ---------------------------------------------------------------------------

def test_strict_mode_fails_on_missing_refs(tmp_path):
    request = scaffold(tmp_path, present=set())
    code, _out, err = run_validator(
        request, "--check-references", "--fail-on-reference-warnings"
    )
    assert code == 1
    assert "FAIL" in err
    assert "reference does not resolve" in err


def test_strict_mode_passes_when_refs_resolve(tmp_path):
    request = scaffold(tmp_path, present=set(ALL_REFS.keys()))
    code, out, _err = run_validator(
        request, "--check-references", "--fail-on-reference-warnings"
    )
    assert code == 0
    assert "PASS" in out


def test_strict_flag_is_noop_without_check_references(tmp_path):
    request = scaffold(tmp_path, present=set())
    code, out, _err = run_validator(request, "--fail-on-reference-warnings")
    assert code == 0
    assert "does not resolve" not in out


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------

def test_witness_mutates_nothing(tmp_path):
    request = scaffold(tmp_path, present={"strategy_file"})
    before = snapshot(tmp_path)
    run_validator(request, "--check-references")
    assert snapshot(tmp_path) == before
