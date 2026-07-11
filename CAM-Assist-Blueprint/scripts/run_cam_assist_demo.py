#!/usr/bin/env python3
"""
CAM Assist End-to-End Demonstration Runner (CAM-A21)

Runs the existing CAM Assist pipeline end to end against the canonical synthetic
V-Carve input, so a new user can reproduce the whole product workflow with one
command. It ORCHESTRATES the existing public CLIs as subprocesses — it never
duplicates their internal logic, and running each real CLI witnesses its true
behavior.

The demonstration takes a manufacturing intent (an LTB CAM output) all the way to
a reviewed, portable, non-execution Production Shop handoff:

    import -> validate strategy -> review packet -> assemble -> inspect ->
    archive -> validate archive -> stage -> review queue -> review decision ->
    annotations -> assumptions -> risk -> decision record -> lineage ->
    traceability bundle -> validate bundle -> production shop handoff ->
    validate handoff -> final inspect -> non-execution invariant

Non-execution doctrine: this runner generates NO G-code, calls NO CAM engine or
Production Shop runtime, claims NO machine readiness, and never mutates the
committed source examples. Every artifact is written inside a workspace directory
(a temporary one by default, removed on exit unless --keep or an explicit
--workspace is supplied). A non-zero exit from any step aborts the run.

Usage:
    python scripts/run_cam_assist_demo.py
    python scripts/run_cam_assist_demo.py --workspace .tmp/cam_assist_demo --keep
    python scripts/run_cam_assist_demo.py --json

Exit codes:
    0 — Demonstration completed; every step passed
    1 — A pipeline step failed (see the reported step and its captured stderr)
    2 — Argument or setup error
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
DEFAULT_INPUT = REPO_ROOT / "examples" / "ltb_import" / "synthetic_vcarve_ltb_output.json"

# The assembled package directory name inside the workspace. Sidecar creators
# derive conventional sibling locations (traceability/, review_annotations/,
# production_shop/) from this directory's parent, so the whole demo stays inside
# the workspace and the inspector discovers everything conventionally.
PACKAGE_NAME = "package"


class StepResult(NamedTuple):
    name: str
    exit_code: int
    status: str
    stdout: str
    stderr: str


def build_steps(ws: Path, input_path: Path) -> list[tuple[str, list[str]]]:
    """The ordered demonstration steps as (name, argv-after-interpreter).

    Every command is a real public CLI; the sequence and flags match what the
    workflow guide documents.
    """
    strategy = ws / "strategy.json"
    package = ws / PACKAGE_NAME
    archive = ws / "package.zip"
    staged = ws / "staged"
    staged_pkg = staged / PACKAGE_NAME
    trace = ws / "traceability"
    handoff = ws / "production_shop" / f"{PACKAGE_NAME}_handoff.json"

    def script(name: str) -> str:
        return str(SCRIPTS / name)

    return [
        ("import_strategy", [script("import_ltb_cam_output.py"), str(input_path), "--out", str(strategy), "--quiet"]),
        ("validate_strategy", [script("validate_strategy_package.py"), str(strategy), "--quiet"]),
        ("generate_review_packet", [script("generate_review_packet.py"), str(strategy), "--out", str(ws / "review_packet.md")]),
        ("assemble_package", [script("assemble_strategy_package.py"), str(strategy), "--out", str(package)]),
        ("inspect_package", [script("inspect_strategy_package.py"), str(package)]),
        ("archive_package", [script("archive_strategy_package.py"), str(package), "--out", str(archive), "--quiet"]),
        ("validate_archive", [script("validate_package_archive.py"), str(archive), "--quiet"]),
        ("stage_package", [script("stage_strategy_package.py"), str(archive), "--out", str(staged), "--quiet"]),
        ("review_queue", [script("index_staged_packages.py"), str(staged), "--quiet"]),
        ("record_review_decision", [script("record_review_decision.py"), str(staged_pkg),
                                    "--decision", "approve_for_downstream_cam", "--reviewer", "Demo Reviewer",
                                    "--notes", "Reviewed scale, tooling, and workholding assumptions.", "--quiet"]),
        ("review_annotations", [script("create_review_annotations.py"), "--package", str(package),
                                "--reviewer", "Demo Reviewer", "--severity", "info", "--category", "tooling",
                                "--message", "Verify bit runout before downstream toolpath development.", "--quiet"]),
        ("manufacturing_assumptions", [script("create_manufacturing_assumptions.py"), "--package", str(package),
                                       "--assumption", "tooling", "Tool rigidity is adequate for the selected depth of cut.", "--quiet"]),
        ("risk_assessment", [script("create_risk_assessment.py"), "--package", str(package),
                             "--overall-risk", "medium", "--risk", "geometry", "warning",
                             "Thin wall section may chatter.", "--quiet"]),
        ("decision_record", [script("create_manufacturing_decision_record.py"), "--package", str(package),
                             "--decision", "approved", "--prepared-by", "Manufacturing Engineer",
                             "--reviewed-by", "Senior Reviewer", "--rationale",
                             "Tooling, fixturing, and material assumptions reviewed.", "--quiet"]),
        ("revision_lineage", [script("create_revision_lineage.py"), "--package", str(package),
                              "--summary", "Initial manufacturing strategy review.", "--quiet"]),
        ("traceability_bundle", [script("create_traceability_bundle.py"), "--package", str(package), "--quiet"]),
        ("validate_bundle", [script("validate_traceability_bundle.py"), str(trace / f"{PACKAGE_NAME}_bundle.json"), "--check-references"]),
        ("production_shop_handoff", [script("create_production_shop_handoff.py"), "--package", str(package),
                                     "--out", str(handoff), "--quiet"]),
        ("validate_handoff", [script("validate_production_shop_handoff.py"), str(handoff), "--check-references"]),
        ("inspect_final", [script("inspect_strategy_package.py"), str(package)]),
        ("verify_non_execution_invariant", [script("verify_non_execution_invariant.py"), str(package), "--quiet"]),
    ]


def artifact_map(ws: Path) -> dict:
    """Expected artifacts, as paths relative to the workspace root."""
    return {
        "strategy": "strategy.json",
        "review_packet": f"{PACKAGE_NAME}/review_packet.md",
        "manifest": f"{PACKAGE_NAME}/manifest.json",
        "archive": "package.zip",
        "staged_package": f"staged/{PACKAGE_NAME}",
        "review_decision": f"staged/{PACKAGE_NAME}.review_decision.json",
        "review_annotations": f"review_annotations/{PACKAGE_NAME}_annotations.json",
        "manufacturing_assumptions": f"traceability/{PACKAGE_NAME}_assumptions.json",
        "risk_assessment": f"traceability/{PACKAGE_NAME}_risk.json",
        "decision_record": f"traceability/{PACKAGE_NAME}_decision_record.json",
        "revision_lineage": f"traceability/{PACKAGE_NAME}_lineage.json",
        "traceability_bundle": f"traceability/{PACKAGE_NAME}_bundle.json",
        "production_shop_handoff": f"production_shop/{PACKAGE_NAME}_handoff.json",
    }


def run_demo(ws: Path, input_path: Path, quiet: bool = False) -> tuple[list[StepResult], bool]:
    """Run every step in order, stopping at the first failure.

    Returns (results, ok). A step whose child process exits non-zero sets ok to
    False and halts the run (later steps are not attempted).
    """
    results: list[StepResult] = []
    ok = True
    for name, argv in build_steps(ws, input_path):
        proc = subprocess.run([sys.executable, *argv], capture_output=True, text=True)
        status = "passed" if proc.returncode == 0 else "failed"
        results.append(StepResult(name, proc.returncode, status, proc.stdout, proc.stderr))
        if not quiet:
            print(f"  [{status.upper():6}] {name}")
        if proc.returncode != 0:
            ok = False
            if not quiet:
                print(f"    exit={proc.returncode}", file=sys.stderr)
                if proc.stderr.strip():
                    print("    " + proc.stderr.strip().replace("\n", "\n    "), file=sys.stderr)
            break
    return results, ok


def build_summary(input_path: Path, results: list[StepResult], ok: bool, ws: Path) -> dict:
    """Assemble the demonstration report (not a product contract; no schema)."""
    summary = {
        "record_type": "cam_assist_demo_summary",
        "record_version": "1.0.0",
        "status": "passed" if ok else "failed",
        "input": input_path.name,
        "steps": [
            {"name": r.name, "exit_code": r.exit_code, "status": r.status} for r in results
        ],
        "authority": {
            "is_informational": True,
            "does_not_authorize_execution": True,
            "does_not_confirm_machine_readiness": True,
            "does_not_generate_gcode": True,
        },
    }
    # Only advertise artifacts that were actually produced (a partial/failed run
    # must not claim artifacts it never created).
    if ok:
        summary["artifacts"] = {
            key: rel for key, rel in artifact_map(ws).items() if (ws / rel).exists()
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the CAM Assist end-to-end demonstration (non-execution).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--workspace", type=Path, default=None,
        help="Directory for generated artifacts (default: a temporary directory, removed on exit).",
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT,
        help="LTB CAM output to import (default: the canonical synthetic V-Carve example).",
    )
    parser.add_argument("--keep", action="store_true", help="Preserve the workspace instead of cleaning it up.")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress per-step progress output.")
    parser.add_argument("--json", action="store_true", help="Emit the machine-readable demo summary to stdout.")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input not found: {args.input}", file=sys.stderr)
        return 2

    # A user-supplied workspace is never auto-deleted; only a temp one we created
    # is cleaned up (and only when --keep is absent).
    created_temp = args.workspace is None
    ws = Path(tempfile.mkdtemp(prefix="cam_assist_demo_")) if created_temp else args.workspace
    ws.mkdir(parents=True, exist_ok=True)

    try:
        if not args.quiet:
            print(f"CAM Assist demonstration — workspace: {ws}")
        results, ok = run_demo(ws, args.input, quiet=args.quiet)
        summary = build_summary(args.input, results, ok, ws)
        (ws / "demo_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        if args.json:
            print(json.dumps(summary, indent=2))
        elif not args.quiet:
            print(f"Status: {summary['status']} ({len(results)} steps)")
            if ok and args.keep:
                print(f"Artifacts preserved in: {ws}")

        return 0 if ok else 1
    finally:
        if created_temp and not args.keep:
            shutil.rmtree(ws, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
