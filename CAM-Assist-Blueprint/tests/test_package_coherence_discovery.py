"""CAM-A28 conventional discovery."""

from __future__ import annotations

import sys
from pathlib import Path

from package_coherence_fixtures import make_package, write_sidecar_set

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _shared.package_coherence import (  # noqa: E402
    ARTIFACT_ORDER,
    audit_package_coherence,
    discover_package_artifacts,
)
from _shared.package_discovery import (  # noqa: E402
    conventional_annotations_path,
    conventional_handoff_path,
    conventional_request_path,
    conventional_traceability_path,
    is_examples_package,
    resolve_traceability,
)
import _shared.package_discovery as discovery_module  # noqa: E402


def test_importing_discovery_has_no_cli_side_effects(capsys) -> None:
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert callable(discovery_module.resolve_traceability)
    assert callable(discovery_module.resolve_bundle)
    assert "argparse" not in discovery_module.__doc__.lower()


def test_examples_layout_is_detected() -> None:
    example = REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example"
    assert is_examples_package(example)
    assert not is_examples_package(REPO_ROOT / "elsewhere" / "pkg")


def test_conventional_paths_for_plain_package(tmp_path: Path) -> None:
    package = make_package(tmp_path, name="pkg")
    assert conventional_traceability_path(package, "_risk.json") == (
        tmp_path / "traceability" / "pkg_risk.json"
    )
    assert conventional_handoff_path(package) == (
        tmp_path / "production_shop" / "pkg_handoff.json"
    )
    assert conventional_request_path(package) == (
        tmp_path / "creation_studio" / "pkg_request.json"
    )
    assert conventional_annotations_path(package) == (
        tmp_path / "review_annotations" / "pkg_annotations.json"
    )


def test_conventional_paths_for_examples_layout(tmp_path: Path) -> None:
    examples = tmp_path / "examples"
    package = make_package(examples / "packages", name="demo")
    assert is_examples_package(package)
    assert conventional_traceability_path(package, "_bundle.json") == (
        examples / "traceability" / "demo_bundle.json"
    )
    assert conventional_handoff_path(package) == (
        examples / "production_shop" / "demo_handoff.json"
    )


def test_discovery_order_is_stable(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "luthiers-toolbox:vcarve:test-001")
    manifest = {"strategy_file": "strategy.json", "review_packet_file": "review_packet.md"}
    discovered = discover_package_artifacts(package, manifest)
    assert list(discovered) == ARTIFACT_ORDER
    result = audit_package_coherence(package)
    assert list(result.artifacts) == ARTIFACT_ORDER


def test_absent_optional_sidecars_are_not_present(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    resolved = resolve_traceability(package)
    assert resolved["assumptions"] == {"present": False, "path": None}
    assert resolved["risk_assessment"]["present"] is False


def test_capability_profile_is_not_in_a28_inventory(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    result = audit_package_coherence(package)
    assert "capability_profile" not in result.artifacts
    assert "creation_studio_capability_map" not in result.artifacts
