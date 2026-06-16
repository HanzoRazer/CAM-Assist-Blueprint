#!/usr/bin/env python3
"""
CAM Assist Revision Lineage Validator

Validates revision lineage sidecar files for:
- Correct record structure
- Required fields present on each revision (revision_id, summary)
- Lineage integrity: unique ids, no dangling/self/cyclic supersession, at least one root
- Authority constraints preserved (when present)

Revision lineage is a package-scoped narrative chain. It is informational only;
it does not grant execution authority and is NOT artifact version control.

Usage:
    python scripts/validate_revision_lineage.py <lineage_json>
    python scripts/validate_revision_lineage.py examples/traceability/revision_lineage_example.json

Exit codes:
    0 — Revision lineage record is valid
    1 — Validation failed
    2 — File/read error
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

import json


RECORD_TYPE = "cam_assist_revision_lineage"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
AUTHORITY_FLAGS = [
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
]
RELATED_RECORD_FIELDS = [
    "assumptions_file",
    "risk_file",
    "decision_record_file",
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


def validate_related_records(related: object, prefix: str, errors: list[str]) -> None:
    """Validate an optional related_records block on a revision.

    When present it must be an object, and any known pointer field must be a
    string path. Pointers are referenced, never resolved or mutated; this only
    checks shape, not file existence or package affinity.
    """
    if not isinstance(related, dict):
        errors.append(f"{prefix}: related_records must be an object")
        return
    for field in RELATED_RECORD_FIELDS:
        if field in related and not isinstance(related.get(field), str):
            errors.append(f"{prefix}: related_records.{field} must be a string path when present")


def validate_lineage_integrity(revisions: list[dict], errors: list[str], warnings: list[str]) -> None:
    """Validate the supersession chain.

    Checks (errors): duplicate revision_id, dangling supersedes, self-supersession,
    cycles, and zero roots. A forked lineage (more than one root) is a warning only,
    preserving informational (non-enforcing) behavior.
    """
    # Collect ids of well-formed revisions (those with a usable string revision_id).
    ids: list[str] = []
    seen: set[str] = set()
    for i, revision in enumerate(revisions):
        if not isinstance(revision, dict):
            continue
        rid = revision.get("revision_id")
        if not isinstance(rid, str) or not rid.strip():
            continue
        if rid in seen:
            errors.append(f"revisions[{i}]: duplicate revision_id '{rid}'")
        else:
            seen.add(rid)
            ids.append(rid)

    if not seen:
        # Field-level validation already reported the missing ids; nothing more to do.
        return

    # supersedes references and pointer integrity. A revision with no supersedes
    # (key absent) is a root.
    supersedes_map: dict[str, str] = {}
    roots = 0
    for i, revision in enumerate(revisions):
        if not isinstance(revision, dict):
            continue
        rid = revision.get("revision_id")
        if not isinstance(rid, str) or not rid.strip():
            continue
        if "supersedes" not in revision:
            roots += 1
            continue
        sup = revision.get("supersedes")
        if not isinstance(sup, str) or not sup.strip():
            errors.append(f"revisions[{i}] ('{rid}'): supersedes must be a non-empty string when present")
            continue
        if sup == rid:
            errors.append(f"revisions[{i}] ('{rid}'): revision cannot supersede itself")
            continue
        if sup not in seen:
            errors.append(
                f"revisions[{i}] ('{rid}'): supersedes references unknown revision_id '{sup}'"
            )
            continue
        # Only record edges that point at a known, distinct id for cycle detection.
        supersedes_map[rid] = sup

    # Cycle detection over the supersedes edges (rid -> the id it supersedes).
    if _has_cycle(supersedes_map):
        errors.append("revisions: supersession chain contains a cycle")
        return

    if roots == 0:
        errors.append(
            "revisions: no root revision found (every revision supersedes another) — "
            "the chain is broken or cyclic"
        )
    elif roots > 1:
        warnings.append(
            f"revisions: {roots} root revisions found (forked lineage) — "
            "permitted, but lineage is not a single chain"
        )


def _has_cycle(edges: dict[str, str]) -> bool:
    """Detect a cycle in a functional graph where edges[node] -> superseded node."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in edges}

    def visit(node: str) -> bool:
        color[node] = GRAY
        nxt = edges.get(node)
        if nxt is not None and nxt in edges:
            if color.get(nxt) == GRAY:
                return True
            if color.get(nxt) == WHITE and visit(nxt):
                return True
        color[node] = BLACK
        return False

    for node in edges:
        if color[node] == WHITE and visit(node):
            return True
    return False


def validate_lineage(data: dict) -> ValidationResult:
    """Validate a revision lineage record."""
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

    if "revisions" not in data:
        errors.append("Missing required field: revisions")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    revisions = data.get("revisions", [])
    if not isinstance(revisions, list):
        errors.append("revisions must be an array")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    if not revisions:
        warnings.append("revisions array is empty")

    for i, revision in enumerate(revisions):
        prefix = f"revisions[{i}]"
        if not isinstance(revision, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        for field in ("revision_id", "summary"):
            value = revision.get(field)
            if field not in revision:
                errors.append(f"{prefix}: missing required field '{field}'")
            elif not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}: '{field}' must be a non-empty string")
        if "related_records" in revision:
            validate_related_records(revision["related_records"], prefix, errors)

    validate_lineage_integrity(revisions, errors, warnings)

    if "authority" in data:
        validate_authority(data["authority"], errors)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def validate_lineage_file(path: Path) -> ValidationResult:
    data, load_error = load_json(path)
    if load_error:
        return ValidationResult(valid=False, errors=[load_error], warnings=[])
    return validate_lineage(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate CAM Assist revision lineage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("lineage_json", type=Path, help="Path to the revision lineage JSON file")
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output errors, not success messages or warnings",
    )

    args = parser.parse_args()
    path: Path = args.lineage_json

    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        return 2

    result = validate_lineage_file(path)

    if result.valid:
        if not args.quiet:
            print("PASS: revision lineage is valid")
            for warning in result.warnings:
                print(f"  [WARN] {warning}")
        return 0
    else:
        print("FAIL: revision lineage validation failed", file=sys.stderr)
        for error in result.errors:
            print(f"  [ERR] {error}", file=sys.stderr)
        for warning in result.warnings:
            print(f"  [WARN] {warning}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
