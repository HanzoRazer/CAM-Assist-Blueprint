"""CAM-A28 coherence engine — filesystem-light, no CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from package_coherence_fixtures import (
    assumptions,
    make_package,
    write_json,
    write_sidecar_set,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _shared.package_coherence import (  # noqa: E402
    CODE_IDENTITY_UNAVAILABLE,
    CODE_PACKAGE_REFERENCE_MISMATCH,
    CODE_STRUCTURAL_INVALID,
    FORBIDDEN_RESULT_KEYS,
    PackageCoherenceInputError,
    audit_package_coherence,
    expected_package_identity,
    serialize_coherence,
    sort_findings,
    CoherenceFinding,
)


def test_expected_identity_prefers_federated_id(tmp_path: Path) -> None:
    package = make_package(tmp_path, federated_id="luthiers-toolbox:vcarve:test-001")
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    assert expected_package_identity(package, manifest) == "luthiers-toolbox:vcarve:test-001"


def test_expected_identity_falls_back_to_directory_name(tmp_path: Path) -> None:
    package = make_package(tmp_path, name="plain_pkg", federated_id=None)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    assert expected_package_identity(package, manifest) == "plain_pkg"


def test_clean_package_has_no_findings(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "luthiers-toolbox:vcarve:test-001")
    result = audit_package_coherence(package)
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.summary() == {"errors": 0, "warnings": 0, "infos": 0}
    assert all(status.present for status in result.artifacts.values())
    assert all(status.structural == "valid" for status in result.artifacts.values())


def test_optional_absence_is_inventory_only(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    result = audit_package_coherence(package)
    assert result.artifacts["assumptions"].present is False
    assert result.artifacts["assumptions"].path is None
    assert result.error_count == 0
    assert result.findings == []


def test_identity_mismatch_is_an_error(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_json(
        package.parent / "traceability" / f"{package.name}_assumptions.json",
        assumptions("other-package"),
    )
    result = audit_package_coherence(package)
    codes = [finding.code for finding in result.findings]
    assert CODE_PACKAGE_REFERENCE_MISMATCH in codes
    mismatch = next(
        finding
        for finding in result.findings
        if finding.code == CODE_PACKAGE_REFERENCE_MISMATCH
    )
    assert mismatch.severity == "error"
    assert mismatch.artifact == "assumptions"
    assert mismatch.expected == "luthiers-toolbox:vcarve:test-001"
    assert mismatch.actual == "other-package"


def test_multiple_identity_mismatches_all_appear(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "wrong-a")
    result = audit_package_coherence(package)
    mismatches = [
        finding.artifact
        for finding in result.findings
        if finding.code == CODE_PACKAGE_REFERENCE_MISMATCH
    ]
    assert "assumptions" in mismatches
    assert "risk_assessment" in mismatches
    assert len(mismatches) >= 2


def test_structurally_invalid_sidecar_skips_identity(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_json(
        package.parent / "traceability" / f"{package.name}_assumptions.json",
        {"record_type": "cam_assist_manufacturing_assumptions"},
    )
    result = audit_package_coherence(package)
    assert result.artifacts["assumptions"].structural == "invalid"
    assert any(finding.code == CODE_STRUCTURAL_INVALID for finding in result.findings)
    assert not any(
        finding.code == CODE_PACKAGE_REFERENCE_MISMATCH
        and finding.artifact == "assumptions"
        for finding in result.findings
    )


def test_missing_package_directory_is_input_error(tmp_path: Path) -> None:
    with pytest.raises(PackageCoherenceInputError, match="not found"):
        audit_package_coherence(tmp_path / "absent")


def test_missing_manifest_is_input_error(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(PackageCoherenceInputError, match="missing"):
        audit_package_coherence(empty)


def test_invalid_manifest_structure_is_input_error(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    write_json(package / "manifest.json", {"package_type": "nope"})
    with pytest.raises(PackageCoherenceInputError, match="not structurally usable"):
        audit_package_coherence(package)


def test_malformed_manifest_json_is_input_error(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "manifest.json").write_text("{ not json", encoding="utf-8")
    with pytest.raises(PackageCoherenceInputError):
        audit_package_coherence(package)


def test_findings_sort_is_deterministic() -> None:
    findings = [
        CoherenceFinding("REFERENCE_MISMATCH", "error", "risk_assessment", "b", path="z"),
        CoherenceFinding("PACKAGE_REFERENCE_MISMATCH", "error", "assumptions", "a", path="a"),
        CoherenceFinding("IDENTITY_UNAVAILABLE", "warning", "assumptions", "c", path="a"),
    ]
    ordered = sort_findings(findings)
    assert [item.code for item in ordered] == [
        "PACKAGE_REFERENCE_MISMATCH",
        "REFERENCE_MISMATCH",
        "IDENTITY_UNAVAILABLE",
    ]


def test_json_payload_has_no_authority_fields(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    result = audit_package_coherence(package)
    raw = serialize_coherence(result)
    for key in FORBIDDEN_RESULT_KEYS:
        assert key not in raw
    payload = json.loads(raw)
    assert payload["summary"]["errors"] == 0
    assert "artifacts" in payload
    assert "findings" in payload
