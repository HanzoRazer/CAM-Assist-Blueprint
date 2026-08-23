"""
Reusable CAM-A26 capability-map loading and indexing.

Import-stable module. CLI adapters in ``scripts/`` consume this file; they
must not import one another. This module has no argument parsing and no
printing.

A22 SOURCE AUTHORITY
--------------------
Mapping sources are checked against
``schemas/creation_studio_request.schema.json``
(``properties.requested_capabilities.items.enum``). The enum is not copied
here.

A23 TARGETS REMAIN OPEN
-----------------------
``satisfied_by`` entries are pattern-constrained, not enumerated.
"""

from __future__ import annotations

import json
import posixpath
import re
from pathlib import Path, PurePosixPath
from typing import NamedTuple

RECORD_TYPE = "cam_assist_creation_studio_capability_map"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
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

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
A22_SCHEMA = REPO_ROOT / "schemas" / "creation_studio_request.schema.json"


class CapabilityMapInputError(Exception):
    """A required file is missing or unreadable, including the A22 schema."""


class CapabilityMapContractError(Exception):
    """Readable input that is not a usable capability map, or a helper
    invoked with data it cannot index."""


class ValidationResult(NamedTuple):
    valid: bool
    errors: list[str]
    warnings: list[str]


class MapIdentity(NamedTuple):
    """Provenance fields only. Versions are never interpreted."""

    record_version: str | None
    map_version: str | None


def normalize_provenance_path(path: Path | str) -> str:
    """POSIX-normalize a provenance path without absolutizing it.

    ``./contracts/x.json`` and ``contracts/../contracts/x.json`` collapse to
    the same relative spelling. ``Path.resolve()`` is not used.
    """
    raw = path.as_posix() if isinstance(path, Path) else PurePosixPath(path).as_posix()
    return posixpath.normpath(raw)


def load_a22_request_enum(schema_path: Path | None = None) -> list[str]:
    """Read the authoritative A22 request vocabulary from the request schema."""
    path = schema_path if schema_path is not None else A22_SCHEMA
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CapabilityMapInputError(f"A22 request schema not found: {path}") from exc
    except OSError as exc:
        raise CapabilityMapInputError(
            f"A22 request schema could not be read: {path} ({exc})"
        ) from exc
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CapabilityMapInputError(
            f"A22 request schema is not valid JSON: {path} ({exc})"
        ) from exc

    try:
        enum = doc["properties"]["requested_capabilities"]["items"]["enum"]
    except (KeyError, TypeError) as exc:
        raise CapabilityMapInputError(
            f"A22 request schema is missing requested_capabilities.items.enum: {path}"
        ) from exc
    if not isinstance(enum, list) or not all(isinstance(v, str) for v in enum):
        raise CapabilityMapInputError(
            f"A22 requested_capabilities enum must be a list of strings: {path}"
        )
    return enum


def load_json(path: Path) -> tuple[dict | None, str | None]:
    """Load a JSON object. Returns (data, error).

    Distinguishes missing/unreadable (caller may escalate to input error)
    from parse failures (invalid content).
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle), None
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: {exc}"
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except OSError as exc:
        return None, f"Error reading file: {exc}"


def load_capability_map_document(path: Path) -> dict:
    """Load map JSON, raising typed errors for missing/unreadable/non-object."""
    if not path.is_file():
        raise CapabilityMapInputError(f"Capability map not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CapabilityMapInputError(
            f"Capability map could not be read: {path} ({exc})"
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CapabilityMapContractError(
            f"Capability map is not valid JSON: {path} ({exc})"
        ) from exc
    if not isinstance(data, dict):
        raise CapabilityMapContractError(f"Capability map must be a JSON object: {path}")
    return data


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
                    errors.append(f"{label}.satisfied_by: duplicate target '{target}'")
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


def validate_capability_map_document(
    data: dict, a22_enum: list[str] | None = None
) -> ValidationResult:
    """Validate a capability-map record (structural layer).

    Raises ``CapabilityMapInputError`` when the authoritative A22 schema
    cannot be loaded and ``a22_enum`` was not supplied.
    """
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


# Back-compat alias used by the validator adapter and existing tests.
validate_map = validate_capability_map_document


def build_mapping_index(data: dict) -> dict[str, list[str]]:
    """request_capability → sorted unique satisfied_by identifiers.

    Callers supply structurally usable mappings. Malformed rows raise
    ``CapabilityMapContractError`` rather than being skipped. This is not a
    second validator: A22 enum membership and A23 identifier syntax are not
    checked here.
    """
    if not isinstance(data, dict):
        raise CapabilityMapContractError("capability map must be an object")
    mappings = data.get("mappings")
    if mappings is None:
        raise CapabilityMapContractError("mappings is required")
    if not isinstance(mappings, list):
        raise CapabilityMapContractError("mappings must be an array")

    index: dict[str, list[str]] = {}
    for index_i, entry in enumerate(mappings):
        label = f"mappings[{index_i}]"
        if not isinstance(entry, dict):
            raise CapabilityMapContractError(f"{label} must be an object")
        source = entry.get("request_capability")
        if not isinstance(source, str) or not source.strip():
            raise CapabilityMapContractError(
                f"{label}.request_capability must be a non-blank string"
            )
        targets = entry.get("satisfied_by")
        if not isinstance(targets, list):
            raise CapabilityMapContractError(f"{label}.satisfied_by must be an array")
        unique: list[str] = []
        seen: set[str] = set()
        for target_index, target in enumerate(targets):
            if not isinstance(target, str) or not target.strip():
                raise CapabilityMapContractError(
                    f"{label}.satisfied_by[{target_index}] must be a non-blank string"
                )
            if target not in seen:
                unique.append(target)
                seen.add(target)
        index[source] = sorted(unique)
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
    """Structural validation of a map file for the validator CLI.

    Missing/unreadable files and A22-schema failures raise
    ``CapabilityMapInputError`` (exit 2). Parse errors and invalid content
    return ``valid=False`` (exit 1).
    """
    if not path.is_file():
        raise CapabilityMapInputError(f"File not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CapabilityMapInputError(f"Error reading file: {path} ({exc})") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return ValidationResult(
            valid=False, errors=[f"JSON parse error: {exc}"], warnings=[]
        )
    if not isinstance(data, dict):
        return ValidationResult(
            valid=False,
            errors=["Capability map root must be a JSON object"],
            warnings=[],
        )
    return validate_capability_map_document(data)


def load_capability_map(path: Path) -> tuple[dict, dict[str, list[str]], MapIdentity]:
    """Load a validated map, returning (document, index, identity)."""
    data = load_capability_map_document(path)
    result = validate_capability_map_document(data)
    if not result.valid:
        joined = "; ".join(result.errors)
        raise CapabilityMapContractError(
            f"Capability map is structurally invalid: {path}: {joined}"
        )
    return data, build_mapping_index(data), extract_map_identity(data)
