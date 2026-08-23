#!/usr/bin/env python3
"""
Creation Studio Capability Map Validator (structural layer)

Thin CLI adapter over ``scripts/_shared/creation_studio_capability_map.py``.
Reusable loading, indexing, and validation live in that module. This file
does not import other CLI scripts.

A capability map is an explicit, human-governed semantic bridge:

    A22 requested outcome
            ↓
    explicit A26 mapping
            ↓
    A23 declared Creation Studio capability

Usage:
    python scripts/validate_creation_studio_capability_map.py <map_json>
    python scripts/validate_creation_studio_capability_map.py \
        contracts/creation_studio_capability_map.json

Exit codes:
    0 — Capability map is structurally valid
    1 — Invalid map content (including unparseable map JSON)
    2 — Map file missing/unreadable, or authoritative A22 schema
        missing/unreadable/malformed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _shared.creation_studio_capability_map import (  # noqa: F401
    A22_SCHEMA,
    AUTHORITY_FLAGS,
    CAPABILITY_ID_PATTERN,
    KNOWN_TOP_LEVEL,
    MAPPING_FIELDS,
    RECORD_TYPE,
    VERSION_PATTERN,
    CapabilityMapContractError,
    CapabilityMapInputError,
    MapIdentity,
    ValidationResult,
    build_mapping_index,
    extract_map_identity,
    load_a22_request_enum,
    load_capability_map,
    load_json,
    validate_capability_map_document,
    validate_map,
    validate_map_file,
)


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

    try:
        result = validate_map_file(path)
    except CapabilityMapInputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

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
