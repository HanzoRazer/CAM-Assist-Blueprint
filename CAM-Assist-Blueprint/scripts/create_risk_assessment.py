#!/usr/bin/env python3
"""
CAM Assist Risk Assessment Creator

Creates a risk assessment sidecar file for a strategy package.

Risk scoring is informational only. It does not grant execution authority and
does not gate execution. Package contents are never modified.

Usage:
    python scripts/create_risk_assessment.py --package <dir> --overall-risk medium \
        --risk geometry warning "Thin wall section may chatter."

    python scripts/create_risk_assessment.py \
        --package examples/packages/ltb_vcarve_synthetic_example --overall-risk medium \
        --risk geometry warning "Thin wall section may chatter." \
        --out examples/traceability/risk_assessment_example.json

Exit codes:
    0 — Risk assessment created successfully
    1 — Validation or argument error
    2 — File/write error
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple


RECORD_TYPE = "cam_assist_risk_assessment"
RECORD_VERSION = "1.0.0"
OUTPUT_SUFFIX = "_risk.json"
VALID_RISK_LEVELS = ["low", "medium", "high"]
VALID_SEVERITIES = ["info", "warning", "concern", "blocking"]


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
    """Conventional output: <parent>/traceability/<package>_risk.json.

    For examples/packages/<name>, place under examples/traceability/ instead.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        base = parent.parent / "traceability"
    else:
        base = parent / "traceability"
    return base / f"{package_dir.name}{OUTPUT_SUFFIX}"


def create_risk_assessment(
    package_dir: Path,
    overall_risk: str,
    risks: list[dict],
    output_path: Path | None = None,
    force: bool = False,
) -> CreateResult:
    if not package_dir.exists():
        return CreateResult(False, None, f"Package directory not found: {package_dir}")
    if not package_dir.is_dir():
        return CreateResult(False, None, f"Path is not a directory: {package_dir}")
    if overall_risk not in VALID_RISK_LEVELS:
        return CreateResult(
            False, None, f"Invalid overall risk '{overall_risk}'. Must be one of: {', '.join(VALID_RISK_LEVELS)}"
        )
    if not risks:
        return CreateResult(False, None, "At least one --risk is required")
    for risk in risks:
        if risk["severity"] not in VALID_SEVERITIES:
            return CreateResult(
                False, None,
                f"Invalid severity '{risk['severity']}'. Must be one of: {', '.join(VALID_SEVERITIES)}",
            )

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
        "overall_risk": overall_risk,
        "risks": risks,
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
        return CreateResult(False, None, f"Failed to write risk assessment: {e}")

    return CreateResult(True, output_path, None)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create CAM Assist risk assessment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--package", type=Path, required=True, help="Path to the strategy package directory")
    parser.add_argument(
        "--overall-risk", type=str, required=True, choices=VALID_RISK_LEVELS,
        help="Overall informational risk level",
    )
    parser.add_argument(
        "--risk",
        nargs=3,
        action="append",
        metavar=("CATEGORY", "SEVERITY", "DESCRIPTION"),
        dest="risks",
        help="A risk as CATEGORY SEVERITY DESCRIPTION (repeatable)",
    )
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: traceability/<package>_risk.json)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing risk assessment file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output the path on success")

    args = parser.parse_args()

    risks = [
        {"category": cat, "severity": sev, "description": desc}
        for cat, sev, desc in (args.risks or [])
    ]

    result = create_risk_assessment(
        package_dir=args.package,
        overall_risk=args.overall_risk,
        risks=risks,
        output_path=args.out,
        force=args.force,
    )

    if result.success:
        if args.quiet:
            print(str(result.output_path))
        else:
            print(f"Risk assessment created: {result.output_path}")
            print()
            print("Note: Risk scoring is informational only.")
            print("It does not grant execution authority or gate execution.")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
