"""
Phase 3 tests for CAM-A19 Traceability Bundle — creator.

Witnesses:
- auto-discovery of conventionally-located sidecars into bundle_contents
- absent sidecars are omitted (missing is allowed)
- references are relative to the bundle's output dir, forward-slashed
- --empty seeds {} without scanning (even when sidecars exist)
- overwrite is refused without --force, allowed with --force
- the generated bundle passes the structural validator
- the source package is not mutated
- record fields (type/version/authority/created_at/package_reference)

Discovery locations are built to mirror the inspector's conventional resolution
(non-examples layout: <parent>/traceability/ and <parent>/review_annotations/).
"""

import json
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
CREATE_SCRIPT = SCRIPTS_DIR / "create_traceability_bundle.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_traceability_bundle.py"


def run_script(script: Path, *args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(script)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def make_package(root: Path, name: str = "pkg", federated_id: str | None = None) -> Path:
    """Create a package directory; optionally a manifest with a federated id."""
    pkg = root / name
    pkg.mkdir(parents=True)
    if federated_id is not None:
        manifest = {
            "manifest_version": "1.0.0",
            "package_type": "cam_assist_strategy_package",
            "federation": {"federated_package_id": federated_id},
        }
        (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pkg


def write_sidecar(root: Path, sub_root: str, pkg_name: str, suffix: str) -> Path:
    """Place a conventionally-named sidecar under <root>/<sub_root>/."""
    d = root / sub_root
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{pkg_name}{suffix}"
    path.write_text("{}", encoding="utf-8")
    return path


def snapshot(d: Path) -> set:
    return {p.relative_to(d).as_posix() for p in d.rglob("*")}


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Auto-discovery
# ---------------------------------------------------------------------------

def test_auto_discovers_present_sidecars_and_omits_absent(tmp_path):
    pkg = make_package(tmp_path)
    write_sidecar(tmp_path, "traceability", "pkg", "_assumptions.json")
    write_sidecar(tmp_path, "traceability", "pkg", "_risk.json")
    write_sidecar(tmp_path, "traceability", "pkg", "_lineage.json")
    # decision_record and annotations intentionally absent

    code, _out, err = run_script(CREATE_SCRIPT, "--package", pkg)
    assert code == 0, err

    bundle = load(tmp_path / "traceability" / "pkg_bundle.json")
    contents = bundle["bundle_contents"]
    assert set(contents.keys()) == {"assumptions_file", "risk_file", "lineage_file"}
    assert "decision_record_file" not in contents
    assert "annotations_file" not in contents


def test_same_dir_reference_is_bare_filename(tmp_path):
    pkg = make_package(tmp_path)
    write_sidecar(tmp_path, "traceability", "pkg", "_assumptions.json")
    code, _out, err = run_script(CREATE_SCRIPT, "--package", pkg)
    assert code == 0, err
    bundle = load(tmp_path / "traceability" / "pkg_bundle.json")
    # bundle lives in traceability/, sidecar lives in traceability/ -> bare name
    assert bundle["bundle_contents"]["assumptions_file"] == "pkg_assumptions.json"


def test_annotations_reference_is_relative_and_forward_slashed(tmp_path):
    pkg = make_package(tmp_path)
    write_sidecar(tmp_path, "review_annotations", "pkg", "_annotations.json")
    code, _out, err = run_script(CREATE_SCRIPT, "--package", pkg)
    assert code == 0, err
    bundle = load(tmp_path / "traceability" / "pkg_bundle.json")
    ref = bundle["bundle_contents"]["annotations_file"]
    # output in traceability/, annotations in review_annotations/ -> ../review_annotations/...
    assert ref == "../review_annotations/pkg_annotations.json"
    assert "\\" not in ref


# ---------------------------------------------------------------------------
# --empty
# ---------------------------------------------------------------------------

def test_empty_flag_seeds_empty_contents_even_with_sidecars(tmp_path):
    pkg = make_package(tmp_path)
    write_sidecar(tmp_path, "traceability", "pkg", "_assumptions.json")
    code, _out, err = run_script(CREATE_SCRIPT, "--package", pkg, "--empty")
    assert code == 0, err
    bundle = load(tmp_path / "traceability" / "pkg_bundle.json")
    assert bundle["bundle_contents"] == {}


# ---------------------------------------------------------------------------
# Overwrite protection
# ---------------------------------------------------------------------------

def test_refuses_overwrite_without_force(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "b.json"
    code1, _o1, _e1 = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert code1 == 0
    code2, _o2, err2 = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert code2 == 1
    assert "already exists" in err2


def test_force_overwrites(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "b.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, "--force")
    assert code == 0, err


# ---------------------------------------------------------------------------
# Generated bundle is valid; package not mutated
# ---------------------------------------------------------------------------

def test_generated_bundle_passes_structural_validator(tmp_path):
    pkg = make_package(tmp_path)
    write_sidecar(tmp_path, "traceability", "pkg", "_risk.json")
    out = tmp_path / "b.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert code == 0, err
    vcode, vout, verr = run_script(VALIDATE_SCRIPT, out)
    assert vcode == 0, verr + vout


def test_empty_generated_bundle_passes_validator_with_warning(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "b.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, "--empty")
    vcode, vout, _verr = run_script(VALIDATE_SCRIPT, out)
    assert vcode == 0
    assert "bundle_contents is empty" in vout


def test_source_package_not_mutated(tmp_path):
    pkg = make_package(tmp_path, federated_id="lt:vcarve:x")
    write_sidecar(tmp_path, "traceability", "pkg", "_assumptions.json")
    before = snapshot(pkg)
    run_script(CREATE_SCRIPT, "--package", pkg)
    after = snapshot(pkg)
    assert before == after


# ---------------------------------------------------------------------------
# Record fields
# ---------------------------------------------------------------------------

def test_record_fields_and_authority(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "b.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    bundle = load(out)
    assert bundle["record_type"] == "cam_assist_traceability_bundle"
    assert bundle["record_version"] == "1.0.0"
    assert bundle["created_at"].endswith("Z")
    assert bundle["authority"] == {
        "is_informational": True,
        "does_not_authorize_execution": True,
        "does_not_bypass_human_review": True,
    }


def test_package_reference_from_manifest_federation(tmp_path):
    pkg = make_package(tmp_path, federated_id="luthiers-toolbox:vcarve:example-001")
    out = tmp_path / "b.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert load(out)["package_reference"] == "luthiers-toolbox:vcarve:example-001"


def test_package_reference_falls_back_to_dir_name(tmp_path):
    pkg = make_package(tmp_path, name="my_pkg")  # no manifest
    out = tmp_path / "b.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert load(out)["package_reference"] == "my_pkg"


def test_default_output_location(tmp_path):
    pkg = make_package(tmp_path)
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg)
    assert code == 0, err
    assert (tmp_path / "traceability" / "pkg_bundle.json").exists()


def test_missing_package_dir_errors(tmp_path):
    code, _o, err = run_script(CREATE_SCRIPT, "--package", tmp_path / "nope")
    assert code == 1
    assert "not found" in err.lower()
