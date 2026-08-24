"""Cross-artifact guard for CAM-A29 canonical traceability references.

Writers, the shared resolver, committed fixtures, and CAM-A28 must agree:

    resolve_declared_reference(output, relative_reference(output, target))
        == normalized target
"""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _shared.artifact_references import (  # noqa: E402
    relative_reference,
    resolve_declared_reference,
)
from _shared.package_coherence import (  # noqa: E402
    CODE_MISSING_REFERENCE,
    audit_package_coherence,
)

EXAMPLE_PACKAGE = REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example"
DECISION = (
    REPO_ROOT / "examples" / "traceability" / "ltb_vcarve_synthetic_example_decision_record.json"
)
LINEAGE = REPO_ROOT / "examples" / "traceability" / "ltb_vcarve_synthetic_example_lineage.json"
BUNDLE = REPO_ROOT / "examples" / "traceability" / "ltb_vcarve_synthetic_example_bundle.json"
HANDOFF = (
    REPO_ROOT / "examples" / "production_shop" / "ltb_vcarve_synthetic_example_handoff.json"
)
REQUEST = (
    REPO_ROOT / "examples" / "creation_studio" / "ltb_vcarve_synthetic_example_request.json"
)
ASSUMPTIONS = (
    REPO_ROOT / "examples" / "traceability" / "ltb_vcarve_synthetic_example_assumptions.json"
)
RISK = REPO_ROOT / "examples" / "traceability" / "ltb_vcarve_synthetic_example_risk.json"
CREATE_MDR = SCRIPTS / "create_manufacturing_decision_record.py"
VALIDATE_MDR = SCRIPTS / "validate_manufacturing_decision_record.py"
VALIDATE_LINEAGE = SCRIPTS / "validate_revision_lineage.py"
VALIDATE_BUNDLE = SCRIPTS / "validate_traceability_bundle.py"
VALIDATE_HANDOFF = SCRIPTS / "validate_production_shop_handoff.py"
AUDIT = SCRIPTS / "audit_package_coherence.py"

EXPECTED_IDENTITY = "luthiers-toolbox:vcarve:les-paul-custom-2024"


def _norm(path: Path) -> Path:
    return Path(posixpath.normpath(Path(path).as_posix()))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *[str(a) for a in args]],
        cwd=str(cwd) if cwd else str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def test_committed_decision_record_paths_are_canonical() -> None:
    data = _load(DECISION)
    assert data["assumptions_file"] == "ltb_vcarve_synthetic_example_assumptions.json"
    assert data["risk_file"] == "ltb_vcarve_synthetic_example_risk.json"
    assert "\\" not in data["assumptions_file"]
    assert "\\" not in data["risk_file"]
    assert not data["assumptions_file"].startswith("examples/")
    assert resolve_declared_reference(DECISION, data["assumptions_file"]) == _norm(ASSUMPTIONS)
    assert resolve_declared_reference(DECISION, data["risk_file"]) == _norm(RISK)
    assert resolve_declared_reference(DECISION, data["assumptions_file"]).exists()
    assert resolve_declared_reference(DECISION, data["risk_file"]).exists()


def test_committed_lineage_related_record_is_canonical() -> None:
    data = _load(LINEAGE)
    related = data["revisions"][1]["related_records"]
    assert related["risk_file"] == "ltb_vcarve_synthetic_example_risk.json"
    assert not related["risk_file"].startswith("examples/")
    assert resolve_declared_reference(LINEAGE, related["risk_file"]) == _norm(RISK)
    assert resolve_declared_reference(LINEAGE, related["risk_file"]).exists()


def test_fixture_correction_did_not_change_semantic_fields() -> None:
    decision = _load(DECISION)
    assert decision["package_reference"] == EXPECTED_IDENTITY
    assert decision["decision"] == "approved"
    assert decision["prepared_by"] == "Manufacturing Engineer"
    assert decision["reviewed_by"] == "Senior Reviewer"
    assert decision["rationale"] == (
        "Tooling, fixturing, and material assumptions reviewed against identified risks."
    )
    assert decision["authority"] == {
        "is_informational": True,
        "does_not_authorize_execution": True,
        "does_not_bypass_human_review": True,
    }
    lineage = _load(LINEAGE)
    assert lineage["package_reference"] == EXPECTED_IDENTITY
    assert lineage["revisions"][0]["summary"] == "Initial manufacturing strategy review."
    assert lineage["revisions"][1]["summary"] == (
        "Reduced depth of cut after thin-wall chatter risk flagged."
    )
    assert lineage["revisions"][1]["supersedes"] == "rev-1"
    assert lineage["authority"]["does_not_authorize_execution"] is True


def test_committed_bundle_handoff_and_request_already_canonical() -> None:
    bundle = _load(BUNDLE)
    assert bundle["bundle_contents"]["assumptions_file"] == (
        "ltb_vcarve_synthetic_example_assumptions.json"
    )
    assert bundle["bundle_contents"]["annotations_file"] == (
        "../review_annotations/ltb_vcarve_synthetic_example_annotations.json"
    )
    annotations = resolve_declared_reference(
        BUNDLE, bundle["bundle_contents"]["annotations_file"]
    )
    assert annotations.exists()
    handoff = _load(HANDOFF)
    for value in handoff["contents"].values():
        assert not str(value).startswith("examples/")
        assert "\\" not in value
        assert resolve_declared_reference(HANDOFF, value).exists()
    request = _load(REQUEST)
    for value in request["contents"].values():
        assert not str(value).startswith("examples/")
        assert "\\" not in value
        assert resolve_declared_reference(REQUEST, value).exists()


def test_a28_example_has_no_missing_reference_path_debt() -> None:
    result = audit_package_coherence(EXAMPLE_PACKAGE)
    missing = [
        (finding.artifact, finding.slot)
        for finding in result.findings
        if finding.code == CODE_MISSING_REFERENCE
    ]
    assert missing == []
    assert result.error_count == 0


def test_creator_emits_canonical_same_directory_and_sibling_paths(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "manifest.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "traceability" / "decision.json"
    assumptions = tmp_path / "traceability" / "assumptions.json"
    risk = tmp_path / "review_annotations" / "risk.json"
    out.parent.mkdir()
    risk.parent.mkdir()
    assumptions.write_text("{}\n", encoding="utf-8")
    risk.write_text("{}\n", encoding="utf-8")
    created = _run(
        CREATE_MDR,
        "--package",
        package,
        "--decision",
        "approved",
        "--prepared-by",
        "ME",
        "--reviewed-by",
        "SR",
        "--rationale",
        "ok",
        "--assumptions-file",
        assumptions,
        "--risk-file",
        risk,
        "--out",
        out,
    )
    assert created.returncode == 0, created.stderr
    data = _load(out)
    assert data["assumptions_file"] == "assumptions.json"
    assert data["risk_file"] == "../review_annotations/risk.json"
    assert resolve_declared_reference(out, data["assumptions_file"]) == _norm(assumptions)
    assert resolve_declared_reference(out, data["risk_file"]) == _norm(risk)
    validated = _run(VALIDATE_MDR, out)
    assert validated.returncode == 0


def test_missing_target_remains_missing(tmp_path: Path) -> None:
    declaring = tmp_path / "decision.json"
    declaring.write_text("{}\n", encoding="utf-8")
    resolved = resolve_declared_reference(declaring, "does_not_exist.json")
    assert not resolved.exists()

    from package_coherence_fixtures import decision_record, make_package, write_traceability

    package = make_package(tmp_path)
    write_traceability(
        package,
        package.name,
        "_decision_record.json",
        decision_record(
            "luthiers-toolbox:vcarve:test-001",
            assumptions_file="does_not_exist.json",
        ),
    )
    result = audit_package_coherence(package)
    assert any(
        finding.code == CODE_MISSING_REFERENCE and finding.slot == "assumptions_file"
        for finding in result.findings
    )


def test_malformed_path_value_rejected_by_owning_validator(tmp_path: Path) -> None:
    record = {
        "record_type": "cam_assist_manufacturing_decision_record",
        "record_version": "1.0.0",
        "package_reference": "pkg",
        "prepared_by": "ME",
        "reviewed_by": "SR",
        "decision": "approved",
        "rationale": "ok",
        "assumptions_file": 123,
    }
    path = tmp_path / "d.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    result = _run(VALIDATE_MDR, path)
    assert result.returncode == 1
    assert "assumptions_file" in result.stderr

    lineage = {
        "record_type": "cam_assist_revision_lineage",
        "record_version": "1.0.0",
        "package_reference": "pkg",
        "revisions": [
            {
                "revision_id": "rev-1",
                "summary": "root",
                "related_records": {"risk_file": ""},
            }
        ],
    }
    lineage_path = tmp_path / "l.json"
    lineage_path.write_text(json.dumps(lineage), encoding="utf-8")
    # Blank string is still a string; structural validator accepts shape.
    # Completeness/A28 must not invent a file. The shared resolver is not a
    # validator replacement.
    structural = _run(VALIDATE_LINEAGE, lineage_path)
    assert structural.returncode == 0


def test_bundle_completeness_independent_of_cwd(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "traceability"
    other = tmp_path / "unrelated"
    bundle_dir.mkdir()
    other.mkdir()
    (bundle_dir / "risk.json").write_text("{}", encoding="utf-8")
    bundle = {
        "record_type": "cam_assist_traceability_bundle",
        "record_version": "1.0.0",
        "package_reference": "pkg",
        "bundle_contents": {"risk_file": "risk.json"},
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
        },
    }
    path = bundle_dir / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    first = _run(VALIDATE_BUNDLE, path, "--check-references", cwd=REPO_ROOT)
    second = _run(VALIDATE_BUNDLE, path, "--check-references", cwd=other)
    assert first.returncode == 0
    assert second.returncode == 0
    assert "does not resolve" not in first.stdout
    assert first.stdout == second.stdout


def test_validators_and_a28_do_not_mutate_example() -> None:
    files = [DECISION, LINEAGE, BUNDLE, HANDOFF, REQUEST]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    assert _run(VALIDATE_MDR, DECISION).returncode == 0
    assert _run(VALIDATE_LINEAGE, LINEAGE).returncode == 0
    assert _run(VALIDATE_BUNDLE, BUNDLE, "--check-references").returncode == 0
    assert _run(VALIDATE_HANDOFF, HANDOFF, "--check-references").returncode == 0
    audit = _run(AUDIT, "--package", EXAMPLE_PACKAGE, "--json", "--fail-on-errors")
    assert audit.returncode == 0, audit.stdout + audit.stderr
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    assert before == after


def test_repo_root_style_string_still_fails_from_example_directory() -> None:
    malformed = "examples/traceability/ltb_vcarve_synthetic_example_risk.json"
    resolved = resolve_declared_reference(DECISION, malformed)
    assert resolved != _norm(RISK)
    assert not resolved.exists()
    assert RISK.exists()
