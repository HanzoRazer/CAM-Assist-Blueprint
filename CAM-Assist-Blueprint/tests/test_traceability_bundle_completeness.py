"""
Tests for CAM-A19 Traceability Bundle — completeness witness.

Boundaries witnessed (per the CAM-A19 dev order):
- --check-references is opt-in
- references resolve relative to the bundle file's own directory, or --base
- a declared reference that does not resolve produces a WARNING only
- a known sidecar slot absent from the bundle produces a completeness WARNING
- a resolved sidecar whose own package_reference differs from the bundle's
  produces a mismatch WARNING; a best-effort read is used only for this cross-
  check (parse failures are ignored — sidecar structure is its own validator's job)
- warnings never change structural validity; exit code stays 0 when valid
- a structurally invalid bundle still FAILS with --check-references
- nothing is mutated
"""

import json
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_traceability_bundle.py"


def run_validator(*args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(VALIDATE_SCRIPT)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def write_bundle(dir_: Path, contents: dict, name: str = "bundle.json", extra: dict | None = None) -> Path:
    data = {
        "record_type": "cam_assist_traceability_bundle",
        "record_version": "1.0.0",
        "package_reference": "pkg:ref:001",
        "bundle_contents": contents,
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
        },
    }
    if extra:
        data.update(extra)
    path = dir_ / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def snapshot(d: Path) -> dict:
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in d.rglob("*") if p.is_file()}


# ---------------------------------------------------------------------------
# Opt-in: default path stays filesystem-free
# ---------------------------------------------------------------------------

def test_without_flag_missing_reference_is_silent(tmp_path):
    path = write_bundle(tmp_path, {"risk_file": "missing_risk.json"})
    code, out, _err = run_validator(path)  # no --check-references
    assert code == 0
    assert "does not resolve" not in out


# ---------------------------------------------------------------------------
# All references present -> PASS, no warnings
# ---------------------------------------------------------------------------

def test_all_slots_present_and_resolve_no_warnings(tmp_path):
    """Every known slot present and resolving -> no warnings of any kind."""
    files = {
        "assumptions_file": "a.json",
        "risk_file": "r.json",
        "decision_record_file": "d.json",
        "annotations_file": "n.json",
        "lineage_file": "l.json",
    }
    for name in files.values():
        (tmp_path / name).write_text("{}", encoding="utf-8")
    path = write_bundle(tmp_path, files)
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0
    assert "PASS" in out
    assert "[WARN]" not in out


# ---------------------------------------------------------------------------
# Missing reference -> PASS, warning, exit 0
# ---------------------------------------------------------------------------

def test_missing_reference_pass_with_warning(tmp_path):
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    path = write_bundle(tmp_path, {"assumptions_file": "a.json", "risk_file": "gone.json"})
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0
    assert "PASS" in out
    assert "risk_file reference does not resolve: gone.json" in out
    assert "assumptions_file" not in out  # the present one is not warned


def test_completeness_warning_does_not_change_exit_code(tmp_path):
    path = write_bundle(tmp_path, {"lineage_file": "nope.json"})
    code, _out, _err = run_validator(path, "--check-references")
    assert code == 0


# ---------------------------------------------------------------------------
# Relative resolution is relative to the bundle file's directory
# ---------------------------------------------------------------------------

def test_reference_resolved_relative_to_bundle_file(tmp_path):
    sub = tmp_path / "review_annotations"
    sub.mkdir()
    (sub / "ann.json").write_text("{}", encoding="utf-8")
    tdir = tmp_path / "traceability"
    tdir.mkdir()
    # bundle in traceability/, reference points up-and-over; resolves -> no resolve warning
    path = write_bundle(tdir, {"annotations_file": "../review_annotations/ann.json"})
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0
    assert "does not resolve" not in out  # the declared reference resolved


# ---------------------------------------------------------------------------
# Structurally invalid bundle still FAILS with --check-references
# ---------------------------------------------------------------------------

def test_invalid_structure_with_check_references_fails(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({
        "record_type": "wrong_type",
        "record_version": "1.0.0",
        "package_reference": "x",
        "bundle_contents": {},
    }), encoding="utf-8")
    code, _out, err = run_validator(path, "--check-references")
    assert code == 1
    assert "record_type" in err


# ---------------------------------------------------------------------------
# Cross-check is best-effort: an unparseable referenced sidecar is never an
# error and never produces a resolve/mismatch warning (its own validator owns
# its structure). Absent-slot completeness warnings are unrelated.
# ---------------------------------------------------------------------------

def test_unparseable_sidecar_is_not_an_error_or_resolve_warning(tmp_path):
    # The referenced file EXISTS but contains invalid JSON / garbage.
    # If the layer treated parse failure as an error or mismatch, this would
    # warn/fail. It must not: existence is satisfied and the cross-check is
    # best-effort. (Absent slots still warn, which is a separate concern.)
    (tmp_path / "garbage.json").write_text("this is not json at all {{{", encoding="utf-8")
    path = write_bundle(tmp_path, {"decision_record_file": "garbage.json"})
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0
    assert "does not resolve" not in out  # the file exists
    assert "mismatch" not in out  # parse failure is ignored, not a mismatch
    assert "decision_record_file" not in out  # the present, resolving slot is unmentioned


# ---------------------------------------------------------------------------
# Mutates nothing
# ---------------------------------------------------------------------------

def test_check_references_mutates_nothing(tmp_path):
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    write_bundle(tmp_path, {"assumptions_file": "a.json", "risk_file": "gone.json"})
    before = snapshot(tmp_path)
    run_validator(tmp_path / "bundle.json", "--check-references")
    after = snapshot(tmp_path)
    assert before == after


# ---------------------------------------------------------------------------
# Absent slots are completeness (omission) findings — warnings only
# ---------------------------------------------------------------------------

def test_absent_slot_emits_completeness_warning(tmp_path):
    (tmp_path / "r.json").write_text("{}", encoding="utf-8")
    path = write_bundle(tmp_path, {"risk_file": "r.json"})  # other four slots absent
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0  # omissions never change the exit code
    assert "completeness: assumptions_file not present in bundle" in out
    assert "completeness: decision_record_file not present in bundle" in out
    assert "completeness: annotations_file not present in bundle" in out
    assert "completeness: lineage_file not present in bundle" in out
    assert "completeness: risk_file" not in out  # the present slot is not an omission


def test_empty_bundle_warns_every_slot_absent(tmp_path):
    path = write_bundle(tmp_path, {})
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0
    for slot in (
        "assumptions_file",
        "risk_file",
        "decision_record_file",
        "annotations_file",
        "lineage_file",
    ):
        assert f"completeness: {slot} not present in bundle" in out


def test_absent_slots_silent_without_flag(tmp_path):
    path = write_bundle(tmp_path, {})
    code, out, _err = run_validator(path)  # no --check-references
    assert code == 0
    assert "completeness:" not in out  # omissions are a witness concern only


# ---------------------------------------------------------------------------
# Cross-artifact package_reference consistency — warning only
# ---------------------------------------------------------------------------

def _sidecar(dir_: Path, name: str, package_reference: str) -> None:
    (dir_ / name).write_text(
        json.dumps({"package_reference": package_reference}), encoding="utf-8"
    )


def test_package_reference_mismatch_emits_warning(tmp_path):
    _sidecar(tmp_path, "r.json", "pkg:ref:OTHER")
    path = write_bundle(tmp_path, {"risk_file": "r.json"})  # bundle ref is pkg:ref:001
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0  # consistency findings never change the exit code
    assert "package_reference mismatch in risk_file" in out
    assert "'pkg:ref:OTHER'" in out
    assert "bundle 'pkg:ref:001'" in out


def test_matching_package_reference_no_mismatch_warning(tmp_path):
    _sidecar(tmp_path, "r.json", "pkg:ref:001")  # matches the bundle's reference
    path = write_bundle(tmp_path, {"risk_file": "r.json"})
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0
    assert "mismatch" not in out


def test_sidecar_without_package_reference_no_mismatch(tmp_path):
    (tmp_path / "r.json").write_text("{}", encoding="utf-8")  # no package_reference key
    path = write_bundle(tmp_path, {"risk_file": "r.json"})
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0
    assert "mismatch" not in out


# ---------------------------------------------------------------------------
# --base overrides the resolution directory
# ---------------------------------------------------------------------------

def test_base_overrides_resolution_directory(tmp_path):
    bundle_dir = tmp_path / "elsewhere"
    bundle_dir.mkdir()
    refs_dir = tmp_path / "refs"
    refs_dir.mkdir()
    (refs_dir / "r.json").write_text("{}", encoding="utf-8")
    # Reference resolves under refs/, not next to the bundle.
    path = write_bundle(bundle_dir, {"risk_file": "r.json"})

    # Without --base it resolves relative to the bundle dir and does not exist.
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0
    assert "risk_file reference does not resolve" in out

    # With --base pointing at refs/, the same reference resolves.
    code, out, _err = run_validator(path, "--check-references", "--base", refs_dir)
    assert code == 0
    assert "does not resolve" not in out
