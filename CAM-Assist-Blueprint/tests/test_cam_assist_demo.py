"""
CAM-A21 tests — end-to-end demonstration runner.

Witnesses that scripts/run_cam_assist_demo.py orchestrates the real public CLIs
into a full, non-execution workflow:

- the demo succeeds in a temporary workspace and creates the expected artifacts
- demo_summary reports every step and the non-execution authority block
- a non-zero child command aborts the demo (exit 1)
- committed source examples are never mutated
- default runs clean up their temporary workspace; --keep preserves it
- --quiet suppresses per-step progress; --json emits a machine-readable summary
- summary paths are relative and no G-code artifact is produced

The runner is invoked as a subprocess so the tests witness real CLI behavior.
"""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO = REPO_ROOT / "scripts" / "run_cam_assist_demo.py"
INPUT = REPO_ROOT / "examples" / "ltb_import" / "synthetic_vcarve_ltb_output.json"
CANONICAL_STRATEGY = (
    REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example" / "strategy.json"
)

EXPECTED_STEPS = [
    "import_strategy", "validate_strategy", "generate_review_packet", "assemble_package",
    "inspect_package", "archive_package", "validate_archive", "stage_package",
    "review_queue", "record_review_decision", "review_annotations",
    "manufacturing_assumptions", "risk_assessment", "decision_record",
    "revision_lineage", "traceability_bundle", "validate_bundle",
    "production_shop_handoff", "validate_handoff", "inspect_final",
    "verify_non_execution_invariant",
]


def run_demo(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(DEMO), *args], capture_output=True, text=True
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    """Run the demo once into a kept workspace; snapshot source files around it."""
    ws = tmp_path_factory.mktemp("demo_ws")
    before = {p: _digest(p) for p in (INPUT, CANONICAL_STRATEGY)}
    proc = run_demo("--workspace", str(ws), "--keep")
    after = {p: _digest(p) for p in (INPUT, CANONICAL_STRATEGY)}
    summary = json.loads((ws / "demo_summary.json").read_text(encoding="utf-8"))
    return {"proc": proc, "ws": ws, "summary": summary, "before": before, "after": after}


# ---------------------------------------------------------------------------
# Success + artifacts
# ---------------------------------------------------------------------------

def test_demo_succeeds(demo):
    assert demo["proc"].returncode == 0, demo["proc"].stderr
    assert demo["summary"]["status"] == "passed"


def test_all_steps_present_and_passed(demo):
    steps = demo["summary"]["steps"]
    assert [s["name"] for s in steps] == EXPECTED_STEPS
    assert all(s["status"] == "passed" and s["exit_code"] == 0 for s in steps)


def test_expected_artifacts_created(demo):
    ws, artifacts = demo["ws"], demo["summary"]["artifacts"]
    for key in ("strategy", "manifest", "traceability_bundle", "production_shop_handoff"):
        assert key in artifacts, key
    for rel in artifacts.values():
        assert (ws / rel).exists(), rel


def test_summary_paths_are_relative(demo):
    for rel in demo["summary"]["artifacts"].values():
        assert not Path(rel).is_absolute()
        assert ":" not in rel  # no Windows drive letter


def test_summary_authority_block(demo):
    auth = demo["summary"]["authority"]
    assert auth["does_not_authorize_execution"] is True
    assert auth["does_not_confirm_machine_readiness"] is True
    assert auth["does_not_generate_gcode"] is True


def test_no_gcode_artifact_produced(demo):
    gcode = [p for p in demo["ws"].rglob("*") if p.suffix.lower() in {".nc", ".gcode", ".tap", ".ngc"}]
    assert gcode == []


# ---------------------------------------------------------------------------
# Source immutability
# ---------------------------------------------------------------------------

def test_source_examples_not_mutated(demo):
    assert demo["before"] == demo["after"]


# ---------------------------------------------------------------------------
# Failure propagation
# ---------------------------------------------------------------------------

def test_nonzero_child_aborts_demo(tmp_path):
    bad = tmp_path / "bad_ltb.json"
    bad.write_text('{"not": "a valid ltb output"}', encoding="utf-8")
    ws = tmp_path / "ws"
    proc = run_demo("--input", str(bad), "--workspace", str(ws), "--keep", "--quiet")
    assert proc.returncode == 1
    summary = json.loads((ws / "demo_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert len(summary["steps"]) < len(EXPECTED_STEPS)  # halted early
    assert summary["steps"][-1]["status"] == "failed"
    assert "artifacts" not in summary  # a failed run advertises no artifacts


# ---------------------------------------------------------------------------
# Workspace lifecycle
# ---------------------------------------------------------------------------

def test_default_run_cleans_temp_workspace():
    proc = run_demo()  # no --workspace, no --keep
    assert proc.returncode == 0, proc.stderr
    m = re.search(r"workspace:\s*(.+)", proc.stdout)
    assert m, proc.stdout
    assert not Path(m.group(1).strip()).exists()  # cleaned up


def test_keep_preserves_workspace(demo):
    assert demo["ws"].exists()
    assert (demo["ws"] / "demo_summary.json").exists()


# ---------------------------------------------------------------------------
# Output modes
# ---------------------------------------------------------------------------

def test_quiet_suppresses_progress(tmp_path):
    proc = run_demo("--workspace", str(tmp_path / "ws"), "--keep", "--quiet")
    assert proc.returncode == 0, proc.stderr
    assert "[PASSED]" not in proc.stdout


def test_json_emits_machine_readable_summary(tmp_path):
    proc = run_demo("--workspace", str(tmp_path / "ws"), "--keep", "--quiet", "--json")
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout)
    assert summary["record_type"] == "cam_assist_demo_summary"
    assert summary["status"] == "passed"
