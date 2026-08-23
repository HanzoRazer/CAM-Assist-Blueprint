#!/usr/bin/env python3
"""
Creation Studio Capability Map Validator (structural layer)

Validates the CAM-Assist-owned CAM-A26 mapping registry for:
- Correct record structure (record_type, record_version, map_version)
- mappings: an array of closed objects, each with a legal A22 source, a
  non-empty unique list of pattern-valid A23 targets, and a non-blank rationale
- no duplicate source identifiers across the array
- authority REQUIRED, with five const-true flags and no undeclared flags
- a closed top-level contract: unrecognized top-level fields are rejected

A capability map is an explicit, human-governed semantic bridge:

    A22 requested outcome
            ↓
    explicit A26 mapping
            ↓
    A23 declared Creation Studio capability

It does not infer similarity from names, does not rewrite A22 or A23 records,
does not authorize execution, does not confirm installation or reachability,
does not confirm machine readiness, and does not grant permission.

A22 SOURCE AUTHORITY
--------------------
`request_capability` is checked against the authoritative CAM-A22 enum in
`schemas/creation_studio_request.schema.json` (properties.requested_capabilities
.items.enum). This file does not duplicate that enum. An unknown source is a
structural error. A new A22 identifier becomes a legal mapping source the
moment it is added to the request schema.

A23 TARGETS REMAIN OPEN
-----------------------
`satisfied_by` entries are validated against the A23 identifier PATTERN
`^[a-z][a-z0-9_]*$`, not against any profile and not against a closed list. A
mapping may name a capability the supplied profile does not declare.

Versions are validated as semantic-version strings and never compared.

Usage:
    python scripts/validate_creation_studio_capability_map.py <map_json>
    python scripts/validate_creation_studio_capability_map.py \
        contracts/creation_studio_capability_map.json

Exit codes:
    0 — Capability map is structurally valid
    1 — Validation failed (including a JSON parse error or a non-object root)
    2 — File not found
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

RECORD_TYPE = "cam_assist_creation_studio_capability_map"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
# Mirrors CAM-A23's open identifier contract. Not an enum.
CAPABILITY_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
AUTHORITY_FLAGS = [
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
    "does_not_confirm_machine_readiness",
    "does_not_grant_permission",
]
MAPPING_FIELDS = ["request_capability", "satisfied_by", "rationale"]
KNOWN_TOP_LEVEL = [
    "record_type",
    "record_version",
    "map_version",
    "mappings",
    "authority",
]

A22_SCHEMA = (
    Path(__file__).resolve().parent.parent
    / "schemas"
    / "creation_studio_request.schema.json"
)


class ValidationResult(NamedTuple):
    valid: bool
    errors: list[str]
    warnings: list[str]


class MapIdentity(NamedTuple):
    """Provenance fields only. Versions are never interpreted."""

    record_version: str | None
    map_version: str | None


def load_a22_request_enum(schema_path: Path | None = None) -> list[str]:
    """Read the authoritative A22 request vocabulary from the request schema.

    This is the only source of legal mapping sources. Duplicating the enum here
    would let the map and the request contract drift.
    """
    path = schema_path if schema_path is not None else A22_SCHEMA
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"A22 request schema not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"A22 request schema is not valid JSON: {path} ({exc})") from exc

    try:
        enum = doc["properties"]["requested_capabilities"]["items"]["enum"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(
            f"A22 request schema is missing requested_capabilities.items.enum: {path}"
        ) from exc
    if not isinstance(enum, list) or not all(isinstance(v, str) for v in enum):
        raise RuntimeError(
            f"A22 requested_capabilities enum must be a list of strings: {path}"
        )
    return enum


def load_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle), None
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc}"
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except OSError as exc:
        return None, f"Error reading file: {exc}"


def validate_authority(authority: object, errors: list[str]) -> None:
    if not isinstance(authority, dict):
        errors.append("authority must be an object")
        return
    for flag in AUTHORITY_FLAGS:
        if flag not in authority:
            errors.append(f"authority.{flag} is required and must be true")
        elif authority.get(flag) is not True:
            errors.append(f"authority.{flag} must be true")
    for flag in authority:
        if flag not in AUTHORITY_FLAGS:
            errors.append(
                f"authority: unknown flag '{flag}' "
                f"(allowed: {', '.join(AUTHORITY_FLAGS)})"
            )


def validate_capability_identifier(value: object) -> str | None:
    """Check an A23 target against the open identifier pattern.

    Returns None when valid, otherwise a human-readable reason.
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


def validate_mapping_sources(
    request_capability: object,
    a22_enum: list[str],
    label: str,
    errors: list[str],
) -> str | None:
    """Validate one mapping source against the authoritative A22 enum."""
    if not isinstance(request_capability, str):
        errors.append(f"{label}.request_capability must be a string")
        return None
    if not request_capability.strip():
        errors.append(f"{label}.request_capability must be a non-blank string")
        return None
    if request_capability not in a22_enum:
        errors.append(
            f"{label}.request_capability: unknown request identifier "
            f"'{request_capability}' (must be an A22 requested_capabilities "
            f"enum value: {', '.join(a22_enum)})"
        )
        return None
    return request_capability


def validate_mapping_entry(
    index: int,
    entry: object,
    a22_enum: list[str],
    errors: list[str],
) -> str | None:
    """Validate one mapping object. Returns the source identifier when usable."""
    label = f"mappings[{index}]"
    if not isinstance(entry, dict):
        errors.append(f"{label} must be an object")
        return None

    for key in entry:
        if key not in MAPPING_FIELDS:
            errors.append(
                f"{label}: unknown field '{key}' "
                f"(allowed: {', '.join(MAPPING_FIELDS)})"
            )

    source = None
    if "request_capability" not in entry:
        errors.append(f"{label}.request_capability is required")
    else:
        source = validate_mapping_sources(
            entry["request_capability"], a22_enum, label, errors
        )

    if "satisfied_by" not in entry:
        errors.append(f"{label}.satisfied_by is required")
    else:
        targets = entry["satisfied_by"]
        if not isinstance(targets, list):
            errors.append(f"{label}.satisfied_by must be an array")
        elif not targets:
            errors.append(f"{label}.satisfied_by must list at least one capability")
        else:
            seen: set[str] = set()
            for target_index, target in enumerate(targets):
                reason = validate_capability_identifier(target)
                if reason is not None:
                    errors.append(f"{label}.satisfied_by[{target_index}] {reason}")
                    continue
                if target in seen:
                    errors.append(
                        f"{label}.satisfied_by: duplicate target '{target}'"
                    )
                seen.add(target)

    if "rationale" not in entry:
        errors.append(f"{label}.rationale is required")
    else:
        rationale = entry["rationale"]
        if not isinstance(rationale, str):
            errors.append(f"{label}.rationale must be a string")
        elif not rationale.strip():
            errors.append(f"{label}.rationale must be a non-blank string")

    return source


def validate_mappings(mappings: object, a22_enum: list[str], errors: list[str]) -> None:
    if not isinstance(mappings, list):
        errors.append("mappings must be an array")
        return

    seen: set[str] = set()
    for index, entry in enumerate(mappings):
        source = validate_mapping_entry(index, entry, a22_enum, errors)
        if source is None:
            continue
        if source in seen:
            errors.append(f"mappings: duplicate request_capability '{source}'")
        seen.add(source)


def validate_map(data: dict, a22_enum: list[str] | None = None) -> ValidationResult:
    """Validate a capability-map record (structural layer)."""
    errors: list[str] = []
    warnings: list[str] = []
    enum = a22_enum if a22_enum is not None else load_a22_request_enum()

    record_type = data.get("record_type")
    if record_type is None:
        errors.append("Missing required field: record_type")
    elif record_type != RECORD_TYPE:
        errors.append(
            f"Invalid record_type: '{record_type}'. Must be '{RECORD_TYPE}'"
        )

    for field in ("record_version", "map_version"):
        if field not in data:
            errors.append(f"Missing required field: {field}")
            continue
        value = data[field]
        if not isinstance(value, str) or not VERSION_PATTERN.fullmatch(value):
            errors.append(
                f"Invalid {field} format: '{value}'. "
                "Must be semantic version (e.g., '1.0.0')"
            )

    if "mappings" not in data:
        errors.append("Missing required field: mappings")
    else:
        validate_mappings(data["mappings"], enum, errors)

    if "authority" not in data:
        errors.append("Missing required field: authority")
    else:
        validate_authority(data["authority"], errors)

    for key in data:
        if key not in KNOWN_TOP_LEVEL:
            errors.append(
                f"unknown top-level field: '{key}' "
                f"(allowed: {', '.join(KNOWN_TOP_LEVEL)})"
            )

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def build_mapping_index(data: dict) -> dict[str, list[str]]:
    """request_capability → sorted unique satisfied_by identifiers.

    Sorting makes later reconciliation independent of mapping-array order.
    Callers must pass a structurally valid map.
    """
    index: dict[str, list[str]] = {}
    mappings = data.get("mappings")
    if not isinstance(mappings, list):
        return index
    for entry in mappings:
        if not isinstance(entry, dict):
            continue
        source = entry.get("request_capability")
        targets = entry.get("satisfied_by")
        if not isinstance(source, str) or not isinstance(targets, list):
            continue
        unique = sorted({t for t in targets if isinstance(t, str)})
        index[source] = unique
    return index


def extract_map_identity(data: dict) -> MapIdentity:
    def optional(key: str) -> str | None:
        value = data.get(key)
        return value if isinstance(value, str) else None

    return MapIdentity(
        record_version=optional("record_version"),
        map_version=optional("map_version"),
    )


def validate_map_file(path: Path) -> ValidationResult:
    data, load_error = load_json(path)
    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])
    if not isinstance(data, dict):
        return ValidationResult(
            valid=False, errors=["Capability map root must be a JSON object"], warnings=[]
        )
    return validate_map(data)


def load_capability_map(path: Path) -> tuple[dict, dict[str, list[str]], MapIdentity]:
    """Load a validated map, returning (document, index, identity).

    Raises ValueError with a joined diagnostic when the file is missing,
    unreadable, or structurally invalid. The reconciler turns that into an
    input failure (exit 2).
    """
    if not path.is_file():
        raise ValueError(f"Capability map not found: {path}")
    data, load_error = load_json(path)
    if load_error:
        raise ValueError(f"Capability map {load_error}")
    if not isinstance(data, dict):
        raise ValueError(f"Capability map must be a JSON object: {path}")
    result = validate_map(data)
    if not result.valid:
        joined = "; ".join(result.errors)
        raise ValueError(f"Capability map is structurally invalid: {path}: {joined}")
    return data, build_mapping_index(data), extract_map_identity(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Creation Studio capability map (structural layer)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("map_json", type=Path, help="Path to the capability map JSON file")
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only output errors, not success messages",
    )
    args = parser.parse_args()
    path: Path = args.map_json

    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 2

    result = validate_map_file(path)
    if result.valid:
        if not args.quiet:
            print("PASS: creation studio capability map is structurally valid")
        return 0

    print("FAIL: creation studio capability map validation failed", file=sys.stderr)
    for error in result.errors:
        print(f"  [ERR] {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
