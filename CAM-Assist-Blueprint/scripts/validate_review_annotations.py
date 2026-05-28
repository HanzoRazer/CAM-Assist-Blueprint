#!/usr/bin/env python3
"""
CAM Assist Review Annotations Validator

Validates review annotation files for:
- Correct annotation structure
- Valid severity levels
- Required fields present
- Authority constraints preserved

Annotations are informational only. They do not grant execution authority.

Usage:
    python scripts/validate_review_annotations.py <annotations_json>
    python scripts/validate_review_annotations.py examples/review_annotations/ltb_vcarve_review_annotations.json

Exit codes:
    0 — Annotations are valid
    1 — Validation failed
    2 — File/read error
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple


VALID_SEVERITIES = ["info", "warning", "concern", "blocking"]
ANNOTATION_ID_PATTERN = re.compile(r"^ann-[a-f0-9-]+$")


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


VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def validate_annotations(data: dict) -> ValidationResult:
    """Validate a review annotations file."""
    errors: list[str] = []
    warnings: list[str] = []

    # Check record_type
    record_type = data.get("record_type")
    if record_type is None:
        errors.append("Missing required field: record_type")
    elif record_type != "cam_assist_review_annotations":
        errors.append(
            f"Invalid record_type: '{record_type}'. "
            "Must be 'cam_assist_review_annotations'"
        )

    # Check record_version
    record_version = data.get("record_version")
    if record_version is None:
        errors.append("Missing required field: record_version")
    elif not VERSION_PATTERN.match(record_version):
        errors.append(
            f"Invalid record_version format: '{record_version}'. "
            "Must be semantic version (e.g., '1.0.0')"
        )

    # Check required top-level fields
    if "package_reference" not in data:
        errors.append("Missing required field: package_reference")

    if "annotations" not in data:
        errors.append("Missing required field: annotations")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    annotations = data.get("annotations", [])

    if not isinstance(annotations, list):
        errors.append("annotations must be an array")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    if not annotations:
        warnings.append("annotations array is empty")

    # Validate each annotation
    seen_ids: set[str] = set()
    for i, annotation in enumerate(annotations):
        prefix = f"annotations[{i}]"

        if not isinstance(annotation, dict):
            errors.append(f"{prefix}: must be an object")
            continue

        # Required fields
        required_fields = ["annotation_id", "reviewer", "timestamp", "severity", "category", "message"]
        for field in required_fields:
            if field not in annotation:
                errors.append(f"{prefix}: missing required field '{field}'")

        # Validate annotation_id format
        annotation_id = annotation.get("annotation_id", "")
        if annotation_id:
            if not ANNOTATION_ID_PATTERN.match(annotation_id):
                errors.append(
                    f"{prefix}: invalid annotation_id format '{annotation_id}'. "
                    "Must match 'ann-<uuid>'"
                )
            if annotation_id in seen_ids:
                errors.append(f"{prefix}: duplicate annotation_id '{annotation_id}'")
            seen_ids.add(annotation_id)

        # Validate severity
        severity = annotation.get("severity", "")
        if severity and severity not in VALID_SEVERITIES:
            errors.append(
                f"{prefix}: invalid severity '{severity}'. "
                f"Must be one of: {', '.join(VALID_SEVERITIES)}"
            )

        # Warning for missing optional fields
        if not annotation.get("recommended_action"):
            if severity in ["warning", "concern", "blocking"]:
                warnings.append(
                    f"{prefix}: {severity} annotation has no recommended_action"
                )

    # Check authority constraints if present
    authority = data.get("authority", {})
    if authority:
        if authority.get("annotations_are_informational") is not True:
            errors.append(
                "authority.annotations_are_informational must be true"
            )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_annotations_file(path: Path) -> ValidationResult:
    """Validate an annotations file."""
    data, load_error = load_json(path)

    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])

    return validate_annotations(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate CAM Assist review annotations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "annotations_json",
        type=Path,
        help="Path to the annotations JSON file",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output errors, not success messages or warnings",
    )

    args = parser.parse_args()
    annotations_path: Path = args.annotations_json

    if not annotations_path.exists():
        print(f"Error: File not found: {annotations_path}", file=sys.stderr)
        return 2

    result = validate_annotations_file(annotations_path)

    if result.valid:
        if not args.quiet:
            print("PASS: review annotations are valid")
            for warning in result.warnings:
                print(f"  [WARN] {warning}")
        return 0
    else:
        print("FAIL: annotations validation failed", file=sys.stderr)
        for error in result.errors:
            print(f"  [ERR] {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"  [WARN] {warning}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
