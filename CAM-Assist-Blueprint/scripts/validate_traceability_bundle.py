#!/usr/bin/env python3
"""
CAM Assist Traceability Bundle Validator (structural layer)

Validates traceability bundle sidecar files for:
- Correct record structure (record_type, record_version)
- package_reference present and a non-empty string
- bundle_contents present and object-shaped, restricted to known slots,
  with string values for any present slot
- Authority constraints preserved (when present)

A traceability bundle is a portable, reference-only navigational index that
aggregates a package's traceability sidecars. The referenced sidecars remain
authoritative; the bundle does not own, copy, or mutate them. It is
informational only and does NOT grant execution authority.

The STRUCTURAL layer (default) is filesystem-free: it opens only the bundle
file itself and never resolves or stats the referenced sidecars. A bundle whose
references do not exist still passes structurally.

The COMPLETENESS-WITNESS layer (opt-in --check-references) resolves each declared
reference relative to the bundle file's own directory and emits a WARNING for any
that do not exist. Completeness findings are warnings only: they never change
structural validity and never change the exit code. The layer checks existence
only — it does NOT open, parse, or validate the referenced sidecars' contents,
and it mutates nothing.

Usage:
    python scripts/validate_traceability_bundle.py <bundle_json>
    python scripts/validate_traceability_bundle.py <bundle_json> --check-references
    python scripts/validate_traceability_bundle.py examples/traceability/traceability_bundle_example.json

Exit codes:
    0 — Traceability bundle record is valid
    1 — Validation failed
    2 — File/read error
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

import json


RECORD_TYPE = "cam_assist_traceability_bundle"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
AUTHORITY_FLAGS = [
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
]
CONTENT_SLOTS = [
    "assumptions_file",
    "risk_file",
    "decision_record_file",
    "annotations_file",
    "lineage_file",
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
    """Validate the informational authority block.

    The block is optional, but when present every flag must be declared and true.
    """
    if not isinstance(authority, dict):
        errors.append("authority must be an object")
        return
    for flag in AUTHORITY_FLAGS:
        if flag not in authority:
            errors.append(f"authority.{flag} is required and must be true")
        elif authority.get(flag) is not True:
            errors.append(f"authority.{flag} must be true")


def validate_bundle_contents(contents: object, errors: list[str], warnings: list[str]) -> None:
    """Validate the bundle_contents object (structural only).

    Must be an object. Only known slots are permitted, and any present slot must
    be a non-empty string path. An empty object is permitted but warned about
    (missing sidecars are allowed). References are never resolved or stated here.
    """
    if not isinstance(contents, dict):
        errors.append("bundle_contents must be an object")
        return

    if not contents:
        warnings.append("bundle_contents is empty")

    for key, value in contents.items():
        if key not in CONTENT_SLOTS:
            errors.append(
                f"bundle_contents: unknown reference slot '{key}' "
                f"(allowed: {', '.join(CONTENT_SLOTS)})"
            )
            continue
        if not isinstance(value, str) or not value.strip():
            errors.append(f"bundle_contents.{key} must be a non-empty string path")


def validate_bundle(data: dict) -> ValidationResult:
    """Validate a traceability bundle record (structural layer)."""
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

    if "bundle_contents" not in data:
        errors.append("Missing required field: bundle_contents")
    else:
        validate_bundle_contents(data["bundle_contents"], errors, warnings)

    if "authority" in data:
        validate_authority(data["authority"], errors)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def check_reference_existence(data: dict, base_dir: Path) -> list[str]:
    """Completeness witness: warn for any DECLARED reference that does not resolve.

    Resolves each present slot relative to base_dir (the bundle file's own
    directory). Checks existence only — never opens, parses, or validates the
    referenced sidecar's contents, and never mutates anything. Returns warnings;
    callers must not let these affect validity or exit code.
    """
    warnings: list[str] = []
    contents = data.get("bundle_contents")
    if not isinstance(contents, dict):
        return warnings
    for slot in CONTENT_SLOTS:
        value = contents.get(slot)
        if isinstance(value, str) and value.strip():
            if not (base_dir / value).exists():
                warnings.append(f"{slot} reference does not resolve: {value}")
    return warnings


def validate_bundle_file(path: Path, check_references: bool = False) -> ValidationResult:
    data, load_error = load_json(path)
    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])
    if not isinstance(data, dict):
        return ValidationResult(
            valid=False, errors=["Bundle root must be a JSON object"], warnings=[]
        )
    result = validate_bundle(data)
    # Completeness checks run only on a structurally valid bundle and only add
    # warnings — they never change validity or the exit code.
    if check_references and result.valid:
        ref_warnings = check_reference_existence(data, path.parent)
        result = ValidationResult(
            valid=result.valid,
            errors=result.errors,
            warnings=result.warnings + ref_warnings,
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate CAM Assist traceability bundle (structural layer)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("bundle_json", type=Path, help="Path to the traceability bundle JSON file")
    parser.add_argument(
        "--check-references",
        action="store_true",
        help=(
            "Completeness witness: warn for declared references that do not resolve "
            "(relative to the bundle file). Existence only; warnings never change validity "
            "or the exit code."
        ),
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output errors, not success messages or warnings",
    )

    args = parser.parse_args()
    path: Path = args.bundle_json

    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 2

    result = validate_bundle_file(path, check_references=args.check_references)

    if result.valid:
        if not args.quiet:
            print("PASS: traceability bundle is valid")
            for warning in result.warnings:
                print(f"  [WARN] {warning}")
        return 0
    else:
        print("FAIL: traceability bundle validation failed", file=sys.stderr)
        for error in result.errors:
            print(f"  [ERR] {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"  [WARN] {warning}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
