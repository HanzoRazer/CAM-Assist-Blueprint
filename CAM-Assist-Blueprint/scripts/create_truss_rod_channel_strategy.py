#!/usr/bin/env python3
"""
CAM Assist Truss Rod Channel Strategy Creator

Transforms a reviewed truss-rod-channel specification into a deterministic
manufacturing-strategy JSON document.

This creator is non-executing. It does not generate G-code, cutter-center
offsets, DXF geometry, or machine instructions.

Usage:
    python scripts/create_truss_rod_channel_strategy.py \\
        examples/operations/truss_rod_channel_example.json
    python scripts/create_truss_rod_channel_strategy.py input.json --out strategy.json
    python scripts/create_truss_rod_channel_strategy.py input.json --out strategy.json --force

Exit codes:
    0 — Strategy written
    1 — Validation or argument error
    2 — File/read/write error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).parent))

from _shared.truss_rod_channel import TrussRodChannelError, build_channel_strategy
from version import CAM_ASSIST_VERSION


class CreateResult(NamedTuple):
    success: bool
    output_path: Path | None
    error: str | None
    exit_code: int


def dump_strategy(data: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def create_strategy(input_path: Path, output_path: Path, force: bool = False) -> CreateResult:
    if not input_path.exists():
        return CreateResult(False, None, f"File not found: {input_path}", 2)
    if not input_path.is_file():
        return CreateResult(False, None, f"Path is not a file: {input_path}", 2)

    try:
        raw = input_path.read_text(encoding="utf-8")
        request = json.loads(raw)
    except json.JSONDecodeError as exc:
        return CreateResult(False, None, f"JSON parse error: {exc}", 2)
    except OSError as exc:
        return CreateResult(False, None, f"Failed to read input: {exc}", 2)

    try:
        strategy = build_channel_strategy(request, CAM_ASSIST_VERSION)
    except TrussRodChannelError as exc:
        return CreateResult(False, None, str(exc), 1)

    if output_path.exists() and not force:
        return CreateResult(
            False,
            None,
            f"Output file already exists: {output_path} (use --force to overwrite)",
            1,
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dump_strategy(strategy, output_path)
    except OSError as exc:
        return CreateResult(False, None, f"Failed to write strategy: {exc}", 2)

    return CreateResult(True, output_path, None, 0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a CAM Assist truss-rod-channel manufacturing strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input_json", type=Path, help="Path to the operation input JSON")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output strategy JSON path (default: <input>_strategy.json)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Print only the output path")
    args = parser.parse_args()

    output_path = args.out
    if output_path is None:
        output_path = args.input_json.with_name(f"{args.input_json.stem}_strategy.json")

    result = create_strategy(args.input_json, output_path, force=args.force)
    if result.success:
        if args.quiet:
            print(str(result.output_path))
        else:
            print(f"PASS: truss rod channel strategy written: {result.output_path}")
        return 0

    prefix = "FAIL" if result.exit_code == 1 else "Error"
    print(f"{prefix}: {result.error}", file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
