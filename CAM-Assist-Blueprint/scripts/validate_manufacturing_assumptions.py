#!/usr/bin/env python3
"""
CAM Assist Manufacturing Assumptions Validator

Validates manufacturing assumptions sidecar files for:
- Correct record structure
- Required fields present on each assumption
- Authority constraints preserved (when present)

Assumptions are informational only. They do not grant execution authority.

Usage:
    python scripts/validate_manufacturing_assumptions.py <assumptions_json>
    python scripts/validate_manufacturing_assumptions.py examples/traceability/manufacturing_assumptions_example.json

Exit codes:
    0 — Assumptions record is valid
    1 — Validation failed
    2 — File/read error
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

import json


RECORD_TYPE = "cam_assist_manufacturing_assumptions"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
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


def validate_assumptions(data: dict) -> ValidationResult:
    """Validate a manufacturing assumptions record."""
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

    if "assumptions" not in data:
        errors.append("Missing required field: assumptions")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    assumptions = data.get("assumptions", [])
    if not isinstance(assumptions, list):
        errors.append("assumptions must be an array")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    if not assumptions:
        warnings.append("assumptions array is empty")

    for i, assumption in enumerate(assumptions):
        prefix = f"assumptions[{i}]"
        if not isinstance(assumption, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        for field in ("category", "statement"):
            value = assumption.get(field)
            if field not in assumption:
                errors.append(f"{prefix}: missing required field '{field}'")
            elif not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}: '{field}' must be a non-empty string")

    authority = data.get("authority", {})
    if authority:
        validate_authority(authority, errors)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_assumptions_file(path: Path) -> ValidationResult:
    data, load_error = load_json(path)
    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])
    return validate_assumptions(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate CAM Assist manufacturing assumptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("assumptions_json", type=Path, help="Path to the assumptions JSON file")
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output errors, not success messages or warnings",
    )

    args = parser.parse_args()
    path: Path = args.assumptions_json

    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 2

    result = validate_assumptions_file(path)

    if result.valid:
        if not args.quiet:
            print("PASS: manufacturing assumptions are valid")
            for warning in result.warnings:
                print(f"  [WARN] {warning}")
        return 0
    else:
        print("FAIL: manufacturing assumptions validation failed", file=sys.stderr)
        for error in result.errors:
            print(f"  [ERR] {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"  [WARN] {warning}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
