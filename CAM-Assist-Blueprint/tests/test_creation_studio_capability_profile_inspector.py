"""
Inspector-detection tests for CAM-A23 Creation Studio Capability Profile.

The inspector is a DISCOVERY surface, not a validator or a consumer. It reports
only:

    Creation Studio Capability Profile:
      present (detected, not validated)

or:

    Creation Studio Capability Profile:
      not declared

Witnessed:
- detection via the conventional creation_studio/capability_profile.json path
- detection via explicit --capability-profile
- not-declared when absent
- detection only: a profile with unparseable contents is still "present"
  (the inspector never parses, validates, or reads declared capabilities)
- the profile is NOT package-specific: one profile serves every package under the
  same root, and a package-named file is not mistaken for it
- explicit --capability-profile to a missing path -> exit 2
- JSON output carries creation_studio_capability_profile (presence + path)
- profile presence does not change the package's own validity
- inspection mutates nothing
"""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
INSPECT_SCRIPT = REPO_ROOT / "scripts" / "inspect_strategy_package.py"
EXAMPLE_PKG = REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example"

PRESENT = "Creation Studio Capability Profile:\n  present (detected, not validated)"
ABSENT = "Creation Studio Capability Profile:\n  not declared"


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
        "strategy_id": "test-profile",
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


def write_conventional_profile(parent: Path, content: str = '{"x": 1}') -> Path:
    d = parent / "creation_studio"
    d.mkdir(parents=True, exist_ok=True)
    path = d / "capability_profile.json"
    path.write_text(content, encoding="utf-8")
    return path


def snapshot(d: Path) -> dict:
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in d.rglob("*") if p.is_file()}


# ---------------------------------------------------------------------------
# Conventional detection
# ---------------------------------------------------------------------------

def test_profile_present_via_conventional_path(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_profile(tmp_path)
    _code, out, _err = run_inspect(pkg)
    assert PRESENT in out


def test_profile_not_declared_when_absent(tmp_path):
    pkg = make_package(tmp_path)
    _code, out, _err = run_inspect(pkg)
    assert ABSENT in out


def test_committed_example_package_shows_profile_present():
    _code, out, _err = run_inspect(EXAMPLE_PKG)
    assert PRESENT in out


# ---------------------------------------------------------------------------
# A profile is per installation, not per package
# ---------------------------------------------------------------------------

def test_one_profile_serves_every_package_under_the_root(tmp_path):
    first = make_package(tmp_path, "pkg_one")
    second = make_package(tmp_path, "pkg_two")
    write_conventional_profile(tmp_path)
    for pkg in (first, second):
        _code, out, _err = run_inspect(pkg)
        assert PRESENT in out


def test_package_named_profile_file_is_not_detected(tmp_path):
    # The filename is fixed. A package-named file in creation_studio/ is a CAM-A22
    # request or something else — never this profile.
    pkg = make_package(tmp_path)
    d = tmp_path / "creation_studio"
    d.mkdir()
    (d / "pkg_capability_profile.json").write_text('{"x": 1}', encoding="utf-8")
    _code, out, _err = run_inspect(pkg)
    assert ABSENT in out


def test_request_and_profile_are_detected_independently(tmp_path):
    # The two CAM-A22/CAM-A23 artifacts share a directory but are separate
    # contracts; neither presence implies the other.
    pkg = make_package(tmp_path)
    d = tmp_path / "creation_studio"
    d.mkdir()
    (d / "pkg_request.json").write_text('{"x": 1}', encoding="utf-8")
    _code, out, _err = run_inspect(pkg)
    assert "CAM-Creation-Studio Request:\n  present" in out
    assert ABSENT in out


# ---------------------------------------------------------------------------
# Explicit flag
# ---------------------------------------------------------------------------

def test_profile_present_via_explicit_flag(tmp_path):
    pkg = make_package(tmp_path)
    p = tmp_path / "somewhere_else.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    _code, out, _err = run_inspect(pkg, "--capability-profile", p)
    assert PRESENT in out


def test_explicit_missing_profile_returns_2(tmp_path):
    pkg = make_package(tmp_path)
    code, _out, err = run_inspect(pkg, "--capability-profile", tmp_path / "nope.json")
    assert code == 2
    assert "not found" in err.lower()


# ---------------------------------------------------------------------------
# Detection only — never parses/validates the profile
# ---------------------------------------------------------------------------

def test_unparseable_profile_still_present(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_profile(tmp_path, content="this is not json {{{")
    _code, out, _err = run_inspect(pkg)
    assert PRESENT in out


def test_structurally_invalid_profile_still_present(tmp_path):
    # Valid JSON, invalid profile (wrong record_type, execution-granting flag).
    # The inspector detects; it does not judge. Validity is the validator's job.
    pkg = make_package(tmp_path)
    write_conventional_profile(
        tmp_path,
        content=json.dumps({"record_type": "nonsense", "authorizes_execution": True}),
    )
    _code, out, _err = run_inspect(pkg)
    assert PRESENT in out


def test_inspector_does_not_echo_declared_capabilities(tmp_path):
    # Detection only: the section reports presence, never what the profile claims.
    pkg = make_package(tmp_path)
    write_conventional_profile(
        tmp_path,
        content=json.dumps({"capabilities": [{"capability_id": "a_secret_capability"}]}),
    )
    _code, out, _err = run_inspect(pkg)
    assert PRESENT in out
    assert "a_secret_capability" not in out


def test_profile_presence_does_not_change_package_validity(tmp_path):
    pkg = make_package(tmp_path)
    without_code, _out, _err = run_inspect(pkg)
    write_conventional_profile(tmp_path)
    with_code, _out, _err = run_inspect(pkg)
    assert without_code == with_code == 0


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def test_json_output_carries_capability_profile(tmp_path):
    pkg = make_package(tmp_path)
    p = write_conventional_profile(tmp_path)
    _code, out, _err = run_inspect(pkg, "--json")
    data = json.loads(out)
    assert data["creation_studio_capability_profile"]["present"] is True
    assert data["creation_studio_capability_profile"]["path"] == str(p)


def test_json_output_profile_absent(tmp_path):
    pkg = make_package(tmp_path)
    _code, out, _err = run_inspect(pkg, "--json")
    data = json.loads(out)
    assert data["creation_studio_capability_profile"]["present"] is False
    assert data["creation_studio_capability_profile"]["path"] is None


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------

def test_inspection_does_not_mutate(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_profile(tmp_path)
    before = snapshot(tmp_path)
    run_inspect(pkg)
    run_inspect(pkg, "--json")
    after = snapshot(tmp_path)
    assert before == after
