"""Verify whether a requested scope is authorized.

Production mode cannot return exit 0. ``--allow-synthetic`` is an isolated
test switch and refuses the production role registry.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from _runtime import ROOT, emit, load_json, policy_paths
from governance.kernel.evaluate import evaluate_authorization


def _time(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    return parsed.astimezone(timezone.utc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, default=None)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--scope", action="append", required=True)
    parser.add_argument("--candidate-policy", type=Path, default=None)
    parser.add_argument("--trusted-roles", type=Path, default=None)
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--as-of", default=None)
    args = parser.parse_args(argv)
    policy, roles = policy_paths(ROOT)
    if args.trusted_roles is not None:
        roles = load_json(args.trusted_roles)
    candidate = policy if args.candidate_policy is None else load_json(args.candidate_policy)
    decision = load_json(args.decision)
    authorization = None if args.authorization is None else load_json(args.authorization)
    mode = "synthetic" if args.allow_synthetic else "production"
    if mode == "synthetic" and roles.get("synthetic") is not True:
        sys.stderr.write("synthetic mode requires a synthetic authority file\n")
        return 4
    verdict = evaluate_authorization(
        decision=decision,
        authorization=authorization,
        request={
            "decision_id": decision.get("decision_id"),
            "repository": args.repository,
            "revision": args.revision,
            "scope": args.scope,
        },
        trusted_policy=policy,
        candidate_policy=candidate,
        trusted_roles=roles,
        mode=mode,
        as_of=_time(args.as_of),
    )
    return emit(verdict)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — CLI boundary, fail closed
        sys.stderr.write(f"verifier error: {exc}\n")
        sys.exit(4)
