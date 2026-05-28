#!/usr/bin/env python3
"""
CAM Assist Review Annotations Creator

Creates or appends to review annotation files for federated manufacturing review.

Annotations are informational only. They do not grant execution authority.
This tool is a federal courier — it transports reviewer observations without
creating or transferring manufacturing authority.

Usage:
    python scripts/create_review_annotations.py --package <dir> --reviewer <name> \
        --severity info --category tooling --message "Check bit diameter"

    python scripts/create_review_annotations.py --package examples/packages/ltb_vcarve_synthetic_example \
        --reviewer "acoustic-review-agent" --severity warning --category geometry \
        --message "V-carve depth exceeds typical range" --recommended-action "Verify with luthier"

Exit codes:
    0 — Annotation created successfully
    1 — Validation or argument error
    2 — File/write error
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple


VALID_SEVERITIES = ["info", "warning", "concern", "blocking"]
RECORD_VERSION = "1.0.0"


class AnnotationResult(NamedTuple):
    success: bool
    output_path: Path | None
    error: str | None


def generate_annotation_id() -> str:
    """Generate a unique annotation ID in the format ann-<uuid>."""
    return f"ann-{uuid.uuid4()}"


def resolve_package_reference(package_dir: Path) -> str:
    """
    Resolve package reference from package directory.

    Checks for federated_package_id in manifest, falls back to directory name.
    """
    manifest_path = package_dir / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            federation = manifest.get("federation", {})
            if federation.get("federated_package_id"):
                return federation["federated_package_id"]
        except (json.JSONDecodeError, OSError):
            pass

    return package_dir.name


def default_output_path(package_dir: Path) -> Path:
    """
    Determine default output path for annotations.

    Convention: annotations/<package_name>_annotations.json in parent directory.
    """
    parent = package_dir.parent
    annotations_dir = parent / "review_annotations"
    return annotations_dir / f"{package_dir.name}_annotations.json"


def load_existing_annotations(path: Path) -> dict | None:
    """Load existing annotations file if it exists."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def create_annotation(
    package_dir: Path,
    reviewer: str,
    severity: str,
    category: str,
    message: str,
    jurisdiction: str | None = None,
    recommended_action: str | None = None,
    output_path: Path | None = None,
    force: bool = False,
) -> AnnotationResult:
    """Create or append a review annotation."""

    # Validate package directory
    if not package_dir.exists():
        return AnnotationResult(
            success=False,
            output_path=None,
            error=f"Package directory not found: {package_dir}",
        )

    if not package_dir.is_dir():
        return AnnotationResult(
            success=False,
            output_path=None,
            error=f"Path is not a directory: {package_dir}",
        )

    # Validate severity
    if severity not in VALID_SEVERITIES:
        return AnnotationResult(
            success=False,
            output_path=None,
            error=f"Invalid severity '{severity}'. Must be one of: {', '.join(VALID_SEVERITIES)}",
        )

    # Resolve output path
    if output_path is None:
        output_path = default_output_path(package_dir)

    # Check for existing file
    existing = load_existing_annotations(output_path)
    if existing is not None and not force:
        # Append mode — verify package_reference matches
        existing_ref = existing.get("package_reference", "")
        new_ref = resolve_package_reference(package_dir)
        if existing_ref != new_ref:
            return AnnotationResult(
                success=False,
                output_path=None,
                error=f"Existing annotations are for '{existing_ref}', not '{new_ref}'. Use --force to overwrite.",
            )

    # Build annotation
    annotation = {
        "annotation_id": generate_annotation_id(),
        "reviewer": reviewer,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "severity": severity,
        "category": category,
        "message": message,
    }

    if jurisdiction:
        annotation["jurisdiction"] = jurisdiction

    if recommended_action:
        annotation["recommended_action"] = recommended_action

    # Build or update annotations file
    if existing is not None and not force:
        # Append to existing
        annotations_data = existing
        annotations_data["annotations"].append(annotation)
    else:
        # Create new
        annotations_data = {
            "record_type": "cam_assist_review_annotations",
            "record_version": RECORD_VERSION,
            "package_reference": resolve_package_reference(package_dir),
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "authority": {
                "annotations_are_informational": True,
            },
            "annotations": [annotation],
        }

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(annotations_data, f, indent=2)
            f.write("\n")
    except OSError as e:
        return AnnotationResult(
            success=False,
            output_path=None,
            error=f"Failed to write annotations: {e}",
        )

    return AnnotationResult(
        success=True,
        output_path=output_path,
        error=None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create CAM Assist review annotations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--package",
        type=Path,
        required=True,
        help="Path to the strategy package directory",
    )
    parser.add_argument(
        "--reviewer",
        type=str,
        required=True,
        help="Reviewer identifier (informational only, no trust validation)",
    )
    parser.add_argument(
        "--severity",
        type=str,
        required=True,
        choices=VALID_SEVERITIES,
        help="Annotation severity level",
    )
    parser.add_argument(
        "--category",
        type=str,
        required=True,
        help="Annotation category (e.g., tooling, geometry, acoustic, safety)",
    )
    parser.add_argument(
        "--message",
        type=str,
        required=True,
        help="Human-readable annotation message",
    )
    parser.add_argument(
        "--jurisdiction",
        type=str,
        default=None,
        help="Optional review jurisdiction (e.g., manufacturing_review, acoustic_review)",
    )
    parser.add_argument(
        "--recommended-action",
        type=str,
        default=None,
        help="Optional recommended action or guidance",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path for annotations file (default: review_annotations/<package>_annotations.json)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing annotations file instead of appending",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output the annotation ID on success",
    )

    args = parser.parse_args()

    result = create_annotation(
        package_dir=args.package,
        reviewer=args.reviewer,
        severity=args.severity,
        category=args.category,
        message=args.message,
        jurisdiction=args.jurisdiction,
        recommended_action=args.recommended_action,
        output_path=args.out,
        force=args.force,
    )

    if result.success:
        if args.quiet:
            # Load and print the annotation ID
            with open(result.output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(data["annotations"][-1]["annotation_id"])
        else:
            print(f"Annotation created: {result.output_path}")
            print()
            print("Note: Annotations are informational only.")
            print("They do not grant execution authority or constitute approval.")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
