#!/usr/bin/env python3
"""
CAM Assist Strategy Package Inspection CLI

Inspects assembled strategy packages and produces human-readable summaries.

This is a read-only inspection tool. It does not mutate, regenerate,
repair, or normalize package contents.

Usage:
    python scripts/inspect_strategy_package.py examples/packages/fret_slot_strategy_example/
    python scripts/inspect_strategy_package.py <package_dir> --json
    python scripts/inspect_strategy_package.py <package_dir> --quiet

Exit codes:
    0 — Inspection successful
    1 — Validation failure
    2 — File/read error
"""

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

KNOWN_MANIFEST_VERSIONS = ["1.0.0", "1.1.0"]
VALID_SEVERITIES = ["info", "warning", "concern", "blocking"]
MIN_REVIEW_PACKET_SIZE = 1024  # 1 KB


class InspectionResult(NamedTuple):
    valid: bool
    package_type: str | None
    operation_type: str | None
    manifest_version: str | None
    authority: dict | None
    files: dict
    provenance: dict | None
    federation: dict | None
    warnings: list[str]
    errors: list[str]


def load_json(path: Path) -> tuple[dict | None, str | None]:
    """Load and parse JSON file. Returns (data, error)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except Exception as e:
        return None, f"Error reading file: {e}"


def inspect_package(package_dir: Path) -> InspectionResult:
    """Inspect a strategy package directory."""
    errors: list[str] = []
    warnings: list[str] = []
    files: dict = {}

    # Check package directory exists
    if not package_dir.exists():
        return InspectionResult(
            valid=False,
            package_type=None,
            operation_type=None,
            manifest_version=None,
            authority=None,
            files={},
            provenance=None,
            federation=None,
            warnings=[],
            errors=[f"Package directory not found: {package_dir}"],
        )

    if not package_dir.is_dir():
        return InspectionResult(
            valid=False,
            package_type=None,
            operation_type=None,
            manifest_version=None,
            authority=None,
            files={},
            provenance=None,
            federation=None,
            warnings=[],
            errors=[f"Path is not a directory: {package_dir}"],
        )

    # Check manifest.json
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.exists():
        errors.append("manifest.json is missing")
        files["manifest"] = "missing"
    else:
        files["manifest"] = "present"

    # Load manifest
    manifest_data = None
    if files.get("manifest") == "present":
        manifest_data, load_error = load_json(manifest_path)
        if load_error:
            errors.append(f"Failed to load manifest: {load_error}")
            files["manifest"] = "invalid"

    # Extract manifest fields
    package_type = None
    operation_type = None
    manifest_version = None
    authority = None
    provenance = None
    federation = None

    if manifest_data:
        package_type = manifest_data.get("package_type")
        operation_type = manifest_data.get("operation_type")
        manifest_version = manifest_data.get("manifest_version")
        authority = manifest_data.get("authority", {})
        provenance = manifest_data.get("provenance", {})
        federation = manifest_data.get("federation")

        # Validate package_type
        if package_type != "cam_assist_strategy_package":
            errors.append(
                f"Invalid package_type: {package_type}. "
                "Expected 'cam_assist_strategy_package'"
            )

        # Validate manifest version
        if manifest_version and manifest_version not in KNOWN_MANIFEST_VERSIONS:
            warnings.append(f"Unknown manifest version: {manifest_version}")

        # Check authority block
        if not authority:
            errors.append("Authority block missing from manifest")
        else:
            if authority.get("non_execution_declaration") is not True:
                errors.append(
                    "AUTHORITY VIOLATION: non_execution_declaration must be true"
                )
            if authority.get("execution_authority_claim") is not False:
                errors.append(
                    "AUTHORITY VIOLATION: execution_authority_claim must be false"
                )
            if authority.get("requires_human_review") is not True:
                errors.append(
                    "AUTHORITY VIOLATION: requires_human_review must be true"
                )

        # Check strategy file
        strategy_file = manifest_data.get("strategy_file")
        if strategy_file:
            strategy_path = package_dir / strategy_file
            if strategy_path.exists():
                files["strategy"] = "present"
            else:
                files["strategy"] = "missing"
                errors.append(f"Strategy file not found: {strategy_file}")
        else:
            files["strategy"] = "missing"
            errors.append("strategy_file not specified in manifest")

        # Check review packet file
        review_file = manifest_data.get("review_packet_file")
        if review_file:
            review_path = package_dir / review_file
            if review_path.exists():
                files["review_packet"] = "present"
                # Check size
                try:
                    size = review_path.stat().st_size
                    if size < MIN_REVIEW_PACKET_SIZE:
                        warnings.append(
                            f"Review packet is unusually small ({size} bytes)"
                        )
                except OSError:
                    pass
            else:
                files["review_packet"] = "missing"
                errors.append(f"Review packet file not found: {review_file}")
        else:
            files["review_packet"] = "missing"
            errors.append("review_packet_file not specified in manifest")

        # Check source geometry files
        geometry_files = manifest_data.get("source_geometry_files", [])
        if not geometry_files:
            warnings.append("source_geometry_files is empty")

        # Check provenance
        if provenance:
            if not provenance.get("derivation_notes"):
                warnings.append("provenance.derivation_notes is empty")
            # Include created_at from top-level if not in provenance
            if "created_at" not in provenance and manifest_data.get("created_at"):
                provenance["created_at"] = manifest_data["created_at"]
        else:
            warnings.append("provenance metadata is missing")

    return InspectionResult(
        valid=len(errors) == 0,
        package_type=package_type,
        operation_type=operation_type,
        manifest_version=manifest_version,
        authority=authority,
        files=files,
        provenance=provenance,
        federation=federation,
        warnings=warnings,
        errors=errors,
    )


def load_annotations(path: Path) -> tuple[dict | None, str | None]:
    """Load annotations file. Returns (data, error)."""
    if not path.exists():
        return None, f"Annotations file not found: {path}"
    data, error = load_json(path)
    if error:
        return None, f"Failed to load annotations: {error}"
    return data, None


def format_annotations_section(annotations_data: dict, quiet: bool = False) -> list[str]:
    """Format annotations for terminal display."""
    lines = []
    lines.append("Review Annotations:")

    annotations = annotations_data.get("annotations", [])
    if not annotations:
        lines.append("  total: 0")
        return lines

    # Count by severity
    counts = {"blocking": 0, "concern": 0, "warning": 0, "info": 0}
    for ann in annotations:
        severity = ann.get("severity", "")
        if severity in counts:
            counts[severity] += 1

    # Summary counts
    lines.append(f"  total: {len(annotations)}")
    lines.append(f"  blocking: {counts['blocking']}")
    lines.append(f"  concerns: {counts['concern']}")
    lines.append(f"  warnings: {counts['warning']}")
    lines.append(f"  info: {counts['info']}")

    # Individual entries (unless quiet)
    if not quiet and annotations:
        lines.append("")
        for ann in annotations:
            severity = ann.get("severity", "?")
            category = ann.get("category", "?")
            message = ann.get("message", "")

            severity_tag = f"[{severity.upper()}]"
            lines.append(f"  {severity_tag} {category} — {message}")

    return lines


# CAM-A17 traceability sidecar conventions
TRACEABILITY_SPECS = [
    ("assumptions", "assumptions", "_assumptions.json"),
    ("risk_assessment", "risk assessment", "_risk.json"),
    ("decision_record", "decision record", "_decision_record.json"),
    ("revision_lineage", "revision lineage", "_lineage.json"),
]


def conventional_traceability_path(package_dir: Path, suffix: str) -> Path:
    """Conventional sidecar location: <parent>/traceability/<package><suffix>.

    For examples/packages/<name>, look under examples/traceability/ instead.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        base = parent.parent / "traceability"
    else:
        base = parent / "traceability"
    return base / f"{package_dir.name}{suffix}"


def resolve_traceability(
    package_dir: Path,
    assumptions: Path | None = None,
    risk: Path | None = None,
    decision_record: Path | None = None,
    revision_lineage: Path | None = None,
) -> dict:
    """Resolve traceability sidecars: explicit flag first, then conventional fallback.

    Does not broad-scan. Returns {key: {"present": bool, "path": str | None}}.
    """
    explicit = {
        "assumptions": assumptions,
        "risk_assessment": risk,
        "decision_record": decision_record,
        "revision_lineage": revision_lineage,
    }
    out: dict = {}
    for key, _label, suffix in TRACEABILITY_SPECS:
        path = explicit.get(key)
        if path is None:
            candidate = conventional_traceability_path(package_dir, suffix)
            if candidate.exists():
                path = candidate
        present = path is not None and Path(path).exists()
        out[key] = {"present": present, "path": str(path) if present else None}
    return out


def format_traceability_section(traceability: dict) -> list[str]:
    """Format the traceability section for terminal display."""
    lines = ["Traceability:"]
    if not any(traceability[key]["present"] for key, _label, _suffix in TRACEABILITY_SPECS):
        lines.append("  not declared")
        return lines
    for key, label, _suffix in TRACEABILITY_SPECS:
        status = "present" if traceability[key]["present"] else "not declared"
        lines.append(f"  {label}: {status}")
    return lines


# CAM-A19 traceability bundle: a separate aggregator artifact, detected (not
# parsed) under its own section. Modeled on the Federated Identity block.
BUNDLE_SUFFIX = "_bundle.json"


def resolve_bundle(package_dir: Path, explicit: Path | None = None) -> dict:
    """Detect a traceability bundle: explicit flag first, then conventional path.

    Detection only — does not parse, validate, resolve, or completeness-check the
    bundle's contents. Returns {"present": bool, "path": str | None}.
    """
    path = explicit
    if path is None:
        candidate = conventional_traceability_path(package_dir, BUNDLE_SUFFIX)
        if candidate.exists():
            path = candidate
    present = path is not None and Path(path).exists()
    return {"present": present, "path": str(path) if present else None}


def format_bundle_section(bundle: dict) -> list[str]:
    """Format the traceability bundle section (detection only)."""
    status = "present" if bundle["present"] else "not declared"
    return ["Traceability Bundle:", f"  {status}"]


# CAM-A20 production shop handoff: a separate outbound sidecar, detected (not
# parsed) under its own section. Unlike traceability artifacts, the conventional
# location is a production_shop/ directory (NOT traceability/).
HANDOFF_SUFFIX = "_handoff.json"


def conventional_handoff_path(package_dir: Path) -> Path:
    """Conventional handoff location: <parent>/production_shop/<package>_handoff.json.

    For examples/packages/<name>, look under examples/production_shop/ instead.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        base = parent.parent / "production_shop"
    else:
        base = parent / "production_shop"
    return base / f"{package_dir.name}{HANDOFF_SUFFIX}"


def resolve_handoff(package_dir: Path, explicit: Path | None = None) -> dict:
    """Detect a production shop handoff: explicit flag first, then conventional path.

    Detection only — never opens, parses, validates, resolves references, or
    completeness-checks the handoff, and makes no Production Shop runtime
    assumptions. An existing-but-unparseable handoff still counts as present.
    Returns {"present": bool, "path": str | None}.
    """
    path = explicit
    if path is None:
        candidate = conventional_handoff_path(package_dir)
        if candidate.exists():
            path = candidate
    present = path is not None and Path(path).exists()
    return {"present": present, "path": str(path) if present else None}


def format_handoff_section(handoff: dict) -> list[str]:
    """Format the production shop handoff section (detection only)."""
    status = "present" if handoff["present"] else "not declared"
    return ["Production Shop Handoff:", f"  {status}"]


# CAM-A22 creation studio request: a separate outbound, advisory sidecar,
# detected (not parsed) under its own section. The conventional location is a
# creation_studio/ directory.
REQUEST_SUFFIX = "_request.json"


def conventional_request_path(package_dir: Path) -> Path:
    """Conventional request location: <parent>/creation_studio/<package>_request.json.

    For examples/packages/<name>, look under examples/creation_studio/ instead.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        base = parent.parent / "creation_studio"
    else:
        base = parent / "creation_studio"
    return base / f"{package_dir.name}{REQUEST_SUFFIX}"


def resolve_creation_studio_request(package_dir: Path, explicit: Path | None = None) -> dict:
    """Detect a creation studio request: explicit flag first, then conventional path.

    Detection only — never opens, parses, validates, resolves references, infers
    supported capabilities, or completeness-checks the request. An
    existing-but-unparseable request still counts as present.
    Returns {"present": bool, "path": str | None}.
    """
    path = explicit
    if path is None:
        candidate = conventional_request_path(package_dir)
        if candidate.exists():
            path = candidate
    present = path is not None and Path(path).exists()
    return {"present": present, "path": str(path) if present else None}


def format_creation_studio_request_section(request: dict) -> list[str]:
    """Format the creation studio request section (detection only).

    The inspector detects a file at the conventional/explicit path; it never
    parses, validates, or resolves the request. The wording says so explicitly
    so "present" is not mistaken for "valid and wired" — run
    validate_creation_studio_request.py for that.
    """
    status = "present (detected, not validated)" if request["present"] else "not declared"
    return ["CAM-Creation-Studio Request:", f"  {status}"]


# CAM-A23 creation studio capability profile: a read-only capability contract
# published BY CAM-Creation-Studio, detected (not parsed) under its own section.
# It shares the creation_studio/ directory with the CAM-A22 request but is NOT
# package-specific — one profile per Creation Studio installation/version — so
# the filename is fixed rather than derived from the package name.
CAPABILITY_PROFILE_FILENAME = "capability_profile.json"


def conventional_capability_profile_path(package_dir: Path) -> Path:
    """Conventional profile location: <parent>/creation_studio/capability_profile.json.

    For examples/packages/<name>, look under examples/creation_studio/ instead.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        base = parent.parent / "creation_studio"
    else:
        base = parent / "creation_studio"
    return base / CAPABILITY_PROFILE_FILENAME


def resolve_capability_profile(package_dir: Path, explicit: Path | None = None) -> dict:
    """Detect a capability profile: explicit flag first, then conventional path.

    Detection only — never opens, parses, validates, resolves references, or reads
    which capabilities are declared. An existing-but-unparseable profile still
    counts as present. Presence says a Creation Studio profile was published
    alongside this package's tree; it says nothing about what Creation Studio can
    do for THIS package, and confers no authority of any kind.
    Returns {"present": bool, "path": str | None}.
    """
    path = explicit
    if path is None:
        candidate = conventional_capability_profile_path(package_dir)
        if candidate.exists():
            path = candidate
    present = path is not None and Path(path).exists()
    return {"present": present, "path": str(path) if present else None}


def format_capability_profile_section(profile: dict) -> list[str]:
    """Format the capability profile section (detection only).

    The inspector detects a file at the conventional/explicit path; it never
    parses, validates, or reads the declared capabilities. The wording says so
    explicitly so "present" is not mistaken for "valid and supported" — run
    validate_creation_studio_capability_profile.py for structural validity, and
    read the profile itself for what it declares.
    """
    status = "present (detected, not validated)" if profile["present"] else "not declared"
    return ["Creation Studio Capability Profile:", f"  {status}"]


def format_terminal_output(
    result: InspectionResult,
    annotations_data: dict | None = None,
    traceability: dict | None = None,
    bundle: dict | None = None,
    handoff: dict | None = None,
    creation_studio_request: dict | None = None,
    capability_profile: dict | None = None,
) -> str:
    """Format inspection result for terminal display."""
    lines = []
    lines.append("CAM Assist Strategy Package Inspection")
    lines.append("=" * 39)
    lines.append("")

    # Package type
    lines.append("Package Type:")
    lines.append(f"  {result.package_type or 'unknown'}")
    lines.append("")

    # Operation type
    lines.append("Operation Type:")
    lines.append(f"  {result.operation_type or 'unknown'}")
    lines.append("")

    # Manifest version
    lines.append("Manifest Version:")
    lines.append(f"  {result.manifest_version or 'unknown'}")
    lines.append("")

    # Authority status
    lines.append("Authority Status:")
    if result.authority:
        if result.authority.get("non_execution_declaration") is True:
            lines.append("  NON-EXECUTION PACKAGE")
        if result.authority.get("requires_human_review") is True:
            lines.append("  Human review required")
        if result.authority.get("execution_authority_claim") is False:
            lines.append("  Execution authority denied")
    else:
        lines.append("  [MISSING]")
    lines.append("")

    # Files
    lines.append("Files:")
    for file_name, status in result.files.items():
        if status == "present":
            lines.append(f"  [OK] {file_name}")
        elif status == "missing":
            lines.append(f"  [MISSING] {file_name}")
        else:
            lines.append(f"  [FAIL] {file_name}")
    lines.append("")

    # Provenance
    lines.append("Provenance:")
    if result.provenance:
        lines.append(f"  created_by: {result.provenance.get('created_by', 'unknown')}")
        lines.append(
            f"  source_spec_id: {result.provenance.get('source_spec_id', 'unknown')}"
        )
        lines.append(f"  created_at: {result.provenance.get('created_at', 'unknown')}")
    else:
        lines.append("  [MISSING]")
    lines.append("")

    # Federated Identity (CAM-A14/A15)
    lines.append("Federated Identity:")
    if result.federation:
        lines.append(f"  origin_system: {result.federation.get('origin_system', 'none')}")
        lines.append(f"  authority_domain: {result.federation.get('authority_domain', 'none')}")
        lines.append(f"  review_jurisdiction: {result.federation.get('review_jurisdiction', 'none')}")
        lines.append(f"  federated_package_id: {result.federation.get('federated_package_id', 'none')}")
    else:
        lines.append("  not declared")
    lines.append("")

    # Warnings
    lines.append("Warnings:")
    if result.warnings:
        for warning in result.warnings:
            lines.append(f"  [WARN] {warning}")
    else:
        lines.append("  none")
    lines.append("")

    # Errors (if any)
    if result.errors:
        lines.append("Errors:")
        for error in result.errors:
            lines.append(f"  [FAIL] {error}")
        lines.append("")

    # Annotations section (always show in verbose mode)
    lines.append("")
    if annotations_data:
        lines.extend(format_annotations_section(annotations_data))
    else:
        lines.append("Review Annotations:")
        lines.append("  not declared")

    # Traceability section (CAM-A17, always show in verbose mode)
    if traceability is not None:
        lines.append("")
        lines.extend(format_traceability_section(traceability))

    # Traceability Bundle section (CAM-A19, detection only)
    if bundle is not None:
        lines.append("")
        lines.extend(format_bundle_section(bundle))

    # Production Shop Handoff section (CAM-A20, detection only)
    if handoff is not None:
        lines.append("")
        lines.extend(format_handoff_section(handoff))

    # CAM-Creation-Studio Request section (CAM-A22, detection only)
    if creation_studio_request is not None:
        lines.append("")
        lines.extend(format_creation_studio_request_section(creation_studio_request))

    # Creation Studio Capability Profile section (CAM-A23, detection only)
    if capability_profile is not None:
        lines.append("")
        lines.extend(format_capability_profile_section(capability_profile))

    # Non-execution notice
    lines.append("")
    lines.append("-" * 39)
    lines.append("This package is advisory only.")
    lines.append("No machine execution authority is present.")
    lines.append("Human review is required before downstream CAM use.")

    return "\n".join(lines)


def format_json_output(
    result: InspectionResult,
    annotations_data: dict | None = None,
    traceability: dict | None = None,
    bundle: dict | None = None,
    handoff: dict | None = None,
    creation_studio_request: dict | None = None,
    capability_profile: dict | None = None,
) -> str:
    """Format inspection result as JSON."""
    output = {
        "valid": result.valid,
        "package_type": result.package_type,
        "operation_type": result.operation_type,
        "manifest_version": result.manifest_version,
        "authority": result.authority,
        "files": result.files,
        "provenance": result.provenance,
        "federation": result.federation,
        "warnings": result.warnings,
    }
    if result.errors:
        output["errors"] = result.errors
    if annotations_data:
        output["annotations"] = annotations_data.get("annotations", [])
    if traceability is not None:
        output["traceability"] = traceability
    if bundle is not None:
        output["traceability_bundle"] = bundle
    if handoff is not None:
        output["production_shop_handoff"] = handoff
    if creation_studio_request is not None:
        output["creation_studio_request"] = creation_studio_request
    if capability_profile is not None:
        output["creation_studio_capability_profile"] = capability_profile
    return json.dumps(output, indent=2)


def format_quiet_output(result: InspectionResult, package_dir: Path) -> str:
    """Format minimal pass/fail output."""
    if result.valid:
        return f"PASS: {package_dir}"
    else:
        return f"FAIL: {package_dir}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect CAM Assist strategy package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "package_dir",
        type=Path,
        help="Path to the strategy package directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only print pass/fail summary",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=None,
        help="Path to a review annotations file to display alongside package inspection",
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=None,
        help="Path to a manufacturing assumptions sidecar (overrides conventional lookup)",
    )
    parser.add_argument(
        "--risk",
        type=Path,
        default=None,
        help="Path to a risk assessment sidecar (overrides conventional lookup)",
    )
    parser.add_argument(
        "--decision-record",
        type=Path,
        default=None,
        dest="decision_record",
        help="Path to a manufacturing decision record sidecar (overrides conventional lookup)",
    )
    parser.add_argument(
        "--lineage",
        type=Path,
        default=None,
        help="Path to a revision lineage sidecar (overrides conventional lookup)",
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        default=None,
        help="Path to a traceability bundle sidecar (overrides conventional lookup; detection only)",
    )
    parser.add_argument(
        "--handoff",
        type=Path,
        default=None,
        help="Path to a production shop handoff sidecar (overrides conventional lookup; detection only)",
    )
    parser.add_argument(
        "--creation-studio-request",
        type=Path,
        default=None,
        dest="creation_studio_request",
        help="Path to a CAM-Creation-Studio request sidecar (overrides conventional lookup; detection only)",
    )
    parser.add_argument(
        "--capability-profile",
        type=Path,
        default=None,
        dest="capability_profile",
        help=(
            "Path to a Creation Studio capability profile (overrides conventional "
            "lookup; detection only)"
        ),
    )

    args = parser.parse_args()
    package_dir: Path = args.package_dir

    if not package_dir.exists():
        print(f"Error: Package directory not found: {package_dir}", file=sys.stderr)
        return 2

    result = inspect_package(package_dir)

    # Load annotations if specified or found by convention
    annotations_data = None
    annotations_path = args.annotations

    if annotations_path:
        # Explicit path provided
        if not annotations_path.exists():
            print(f"Error: Annotations file not found: {annotations_path}", file=sys.stderr)
            return 2
    else:
        # Check conventional path
        # If under examples/packages/<name>, check examples/review_annotations/<name>_annotations.json
        # Otherwise, check <package_parent>/review_annotations/<package_name>_annotations.json
        package_parent = package_dir.parent
        if package_parent.name == "packages" and package_parent.parent.name == "examples":
            # examples/packages/<name> -> examples/review_annotations/<name>_annotations.json
            conventional_path = (
                package_parent.parent / "review_annotations" / f"{package_dir.name}_annotations.json"
            )
        else:
            conventional_path = (
                package_parent / "review_annotations" / f"{package_dir.name}_annotations.json"
            )
        if conventional_path.exists():
            annotations_path = conventional_path

    if annotations_path:
        annotations_data, ann_error = load_annotations(annotations_path)
        if ann_error:
            print(f"Error: {ann_error}", file=sys.stderr)
            return 2

    # Resolve traceability sidecars: explicit flags first, then conventional fallback.
    for flag_name, flag_value in (
        ("--assumptions", args.assumptions),
        ("--risk", args.risk),
        ("--decision-record", args.decision_record),
        ("--lineage", args.lineage),
        ("--bundle", args.bundle),
        ("--handoff", args.handoff),
        ("--creation-studio-request", args.creation_studio_request),
        ("--capability-profile", args.capability_profile),
    ):
        if flag_value is not None and not flag_value.exists():
            print(f"Error: {flag_name} file not found: {flag_value}", file=sys.stderr)
            return 2

    traceability = resolve_traceability(
        package_dir,
        assumptions=args.assumptions,
        risk=args.risk,
        decision_record=args.decision_record,
        revision_lineage=args.lineage,
    )

    bundle = resolve_bundle(package_dir, explicit=args.bundle)

    handoff = resolve_handoff(package_dir, explicit=args.handoff)

    creation_studio_request = resolve_creation_studio_request(
        package_dir, explicit=args.creation_studio_request
    )

    capability_profile = resolve_capability_profile(
        package_dir, explicit=args.capability_profile
    )

    if args.json:
        print(format_json_output(
            result, annotations_data, traceability, bundle, handoff,
            creation_studio_request, capability_profile,
        ))
    elif args.quiet:
        output = format_quiet_output(result, package_dir)
        if result.valid:
            print(output)
        else:
            print(output, file=sys.stderr)
    else:
        print(format_terminal_output(
            result, annotations_data, traceability, bundle, handoff,
            creation_studio_request, capability_profile,
        ))

    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
