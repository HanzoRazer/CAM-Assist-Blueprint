#!/usr/bin/env python3
"""
CAM Assist Traceability Bundle Creator

Creates a traceability bundle sidecar for a strategy package. By default it
auto-discovers the package's traceability sidecars at their conventional
locations and records a reference to each one found, as a path relative to the
bundle's output directory. Absent sidecars are simply omitted (missing sidecars
are allowed).

A traceability bundle is a portable, reference-only navigational index. The
referenced sidecars remain authoritative; the bundle does not own, copy, cache,
or mutate them, and it never modifies the source package. It is informational
only: it does not grant execution authority, constitute approval, or enforce
workflow.

Conventional discovery locations (mirroring the inspector):
    traceability/<package>_assumptions.json       -> assumptions_file
    traceability/<package>_risk.json              -> risk_file
    traceability/<package>_decision_record.json   -> decision_record_file
    traceability/<package>_lineage.json           -> lineage_file
    review_annotations/<package>_annotations.json -> annotations_file

(For examples/packages/<name>, the traceability/ and review_annotations/ roots
live under examples/, exactly as the other creators resolve them.)

Usage:
    python scripts/create_traceability_bundle.py --package <dir>
    python scripts/create_traceability_bundle.py --package <dir> --empty
    python scripts/create_traceability_bundle.py \
        --package examples/packages/ltb_vcarve_synthetic_example \
        --out examples/traceability/ltb_vcarve_synthetic_example_bundle.json

Exit codes:
    0 — Traceability bundle created successfully
    1 — Validation or argument error
    2 — File/write error
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple


RECORD_TYPE = "cam_assist_traceability_bundle"
RECORD_VERSION = "1.0.0"
OUTPUT_SUFFIX = "_bundle.json"

# slot -> (sub-root, filename suffix). sub-root is the directory under the
# conventional base where that sidecar kind lives.
DISCOVERY_MAP = [
    ("assumptions_file", "traceability", "_assumptions.json"),
    ("risk_file", "traceability", "_risk.json"),
    ("decision_record_file", "traceability", "_decision_record.json"),
    ("lineage_file", "traceability", "_lineage.json"),
    ("annotations_file", "review_annotations", "_annotations.json"),
]


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


def conventional_base(package_dir: Path, sub_root: str) -> Path:
    """Conventional root for a sidecar kind.

    For examples/packages/<name>, the sidecar roots live under examples/.
    Otherwise they live beside the package directory.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        return parent.parent / sub_root
    return parent / sub_root


def discover_contents(package_dir: Path, output_dir: Path) -> dict:
    """Scan conventional sidecar locations and build reference entries.

    Each discovered file is recorded as a path relative to output_dir, using
    forward slashes for portability. Absent sidecars are omitted.
    """
    contents: dict = {}
    for slot, sub_root, suffix in DISCOVERY_MAP:
        candidate = conventional_base(package_dir, sub_root) / f"{package_dir.name}{suffix}"
        if candidate.exists():
            rel = os.path.relpath(candidate, start=output_dir)
            contents[slot] = Path(rel).as_posix()
    return contents


def default_output_path(package_dir: Path) -> Path:
    """Conventional output: <traceability_base>/<package>_bundle.json."""
    return conventional_base(package_dir, "traceability") / f"{package_dir.name}{OUTPUT_SUFFIX}"


def create_bundle(
    package_dir: Path,
    output_path: Path | None = None,
    empty: bool = False,
    force: bool = False,
) -> CreateResult:
    if not package_dir.exists():
        return CreateResult(False, None, f"Package directory not found: {package_dir}")
    if not package_dir.is_dir():
        return CreateResult(False, None, f"Path is not a directory: {package_dir}")

    if output_path is None:
        output_path = default_output_path(package_dir)

    if output_path.exists() and not force:
        return CreateResult(
            False, None, f"Output file already exists: {output_path} (use --force to overwrite)"
        )

    if empty:
        bundle_contents: dict = {}
    else:
        bundle_contents = discover_contents(package_dir, output_path.parent)

    record = {
        "record_type": RECORD_TYPE,
        "record_version": RECORD_VERSION,
        "package_reference": resolve_package_reference(package_dir),
        "created_at": utc_now(),
        "bundle_contents": bundle_contents,
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
        return CreateResult(False, None, f"Failed to write bundle: {e}")

    return CreateResult(True, output_path, None)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create CAM Assist traceability bundle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--package", type=Path, required=True, help="Path to the strategy package directory")
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: traceability/<package>_bundle.json)")
    parser.add_argument("--empty", action="store_true", help="Seed an empty bundle_contents without scanning for sidecars")
    parser.add_argument("--force", action="store_true", help="Overwrite existing bundle file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output the path on success")

    args = parser.parse_args()

    result = create_bundle(
        package_dir=args.package,
        output_path=args.out,
        empty=args.empty,
        force=args.force,
    )

    if result.success:
        if args.quiet:
            print(str(result.output_path))
        else:
            print(f"Traceability bundle created: {result.output_path}")
            print()
            print("Note: A traceability bundle is a reference-only navigational index.")
            print("The referenced sidecars remain authoritative. It does not grant")
            print("execution authority, constitute approval, or modify the package.")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
