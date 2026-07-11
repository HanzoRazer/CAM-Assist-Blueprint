#!/usr/bin/env python3
"""
CAM Assist Creation Studio Capability Request Validator (structural layer)

Validates advisory, reference-only CAM-Creation-Studio capability requests for:
- Correct record structure (record_type, record_version)
- package_reference present and a non-empty string
- request_direction present and equal to 'cam_assist_to_creation_studio'
- requested_capabilities: a non-empty array of unique, known-vocabulary strings
- authority REQUIRED, with five const-true flags and no undeclared flags
- contents present and object-shaped, restricted to known slots, string values
- request_context optional; when present, object-shaped with known informational
  fields of the right types
- a closed top-level contract: unrecognized top-level fields are rejected. There
  is no created_at field on this record (the artifact is deterministic).

A request is a contract-first interoperability probe describing what downstream
machining-development assistance CAM Assist is requesting from the separate
CAM-Creation-Studio product. Direction is outbound only (CAM Assist ->
CAM-Creation-Studio). The referenced files remain authoritative; the request does
not own, copy, or mutate them. It is advisory only: it does not authorize machine
execution, does not bypass human review, does not confirm machine readiness, does
not require G-code generation, and does not assert that CAM-Creation-Studio
supports any requested capability.

The STRUCTURAL layer (default) is filesystem-free: it opens only the request file
itself and never resolves or stats the referenced files. A request whose
references do not exist still passes structurally.

The COMPLETENESS-WITNESS layer (opt-in --check-references) is a narrow EXISTENCE
witness. For each reference DECLARED in contents, it resolves the path relative to
the request file's own directory and emits a WARNING when the path does not
resolve on disk. It is existence-only: it never opens, parses, or schema-checks a
referenced file; it performs no package_reference cross-check, no capability
support check, and no absent-slot/omission findings (an omitted reference is
allowed and silent). It mutates nothing. These warnings never change structural
validity, and by default never change the exit code. The opt-in
--fail-on-reference-warnings mode is the sole exception: it promotes
unresolved-reference findings to errors (exit 1) so CI can enforce reference
completeness without altering any structural rule.

Usage:
    python scripts/validate_creation_studio_request.py <request_json>
    python scripts/validate_creation_studio_request.py <request_json> --check-references
    python scripts/validate_creation_studio_request.py examples/creation_studio/ltb_vcarve_synthetic_example_request.json

Exit codes:
    0 — Request record is structurally valid
    1 — Validation failed (including a JSON parse error or a non-object root)
    2 — File not found
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

import json


RECORD_TYPE = "cam_assist_creation_studio_request"
REQUEST_DIRECTION = "cam_assist_to_creation_studio"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
AUTHORITY_FLAGS = [
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
    "does_not_confirm_machine_readiness",
    "does_not_require_gcode_generation",
]
CAPABILITY_VOCABULARY = [
    "feeds_speeds_recommendation",
    "tooling_review",
    "operation_sequence_analysis",
    "cycle_time_estimation",
    "simulation_request",
    "gcode_explanation",
    "toolpath_development_request",
    "workholding_review",
]
CONTENT_SLOTS = [
    "package_manifest_file",
    "strategy_file",
    "review_packet_file",
    "traceability_bundle_file",
    "production_shop_handoff_file",
]
CONTEXT_FIELDS = ["material", "machine_profile", "operator_notes"]
# Closed set of permitted top-level keys (mirrors the schema's
# additionalProperties: false). There is no created_at on this record.
KNOWN_TOP_LEVEL = [
    "record_type",
    "record_version",
    "package_reference",
    "request_direction",
    "requested_capabilities",
    "contents",
    "request_context",
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


def validate_authority(authority: object, errors: list[str]) -> None:
    """Validate the required informational authority block.

    Every one of the five flags must be declared and true. (On a request the
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
    # The non-execution declaration is a closed contract: reject undeclared flags
    # so a contradictory one (e.g. an execution-granting flag) cannot ride along.
    for flag in authority:
        if flag not in AUTHORITY_FLAGS:
            errors.append(
                f"authority: unknown flag '{flag}' "
                f"(allowed: {', '.join(AUTHORITY_FLAGS)})"
            )


def validate_capabilities(capabilities: object, errors: list[str]) -> None:
    """Validate requested_capabilities: non-empty array of unique known strings."""
    if not isinstance(capabilities, list):
        errors.append("requested_capabilities must be an array")
        return
    if not capabilities:
        errors.append("requested_capabilities must list at least one capability")
    seen: set[str] = set()
    for entry in capabilities:
        if not isinstance(entry, str):
            errors.append("requested_capabilities entries must be strings")
            continue
        if entry not in CAPABILITY_VOCABULARY:
            errors.append(
                f"requested_capabilities: unknown capability '{entry}' "
                f"(allowed: {', '.join(CAPABILITY_VOCABULARY)})"
            )
        if entry in seen:
            errors.append(f"requested_capabilities: duplicate capability '{entry}'")
        seen.add(entry)


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


def validate_request_context(context: object, errors: list[str]) -> None:
    """Validate the optional request_context object (types only, informational).

    Closed to the known fields. material and operator_notes are strings;
    machine_profile is a string or null. No field is required and none affects
    authority or validity beyond being well-typed.
    """
    if not isinstance(context, dict):
        errors.append("request_context must be an object")
        return
    for key, value in context.items():
        if key not in CONTEXT_FIELDS:
            errors.append(
                f"request_context: unknown field '{key}' "
                f"(allowed: {', '.join(CONTEXT_FIELDS)})"
            )
            continue
        if key == "machine_profile":
            if value is not None and not isinstance(value, str):
                errors.append("request_context.machine_profile must be a string or null")
        elif not isinstance(value, str):
            errors.append(f"request_context.{key} must be a string")


def validate_request(data: dict) -> ValidationResult:
    """Validate a creation studio capability request record (structural layer)."""
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

    request_direction = data.get("request_direction")
    if "request_direction" not in data:
        errors.append("Missing required field: request_direction")
    elif request_direction != REQUEST_DIRECTION:
        errors.append(
            f"Invalid request_direction: '{request_direction}'. Must be '{REQUEST_DIRECTION}'"
        )

    if "requested_capabilities" not in data:
        errors.append("Missing required field: requested_capabilities")
    else:
        validate_capabilities(data["requested_capabilities"], errors)

    if "authority" not in data:
        errors.append("Missing required field: authority")
    else:
        validate_authority(data["authority"], errors)

    if "contents" not in data:
        errors.append("Missing required field: contents")
    else:
        validate_contents(data["contents"], errors, warnings)

    # request_context is optional, but when present it must be well-typed.
    if "request_context" in data:
        validate_request_context(data["request_context"], errors)

    # Closed top-level contract (mirrors the schema's additionalProperties: false):
    # an unrecognized top-level key is rejected so stray/misleading fields cannot
    # ride along unnoticed. (created_at is deliberately not a known field.)
    for key in data:
        if key not in KNOWN_TOP_LEVEL:
            errors.append(
                f"unknown top-level field: '{key}' "
                f"(allowed: {', '.join(KNOWN_TOP_LEVEL)})"
            )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def collect_reference_findings(data: dict, base_dir: Path) -> list[str]:
    """Existence witness (warnings only).

    For each reference DECLARED in contents, resolve it relative to base_dir and
    warn when it does not resolve on disk. Existence only: never opens, parses,
    or schema-checks a referenced file, performs no package_reference cross-check,
    and emits NO absent-slot/omission findings (an omitted reference is allowed
    and silent). Mutates nothing. Callers must not let these warnings affect
    validity or the exit code.
    """
    warnings: list[str] = []
    contents = data.get("contents")
    if not isinstance(contents, dict):
        contents = {}
    for slot in CONTENT_SLOTS:
        value = contents.get(slot)
        if isinstance(value, str) and value.strip():
            resolved = base_dir / value
            if not resolved.exists():
                warnings.append(f"{slot} reference does not resolve: {value}")
    return warnings


def validate_request_file(
    path: Path,
    check_references: bool = False,
    fail_on_reference_warnings: bool = False,
) -> ValidationResult:
    data, load_error = load_json(path)
    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])
    if not isinstance(data, dict):
        return ValidationResult(
            valid=False, errors=["Request root must be a JSON object"], warnings=[]
        )
    result = validate_request(data)
    # The existence witness runs only on a structurally valid request. By default
    # its findings are warnings — structure dominates and the exit code is
    # unchanged. The opt-in --fail-on-reference-warnings mode is the sole
    # exception: it promotes unresolved-reference findings to errors so CI can
    # enforce reference completeness. Structural rules are never affected either way.
    if check_references and result.valid:
        ref_warnings = collect_reference_findings(data, path.parent)
        if fail_on_reference_warnings and ref_warnings:
            result = ValidationResult(
                valid=False,
                errors=result.errors + ref_warnings,
                warnings=result.warnings,
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
        description="Validate CAM Assist creation studio capability request (structural layer)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("request_json", type=Path, help="Path to the request JSON file")
    parser.add_argument(
        "--check-references",
        action="store_true",
        help=(
            "Existence witness: warn for declared references that do not resolve "
            "relative to the request file's directory. Existence only -- never "
            "parses referenced content, cross-checks package_reference, or reports "
            "omitted slots. Warnings only; they never change validity or the exit code "
            "unless --fail-on-reference-warnings is also given."
        ),
    )
    parser.add_argument(
        "--fail-on-reference-warnings",
        action="store_true",
        dest="fail_on_reference_warnings",
        help=(
            "With --check-references, treat unresolved declared references as "
            "validation failures (exit 1) instead of warnings. Structural rules are "
            "unchanged; this only upgrades reference-existence findings for CI "
            "enforcement. No effect without --check-references."
        ),
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output errors, not success messages or warnings",
    )

    args = parser.parse_args()
    path: Path = args.request_json

    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 2

    result = validate_request_file(
        path,
        check_references=args.check_references,
        fail_on_reference_warnings=args.fail_on_reference_warnings,
    )

    if result.valid:
        if not args.quiet:
            print("PASS: creation studio request is structurally valid")
            for warning in result.warnings:
                print(f"  [WARN] {warning}")
        return 0
    else:
        print("FAIL: creation studio request validation failed", file=sys.stderr)
        for error in result.errors:
            print(f"  [ERR] {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"  [WARN] {warning}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
