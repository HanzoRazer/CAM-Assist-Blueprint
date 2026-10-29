"""Validate a governance decision record. This command does not authorize work."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from _runtime import ROOT, emit, load_json, policy_paths
from governance.kernel.evaluate import evaluate_authorization


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--scope", action="append", required=True)
    parser.add_argument("--as-of", default=None)
    args = parser.parse_args(argv)
    policy, roles = policy_paths(ROOT)
    decision = load_json(args.decision)
    as_of = None
    if args.as_of:
        text = args.as_of[:-1] + "+00:00" if args.as_of.endswith("Z") else args.as_of
        as_of = datetime.fromisoformat(text).astimezone(timezone.utc)
    verdict = evaluate_authorization(
        decision=decision,
        authorization=None,
        request={
            "decision_id": decision.get("decision_id"),
            "repository": args.repository,
            "revision": args.revision,
            "scope": args.scope,
        },
        trusted_policy=policy,
        candidate_policy=policy,
        trusted_roles=roles,
        mode="production",
        as_of=as_of,
    )
    return emit(verdict)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — CLI boundary, fail closed
        sys.stderr.write(f"verifier error: {exc}\n")
        sys.exit(4)
