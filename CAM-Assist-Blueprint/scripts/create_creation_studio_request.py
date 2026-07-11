#!/usr/bin/env python3
"""
CAM Assist Creation Studio Capability Request Creator

Creates an advisory, reference-only CAM-Creation-Studio capability request from an
existing CAM Assist strategy package. The request is a portable artifact pointing
at the package's manifest, strategy, review packet, and (when available) its
traceability bundle and production shop handoff. Every reference is recorded as a
path relative to the request file's own location, forward-slashed for portability.

The request is outbound only (CAM Assist -> CAM-Creation-Studio) and advisory: it
names requested downstream capabilities but does NOT authorize execution, bypass
human review, confirm machine readiness, require G-code generation, or assert that
CAM-Creation-Studio supports any requested capability. It does NOT own, copy,
cache, or mutate the referenced files, and never modifies the source package.

The request carries NO created_at timestamp: the artifact is deterministic so that
regenerating it (delete -> recreate) yields byte-identical output. Auditability of
when a request was made belongs to the surrounding workflow (git, filesystem),
not the artifact body.

This is the CREATOR only. It validates that at least one known capability was
requested, then discovers its inputs. It does NOT check that referenced files
exist (existence is the opt-in --check-references concern of the validator). The
core three content references (package manifest, strategy, review packet) are
always emitted; the traceability bundle and production shop handoff references are
included only when explicitly supplied or conventionally discovered.

Discovery:
    package_reference     -> manifest.federation.federated_package_id, else dir name
    package_manifest_file -> <package>/manifest.json
    strategy_file         -> <package>/<manifest.strategy_file>
    review_packet_file    -> <package>/<manifest.review_packet_file>
    traceability_bundle_file:
        --traceability-bundle <path>            (explicit, recorded as-is)
        else traceability/<package>_bundle.json (conventional, if it exists)
        else omitted
    production_shop_handoff_file:
        --production-shop-handoff <path>         (explicit, recorded as-is)
        else production_shop/<package>_handoff.json (conventional, if it exists)
        else omitted

(For examples/packages/<name>, the creation_studio/, production_shop/, and
traceability/ roots live under examples/, exactly as the other creators resolve
their conventional dirs.)

Usage:
    python scripts/create_creation_studio_request.py --package <dir> \
        --capability feeds_speeds_recommendation --capability tooling_review
    python scripts/create_creation_studio_request.py --package <dir> \
        --capability tooling_review --material mahogany --operator-notes "..." --force

Exit codes:
    0 — Request created successfully
    1 — Argument error (package not found / not a directory, no/unknown capability,
        output exists without --force, or references that cannot be made relative
        to the output)
    2 — File/write error (directory creation or write failed)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import NamedTuple


RECORD_TYPE = "cam_assist_creation_studio_request"
RECORD_VERSION = "1.0.0"
REQUEST_DIRECTION = "cam_assist_to_creation_studio"
OUTPUT_SUFFIX = "_request.json"
BUNDLE_SUFFIX = "_bundle.json"
HANDOFF_SUFFIX = "_handoff.json"

# Conventional filenames within the package, used as fallbacks when the manifest
# does not declare them.
DEFAULT_STRATEGY_FILE = "strategy.json"
DEFAULT_REVIEW_PACKET_FILE = "review_packet.md"

CAPABILITY_VOCABULARY = [
    "feeds_speeds_recommendation",
    "tooling_review",
    "operation_sequence_analysis",
    "cycle_time_estimation",
    "simulation_request",
    "gcode_explanation",
    "toolpath_development_request",
    "workholding_review",
]

AUTHORITY = {
    "is_informational": True,
    "does_not_authorize_execution": True,
    "does_not_bypass_human_review": True,
    "does_not_confirm_machine_readiness": True,
    "does_not_require_gcode_generation": True,
}


class CreateResult(NamedTuple):
    success: bool
    output_path: Path | None
    error: str | None
    exit_code: int = 0


class ManifestError(Exception):
    """Raised when a manifest.json is present but cannot be read/parsed.

    A missing manifest is fine (the creator falls back to conventions), but a
    present-but-corrupt one must not be silently swallowed: doing so would emit
    a request with fallback identity/filenames derived from corrupt data, which
    looks correct while being wrong.
    """


def load_manifest(package_dir: Path) -> dict:
    """Load <package>/manifest.json.

    Returns {} when the file is absent (conventions apply). Raises
    ManifestError when the file exists but cannot be read or parsed, so the
    caller surfaces a clean error instead of producing a misleading artifact.
    """
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ManifestError(f"manifest.json is present but not valid JSON: {e}") from e
    except OSError as e:
        raise ManifestError(f"manifest.json is present but unreadable: {e}") from e
    if not isinstance(data, dict):
        raise ManifestError("manifest.json is present but is not a JSON object")
    return data


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


def relref(target: Path, output_dir: Path) -> str:
    """Path to target relative to output_dir, forward-slashed for portability."""
    return Path(os.path.relpath(target, start=output_dir)).as_posix()


def default_output_path(package_dir: Path) -> Path:
    """Conventional output: <creation_studio_base>/<package>_request.json."""
    return conventional_base(package_dir, "creation_studio") / f"{package_dir.name}{OUTPUT_SUFFIX}"


def conventional_bundle_path(package_dir: Path) -> Path:
    """Conventional traceability bundle: <traceability_base>/<package>_bundle.json."""
    return conventional_base(package_dir, "traceability") / f"{package_dir.name}{BUNDLE_SUFFIX}"


def conventional_handoff_path(package_dir: Path) -> Path:
    """Conventional production shop handoff: <production_shop_base>/<package>_handoff.json."""
    return conventional_base(package_dir, "production_shop") / f"{package_dir.name}{HANDOFF_SUFFIX}"


def build_contents(
    package_dir: Path,
    manifest: dict,
    output_dir: Path,
    explicit_bundle: Path | None,
    explicit_handoff: Path | None,
) -> dict:
    """Build the contents reference map, all relative to output_dir.

    The core three references are always emitted. The traceability bundle and the
    production shop handoff are each included only when explicitly supplied
    (recorded as-is, no existence check) or conventionally discovered (included
    only if the file exists).
    """
    strategy_name = manifest.get("strategy_file") or DEFAULT_STRATEGY_FILE
    review_packet_name = manifest.get("review_packet_file") or DEFAULT_REVIEW_PACKET_FILE

    contents = {
        "package_manifest_file": relref(package_dir / "manifest.json", output_dir),
        "strategy_file": relref(package_dir / strategy_name, output_dir),
        "review_packet_file": relref(package_dir / review_packet_name, output_dir),
    }

    if explicit_bundle is not None:
        contents["traceability_bundle_file"] = relref(explicit_bundle, output_dir)
    else:
        conventional = conventional_bundle_path(package_dir)
        if conventional.exists():
            contents["traceability_bundle_file"] = relref(conventional, output_dir)

    if explicit_handoff is not None:
        contents["production_shop_handoff_file"] = relref(explicit_handoff, output_dir)
    else:
        conventional = conventional_handoff_path(package_dir)
        if conventional.exists():
            contents["production_shop_handoff_file"] = relref(conventional, output_dir)

    return contents


def build_request_context(
    material: str | None,
    machine_profile: str | None,
    operator_notes: str | None,
) -> dict | None:
    """Build the optional request_context from supplied flags.

    Returns None when no context flag was given, so the default request stays
    minimal and deterministic. Only supplied, non-blank fields are emitted: a
    blank ('' or whitespace-only) flag value carries no information and would be
    rejected by the validator, so it is treated as absent rather than recorded.
    """
    context: dict = {}
    if material is not None and material.strip():
        context["material"] = material
    if machine_profile is not None and machine_profile.strip():
        context["machine_profile"] = machine_profile
    if operator_notes is not None and operator_notes.strip():
        context["operator_notes"] = operator_notes
    return context or None


def create_request(
    package_dir: Path,
    capabilities: list[str],
    output_path: Path | None = None,
    traceability_bundle: Path | None = None,
    production_shop_handoff: Path | None = None,
    material: str | None = None,
    machine_profile: str | None = None,
    operator_notes: str | None = None,
    force: bool = False,
) -> CreateResult:
    if not package_dir.exists():
        return CreateResult(False, None, f"Package directory not found: {package_dir}", 1)
    if not package_dir.is_dir():
        return CreateResult(False, None, f"Path is not a directory: {package_dir}", 1)

    if not capabilities:
        return CreateResult(
            False, None,
            "At least one --capability is required "
            f"(allowed: {', '.join(CAPABILITY_VOCABULARY)})", 1,
        )
    unknown = [c for c in capabilities if c not in CAPABILITY_VOCABULARY]
    if unknown:
        return CreateResult(
            False, None,
            f"Unknown capability/capabilities: {', '.join(unknown)} "
            f"(allowed: {', '.join(CAPABILITY_VOCABULARY)})", 1,
        )
    # De-duplicate while preserving request order (the schema forbids duplicates).
    seen: set[str] = set()
    deduped = [c for c in capabilities if not (c in seen or seen.add(c))]

    if output_path is None:
        output_path = default_output_path(package_dir)

    if output_path.exists() and not force:
        return CreateResult(
            False, None,
            f"Output file already exists: {output_path} (use --force to overwrite)", 1,
        )

    # A missing manifest is fine (conventions apply); a present-but-corrupt one
    # is a clean argument error rather than a silent fallback to bad identity.
    try:
        manifest = load_manifest(package_dir)
    except ManifestError as e:
        return CreateResult(False, None, str(e), 1)

    # References are stored relative to the output directory. os.path.relpath
    # raises ValueError when the two paths share no common anchor — most notably
    # a package and output on different Windows drives — so surface that as a
    # clean argument error rather than an uncaught traceback.
    try:
        contents = build_contents(
            package_dir, manifest, output_path.parent,
            traceability_bundle, production_shop_handoff,
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
        "request_direction": REQUEST_DIRECTION,
        "requested_capabilities": deduped,
        "contents": contents,
    }
    context = build_request_context(material, machine_profile, operator_notes)
    if context is not None:
        record["request_context"] = context
    record["authority"] = dict(AUTHORITY)

    # Directory creation and the write share the file/write-error class (exit 2).
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
            f.write("\n")
    except OSError as e:
        return CreateResult(False, None, f"Failed to write request: {e}", 2)

    return CreateResult(True, output_path, None, 0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create CAM Assist creation studio capability request (reference-only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--package", type=Path, required=True, help="Path to the strategy package directory"
    )
    parser.add_argument(
        "--capability", action="append", default=[], dest="capabilities", metavar="NAME",
        help=(
            "Requested downstream capability (repeatable). Allowed: "
            + ", ".join(CAPABILITY_VOCABULARY)
        ),
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Output path (default: creation_studio/<package>_request.json)",
    )
    parser.add_argument(
        "--traceability-bundle", type=Path, default=None, dest="traceability_bundle",
        help="Explicit traceability bundle path (overrides conventional discovery)",
    )
    parser.add_argument(
        "--production-shop-handoff", type=Path, default=None, dest="production_shop_handoff",
        help="Explicit production shop handoff path (overrides conventional discovery)",
    )
    parser.add_argument(
        "--material", type=str, default=None,
        help="Informational material description for request_context",
    )
    parser.add_argument(
        "--machine-profile", type=str, default=None, dest="machine_profile",
        help="Informational machine profile reference for request_context",
    )
    parser.add_argument(
        "--operator-notes", type=str, default=None, dest="operator_notes",
        help="Informational free-text notes for request_context",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing request file")
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only output the path on success"
    )

    args = parser.parse_args()

    result = create_request(
        package_dir=args.package,
        capabilities=args.capabilities,
        output_path=args.out,
        traceability_bundle=args.traceability_bundle,
        production_shop_handoff=args.production_shop_handoff,
        material=args.material,
        machine_profile=args.machine_profile,
        operator_notes=args.operator_notes,
        force=args.force,
    )

    if result.success:
        if args.quiet:
            print(str(result.output_path))
        else:
            print(f"Creation studio request created: {result.output_path}")
            print()
            print("Note: A creation studio request is a reference-only, outbound, advisory")
            print("artifact. The referenced files remain authoritative. It does not authorize")
            print("execution, bypass human review, confirm machine readiness, require G-code")
            print("generation, or modify the package.")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
