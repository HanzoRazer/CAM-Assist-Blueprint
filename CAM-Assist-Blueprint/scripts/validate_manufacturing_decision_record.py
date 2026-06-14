#!/usr/bin/env python3
"""
CAM Assist Manufacturing Decision Record Validator

Validates manufacturing decision record sidecar files for:
- Correct record structure
- Valid decision value
- Required human declaration fields present
- Optional linked traceability files are strings
- Authority constraints preserved (when present)

A decision record captures a human declaration. It does not enforce approval
authority or authorize machine execution.

Usage:
    python scripts/validate_manufacturing_decision_record.py <record_json>
    python scripts/validate_manufacturing_decision_record.py examples/traceability/manufacturing_decision_record_example.json

Exit codes:
    0 — Decision record is valid
    1 — Validation failed
    2 — File/read error
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple


RECORD_TYPE = "cam_assist_manufacturing_decision_record"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
VALID_DECISIONS = ["approved", "needs_revision", "rejected"]
REQUIRED_STRING_FIELDS = ["package_reference", "prepared_by", "reviewed_by", "rationale"]
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


def validate_decision_record(data: dict) -> ValidationResult:
    """Validate a manufacturing decision record."""
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

    for field in REQUIRED_STRING_FIELDS:
        value = data.get(field)
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(value, str) or not value.strip():
            errors.append(f"'{field}' must be a non-empty string")

    decision = data.get("decision")
    if "decision" not in data:
        errors.append("Missing required field: decision")
    elif decision not in VALID_DECISIONS:
        errors.append(
            f"Invalid decision value: '{decision}'. "
            f"Must be one of: {', '.join(VALID_DECISIONS)}"
        )

    for link_field in ("assumptions_file", "risk_file"):
        if link_field in data and not isinstance(data.get(link_field), str):
            errors.append(f"'{link_field}' must be a string path when present")

    authority = data.get("authority", {})
    if authority:
        validate_authority(authority, errors)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_decision_record_file(path: Path) -> ValidationResult:
    data, load_error = load_json(path)
    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])
    return validate_decision_record(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate CAM Assist manufacturing decision record",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("record_json", type=Path, help="Path to the decision record JSON file")
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output errors, not success messages or warnings",
    )

    args = parser.parse_args()
    path: Path = args.record_json

    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 2

    result = validate_decision_record_file(path)

    if result.valid:
        if not args.quiet:
            print("PASS: manufacturing decision record is valid")
            for warning in result.warnings:
                print(f"  [WARN] {warning}")
        return 0
    else:
        print("FAIL: manufacturing decision record validation failed", file=sys.stderr)
        for error in result.errors:
            print(f"  [ERR] {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"  [WARN] {warning}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
