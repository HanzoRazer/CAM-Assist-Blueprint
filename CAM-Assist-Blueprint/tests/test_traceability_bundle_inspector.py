"""
Phase 6 tests for CAM-A19 Traceability Bundle — inspector presence rendering.

The inspector is a DISCOVERY surface, not a validator. It reports only:

    Traceability Bundle:
      present

or:

    Traceability Bundle:
      not declared

Witnessed:
- detection via the conventional path
- detection via explicit --bundle
- not-declared when absent
- detection only: a bundle with unparseable contents is still "present"
  (the inspector never parses, validates, or completeness-checks it)
- explicit --bundle to a missing path -> exit 2
- JSON output carries traceability_bundle
- inspection mutates nothing
"""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
INSPECT_SCRIPT = SCRIPTS_DIR / "inspect_strategy_package.py"
EXAMPLE_PKG = REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example"


def run_inspect(*args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(INSPECT_SCRIPT)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def make_package(parent: Path, name: str = "pkg") -> Path:
    """Create a minimal valid strategy package (inspector returns valid)."""
    pkg = parent / name
    pkg.mkdir(parents=True)
    strategy = {
        "strategy_version": "1.0",
        "strategy_id": "test-bundle",
        "units": "mm",
        "coordinate_frame": {"origin": "nut", "x_axis": "x", "y_axis": "y", "z_axis": "z"},
        "provenance": {"source_spec_id": "test", "cam_assist_version": "0.6.0", "created_at": "2026-06-15T00:00:00Z"},
        "operation_intent": {"operation_type": "test", "target_feature": "test", "non_execution_declaration": True},
        "material_context": {"material_class": "test"},
        "safety_boundary": {"non_execution_declaration": True, "human_review_required": True, "execution_authority_claim": False},
        "approval_state": "pending",
    }
    (pkg / "strategy.json").write_text(json.dumps(strategy), encoding="utf-8")
    (pkg / "review_packet.md").write_text("# Review Packet\n\nTest content.\n" * 50, encoding="utf-8")
    manifest = {
        "manifest_version": "1.0.0",
        "package_type": "cam_assist_strategy_package",
        "operation_type": "test",
        "strategy_file": "strategy.json",
        "review_packet_file": "review_packet.md",
        "source_geometry_files": ["geo.dxf"],
        "created_at": "2026-06-15T00:00:00Z",
        "authority": {
            "non_execution_declaration": True,
            "execution_authority_claim": False,
            "requires_human_review": True,
        },
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pkg


def write_conventional_bundle(parent: Path, pkg_name: str, content: str = '{"x": 1}') -> Path:
    d = parent / "traceability"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{pkg_name}_bundle.json"
    path.write_text(content, encoding="utf-8")
    return path


def snapshot(d: Path) -> dict:
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in d.rglob("*") if p.is_file()}


# ---------------------------------------------------------------------------
# Conventional detection
# ---------------------------------------------------------------------------

def test_bundle_present_via_conventional_path(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_bundle(tmp_path, "pkg")
    code, out, _err = run_inspect(pkg)
    assert "Traceability Bundle:" in out
    assert "Traceability Bundle:\n  present" in out


def test_bundle_not_declared_when_absent(tmp_path):
    pkg = make_package(tmp_path)
    code, out, _err = run_inspect(pkg)
    assert "Traceability Bundle:\n  not declared" in out


def test_committed_example_package_shows_bundle_present():
    code, out, _err = run_inspect(EXAMPLE_PKG)
    assert "Traceability Bundle:\n  present" in out


# ---------------------------------------------------------------------------
# Explicit flag
# ---------------------------------------------------------------------------

def test_bundle_present_via_explicit_flag(tmp_path):
    pkg = make_package(tmp_path)
    b = tmp_path / "somewhere_bundle.json"
    b.write_text('{"x": 1}', encoding="utf-8")
    code, out, _err = run_inspect(pkg, "--bundle", b)
    assert "Traceability Bundle:\n  present" in out


def test_explicit_missing_bundle_returns_2(tmp_path):
    pkg = make_package(tmp_path)
    code, _out, err = run_inspect(pkg, "--bundle", tmp_path / "nope_bundle.json")
    assert code == 2
    assert "not found" in err.lower()


# ---------------------------------------------------------------------------
# Detection only — never parses/validates the bundle
# ---------------------------------------------------------------------------

def test_unparseable_bundle_still_present(tmp_path):
    pkg = make_package(tmp_path)
    # Garbage content: if the inspector parsed/validated it, this would error.
    write_conventional_bundle(tmp_path, "pkg", content="this is not json {{{")
    code, out, _err = run_inspect(pkg)
    assert "Traceability Bundle:\n  present" in out


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def test_json_output_carries_traceability_bundle(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_bundle(tmp_path, "pkg")
    code, out, _err = run_inspect(pkg, "--json")
    data = json.loads(out)
    assert data["traceability_bundle"]["present"] is True


def test_json_output_bundle_absent(tmp_path):
    pkg = make_package(tmp_path)
    code, out, _err = run_inspect(pkg, "--json")
    data = json.loads(out)
    assert data["traceability_bundle"]["present"] is False


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------

def test_inspection_does_not_mutate(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_bundle(tmp_path, "pkg")
    before = snapshot(tmp_path)
    run_inspect(pkg)
    run_inspect(pkg, "--json")
    after = snapshot(tmp_path)
    assert before == after
