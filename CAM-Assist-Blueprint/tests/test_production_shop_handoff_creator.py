"""
Phase 3 tests for CAM-A20 Production Shop Handoff — creator.

Witnesses (mapping to the dev-order test matrix):
- creator emits a valid handoff; generated handoff passes the structural validator
- the non-execution authority block (four const-true flags) is always emitted
- handoff_direction is always emitted
- the core three content references are always emitted
- an explicit --traceability-bundle path is included
- a conventionally-located bundle is discovered and included
- an absent (non-explicit, non-conventional) bundle is omitted
- references are relative to the output file, forward-slashed
- a created_at UTC timestamp is stamped (parseable ISO-8601)
- overwrite is refused without --force, allowed with --force
- the source package is not mutated
- a missing package directory exits nonzero
- package_reference uses manifest federated_package_id, else the directory name

The creator is reference-only: it never resolves or stats the referenced core
files, and an explicit bundle path is recorded as-is without an existence check.
"""

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
CREATE_SCRIPT = SCRIPTS_DIR / "create_production_shop_handoff.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_production_shop_handoff.py"

CORE_SLOTS = {"package_manifest_file", "strategy_file", "review_packet_file"}


def run_script(script: Path, *args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(script)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def make_package(
    root: Path,
    name: str = "pkg",
    federated_id: str | None = None,
    strategy_file: str = "strategy.json",
    review_packet_file: str = "review_packet.md",
) -> Path:
    """Create a package dir with a manifest and the files it declares."""
    pkg = root / name
    pkg.mkdir(parents=True)
    manifest: dict = {
        "manifest_version": "1.1.0",
        "package_type": "cam_assist_strategy_package",
        "strategy_file": strategy_file,
        "review_packet_file": review_packet_file,
    }
    if federated_id is not None:
        manifest["federation"] = {"federated_package_id": federated_id}
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (pkg / strategy_file).write_text("{}", encoding="utf-8")
    (pkg / review_packet_file).write_text("# review\n", encoding="utf-8")
    return pkg


def write_conventional_bundle(root: Path, pkg_name: str) -> Path:
    """Place a conventionally-named traceability bundle under <root>/traceability/."""
    d = root / "traceability"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{pkg_name}_bundle.json"
    path.write_text("{}", encoding="utf-8")
    return path


def snapshot(d: Path) -> dict:
    """Map of relative path -> bytes for every file under d (for mutation checks)."""
    return {
        p.relative_to(d).as_posix(): p.read_bytes()
        for p in d.rglob("*")
        if p.is_file()
    }


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Emits valid handoff; structural validator agrees
# ---------------------------------------------------------------------------

def test_creator_emits_valid_handoff(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "out" / "h.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert code == 0, err
    assert out.exists()
    handoff = load(out)
    assert handoff["record_type"] == "cam_assist_production_shop_handoff"
    assert handoff["record_version"] == "1.0.0"


def test_generated_handoff_passes_structural_validator(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "out" / "h.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert code == 0, err
    vcode, vout, verr = run_script(VALIDATE_SCRIPT, out)
    assert vcode == 0, verr + vout


# ---------------------------------------------------------------------------
# Always-emitted invariants
# ---------------------------------------------------------------------------

def test_authority_block_always_emitted(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert load(out)["authority"] == {
        "is_informational": True,
        "does_not_authorize_execution": True,
        "does_not_bypass_human_review": True,
        "does_not_confirm_machine_readiness": True,
    }


def test_direction_always_emitted(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert load(out)["handoff_direction"] == "cam_assist_to_production_shop"


def test_core_three_content_refs_emitted(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    contents = load(out)["contents"]
    assert CORE_SLOTS <= set(contents.keys())
    for slot in CORE_SLOTS:
        assert contents[slot]  # non-empty


def test_core_refs_follow_manifest_declared_filenames(tmp_path):
    pkg = make_package(
        tmp_path, strategy_file="custom_strategy.json", review_packet_file="packet.md"
    )
    out = tmp_path / "out" / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    contents = load(out)["contents"]
    assert contents["strategy_file"].endswith("custom_strategy.json")
    assert contents["review_packet_file"].endswith("packet.md")


# ---------------------------------------------------------------------------
# Traceability bundle resolution: explicit > conventional > omit
# ---------------------------------------------------------------------------

def test_explicit_bundle_path_included(tmp_path):
    pkg = make_package(tmp_path)
    bundle = tmp_path / "elsewhere" / "custom_bundle.json"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("{}", encoding="utf-8")
    out = tmp_path / "out" / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, "--traceability-bundle", bundle)
    ref = load(out)["contents"]["traceability_bundle_file"]
    assert ref.endswith("custom_bundle.json")


def test_explicit_bundle_overrides_conventional(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_bundle(tmp_path, "pkg")  # would be discovered if not overridden
    explicit = tmp_path / "explicit_bundle.json"
    explicit.write_text("{}", encoding="utf-8")
    out = tmp_path / "out" / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, "--traceability-bundle", explicit)
    assert load(out)["contents"]["traceability_bundle_file"].endswith("explicit_bundle.json")


def test_conventional_bundle_discovered(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_bundle(tmp_path, "pkg")
    out = tmp_path / "out" / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert "traceability_bundle_file" in load(out)["contents"]


def test_missing_bundle_omitted(tmp_path):
    pkg = make_package(tmp_path)  # no conventional bundle, no explicit flag
    out = tmp_path / "out" / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert "traceability_bundle_file" not in load(out)["contents"]


# ---------------------------------------------------------------------------
# Path shape: relative to the output file, forward-slashed
# ---------------------------------------------------------------------------

def test_paths_relative_to_output_file(tmp_path):
    # package at examples/packages/<name>; output at examples/production_shop/...
    examples = tmp_path / "examples"
    pkg = make_package(examples / "packages", name="pkg")
    out = examples / "production_shop" / "pkg_handoff.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    ref = load(out)["contents"]["package_manifest_file"]
    assert ref == "../packages/pkg/manifest.json"


def test_paths_use_forward_slashes(tmp_path):
    examples = tmp_path / "examples"
    pkg = make_package(examples / "packages", name="pkg")
    out = examples / "production_shop" / "pkg_handoff.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    for ref in load(out)["contents"].values():
        assert "\\" not in ref


# ---------------------------------------------------------------------------
# Overwrite protection
# ---------------------------------------------------------------------------

def test_refuses_overwrite_without_force(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "h.json"
    code1, _o1, _e1 = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert code1 == 0
    code2, _o2, err2 = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert code2 == 1
    assert "already exists" in err2


def test_force_overwrites(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, "--force")
    assert code == 0, err


# ---------------------------------------------------------------------------
# No mutation; missing package; default output; package_reference
# ---------------------------------------------------------------------------

def test_source_package_not_mutated(tmp_path):
    pkg = make_package(tmp_path, federated_id="lt:vcarve:x")
    write_conventional_bundle(tmp_path, "pkg")
    before = snapshot(pkg)
    out = tmp_path / "out" / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert snapshot(pkg) == before


def test_missing_package_exits_nonzero(tmp_path):
    code, _o, err = run_script(CREATE_SCRIPT, "--package", tmp_path / "nope")
    assert code != 0
    assert "not found" in err.lower()


def test_default_output_location(tmp_path):
    examples = tmp_path / "examples"
    pkg = make_package(examples / "packages", name="pkg")
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg)
    assert code == 0, err
    assert (examples / "production_shop" / "pkg_handoff.json").exists()


def test_package_reference_from_manifest_federation(tmp_path):
    pkg = make_package(tmp_path, federated_id="luthiers-toolbox:vcarve:example-001")
    out = tmp_path / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert load(out)["package_reference"] == "luthiers-toolbox:vcarve:example-001"


def test_package_reference_falls_back_to_dir_name(tmp_path):
    # package dir with a manifest but no federation block
    pkg = make_package(tmp_path, name="my_pkg")
    out = tmp_path / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert load(out)["package_reference"] == "my_pkg"


def _load_creator_module():
    """Import the creator as a module for unit-level (non-subprocess) tests."""
    spec = importlib.util.spec_from_file_location("_create_psh", CREATE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Exit-code contract: write errors are distinct from argument errors
# ---------------------------------------------------------------------------

def test_write_error_returns_exit_2(tmp_path):
    # Route the output through a path whose parent is a regular file, so the
    # directory creation / write fails -> documented file/write error (exit 2).
    pkg = make_package(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory", encoding="utf-8")
    out = blocker / "sub" / "h.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert code == 2, err
    assert "Failed to write" in err


def test_missing_package_is_argument_error_exit_1(tmp_path):
    code, _o, err = run_script(CREATE_SCRIPT, "--package", tmp_path / "nope")
    assert code == 1
    assert "not found" in err.lower()


def test_cross_drive_relpath_reported_cleanly(tmp_path, monkeypatch):
    # relative_reference raises ValueError for paths on different Windows drives.
    # That must surface as a clean argument error (exit 1), not a traceback.
    mod = _load_creator_module()
    pkg = make_package(tmp_path)

    def boom(*_a, **_k):
        raise ValueError("path is on mount 'C:', start on mount 'D:'")

    monkeypatch.setattr(mod, "relative_reference", boom)
    result = mod.create_handoff(pkg, output_path=tmp_path / "out" / "h.json")
    assert result.success is False
    assert result.exit_code == 1
    assert "different drives" in result.error


def test_created_at_emitted_as_utc_timestamp(tmp_path):
    # The creator stamps created_at (dev order: "Stamp created_at..."), mirroring
    # the traceability bundle creator. It must be a parseable UTC ISO-8601 string.
    pkg = make_package(tmp_path)
    out = tmp_path / "h.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    created_at = load(out)["created_at"]
    assert isinstance(created_at, str) and created_at.endswith("Z")
    # Parseable as an aware UTC datetime (Z -> +00:00 for fromisoformat).
    parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)
