"""
Phase 5 tests for CAM-A20 Production Shop Handoff — completeness witness.

Witnesses the opt-in --check-references EXISTENCE layer of
scripts/validate_production_shop_handoff.py:

- a valid handoff whose declared references all exist -> PASS, no warnings
- a declared reference that does not resolve -> WARNING only (manifest/strategy/
  review packet/bundle each), validity and exit code unchanged
- a structurally invalid handoff + --check-references -> FAIL (structure dominates)
- a referenced file that exists but is garbage -> PASS (existence only, never parsed)
- references resolve relative to the handoff file's directory, independent of cwd
- the witness mutates nothing
- default mode (no flag) remains filesystem-free: missing refs do not warn

The witness is existence-only: it never parses referenced content, never
cross-checks package_reference, and emits no absent-slot/omission findings.
"""

import json
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_production_shop_handoff.py"

ALL_REFS = {
    "package_manifest_file": "../packages/pkg/manifest.json",
    "strategy_file": "../packages/pkg/strategy.json",
    "review_packet_file": "../packages/pkg/review_packet.md",
    "traceability_bundle_file": "../traceability/pkg_bundle.json",
}


def run_validator(*args, cwd: Path | None = None) -> tuple[int, str, str]:
    cmd = [sys.executable, str(VALIDATE_SCRIPT)] + [str(a) for a in args]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(cwd) if cwd else None
    )
    return result.returncode, result.stdout, result.stderr


def valid_handoff(contents: dict) -> dict:
    return {
        "record_type": "cam_assist_production_shop_handoff",
        "record_version": "1.0.0",
        "package_reference": "luthiers-toolbox:vcarve:example",
        "handoff_direction": "cam_assist_to_production_shop",
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
            "does_not_confirm_machine_readiness": True,
        },
        "contents": contents,
    }


def scaffold(root: Path, present: set[str], contents: dict | None = None) -> Path:
    """Lay out a handoff at root/production_shop/h.json with sibling referenced
    files, creating only those in `present`. Returns the handoff path.

    File content for the referenced files is intentionally garbage-ish ("{}" /
    plain text) — the witness must care only about existence, never content.
    """
    handoff_dir = root / "production_shop"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    pkg = root / "packages" / "pkg"
    trace = root / "traceability"
    pkg.mkdir(parents=True, exist_ok=True)
    trace.mkdir(parents=True, exist_ok=True)

    targets = {
        "package_manifest_file": pkg / "manifest.json",
        "strategy_file": pkg / "strategy.json",
        "review_packet_file": pkg / "review_packet.md",
        "traceability_bundle_file": trace / "pkg_bundle.json",
    }
    for slot, target in targets.items():
        if slot in present:
            target.write_text("{}", encoding="utf-8")

    handoff_path = handoff_dir / "h.json"
    handoff_path.write_text(
        json.dumps(valid_handoff(contents if contents is not None else dict(ALL_REFS))),
        encoding="utf-8",
    )
    return handoff_path


def snapshot(d: Path) -> dict:
    return {
        p.relative_to(d).as_posix(): p.read_bytes()
        for p in d.rglob("*")
        if p.is_file()
    }


# ---------------------------------------------------------------------------
# All references present
# ---------------------------------------------------------------------------

def test_valid_example_all_refs_present_passes_no_warnings(tmp_path):
    handoff = scaffold(tmp_path, present=set(ALL_REFS.keys()))
    code, out, _err = run_validator(handoff, "--check-references")
    assert code == 0
    assert "PASS" in out
    assert "[WARN]" not in out


def test_committed_example_check_references_clean(tmp_path):
    # The real committed example: all four refs resolve from its own directory.
    repo = Path(__file__).parent.parent
    example = repo / "examples" / "production_shop" / "ltb_vcarve_synthetic_example_handoff.json"
    code, out, _err = run_validator(example, "--check-references")
    assert code == 0
    assert "[WARN]" not in out


# ---------------------------------------------------------------------------
# Missing references -> warning only, exit code unchanged
# ---------------------------------------------------------------------------

def test_missing_manifest_warns_only(tmp_path):
    handoff = scaffold(tmp_path, present=set(ALL_REFS) - {"package_manifest_file"})
    code, out, _err = run_validator(handoff, "--check-references")
    assert code == 0
    assert "PASS" in out
    assert "package_manifest_file reference does not resolve" in out


def test_missing_strategy_warns_only(tmp_path):
    handoff = scaffold(tmp_path, present=set(ALL_REFS) - {"strategy_file"})
    code, out, _err = run_validator(handoff, "--check-references")
    assert code == 0
    assert "strategy_file reference does not resolve" in out


def test_missing_review_packet_warns_only(tmp_path):
    handoff = scaffold(tmp_path, present=set(ALL_REFS) - {"review_packet_file"})
    code, out, _err = run_validator(handoff, "--check-references")
    assert code == 0
    assert "review_packet_file reference does not resolve" in out


def test_missing_bundle_warns_only(tmp_path):
    handoff = scaffold(tmp_path, present=set(ALL_REFS) - {"traceability_bundle_file"})
    code, out, _err = run_validator(handoff, "--check-references")
    assert code == 0
    assert "traceability_bundle_file reference does not resolve" in out


def test_exit_code_zero_with_missing_refs(tmp_path):
    handoff = scaffold(tmp_path, present=set())  # nothing exists
    code, out, _err = run_validator(handoff, "--check-references")
    assert code == 0
    assert out.count("[WARN]") == 4  # all four declared refs warn, none fatal


# ---------------------------------------------------------------------------
# Structure dominates; existence-only (no parsing); omissions are silent
# ---------------------------------------------------------------------------

def test_structural_invalidity_dominates(tmp_path):
    handoff_dir = tmp_path / "production_shop"
    handoff_dir.mkdir(parents=True)
    bad = valid_handoff(dict(ALL_REFS))
    bad["record_type"] = "not_a_handoff"
    handoff = handoff_dir / "h.json"
    handoff.write_text(json.dumps(bad), encoding="utf-8")
    code, _out, err = run_validator(handoff, "--check-references")
    assert code == 1
    assert "FAIL" in err


def test_existing_garbage_file_passes_existence_only(tmp_path):
    # Referenced files exist but contain non-JSON garbage; witness must not parse.
    handoff = scaffold(tmp_path, present=set(ALL_REFS.keys()))
    (tmp_path / "packages" / "pkg" / "manifest.json").write_text(
        "this is not json at all !!!", encoding="utf-8"
    )
    code, out, _err = run_validator(handoff, "--check-references")
    assert code == 0
    assert "[WARN]" not in out


def test_omitted_slot_is_silent(tmp_path):
    # A handoff that simply omits the bundle slot: no warning (no absent-slot finding).
    contents = {k: v for k, v in ALL_REFS.items() if k != "traceability_bundle_file"}
    handoff = scaffold(tmp_path, present=set(contents.keys()), contents=contents)
    code, out, _err = run_validator(handoff, "--check-references")
    assert code == 0
    assert "[WARN]" not in out


# ---------------------------------------------------------------------------
# Resolution is relative to the handoff dir (not cwd); default mode is fs-free
# ---------------------------------------------------------------------------

def test_resolution_relative_to_handoff_dir_independent_of_cwd(tmp_path):
    handoff = scaffold(tmp_path, present=set(ALL_REFS.keys()))
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    code, out, _err = run_validator(handoff, "--check-references", cwd=other_cwd)
    assert code == 0
    assert "[WARN]" not in out  # resolved from handoff dir, not the foreign cwd


def test_default_mode_is_filesystem_free(tmp_path):
    handoff = scaffold(tmp_path, present=set())  # no referenced files exist
    code, out, _err = run_validator(handoff)  # no --check-references
    assert code == 0
    assert "does not resolve" not in out


# ---------------------------------------------------------------------------
# Strict enforcement: --fail-on-reference-warnings (opt-in, additive)
# ---------------------------------------------------------------------------

def test_strict_mode_fails_on_missing_refs(tmp_path):
    # Unresolved references become fatal ONLY under the opt-in strict flag.
    handoff = scaffold(tmp_path, present=set())  # nothing exists
    code, _out, err = run_validator(
        handoff, "--check-references", "--fail-on-reference-warnings"
    )
    assert code == 1
    assert "FAIL" in err
    assert "reference does not resolve" in err


def test_strict_mode_passes_when_refs_resolve(tmp_path):
    handoff = scaffold(tmp_path, present=set(ALL_REFS.keys()))
    code, out, _err = run_validator(
        handoff, "--check-references", "--fail-on-reference-warnings"
    )
    assert code == 0
    assert "PASS" in out


def test_strict_flag_is_noop_without_check_references(tmp_path):
    # Without --check-references there is nothing to enforce; default behavior holds.
    handoff = scaffold(tmp_path, present=set())  # missing refs, but not checked
    code, out, _err = run_validator(handoff, "--fail-on-reference-warnings")
    assert code == 0
    assert "does not resolve" not in out


def test_strict_mode_does_not_affect_structural_failure_semantics(tmp_path):
    # A structurally invalid handoff still exits 1 (structure dominates), strict or not.
    handoff_dir = tmp_path / "production_shop"
    handoff_dir.mkdir(parents=True)
    bad = valid_handoff(dict(ALL_REFS))
    bad["record_type"] = "not_a_handoff"
    handoff = handoff_dir / "h.json"
    handoff.write_text(json.dumps(bad), encoding="utf-8")
    code, _out, err = run_validator(
        handoff, "--check-references", "--fail-on-reference-warnings"
    )
    assert code == 1
    assert "FAIL" in err


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------

def test_witness_mutates_nothing(tmp_path):
    handoff = scaffold(tmp_path, present={"strategy_file"})  # partial, to exercise warns
    before = snapshot(tmp_path)
    run_validator(handoff, "--check-references")
    assert snapshot(tmp_path) == before
