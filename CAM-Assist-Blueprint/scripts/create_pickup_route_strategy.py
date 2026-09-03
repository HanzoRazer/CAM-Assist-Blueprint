#!/usr/bin/env python3
"""
CAM Assist Pickup Route Strategy Creator

Transforms a reviewed pickup-route specification into a deterministic
manufacturing-strategy JSON document.

This creator is non-executing. It does not generate G-code, cutter-center
offsets, DXF geometry, or machine instructions.

Usage:
    python scripts/create_pickup_route_strategy.py \\
        examples/operations/pickup_route_example.json
    python scripts/create_pickup_route_strategy.py input.json --out strategy.json
    python scripts/create_pickup_route_strategy.py --input input.json --out strategy.json
    python scripts/create_pickup_route_strategy.py input.json --out strategy.json --force

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

from _shared.pickup_route import PickupRouteError, build_pickup_route_strategy
from version import CAM_ASSIST_VERSION


class CreateResult(NamedTuple):
    success: bool
    output_path: Path | None
    error: str | None
    exit_code: int


def resolve_input_path(positional: Path | None, named: Path | None) -> Path | None:
    """Return the input path from positional form, --input, or both if they agree."""
    if positional is not None and named is not None:
        try:
            same = positional.resolve() == named.resolve()
        except OSError:
            same = positional == named
        if not same:
            raise PickupRouteError(
                "conflicting input paths: positional argument and --input must refer to the same file"
            )
        return positional
    return positional if positional is not None else named


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
        strategy = build_pickup_route_strategy(request, CAM_ASSIST_VERSION)
    except PickupRouteError as exc:
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
        description="Create a CAM Assist pickup-route manufacturing strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input_json",
        nargs="?",
        type=Path,
        help="Path to the operation input JSON",
    )
    parser.add_argument(
        "--input",
        dest="input_option",
        type=Path,
        default=None,
        help="Alias for the operation input JSON path",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output strategy JSON path (default: <input>_strategy.json)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Print only the output path")
    args = parser.parse_args()

    try:
        input_path = resolve_input_path(args.input_json, args.input_option)
    except PickupRouteError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if input_path is None:
        parser.error("input JSON is required (positional argument or --input)")

    output_path = args.out
    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}_strategy.json")

    result = create_strategy(input_path, output_path, force=args.force)
    if result.success:
        if args.quiet:
            print(str(result.output_path))
        else:
            print(f"PASS: pickup route strategy written: {result.output_path}")
        return 0

    prefix = "FAIL" if result.exit_code == 1 else "Error"
    print(f"{prefix}: {result.error}", file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
