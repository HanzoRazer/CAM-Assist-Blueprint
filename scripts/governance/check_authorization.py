"""Verify whether a requested scope is authorized.

Production mode cannot return exit 0. ``--allow-synthetic`` is an isolated
test switch and refuses the production role registry. ``--trust-commit`` reads
policy and roles from that commit. The worktree copies are candidate data.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _runtime import ROOT, emit, load_json, parse_cli_time, policy_paths
from governance.kernel.evaluate import evaluate_authorization
from governance.kernel.github_evidence import GitHubEvidenceResolver, UrllibGitHubClient
from governance.kernel.trust_root import (
    TrustRootError,
    load_git_trust_root,
    running_verifier_digest,
)
from governance.kernel.verdict import CODE_VERIFIER, VERIFIER_ERROR, make_verdict


def _candidate_policy(root: Path, explicit: Path | None) -> dict:
    if explicit is not None:
        return load_json(explicit)
    path = root / "governance" / "policy" / "governance_policy_v1.json"
    try:
        return load_json(path)
    except (OSError, ValueError):
        return {"schema_version": "unreadable-candidate"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, default=None)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--scope", action="append", required=True)
    parser.add_argument("--candidate-policy", type=Path, default=None)
    parser.add_argument("--trusted-roles", type=Path, default=None)
    parser.add_argument("--trust-commit", default=None)
    parser.add_argument("--github-pr", type=int, default=None)
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--as-of", default=None)
    args = parser.parse_args(argv)
    if args.trust_commit is None:
        policy, roles = policy_paths(ROOT)
    else:
        try:
            loaded = load_git_trust_root(ROOT, args.trust_commit)
            running = running_verifier_digest(ROOT)
        except TrustRootError as exc:
            sys.stderr.write(f"{exc.code}\n")
            return 4
        if running != loaded.verifier_digest:
            verdict = make_verdict(
                CODE_VERIFIER,
                VERIFIER_ERROR,
                ["VERIFIER_PIN_MISMATCH"],
                decision_id=None,
                production_operational=False,
            )
            return emit(verdict)
        policy, roles = loaded.policy, loaded.roles
    if args.trusted_roles is not None:
        if args.trust_commit is not None:
            sys.stderr.write("trusted roles must come from the trust commit\n")
            return 4
        roles = load_json(args.trusted_roles)
    candidate = _candidate_policy(ROOT, args.candidate_policy)
    decision = load_json(args.decision)
    authorization = None if args.authorization is None else load_json(args.authorization)
    mode = "synthetic" if args.allow_synthetic else "production"
    if mode == "synthetic" and roles.get("synthetic") is not True:
        sys.stderr.write("synthetic mode requires a synthetic authority file\n")
        return 4
    if mode == "synthetic" and args.trust_commit is not None:
        sys.stderr.write("synthetic mode cannot use a production trust commit\n")
        return 4
    resolver = None
    if args.github_pr is not None:
        import os

        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        resolver = GitHubEvidenceResolver(
            UrllibGitHubClient(token),
            repository=args.repository,
            pull_number=args.github_pr,
        )
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
        evidence_resolver=resolver,
        mode=mode,
        as_of=parse_cli_time(args.as_of),
    )
    return emit(verdict)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — CLI boundary, fail closed
        sys.stderr.write(f"verifier error: {exc}\n")
        sys.exit(4)
