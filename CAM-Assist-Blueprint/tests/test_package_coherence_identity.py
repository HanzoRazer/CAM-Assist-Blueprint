"""CAM-A28 package-reference comparisons."""

from __future__ import annotations

import sys
from pathlib import Path

from package_coherence_fixtures import (
    annotations,
    assumptions,
    handoff,
    make_package,
    request,
    write_json,
    write_sidecar_set,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _shared.package_coherence import (  # noqa: E402
    CODE_IDENTITY_UNAVAILABLE,
    CODE_PACKAGE_REFERENCE_MISMATCH,
    audit_package_coherence,
)


def test_matching_sidecar_identity_passes(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "luthiers-toolbox:vcarve:test-001")
    result = audit_package_coherence(package)
    assert not any(
        finding.code == CODE_PACKAGE_REFERENCE_MISMATCH for finding in result.findings
    )


def test_directory_name_identity_when_unfederated(tmp_path: Path) -> None:
    package = make_package(tmp_path, name="plain_pkg", federated_id=None)
    write_json(
        tmp_path / "traceability" / "plain_pkg_assumptions.json",
        assumptions("plain_pkg"),
    )
    result = audit_package_coherence(package)
    assert result.package_reference == "plain_pkg"
    assert not any(
        finding.code == CODE_PACKAGE_REFERENCE_MISMATCH for finding in result.findings
    )


def test_handoff_and_request_identity_mismatch(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "luthiers-toolbox:vcarve:test-001")
    write_json(
        tmp_path / "production_shop" / f"{package.name}_handoff.json",
        handoff(
            "other-package",
            {
                "package_manifest_file": f"../{package.name}/manifest.json",
                "strategy_file": f"../{package.name}/strategy.json",
                "review_packet_file": f"../{package.name}/review_packet.md",
                "traceability_bundle_file": f"../traceability/{package.name}_bundle.json",
            },
        ),
    )
    write_json(
        tmp_path / "creation_studio" / f"{package.name}_request.json",
        request(
            "other-request",
            {
                "package_manifest_file": f"../{package.name}/manifest.json",
                "strategy_file": f"../{package.name}/strategy.json",
                "review_packet_file": f"../{package.name}/review_packet.md",
                "traceability_bundle_file": f"../traceability/{package.name}_bundle.json",
                "production_shop_handoff_file": f"../production_shop/{package.name}_handoff.json",
            },
        ),
    )
    result = audit_package_coherence(package)
    artifacts = {
        finding.artifact
        for finding in result.findings
        if finding.code == CODE_PACKAGE_REFERENCE_MISMATCH
    }
    assert "production_shop_handoff" in artifacts
    assert "creation_studio_request" in artifacts


def test_identity_unavailable_when_field_missing_after_valid_structure(
    tmp_path: Path, monkeypatch
) -> None:
    """If comparison is expected but the field is absent, warn — do not invent it."""
    package = make_package(tmp_path)
    path = tmp_path / "review_annotations" / f"{package.name}_annotations.json"
    write_json(path, annotations("luthiers-toolbox:vcarve:test-001"))
    from _shared import package_coherence as shared

    original = shared.extract_package_reference

    def hide_reference(data: dict):
        if data.get("record_type") == "cam_assist_review_annotations":
            return None
        return original(data)

    monkeypatch.setattr(shared, "extract_package_reference", hide_reference)
    result = shared.audit_package_coherence(package)
    assert any(
        finding.code == CODE_IDENTITY_UNAVAILABLE and finding.artifact == "annotations"
        for finding in result.findings
    )
