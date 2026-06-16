#!/usr/bin/env python3
"""
CAM Assist Revision Lineage Creator

Creates a revision lineage sidecar file for a strategy package, seeded with a
single root revision.

Revision lineage is a package-scoped narrative chain of human-declared revision
checkpoints. It is informational only: it records how manufacturing reasoning
evolved; it does NOT grant execution authority, constitute approval, or version
individual traceability artifacts. Package contents are never modified.

Usage:
    python scripts/create_revision_lineage.py --package <dir> \
        --revised-by "Manufacturing Engineer" \
        --summary "Initial manufacturing strategy review."

    python scripts/create_revision_lineage.py \
        --package examples/packages/ltb_vcarve_synthetic_example \
        --out examples/traceability/revision_lineage_example.json

Exit codes:
    0 — Revision lineage record created successfully
    1 — Validation or argument error
    2 — File/write error
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple


RECORD_TYPE = "cam_assist_revision_lineage"
RECORD_VERSION = "1.0.0"
OUTPUT_SUFFIX = "_lineage.json"
DEFAULT_REVISION_ID = "rev-1"
DEFAULT_SUMMARY = "Initial manufacturing strategy review."


class CreateResult(NamedTuple):
    success: bool
    output_path: Path | None
    error: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_package_reference(package_dir: Path) -> str:
    """Resolve package reference: manifest federated_package_id, else directory name."""
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
    """Conventional output: <parent>/traceability/<package>_lineage.json.

    For examples/packages/<name>, place under examples/traceability/ instead.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        base = parent.parent / "traceability"
    else:
        base = parent / "traceability"
    return base / f"{package_dir.name}{OUTPUT_SUFFIX}"


def create_lineage(
    package_dir: Path,
    revision_id: str = DEFAULT_REVISION_ID,
    summary: str = DEFAULT_SUMMARY,
    revised_by: str | None = None,
    output_path: Path | None = None,
    force: bool = False,
) -> CreateResult:
    if not package_dir.exists():
        return CreateResult(False, None, f"Package directory not found: {package_dir}")
    if not package_dir.is_dir():
        return CreateResult(False, None, f"Path is not a directory: {package_dir}")
    if not revision_id or not revision_id.strip():
        return CreateResult(False, None, "revision_id must be a non-empty string")
    if not summary or not summary.strip():
        return CreateResult(False, None, "summary must be a non-empty string")

    if output_path is None:
        output_path = default_output_path(package_dir)

    if output_path.exists() and not force:
        return CreateResult(
            False, None, f"Output file already exists: {output_path} (use --force to overwrite)"
        )

    revision: dict = {"revision_id": revision_id, "summary": summary}
    if revised_by and revised_by.strip():
        revision["revised_by"] = revised_by.strip()

    record = {
        "record_type": RECORD_TYPE,
        "record_version": RECORD_VERSION,
        "package_reference": resolve_package_reference(package_dir),
        "created_at": utc_now(),
        "revisions": [revision],
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
            f.write("\n")
    except OSError as e:
        return CreateResult(False, None, f"Failed to write lineage: {e}")

    return CreateResult(True, output_path, None)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create CAM Assist revision lineage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--package", type=Path, required=True, help="Path to the strategy package directory")
    parser.add_argument("--revision-id", type=str, default=DEFAULT_REVISION_ID, help=f"Root revision id (default: {DEFAULT_REVISION_ID})")
    parser.add_argument("--summary", type=str, default=DEFAULT_SUMMARY, help="Summary of the root revision")
    parser.add_argument("--revised-by", type=str, default=None, help="Optional informational identifier of who made the revision")
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: traceability/<package>_lineage.json)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing lineage file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output the path on success")

    args = parser.parse_args()

    result = create_lineage(
        package_dir=args.package,
        revision_id=args.revision_id,
        summary=args.summary,
        revised_by=args.revised_by,
        output_path=args.out,
        force=args.force,
    )

    if result.success:
        if args.quiet:
            print(str(result.output_path))
        else:
            print(f"Revision lineage created: {result.output_path}")
            print()
            print("Note: Revision lineage is a package-scoped narrative chain, informational only.")
            print("It does not grant execution authority, constitute approval, or version artifacts.")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
