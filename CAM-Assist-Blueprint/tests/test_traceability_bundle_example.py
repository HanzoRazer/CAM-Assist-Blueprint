"""
Phase 5 tests for CAM-A19 Traceability Bundle — the committed example.

Locks in the example bundle as a witness of the real convention path:
- it exists at the conventional location
- it was assembled by auto-discovery (all five known slots are present)
- it passes structural validation
- it passes --check-references with no warnings (every reference resolves)

This proves the example demonstrates the actual create -> discover -> validate
path, not a hand-authored special case.
"""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_traceability_bundle.py"
EXAMPLE_BUNDLE = REPO_ROOT / "examples" / "traceability" / "ltb_vcarve_synthetic_example_bundle.json"

EXPECTED_SLOTS = {
    "assumptions_file",
    "risk_file",
    "decision_record_file",
    "lineage_file",
    "annotations_file",
}


def run_validator(*args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(VALIDATE_SCRIPT)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_example_bundle_exists():
    assert EXAMPLE_BUNDLE.exists(), f"missing example bundle: {EXAMPLE_BUNDLE}"


def test_example_bundle_has_all_discovered_slots():
    data = json.loads(EXAMPLE_BUNDLE.read_text(encoding="utf-8"))
    assert set(data["bundle_contents"].keys()) == EXPECTED_SLOTS


def test_example_bundle_passes_structural_validation():
    code, out, err = run_validator(EXAMPLE_BUNDLE)
    assert code == 0, err + out


def test_example_bundle_passes_check_references_without_warnings():
    code, out, err = run_validator(EXAMPLE_BUNDLE, "--check-references")
    assert code == 0, err + out
    assert "[WARN]" not in out
    assert "does not resolve" not in out
