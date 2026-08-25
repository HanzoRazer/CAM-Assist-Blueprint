"""CAM-A28 against the committed example ecosystem.

After CAM-A29 fixture correction, the canonical example is identity-coherent
and its declared traceability references resolve declaring-file-relative.
CAM-A28 still reports repo-root-style strings as MISSING_REFERENCE; this
suite requires the committed example not to use that form.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example"
SCRIPT = REPO_ROOT / "scripts" / "audit_package_coherence.py"
EXPECTED_IDENTITY = "luthiers-toolbox:vcarve:les-paul-custom-2024"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--package", str(EXAMPLE), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_example_audit_has_no_reference_path_incoherence() -> None:
    result = _run("--json")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["package"]["package_reference"] == EXPECTED_IDENTITY
    assert payload["summary"]["errors"] == 0
    assert payload["findings"] == []

    missing = [
        (finding["artifact"], finding["slot"])
        for finding in payload["findings"]
        if finding["code"] == "MISSING_REFERENCE"
    ]
    assert ("decision_record", "assumptions_file") not in missing
    assert ("decision_record", "risk_file") not in missing
    assert ("revision_lineage", "revisions[1].related_records.risk_file") not in missing

    identity_mismatches = [
        finding["artifact"]
        for finding in payload["findings"]
        if finding["code"] == "PACKAGE_REFERENCE_MISMATCH"
    ]
    assert identity_mismatches == []


def test_example_strict_mode_exits_0_with_identical_json() -> None:
    default = _run("--json")
    strict = _run("--json", "--fail-on-errors")
    assert default.returncode == 0
    assert strict.returncode == 0
    assert default.stdout == strict.stdout


def test_example_artifacts_are_not_mutated() -> None:
    files = [
        EXAMPLE / "manifest.json",
        EXAMPLE / "strategy.json",
        EXAMPLE / "review_packet.md",
        REPO_ROOT / "examples" / "traceability" / "ltb_vcarve_synthetic_example_decision_record.json",
        REPO_ROOT / "examples" / "traceability" / "ltb_vcarve_synthetic_example_lineage.json",
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    result = _run("--json")
    assert result.returncode == 0
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    assert before == after
