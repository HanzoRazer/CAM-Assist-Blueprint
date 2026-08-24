"""Builders for CAM-A28 package-coherence tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_STRATEGY = (
    REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example" / "strategy.json"
)
EXAMPLE_PACKAGE = REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example"

TRACE_AUTH = {
    "is_informational": True,
    "does_not_authorize_execution": True,
    "does_not_bypass_human_review": True,
}
HANDOFF_AUTH = {
    "is_informational": True,
    "does_not_authorize_execution": True,
    "does_not_confirm_machine_readiness": True,
    "does_not_bypass_human_review": True,
}
REQUEST_AUTH = {
    "is_informational": True,
    "does_not_authorize_execution": True,
    "does_not_bypass_human_review": True,
    "does_not_confirm_machine_readiness": True,
    "does_not_require_gcode_generation": True,
}


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def make_package(
    parent: Path,
    name: str = "pkg",
    *,
    federated_id: str | None = "luthiers-toolbox:vcarve:test-001",
) -> Path:
    package_dir = parent / name
    package_dir.mkdir(parents=True)
    shutil.copy(EXAMPLE_STRATEGY, package_dir / "strategy.json")
    (package_dir / "review_packet.md").write_text(
        "# Review Packet\n\nSynthetic review packet for coherence tests.\n" * 40,
        encoding="utf-8",
    )
    manifest = {
        "manifest_version": "1.1.0",
        "package_type": "cam_assist_strategy_package",
        "operation_type": "v_carve",
        "strategy_file": "strategy.json",
        "review_packet_file": "review_packet.md",
        "created_at": "2026-06-14T00:00:00Z",
        "cam_assist_version": "0.6.0",
        "authority": {
            "non_execution_declaration": True,
            "execution_authority_claim": False,
            "requires_human_review": True,
        },
        "provenance": {
            "created_by": "coherence-tests",
            "derivation_notes": "Synthetic package for CAM-A28",
        },
    }
    if federated_id is not None:
        manifest["federation"] = {
            "origin_system": "luthiers-toolbox",
            "federated_package_id": federated_id,
        }
    write_json(package_dir / "manifest.json", manifest)
    return package_dir


def identity(package_dir: Path, federated_id: str | None) -> str:
    return federated_id if federated_id else package_dir.name


def assumptions(package_reference: str) -> dict:
    return {
        "record_type": "cam_assist_manufacturing_assumptions",
        "record_version": "1.0.0",
        "package_reference": package_reference,
        "created_at": "2026-06-14T00:00:00Z",
        "assumptions": [{"category": "tooling", "statement": "Tooling is adequate."}],
        "authority": TRACE_AUTH,
    }


def risk(package_reference: str) -> dict:
    return {
        "record_type": "cam_assist_risk_assessment",
        "record_version": "1.0.0",
        "package_reference": package_reference,
        "overall_risk": "low",
        "risks": [
            {"category": "geometry", "severity": "info", "description": "Clearance is adequate."}
        ],
        "authority": TRACE_AUTH,
    }


def decision_record(package_reference: str, **links: str) -> dict:
    data = {
        "record_type": "cam_assist_manufacturing_decision_record",
        "record_version": "1.0.0",
        "package_reference": package_reference,
        "prepared_by": "Engineer",
        "reviewed_by": "Reviewer",
        "decision": "needs_revision",
        "rationale": "Informational review record for coherence tests.",
        "authority": TRACE_AUTH,
    }
    data.update(links)
    return data


def lineage(package_reference: str, related: dict | None = None) -> dict:
    revision: dict = {"revision_id": "rev-1", "summary": "Initial review."}
    if related:
        revision["related_records"] = related
    return {
        "record_type": "cam_assist_revision_lineage",
        "record_version": "1.0.0",
        "package_reference": package_reference,
        "created_at": "2026-06-14T00:00:00Z",
        "revisions": [revision],
        "authority": TRACE_AUTH,
    }


def annotations(package_reference: str) -> dict:
    return {
        "record_type": "cam_assist_review_annotations",
        "record_version": "1.0.0",
        "package_reference": package_reference,
        "created_at": "2026-06-14T00:00:00Z",
        "annotations": [
            {
                "annotation_id": "ann-00000000-0000-4000-8000-000000000001",
                "reviewer": "reviewer",
                "jurisdiction": "design_review",
                "timestamp": "2026-06-14T00:00:00Z",
                "severity": "info",
                "category": "geometry",
                "message": "Clearance is adequate.",
            }
        ],
        "authority": {
            "annotations_are_informational": True,
            "annotations_do_not_approve": True,
        },
    }


def bundle(package_reference: str, contents: dict) -> dict:
    return {
        "record_type": "cam_assist_traceability_bundle",
        "record_version": "1.0.0",
        "package_reference": package_reference,
        "created_at": "2026-06-14T00:00:00Z",
        "bundle_contents": contents,
        "authority": TRACE_AUTH,
    }


def handoff(package_reference: str, contents: dict) -> dict:
    return {
        "record_type": "cam_assist_production_shop_handoff",
        "record_version": "1.0.0",
        "package_reference": package_reference,
        "handoff_direction": "cam_assist_to_production_shop",
        "created_at": "2026-06-14T00:00:00Z",
        "contents": contents,
        "authority": HANDOFF_AUTH,
    }


def request(package_reference: str, contents: dict) -> dict:
    return {
        "record_type": "cam_assist_creation_studio_request",
        "record_version": "1.0.0",
        "package_reference": package_reference,
        "request_direction": "cam_assist_to_creation_studio",
        "requested_capabilities": ["feeds_speeds_recommendation"],
        "contents": contents,
        "authority": REQUEST_AUTH,
    }


def write_traceability(package_dir: Path, name: str, suffix: str, data: dict) -> Path:
    return write_json(package_dir.parent / "traceability" / f"{name}{suffix}", data)


def write_sidecar_set(
    package_dir: Path,
    package_reference: str,
    *,
    with_links: bool = True,
) -> dict[str, Path]:
    name = package_dir.name
    parent = package_dir.parent
    paths = {}
    paths["assumptions"] = write_traceability(
        package_dir, name, "_assumptions.json", assumptions(package_reference)
    )
    paths["risk"] = write_traceability(package_dir, name, "_risk.json", risk(package_reference))
    decision_links = {}
    if with_links:
        decision_links = {
            "assumptions_file": f"{name}_assumptions.json",
            "risk_file": f"{name}_risk.json",
        }
    paths["decision"] = write_traceability(
        package_dir,
        name,
        "_decision_record.json",
        decision_record(package_reference, **decision_links),
    )
    related = {"risk_file": f"{name}_risk.json"} if with_links else None
    paths["lineage"] = write_traceability(
        package_dir, name, "_lineage.json", lineage(package_reference, related)
    )
    paths["annotations"] = write_json(
        parent / "review_annotations" / f"{name}_annotations.json",
        annotations(package_reference),
    )
    paths["bundle"] = write_traceability(
        package_dir,
        name,
        "_bundle.json",
        bundle(
            package_reference,
            {
                "assumptions_file": f"{name}_assumptions.json",
                "risk_file": f"{name}_risk.json",
                "decision_record_file": f"{name}_decision_record.json",
                "lineage_file": f"{name}_lineage.json",
                "annotations_file": f"../review_annotations/{name}_annotations.json",
            },
        ),
    )
    paths["handoff"] = write_json(
        parent / "production_shop" / f"{name}_handoff.json",
        handoff(
            package_reference,
            {
                "package_manifest_file": f"../{name}/manifest.json",
                "strategy_file": f"../{name}/strategy.json",
                "review_packet_file": f"../{name}/review_packet.md",
                "traceability_bundle_file": f"../traceability/{name}_bundle.json",
            },
        ),
    )
    paths["request"] = write_json(
        parent / "creation_studio" / f"{name}_request.json",
        request(
            package_reference,
            {
                "package_manifest_file": f"../{name}/manifest.json",
                "strategy_file": f"../{name}/strategy.json",
                "review_packet_file": f"../{name}/review_packet.md",
                "traceability_bundle_file": f"../traceability/{name}_bundle.json",
                "production_shop_handoff_file": f"../production_shop/{name}_handoff.json",
            },
        ),
    )
    return paths
