"""CAM-A28 declared-reference coherence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from package_coherence_fixtures import (
    bundle,
    decision_record,
    make_package,
    risk,
    write_json,
    write_sidecar_set,
    write_traceability,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _shared.package_coherence import (  # noqa: E402
    CODE_MISSING_REFERENCE,
    CODE_REFERENCE_MISMATCH,
    CODE_STRUCTURAL_INVALID,
    audit_package_coherence,
)


def test_explicit_missing_reference_is_an_error(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "luthiers-toolbox:vcarve:test-001", with_links=False)
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
    missing = [
        finding
        for finding in result.findings
        if finding.code == CODE_MISSING_REFERENCE and finding.artifact == "decision_record"
    ]
    assert missing
    assert missing[0].severity == "error"
    assert missing[0].slot == "assumptions_file"


def test_declared_vs_conventional_mismatch(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    ref = "luthiers-toolbox:vcarve:test-001"
    write_sidecar_set(package, ref)
    write_json(tmp_path / "traceability" / "old_risk.json", risk(ref))
    data = json.loads(
        (tmp_path / "traceability" / f"{package.name}_bundle.json").read_text(encoding="utf-8")
    )
    data["bundle_contents"]["risk_file"] = "old_risk.json"
    write_json(tmp_path / "traceability" / f"{package.name}_bundle.json", data)
    result = audit_package_coherence(package)
    mismatch = [
        finding
        for finding in result.findings
        if finding.code == CODE_REFERENCE_MISMATCH and finding.artifact == "traceability_bundle"
    ]
    assert mismatch
    assert mismatch[0].slot == "bundle_contents.risk_file"
    assert mismatch[0].expected == f"../traceability/{package.name}_risk.json"
    assert mismatch[0].actual == "../traceability/old_risk.json"
    assert "old_risk.json" in mismatch[0].message


def test_bundle_consistent_with_discovery(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "luthiers-toolbox:vcarve:test-001")
    result = audit_package_coherence(package)
    assert not any(
        finding.artifact == "traceability_bundle"
        and finding.code in {CODE_MISSING_REFERENCE, CODE_REFERENCE_MISMATCH}
        for finding in result.findings
    )


def test_handoff_wrong_bundle_is_mismatch_or_missing(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "luthiers-toolbox:vcarve:test-001")
    write_json(
        tmp_path / "traceability" / "other_bundle.json",
        bundle("luthiers-toolbox:vcarve:test-001", {}),
    )
    handoff_path = tmp_path / "production_shop" / f"{package.name}_handoff.json"
    data = json.loads(handoff_path.read_text(encoding="utf-8"))
    data["contents"]["traceability_bundle_file"] = "../traceability/other_bundle.json"
    write_json(handoff_path, data)
    result = audit_package_coherence(package)
    assert any(
        finding.artifact == "production_shop_handoff"
        and finding.code == CODE_REFERENCE_MISMATCH
        for finding in result.findings
    )


def test_malformed_sidecar_is_structural_not_reference(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    bad = tmp_path / "traceability" / f"{package.name}_assumptions.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("{ not json", encoding="utf-8")
    result = audit_package_coherence(package)
    assert result.artifacts["assumptions"].structural == "invalid"
    assert any(
        finding.code == CODE_STRUCTURAL_INVALID and finding.artifact == "assumptions"
        for finding in result.findings
    )


def test_repo_root_style_path_does_not_get_a_fallback(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    ref = "luthiers-toolbox:vcarve:test-001"
    write_sidecar_set(package, ref, with_links=False)
    write_traceability(
        package,
        package.name,
        "_decision_record.json",
        decision_record(
            ref,
            assumptions_file="examples/traceability/pkg_assumptions.json",
        ),
    )
    result = audit_package_coherence(package)
    assert any(
        finding.code == CODE_MISSING_REFERENCE
        and finding.artifact == "decision_record"
        and finding.slot == "assumptions_file"
        for finding in result.findings
    )
