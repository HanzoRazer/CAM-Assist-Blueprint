#!/usr/bin/env python3
"""
Creation Studio Capability Profile Validator (structural layer)

Validates read-only, informational CAM-Creation-Studio capability profiles for:
- Correct record structure (record_type, record_version)
- profile_version present and a semantic version (owned by Creation Studio,
  independent of the CAM Assist version)
- studio_reference present and a non-blank string
- publication_direction present and equal to 'creation_studio_to_cam_assist'
- capabilities: a non-empty array of closed objects, each with a pattern-valid
  capability_id, unique across the profile
- authority REQUIRED, with five const-true flags and no undeclared flags
- a closed top-level contract: unrecognized top-level fields are rejected. There
  is no created_at field on this record (the artifact is deterministic).

A capability profile is published BY CAM-Creation-Studio and consumed by CAM
Assist. Direction is inbound only (CAM-Creation-Studio -> CAM Assist). It
declares what Creation Studio is capable of AUTHORING -- not what has been
authored, approved, or executed. It is descriptive and advisory: it does not
authorize execution, does not request execution, does not bypass human review,
does not confirm machine readiness, does not validate machining, does not approve
strategies, and never requires CAM Assist to use a declared capability. No
capability implies approval.

The capability vocabulary is deliberately OPEN: capability_id is validated
against a stable identifier PATTERN rather than a closed enum, because Creation
Studio owns its own capability evolution. Compatibility rests on stable
identifiers plus semantic versioning, not on a vocabulary this repository would
have to amend for every upstream feature.

Identifier uniqueness is enforced HERE rather than in the schema: vanilla JSON
Schema cannot express uniqueness by object property (its uniqueItems only rejects
wholly identical entries). The schema documents the same split.

The STRUCTURAL layer (default) is filesystem-free: it opens only the profile file
itself and never resolves or stats declared documentation references. A profile
whose references do not exist still passes structurally.

The COMPLETENESS-WITNESS layer (opt-in --check-references) is a narrow EXISTENCE
witness. For each documentation_reference DECLARED in capabilities, it resolves
the path relative to the profile file's own directory and emits a WARNING when
the path does not resolve on disk. It is existence-only: it never opens, parses,
or schema-checks a referenced file, and emits no absent-reference findings (an
omitted reference is allowed and silent). It mutates nothing. These warnings never
change structural validity, and by default never change the exit code. The opt-in
--fail-on-reference-warnings mode is the sole exception: it promotes
unresolved-reference findings to errors (exit 1) so CI can enforce reference
completeness without altering any structural rule.

Usage:
    python scripts/validate_creation_studio_capability_profile.py <profile_json>
    python scripts/validate_creation_studio_capability_profile.py <profile_json> --check-references
    python scripts/validate_creation_studio_capability_profile.py examples/creation_studio/capability_profile.json

Exit codes:
    0 — Capability profile is structurally valid
    1 — Validation failed (including a JSON parse error or a non-object root)
    2 — File not found
"""

import argparse
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import NamedTuple

import json


RECORD_TYPE = "creation_studio_capability_profile"
PUBLICATION_DIRECTION = "creation_studio_to_cam_assist"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
# Stable identifier pattern (open vocabulary, not an enum). Mirrors the schema.
CAPABILITY_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
AUTHORITY_FLAGS = [
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
    "does_not_confirm_machine_readiness",
    "does_not_require_capability_use",
]
# Closed set of permitted keys on a capability entry (mirrors the schema).
CAPABILITY_FIELDS = [
    "capability_id",
    "display_name",
    "description",
    "documentation_reference",
]
# Optional capability fields that must be non-blank strings when present.
CAPABILITY_TEXT_FIELDS = ["display_name", "description"]
# Closed set of permitted top-level keys (mirrors the schema's
# additionalProperties: false). There is no created_at on this record.
KNOWN_TOP_LEVEL = [
    "record_type",
    "record_version",
    "profile_version",
    "studio_reference",
    "publication_direction",
    "capabilities",
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


def is_absolute_reference(value: str) -> bool:
    """True if a documentation reference is an absolute (non-portable) path.

    References are resolved relative to the profile file's own location. An
    absolute path silently escapes that base (``base / "/abs"`` discards the
    base entirely under pathlib), so it is a contract violation, not a valid
    reference. Detect absolute forms in either path flavor: POSIX ('/x'),
    Windows drive-absolute ('C:/x', 'C:\\x'), UNC, drive-relative ('C:x'), and
    a leading slash/backslash root.
    """
    v = value.strip()
    if PurePosixPath(v).is_absolute() or PureWindowsPath(v).is_absolute():
        return True
    if v.startswith(("/", "\\")):
        return True
    if len(v) >= 2 and v[1] == ":" and v[0].isalpha():
        return True
    return False


def validate_capability_identifier(value: object) -> str | None:
    """Check a capability_id against the stable identifier contract.

    Returns None when valid, otherwise a human-readable reason. The vocabulary is
    open by design (see module docstring): only the SHAPE of the identifier is
    constrained, never the set of allowed values.
    """
    if not isinstance(value, str):
        return "must be a string"
    if not value.strip():
        return "must be a non-blank string"
    if not CAPABILITY_ID_PATTERN.fullmatch(value):
        return (
            "must match ^[a-z][a-z0-9_]*$ (lowercase letters, digits and "
            f"underscores, starting with a letter): '{value}'"
        )
    return None


def validate_authority(authority: object, errors: list[str]) -> None:
    """Validate the required informational authority block.

    Every one of the five flags must be declared and true. (On a profile the
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
    # The non-authority declaration is a closed contract: reject undeclared flags
    # so a contradictory one (e.g. an execution-granting flag) cannot ride along.
    for flag in authority:
        if flag not in AUTHORITY_FLAGS:
            errors.append(
                f"authority: unknown flag '{flag}' "
                f"(allowed: {', '.join(AUTHORITY_FLAGS)})"
            )


def validate_capability_entry(index: int, entry: object, errors: list[str]) -> str | None:
    """Validate a single capability entry. Returns its capability_id when usable.

    Only the entry's SHAPE is checked. The validator never asks whether a
    declared capability is supported, appropriate, or approved: a profile records
    declared support, and support is Creation Studio's to declare.
    """
    label = f"capabilities[{index}]"
    if not isinstance(entry, dict):
        errors.append(f"{label} must be an object")
        return None

    for key in entry:
        if key not in CAPABILITY_FIELDS:
            errors.append(
                f"{label}: unknown field '{key}' "
                f"(allowed: {', '.join(CAPABILITY_FIELDS)})"
            )

    capability_id: str | None = None
    if "capability_id" not in entry:
        errors.append(f"{label}.capability_id is required")
    else:
        reason = validate_capability_identifier(entry["capability_id"])
        if reason is not None:
            errors.append(f"{label}.capability_id {reason}")
        else:
            capability_id = entry["capability_id"]

    for field in CAPABILITY_TEXT_FIELDS:
        if field not in entry:
            continue
        value = entry[field]
        if not isinstance(value, str):
            errors.append(f"{label}.{field} must be a string")
        elif not value.strip():
            errors.append(f"{label}.{field} must be a non-blank string")

    if "documentation_reference" in entry:
        value = entry["documentation_reference"]
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label}.documentation_reference must be a non-empty string path")
        elif is_absolute_reference(value):
            errors.append(
                f"{label}.documentation_reference must be a relative path "
                f"(absolute paths are not portable): '{value}'"
            )

    return capability_id


def validate_capabilities(capabilities: object, errors: list[str]) -> None:
    """Validate the capabilities array: non-empty, well-shaped, unique identifiers."""
    if not isinstance(capabilities, list):
        errors.append("capabilities must be an array")
        return
    if not capabilities:
        errors.append("capabilities must declare at least one capability")

    seen: set[str] = set()
    for index, entry in enumerate(capabilities):
        capability_id = validate_capability_entry(index, entry, errors)
        if capability_id is None:
            continue
        # Uniqueness lives here, not in the schema: vanilla JSON Schema cannot
        # express uniqueness by object property.
        if capability_id in seen:
            errors.append(f"capabilities: duplicate capability_id '{capability_id}'")
        seen.add(capability_id)


def validate_profile(data: dict) -> ValidationResult:
    """Validate a creation studio capability profile record (structural layer)."""
    errors: list[str] = []
    warnings: list[str] = []

    record_type = data.get("record_type")
    if record_type is None:
        errors.append("Missing required field: record_type")
    elif record_type != RECORD_TYPE:
        errors.append(f"Invalid record_type: '{record_type}'. Must be '{RECORD_TYPE}'")

    for field in ("record_version", "profile_version"):
        if field not in data:
            errors.append(f"Missing required field: {field}")
            continue
        value = data[field]
        if not isinstance(value, str) or not VERSION_PATTERN.fullmatch(value):
            errors.append(
                f"Invalid {field} format: '{value}'. "
                "Must be semantic version (e.g., '1.0.0')"
            )

    studio_reference = data.get("studio_reference")
    if "studio_reference" not in data:
        errors.append("Missing required field: studio_reference")
    elif not isinstance(studio_reference, str) or not studio_reference.strip():
        errors.append("'studio_reference' must be a non-empty string")

    publication_direction = data.get("publication_direction")
    if "publication_direction" not in data:
        errors.append("Missing required field: publication_direction")
    elif publication_direction != PUBLICATION_DIRECTION:
        errors.append(
            f"Invalid publication_direction: '{publication_direction}'. "
            f"Must be '{PUBLICATION_DIRECTION}'"
        )

    if "capabilities" not in data:
        errors.append("Missing required field: capabilities")
    else:
        validate_capabilities(data["capabilities"], errors)

    if "authority" not in data:
        errors.append("Missing required field: authority")
    else:
        validate_authority(data["authority"], errors)

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


def check_reference_existence(data: dict, base_dir: Path) -> list[str]:
    """Existence witness (warnings only).

    For each documentation_reference DECLARED on a capability, resolve it relative
    to base_dir and warn when it does not resolve on disk. Existence only: never
    opens, parses, or schema-checks a referenced file, and emits NO
    absent-reference findings (an omitted reference is allowed and silent).
    Mutates nothing. Callers must not let these warnings affect validity or the
    exit code.
    """
    warnings: list[str] = []
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list):
        return warnings
    for entry in capabilities:
        if not isinstance(entry, dict):
            continue
        reference = entry.get("documentation_reference")
        if not isinstance(reference, str) or not reference.strip():
            continue
        capability_id = entry.get("capability_id")
        label = capability_id if isinstance(capability_id, str) else "<unknown capability>"
        if not (base_dir / reference).exists():
            warnings.append(
                f"{label}: documentation_reference does not resolve: {reference}"
            )
    return warnings


def validate_profile_file(
    path: Path,
    check_references: bool = False,
    fail_on_reference_warnings: bool = False,
) -> ValidationResult:
    data, load_error = load_json(path)
    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])
    if not isinstance(data, dict):
        return ValidationResult(
            valid=False, errors=["Capability profile root must be a JSON object"], warnings=[]
        )
    result = validate_profile(data)
    # The existence witness runs only on a structurally valid profile. By default
    # its findings are warnings — structure dominates and the exit code is
    # unchanged. The opt-in --fail-on-reference-warnings mode is the sole
    # exception: it promotes unresolved-reference findings to errors so CI can
    # enforce reference completeness. Structural rules are never affected either way.
    if check_references and result.valid:
        ref_warnings = check_reference_existence(data, path.parent)
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
        description="Validate Creation Studio capability profile (structural layer)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("profile_json", type=Path, help="Path to the capability profile JSON file")
    parser.add_argument(
        "--check-references",
        action="store_true",
        help=(
            "Existence witness: warn for declared documentation references that do "
            "not resolve relative to the profile file's directory. Existence only -- "
            "never parses referenced content or reports omitted references. Warnings "
            "only; they never change validity or the exit code unless "
            "--fail-on-reference-warnings is also given."
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
    path: Path = args.profile_json

    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 2

    result = validate_profile_file(
        path,
        check_references=args.check_references,
        fail_on_reference_warnings=args.fail_on_reference_warnings,
    )

    if result.valid:
        if not args.quiet:
            print("PASS: creation studio capability profile is structurally valid")
            for warning in result.warnings:
                print(f"  [WARN] {warning}")
        return 0
    else:
        print("FAIL: creation studio capability profile validation failed", file=sys.stderr)
        for error in result.errors:
            print(f"  [ERR] {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"  [WARN] {warning}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
