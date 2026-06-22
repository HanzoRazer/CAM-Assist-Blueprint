#!/usr/bin/env python3
"""
CAM Assist Production Shop Handoff Validator (structural layer)

Validates read-only Production Shop handoff manifests for:
- Correct record structure (record_type, record_version)
- package_reference present and a non-empty string
- handoff_direction present and equal to 'cam_assist_to_production_shop'
- authority REQUIRED, with four const-true flags
- contents present and object-shaped, restricted to known slots, string values

A handoff is a portable, reference-only manifest exporting a reviewed package and
its traceability bundle toward the future Production Shop runtime. Direction is
outbound only (CAM Assist -> Production Shop). The referenced files remain
authoritative; the handoff does not own, copy, or mutate them. It is
execution-adjacent, so the non-execution authority block is REQUIRED: the handoff
does not authorize machine execution, does not bypass human review, and does NOT
confirm machine readiness.

This is the STRUCTURAL layer only. It is filesystem-free: it opens only the
handoff file itself and never resolves or stats the referenced files. The
completeness-witness layer (--check-references) is a separate, opt-in concern and
is NOT implemented here.

Usage:
    python scripts/validate_production_shop_handoff.py <handoff_json>
    python scripts/validate_production_shop_handoff.py examples/production_shop/ltb_vcarve_synthetic_example_handoff.json

Exit codes:
    0 — Handoff record is valid
    1 — Validation failed
    2 — File/read error
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

import json


RECORD_TYPE = "cam_assist_production_shop_handoff"
HANDOFF_DIRECTION = "cam_assist_to_production_shop"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
AUTHORITY_FLAGS = [
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
    "does_not_confirm_machine_readiness",
]
CONTENT_SLOTS = [
    "package_manifest_file",
    "strategy_file",
    "review_packet_file",
    "traceability_bundle_file",
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


def validate_authority(authority: object, errors: list[str]) -> None:
    """Validate the required informational authority block.

    Every one of the four flags must be declared and true. (On a handoff the
    block itself is required; the caller checks for its presence.)
    """
    if not isinstance(authority, dict):
        errors.append("authority must be an object")
        return
    for flag in AUTHORITY_FLAGS:
        if flag not in authority:
            errors.append(f"authority.{flag} is required and must be true")
        elif authority.get(flag) is not True:
            errors.append(f"authority.{flag} must be true")


def validate_contents(contents: object, errors: list[str], warnings: list[str]) -> None:
    """Validate the contents object (structural only).

    Must be an object. Only known slots are permitted, and any present slot must
    be a non-empty string path. An empty object is permitted but warned about (no
    individual slot is required). References are never resolved or stated here.
    """
    if not isinstance(contents, dict):
        errors.append("contents must be an object")
        return

    if not contents:
        warnings.append("contents is empty")

    for key, value in contents.items():
        if key not in CONTENT_SLOTS:
            errors.append(
                f"contents: unknown content slot '{key}' "
                f"(allowed: {', '.join(CONTENT_SLOTS)})"
            )
            continue
        if not isinstance(value, str) or not value.strip():
            errors.append(f"contents.{key} must be a non-empty string path")


def validate_handoff(data: dict) -> ValidationResult:
    """Validate a production shop handoff record (structural layer)."""
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

    package_reference = data.get("package_reference")
    if "package_reference" not in data:
        errors.append("Missing required field: package_reference")
    elif not isinstance(package_reference, str) or not package_reference.strip():
        errors.append("'package_reference' must be a non-empty string")

    handoff_direction = data.get("handoff_direction")
    if "handoff_direction" not in data:
        errors.append("Missing required field: handoff_direction")
    elif handoff_direction != HANDOFF_DIRECTION:
        errors.append(
            f"Invalid handoff_direction: '{handoff_direction}'. Must be '{HANDOFF_DIRECTION}'"
        )

    if "authority" not in data:
        errors.append("Missing required field: authority")
    else:
        validate_authority(data["authority"], errors)

    if "contents" not in data:
        errors.append("Missing required field: contents")
    else:
        validate_contents(data["contents"], errors, warnings)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_handoff_file(path: Path) -> ValidationResult:
    data, load_error = load_json(path)
    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])
    if not isinstance(data, dict):
        return ValidationResult(
            valid=False, errors=["Handoff root must be a JSON object"], warnings=[]
        )
    return validate_handoff(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate CAM Assist production shop handoff (structural layer)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("handoff_json", type=Path, help="Path to the handoff JSON file")
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output errors, not success messages or warnings",
    )

    args = parser.parse_args()
    path: Path = args.handoff_json

    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 2

    result = validate_handoff_file(path)

    if result.valid:
        if not args.quiet:
            print("PASS: production shop handoff is valid")
            for warning in result.warnings:
                print(f"  [WARN] {warning}")
        return 0
    else:
        print("FAIL: production shop handoff validation failed", file=sys.stderr)
        for error in result.errors:
            print(f"  [ERR] {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"  [WARN] {warning}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
