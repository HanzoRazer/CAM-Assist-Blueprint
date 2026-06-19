"""
Phase 4 tests for CAM-A19 Traceability Bundle — completeness witness.

Boundaries witnessed (per the Phase 4 directive):
- --check-references is opt-in
- declared references are resolved relative to the bundle file's own directory
- a declared reference that does not resolve produces a WARNING only
- warnings never change structural validity; exit code stays 0 when valid
- a structurally invalid bundle still FAILS with --check-references
- existence only: the layer does NOT open/parse/validate sidecar contents
- nothing is mutated

Scope note: this layer checks DECLARED references only. It does not warn about
absent slots and does not read sidecar package_reference values (those handoff
items are deferred and intentionally out of Phase 4 scope).
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

def test_all_references_present_pass_no_warnings(tmp_path):
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "r.json").write_text("{}", encoding="utf-8")
    path = write_bundle(tmp_path, {"assumptions_file": "a.json", "risk_file": "r.json"})
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
    # bundle in traceability/, reference points up-and-over; resolves -> no warning
    path = write_bundle(tdir, {"annotations_file": "../review_annotations/ann.json"})
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0
    assert "[WARN]" not in out


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
# Existence only: does NOT open / parse / validate sidecar contents
# ---------------------------------------------------------------------------

def test_does_not_open_or_validate_sidecar_contents(tmp_path):
    # The referenced file EXISTS but contains invalid JSON / garbage.
    # If the layer opened/parsed it, this would error or warn. It must not.
    (tmp_path / "garbage.json").write_text("this is not json at all {{{", encoding="utf-8")
    path = write_bundle(tmp_path, {"decision_record_file": "garbage.json"})
    code, out, _err = run_validator(path, "--check-references")
    assert code == 0
    assert "[WARN]" not in out  # existence satisfied; contents never inspected


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
