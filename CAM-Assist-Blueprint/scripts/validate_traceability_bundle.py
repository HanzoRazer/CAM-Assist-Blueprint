#!/usr/bin/env python3
"""
CAM Assist Traceability Bundle Validator (structural layer)

Validates traceability bundle sidecar files for:
- Correct record structure (record_type, record_version)
- package_reference present and a non-empty string
- bundle_contents present and object-shaped, restricted to known slots,
  with string values for any present slot
- Authority constraints preserved (when present), with no undeclared flags
- a closed top-level contract: unrecognized top-level fields are rejected
  (created_at and authority are optional but recognized)

A traceability bundle is a portable, reference-only navigational index that
aggregates a package's traceability sidecars. The referenced sidecars remain
authoritative; the bundle does not own, copy, or mutate them. It is
informational only and does NOT grant execution authority.

The STRUCTURAL layer (default) is filesystem-free: it opens only the bundle
file itself and never resolves or stats the referenced sidecars. A bundle whose
references do not exist still passes structurally.

The COMPLETENESS-WITNESS layer (opt-in --check-references) resolves each declared
reference relative to a base directory (the bundle file's own directory by
default; override with --base) and emits WARNINGS for completeness findings:
  - a declared reference that does not resolve on disk
  - a known sidecar slot that is absent from bundle_contents (an omission)
  - a resolved sidecar whose own package_reference differs from the bundle's
Completeness findings are warnings only: they never change structural validity,
and by default never change the exit code. The opt-in --fail-on-reference-warnings
mode escalates ONLY unresolved declared references to errors (exit 1); omissions
(a missing sidecar is allowed) and package_reference mismatches stay advisory.
Beyond a single best-effort read for the package_reference cross-check, the layer
does NOT validate the referenced sidecars' contents, and it mutates nothing. Parse failures during the
cross-check are ignored — validating a sidecar's structure is that file's own
validator's job.

Usage:
    python scripts/validate_traceability_bundle.py <bundle_json>
    python scripts/validate_traceability_bundle.py <bundle_json> --check-references
    python scripts/validate_traceability_bundle.py <bundle_json> --check-references --base <dir>
    python scripts/validate_traceability_bundle.py examples/traceability/ltb_vcarve_synthetic_example_bundle.json

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
# Closed set of permitted top-level keys (mirrors the schema's
# additionalProperties: false). created_at and authority are optional but
# recognized.
KNOWN_TOP_LEVEL = [
    "record_type",
    "record_version",
    "package_reference",
    "created_at",
    "bundle_contents",
    "authority",
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
    # The informational block is a closed contract: reject undeclared flags so a
    # contradictory one (e.g. an execution-granting flag) cannot ride along.
    for flag in authority:
        if flag not in AUTHORITY_FLAGS:
            errors.append(
                f"authority: unknown flag '{flag}' "
                f"(allowed: {', '.join(AUTHORITY_FLAGS)})"
            )


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

    # Closed top-level contract (mirrors the schema's additionalProperties: false):
    # an unrecognized top-level key is rejected so stray/misleading fields cannot
    # ride along unnoticed.
    for key in data:
        if key not in KNOWN_TOP_LEVEL:
            errors.append(
                f"unknown top-level field: '{key}' "
                f"(allowed: {', '.join(KNOWN_TOP_LEVEL)})"
            )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def referenced_package_reference(path: Path) -> str | None:
    """Best-effort read of a referenced sidecar's own package_reference.

    Returns the string when the file parses as a JSON object carrying a string
    package_reference, else None. Read/parse failures are ignored on purpose:
    validating the referenced file's structure is that file's validator's job.
    """
    data, error = load_json(path)
    if error or not isinstance(data, dict):
        return None
    ref = data.get("package_reference")
    return ref if isinstance(ref, str) else None


def collect_completeness_findings(
    data: dict, base_dir: Path, bundle_reference: str | None
) -> tuple[list[str], list[str]]:
    """Completeness witness (warnings only).

    For each known sidecar slot, relative to base_dir:
    - present and does not resolve  -> warn (declared reference missing on disk)
    - present and resolves          -> best-effort read; warn if the sidecar's
                                       own package_reference differs from the
                                       bundle's (cross-artifact consistency)
    - absent from bundle_contents   -> warn (completeness/omission finding)

    Existence checks plus a single best-effort read for the cross-check only;
    never validates sidecar structure, never mutates anything. Callers must not
    let these warnings affect validity or the exit code.

    Returns (all_findings, unresolved_reference_findings). The second list is the
    subset representing a DECLARED reference missing on disk — the only findings
    --fail-on-reference-warnings escalates. Omission findings (a missing sidecar
    is allowed by design) and package_reference mismatches stay advisory and are
    never escalated.
    """
    warnings: list[str] = []
    unresolved: list[str] = []
    contents = data.get("bundle_contents")
    if not isinstance(contents, dict):
        contents = {}
    for slot in CONTENT_SLOTS:
        value = contents.get(slot)
        if isinstance(value, str) and value.strip():
            resolved = base_dir / value
            if not resolved.exists():
                msg = f"{slot} reference does not resolve: {value}"
                warnings.append(msg)
                unresolved.append(msg)
                continue
            ref = referenced_package_reference(resolved)
            if ref is not None and bundle_reference is not None and ref != bundle_reference:
                warnings.append(
                    f"package_reference mismatch in {slot}: "
                    f"'{ref}' != bundle '{bundle_reference}'"
                )
        else:
            warnings.append(f"completeness: {slot} not present in bundle")
    return warnings, unresolved


def validate_bundle_file(
    path: Path,
    check_references: bool = False,
    base: Path | None = None,
    fail_on_reference_warnings: bool = False,
) -> ValidationResult:
    data, load_error = load_json(path)
    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])
    if not isinstance(data, dict):
        return ValidationResult(
            valid=False, errors=["Bundle root must be a JSON object"], warnings=[]
        )
    result = validate_bundle(data)
    # Completeness checks run only on a structurally valid bundle. By default they
    # only add warnings — never changing validity or the exit code. The opt-in
    # --fail-on-reference-warnings mode escalates ONLY unresolved declared
    # references to errors (exit 1); omissions (a missing sidecar is allowed) and
    # package_reference mismatches remain advisory. Structural rules are never
    # affected either way.
    if check_references and result.valid:
        base_dir = base if base is not None else path.parent
        bundle_reference = data.get("package_reference")
        if not isinstance(bundle_reference, str):
            bundle_reference = None
        ref_warnings, unresolved = collect_completeness_findings(
            data, base_dir, bundle_reference
        )
        if fail_on_reference_warnings and unresolved:
            advisory = [w for w in ref_warnings if w not in unresolved]
            result = ValidationResult(
                valid=False,
                errors=result.errors + unresolved,
                warnings=result.warnings + advisory,
            )
        else:
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
            "Completeness witness: warn for declared references that do not resolve, "
            "known slots absent from the bundle, and referenced sidecars whose "
            "package_reference differs from the bundle's. Warnings only; they never "
            "change validity or the exit code unless --fail-on-reference-warnings "
            "is also given."
        ),
    )
    parser.add_argument(
        "--fail-on-reference-warnings",
        action="store_true",
        dest="fail_on_reference_warnings",
        help=(
            "With --check-references, treat unresolved declared references as "
            "validation failures (exit 1). Only unresolved references are escalated; "
            "omissions (a missing sidecar is allowed) and package_reference "
            "mismatches remain advisory. Structural rules are unchanged; no effect "
            "without --check-references."
        ),
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=None,
        help=(
            "Base directory for resolving references under --check-references "
            "(default: the bundle file's own directory)"
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

    result = validate_bundle_file(
        path,
        check_references=args.check_references,
        base=args.base,
        fail_on_reference_warnings=args.fail_on_reference_warnings,
    )

    if result.valid:
        if not args.quiet:
            print("PASS: traceability bundle is structurally valid")
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
