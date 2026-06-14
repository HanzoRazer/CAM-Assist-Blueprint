#!/usr/bin/env python3
"""
CAM Assist Manufacturing Assumptions Creator

Creates a manufacturing assumptions sidecar file for a strategy package.

Assumptions are informational only. They record the reasoning that influenced a
manufacturing decision; they do not grant execution authority or constitute approval.
Package contents are never modified.

Usage:
    python scripts/create_manufacturing_assumptions.py --package <dir> \
        --assumption tooling "Tool rigidity is adequate for selected depth of cut." \
        --assumption material "Material certification supplied by customer."

    python scripts/create_manufacturing_assumptions.py \
        --package examples/packages/ltb_vcarve_synthetic_example \
        --assumption tooling "Tool rigidity is adequate for selected depth of cut." \
        --out examples/traceability/manufacturing_assumptions_example.json

Exit codes:
    0 — Assumptions record created successfully
    1 — Validation or argument error
    2 — File/write error
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple


RECORD_TYPE = "cam_assist_manufacturing_assumptions"
RECORD_VERSION = "1.0.0"
OUTPUT_SUFFIX = "_assumptions.json"


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
    """Conventional output: <parent>/traceability/<package>_assumptions.json.

    For examples/packages/<name>, place under examples/traceability/ instead.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        base = parent.parent / "traceability"
    else:
        base = parent / "traceability"
    return base / f"{package_dir.name}{OUTPUT_SUFFIX}"


def create_assumptions(
    package_dir: Path,
    assumptions: list[dict],
    output_path: Path | None = None,
    force: bool = False,
) -> CreateResult:
    if not package_dir.exists():
        return CreateResult(False, None, f"Package directory not found: {package_dir}")
    if not package_dir.is_dir():
        return CreateResult(False, None, f"Path is not a directory: {package_dir}")
    if not assumptions:
        return CreateResult(False, None, "At least one --assumption is required")

    if output_path is None:
        output_path = default_output_path(package_dir)

    if output_path.exists() and not force:
        return CreateResult(
            False, None, f"Output file already exists: {output_path} (use --force to overwrite)"
        )

    record = {
        "record_type": RECORD_TYPE,
        "record_version": RECORD_VERSION,
        "package_reference": resolve_package_reference(package_dir),
        "created_at": utc_now(),
        "assumptions": assumptions,
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
        return CreateResult(False, None, f"Failed to write assumptions: {e}")

    return CreateResult(True, output_path, None)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create CAM Assist manufacturing assumptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--package", type=Path, required=True, help="Path to the strategy package directory")
    parser.add_argument(
        "--assumption",
        nargs=2,
        action="append",
        metavar=("CATEGORY", "STATEMENT"),
        dest="assumptions",
        help="An assumption as CATEGORY STATEMENT (repeatable)",
    )
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: traceability/<package>_assumptions.json)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing assumptions file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output the path on success")

    args = parser.parse_args()

    assumptions = [{"category": cat, "statement": stmt} for cat, stmt in (args.assumptions or [])]

    result = create_assumptions(
        package_dir=args.package,
        assumptions=assumptions,
        output_path=args.out,
        force=args.force,
    )

    if result.success:
        if args.quiet:
            print(str(result.output_path))
        else:
            print(f"Manufacturing assumptions created: {result.output_path}")
            print()
            print("Note: Assumptions are informational only.")
            print("They do not grant execution authority or constitute approval.")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
