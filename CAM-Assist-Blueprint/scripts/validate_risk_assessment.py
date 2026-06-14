#!/usr/bin/env python3
"""
CAM Assist Risk Assessment Validator

Validates risk assessment sidecar files for:
- Correct record structure
- Valid overall risk level and per-risk severity
- Required fields present on each risk
- Authority constraints preserved (when present)

Risk scoring is informational only. It does not grant execution authority
and does not gate execution.

Usage:
    python scripts/validate_risk_assessment.py <risk_json>
    python scripts/validate_risk_assessment.py examples/traceability/risk_assessment_example.json

Exit codes:
    0 — Risk assessment is valid
    1 — Validation failed
    2 — File/read error
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple


RECORD_TYPE = "cam_assist_risk_assessment"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
VALID_RISK_LEVELS = ["low", "medium", "high"]
VALID_SEVERITIES = ["info", "warning", "concern", "blocking"]
AUTHORITY_FLAGS = [
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
]


class ValidationResult(NamedTuple):
    valid: bool
    errors: list[str]
    warnings: list[str]


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


def validate_authority(authority: dict, errors: list[str]) -> None:
    """Validate the optional informational authority block. Every flag must be true."""
    for flag in AUTHORITY_FLAGS:
        if flag in authority and authority.get(flag) is not True:
            errors.append(f"authority.{flag} must be true")


def validate_risk_assessment(data: dict) -> ValidationResult:
    """Validate a risk assessment record."""
    errors: list[str] = []
    warnings: list[str] = []

    record_type = data.get("record_type")
    if record_type is None:
        errors.append("Missing required field: record_type")
    elif record_type != RECORD_TYPE:
        errors.append(f"Invalid record_type: '{record_type}'. Must be '{RECORD_TYPE}'")

    record_version = data.get("record_version")
    if record_version is None:
        errors.append("Missing required field: record_version")
    elif not VERSION_PATTERN.match(record_version):
        errors.append(
            f"Invalid record_version format: '{record_version}'. "
            "Must be semantic version (e.g., '1.0.0')"
        )

    if "package_reference" not in data:
        errors.append("Missing required field: package_reference")

    overall_risk = data.get("overall_risk")
    if overall_risk is None:
        errors.append("Missing required field: overall_risk")
    elif overall_risk not in VALID_RISK_LEVELS:
        errors.append(
            f"Invalid overall_risk level: '{overall_risk}'. "
            f"Must be one of: {', '.join(VALID_RISK_LEVELS)}"
        )

    if "risks" not in data:
        errors.append("Missing required field: risks")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    risks = data.get("risks", [])
    if not isinstance(risks, list):
        errors.append("risks must be an array")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    if not risks:
        warnings.append("risks array is empty")

    for i, risk in enumerate(risks):
        prefix = f"risks[{i}]"
        if not isinstance(risk, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        for field in ("category", "description"):
            value = risk.get(field)
            if field not in risk:
                errors.append(f"{prefix}: missing required field '{field}'")
            elif not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}: '{field}' must be a non-empty string")

        severity = risk.get("severity")
        if "severity" not in risk:
            errors.append(f"{prefix}: missing required field 'severity'")
        elif severity not in VALID_SEVERITIES:
            errors.append(
                f"{prefix}: invalid severity '{severity}'. "
                f"Must be one of: {', '.join(VALID_SEVERITIES)}"
            )

    authority = data.get("authority", {})
    if authority:
        validate_authority(authority, errors)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_risk_assessment_file(path: Path) -> ValidationResult:
    data, load_error = load_json(path)
    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])
    return validate_risk_assessment(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate CAM Assist risk assessment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("risk_json", type=Path, help="Path to the risk assessment JSON file")
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output errors, not success messages or warnings",
    )

    args = parser.parse_args()
    path: Path = args.risk_json

    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 2

    result = validate_risk_assessment_file(path)

    if result.valid:
        if not args.quiet:
            print("PASS: risk assessment is valid")
            for warning in result.warnings:
                print(f"  [WARN] {warning}")
        return 0
    else:
        print("FAIL: risk assessment validation failed", file=sys.stderr)
        for error in result.errors:
            print(f"  [ERR] {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"  [WARN] {warning}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
