#!/usr/bin/env python3
"""
CAM Assist Production Shop Handoff Creator

Creates a read-only Production Shop handoff manifest from an existing CAM Assist
strategy package. The handoff is a portable, reference-only artifact pointing at
the package's manifest, strategy, review packet, and (when available) its
traceability bundle. Every reference is recorded as a path relative to the
handoff file's own location, forward-slashed for portability.

The handoff is outbound only (CAM Assist -> Production Shop). It records a
`created_at` UTC timestamp for auditability. It does NOT own, copy, cache, or
mutate the referenced files, and it never modifies the source package. It is execution-adjacent, so the non-execution authority block is always
emitted and every flag is true: the handoff is informational, does not authorize
machine execution, does not bypass human review, and does NOT confirm machine
readiness. It introduces no Production Shop runtime dependency.

This is the CREATOR only. It performs no validation beyond discovering its
required inputs, and it does NOT check that referenced files exist (existence is
the opt-in --check-references concern of a later phase). The core three content
references (package manifest, strategy, review packet) are always emitted; the
traceability bundle reference is included only when explicitly supplied or
conventionally discovered.

Discovery:
    package_reference   -> manifest.federation.federated_package_id, else dir name
    package_manifest_file -> <package>/manifest.json
    strategy_file       -> <package>/<manifest.strategy_file>
    review_packet_file  -> <package>/<manifest.review_packet_file>
    traceability_bundle_file:
        --traceability-bundle <path>            (explicit, recorded as-is)
        else traceability/<package>_bundle.json (conventional, if it exists)
        else omitted

(For examples/packages/<name>, the production_shop/ and traceability/ roots live
under examples/, exactly as the other creators resolve their conventional dirs.)

Usage:
    python scripts/create_production_shop_handoff.py --package <dir>
    python scripts/create_production_shop_handoff.py \
        --package examples/packages/ltb_vcarve_synthetic_example \
        --out examples/production_shop/ltb_vcarve_synthetic_example_handoff.json
    python scripts/create_production_shop_handoff.py --package <dir> \
        --traceability-bundle examples/traceability/<package>_bundle.json --force

Exit codes:
    0 — Handoff created successfully
    1 — Argument error (package not found / not a directory, output exists without
        --force, or references that cannot be made relative to the output)
    2 — File/write error (directory creation or write failed)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared.artifact_references import relative_reference


RECORD_TYPE = "cam_assist_production_shop_handoff"
RECORD_VERSION = "1.0.0"
HANDOFF_DIRECTION = "cam_assist_to_production_shop"
OUTPUT_SUFFIX = "_handoff.json"
BUNDLE_SUFFIX = "_bundle.json"

# Conventional filenames within the package, used as fallbacks when the manifest
# does not declare them.
DEFAULT_STRATEGY_FILE = "strategy.json"
DEFAULT_REVIEW_PACKET_FILE = "review_packet.md"

AUTHORITY = {
    "is_informational": True,
    "does_not_authorize_execution": True,
    "does_not_bypass_human_review": True,
    "does_not_confirm_machine_readiness": True,
}


class CreateResult(NamedTuple):
    success: bool
    output_path: Path | None
    error: str | None
    exit_code: int = 0


def utc_now() -> str:
    """Current UTC time as an ISO-8601 timestamp with a 'Z' suffix.

    Mirrors the traceability bundle creator so both outbound artifacts stamp
    their creation time identically.
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_manifest(package_dir: Path) -> dict:
    """Load <package>/manifest.json, or {} if absent/unparseable."""
    manifest_path = package_dir / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def resolve_package_reference(package_dir: Path, manifest: dict) -> str:
    """Package's portable identity: manifest federated_package_id, else dir name."""
    federation = manifest.get("federation", {})
    if isinstance(federation, dict) and federation.get("federated_package_id"):
        return federation["federated_package_id"]
    return package_dir.name


def conventional_base(package_dir: Path, sub_root: str) -> Path:
    """Conventional root for a sibling artifact kind.

    For examples/packages/<name>, the sibling roots live under examples/.
    Otherwise they live beside the package directory.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        return parent.parent / sub_root
    return parent / sub_root


def default_output_path(package_dir: Path) -> Path:
    """Conventional output: <production_shop_base>/<package>_handoff.json."""
    return conventional_base(package_dir, "production_shop") / f"{package_dir.name}{OUTPUT_SUFFIX}"


def conventional_bundle_path(package_dir: Path) -> Path:
    """Conventional traceability bundle: <traceability_base>/<package>_bundle.json."""
    return conventional_base(package_dir, "traceability") / f"{package_dir.name}{BUNDLE_SUFFIX}"


def build_contents(
    package_dir: Path,
    manifest: dict,
    output_file: Path,
    explicit_bundle: Path | None,
) -> dict:
    """Build the contents reference map, all relative to the output file.

    The core three references are always emitted. The traceability bundle is
    included only when explicitly supplied (recorded as-is, no existence check)
    or conventionally discovered (included only if the file exists).
    """
    strategy_name = manifest.get("strategy_file") or DEFAULT_STRATEGY_FILE
    review_packet_name = manifest.get("review_packet_file") or DEFAULT_REVIEW_PACKET_FILE

    contents = {
        "package_manifest_file": relative_reference(output_file, package_dir / "manifest.json"),
        "strategy_file": relative_reference(output_file, package_dir / strategy_name),
        "review_packet_file": relative_reference(output_file, package_dir / review_packet_name),
    }

    if explicit_bundle is not None:
        contents["traceability_bundle_file"] = relative_reference(output_file, explicit_bundle)
    else:
        conventional = conventional_bundle_path(package_dir)
        if conventional.exists():
            contents["traceability_bundle_file"] = relative_reference(output_file, conventional)

    return contents


def create_handoff(
    package_dir: Path,
    output_path: Path | None = None,
    traceability_bundle: Path | None = None,
    force: bool = False,
) -> CreateResult:
    if not package_dir.exists():
        return CreateResult(False, None, f"Package directory not found: {package_dir}", 1)
    if not package_dir.is_dir():
        return CreateResult(False, None, f"Path is not a directory: {package_dir}", 1)

    if output_path is None:
        output_path = default_output_path(package_dir)

    if output_path.exists() and not force:
        return CreateResult(
            False, None,
            f"Output file already exists: {output_path} (use --force to overwrite)", 1,
        )

    manifest = load_manifest(package_dir)

    # References are stored relative to the output file. relative_reference
    # raises ValueError when the two paths share no common anchor — most notably
    # a package and output on different Windows drives — so surface that as a
    # clean argument error rather than an uncaught traceback.
    try:
        contents = build_contents(
            package_dir, manifest, output_path, traceability_bundle
        )
    except ValueError as e:
        return CreateResult(
            False, None,
            f"Cannot compute a relative path from the output location to a "
            f"referenced file (are they on different drives?): {e}", 1,
        )

    record = {
        "record_type": RECORD_TYPE,
        "record_version": RECORD_VERSION,
        "package_reference": resolve_package_reference(package_dir, manifest),
        "handoff_direction": HANDOFF_DIRECTION,
        "created_at": utc_now(),
        "authority": dict(AUTHORITY),
        "contents": contents,
    }

    # Directory creation and the write share the file/write-error class (exit 2).
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
            f.write("\n")
    except OSError as e:
        return CreateResult(False, None, f"Failed to write handoff: {e}", 2)

    return CreateResult(True, output_path, None, 0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create CAM Assist production shop handoff (reference-only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--package", type=Path, required=True, help="Path to the strategy package directory"
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Output path (default: production_shop/<package>_handoff.json)",
    )
    parser.add_argument(
        "--traceability-bundle", type=Path, default=None, dest="traceability_bundle",
        help="Explicit traceability bundle path (overrides conventional discovery)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing handoff file")
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only output the path on success"
    )

    args = parser.parse_args()

    result = create_handoff(
        package_dir=args.package,
        output_path=args.out,
        traceability_bundle=args.traceability_bundle,
        force=args.force,
    )

    if result.success:
        if args.quiet:
            print(str(result.output_path))
        else:
            print(f"Production shop handoff created: {result.output_path}")
            print()
            print("Note: A production shop handoff is a reference-only, outbound artifact.")
            print("The referenced files remain authoritative. It does not authorize")
            print("execution, bypass human review, confirm machine readiness, or modify")
            print("the package.")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
