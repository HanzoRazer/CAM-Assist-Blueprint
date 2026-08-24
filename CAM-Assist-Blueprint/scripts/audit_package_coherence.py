#!/usr/bin/env python3
"""
CAM Assist Package Coherence Audit (read-only)

Thin CLI adapter over ``scripts/_shared/package_coherence.py``.

Reports whether the evidence surrounding one strategy package agrees about
identity and references. It does not approve a package, authorize execution,
or establish machine readiness.

Usage:
    python scripts/audit_package_coherence.py \\
        --package examples/packages/ltb_vcarve_synthetic_example
    python scripts/audit_package_coherence.py \\
        --package examples/packages/ltb_vcarve_synthetic_example --json
    python scripts/audit_package_coherence.py \\
        --package examples/packages/ltb_vcarve_synthetic_example \\
        --json --fail-on-errors

Exit codes:
    0 — Audit completed (findings, if any, are advisory)
    1 — Audit completed with error findings and --fail-on-errors
    2 — Package/manifest cannot be established, or other input failure
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _shared.package_coherence import (
    PackageCoherenceInputError,
    audit_package_coherence,
    format_human_report,
    serialize_coherence,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit CAM Assist package identity and reference coherence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--package",
        type=Path,
        required=True,
        help="Strategy package directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a deterministic JSON report on stdout",
    )
    parser.add_argument(
        "--fail-on-errors",
        action="store_true",
        help="Exit 1 when the audit records one or more error findings",
    )
    args = parser.parse_args()

    try:
        result = audit_package_coherence(args.package)
    except PackageCoherenceInputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(serialize_coherence(result), end="")
    else:
        print(format_human_report(result), end="")

    if args.fail_on_errors and result.error_count:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
