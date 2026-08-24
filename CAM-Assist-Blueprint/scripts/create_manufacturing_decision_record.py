#!/usr/bin/env python3
"""
CAM Assist Manufacturing Decision Record Creator

Creates a manufacturing decision record sidecar file for a strategy package.

A decision record captures a human declaration of why a manufacturing decision
was made. It does not enforce approval authority or authorize machine execution.
Package contents and any linked sidecars are never modified.

Usage:
    python scripts/create_manufacturing_decision_record.py --package <dir> \
        --decision approved --prepared-by "Manufacturing Engineer" \
        --reviewed-by "Senior Reviewer" \
        --rationale "Tooling, fixturing, and material assumptions reviewed."

    python scripts/create_manufacturing_decision_record.py \
        --package examples/packages/ltb_vcarve_synthetic_example \
        --decision approved --prepared-by "Manufacturing Engineer" \
        --reviewed-by "Senior Reviewer" --rationale "Reviewed." \
        --assumptions-file examples/traceability/ltb_vcarve_synthetic_example_assumptions.json \
        --risk-file examples/traceability/ltb_vcarve_synthetic_example_risk.json \
        --out examples/traceability/ltb_vcarve_synthetic_example_decision_record.json

Exit codes:
    0 — Decision record created successfully
    1 — Validation or argument error
    2 — File/write error
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared.artifact_references import relative_reference


RECORD_TYPE = "cam_assist_manufacturing_decision_record"
RECORD_VERSION = "1.0.0"
OUTPUT_SUFFIX = "_decision_record.json"
VALID_DECISIONS = ["approved", "needs_revision", "rejected"]


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


def _locate_cli_path(path: Path | str) -> Path:
    """Locate a CLI-supplied path. Relative values follow process CWD.

    This is argument location, not reference resolution. Stored references are
    then computed with relative_reference() against the output file.
    """
    located = Path(path)
    return located if located.is_absolute() else Path.cwd() / located


def default_output_path(package_dir: Path) -> Path:
    """Conventional output: <parent>/traceability/<package>_decision_record.json.

    For examples/packages/<name>, place under examples/traceability/ instead.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        base = parent.parent / "traceability"
    else:
        base = parent / "traceability"
    return base / f"{package_dir.name}{OUTPUT_SUFFIX}"


def create_decision_record(
    package_dir: Path,
    decision: str,
    prepared_by: str,
    reviewed_by: str,
    rationale: str,
    assumptions_file: str | None = None,
    risk_file: str | None = None,
    output_path: Path | None = None,
    force: bool = False,
) -> CreateResult:
    if not package_dir.exists():
        return CreateResult(False, None, f"Package directory not found: {package_dir}")
    if not package_dir.is_dir():
        return CreateResult(False, None, f"Path is not a directory: {package_dir}")
    if decision not in VALID_DECISIONS:
        return CreateResult(
            False, None, f"Invalid decision '{decision}'. Must be one of: {', '.join(VALID_DECISIONS)}"
        )
    for label, value in (("--prepared-by", prepared_by), ("--reviewed-by", reviewed_by), ("--rationale", rationale)):
        if not value or not value.strip():
            return CreateResult(False, None, f"{label} is required")

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
        "prepared_by": prepared_by.strip(),
        "reviewed_by": reviewed_by.strip(),
        "decision": decision,
        "rationale": rationale.strip(),
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_bypass_human_review": True,
        },
    }

    # Linked traceability sidecars are referenced, never mutated.
    # Store declaring-file-relative portable paths, not the raw CLI string.
    output_located = _locate_cli_path(output_path)
    try:
        if assumptions_file:
            record["assumptions_file"] = relative_reference(
                output_located, _locate_cli_path(assumptions_file)
            )
        if risk_file:
            record["risk_file"] = relative_reference(
                output_located, _locate_cli_path(risk_file)
            )
    except ValueError as e:
        return CreateResult(
            False,
            None,
            f"Cannot compute a relative path from the output location to a "
            f"linked sidecar (are they on different drives?): {e}",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
            f.write("\n")
    except OSError as e:
        return CreateResult(False, None, f"Failed to write decision record: {e}")

    return CreateResult(True, output_path, None)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create CAM Assist manufacturing decision record",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--package", type=Path, required=True, help="Path to the strategy package directory")
    parser.add_argument("--decision", type=str, required=True, choices=VALID_DECISIONS, help="Manufacturing decision")
    parser.add_argument("--prepared-by", type=str, required=True, help="Who prepared the decision (informational)")
    parser.add_argument("--reviewed-by", type=str, required=True, help="Who reviewed the decision (informational)")
    parser.add_argument("--rationale", type=str, required=True, help="Rationale for the decision")
    parser.add_argument("--assumptions-file", type=str, default=None, help="Optional path to a linked assumptions sidecar")
    parser.add_argument("--risk-file", type=str, default=None, help="Optional path to a linked risk assessment sidecar")
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: traceability/<package>_decision_record.json)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing decision record")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output the path on success")

    args = parser.parse_args()

    result = create_decision_record(
        package_dir=args.package,
        decision=args.decision,
        prepared_by=args.prepared_by,
        reviewed_by=args.reviewed_by,
        rationale=args.rationale,
        assumptions_file=args.assumptions_file,
        risk_file=args.risk_file,
        output_path=args.out,
        force=args.force,
    )

    if result.success:
        if args.quiet:
            print(str(result.output_path))
        else:
            print(f"Manufacturing decision record created: {result.output_path}")
            print()
            print("Note: This record captures a human declaration only.")
            print("It does not authorize machine execution or bypass human review.")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
