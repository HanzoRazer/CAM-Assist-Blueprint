"""Report the registered PEP-CAM-CONTRACT-002 verdict.

The report is a pilot observation unless GOVERNANCE_TRUST_COMMIT names a
commit whose blobs supply policy and roles. The worktree is never a trust
root. Production authorization stays disabled.
"""

from __future__ import annotations

import json
import sys

from _runtime import ROOT, load_json, policy_paths
from governance.kernel.canonical import digest_of
from governance.kernel.evaluate import evaluate_authorization, verify_registry
from governance.kernel.trust_root import (
    TrustRootError,
    load_git_trust_root,
    running_verifier_digest,
    trust_commit_from_env,
    unresolved_trust_root,
)


def _sources() -> tuple[dict, dict, dict]:
    commit = trust_commit_from_env()
    if commit is None:
        policy, roles = policy_paths(ROOT)
        return policy, roles, unresolved_trust_root(digest_of(policy))
    loaded = load_git_trust_root(ROOT, commit)
    try:
        running = running_verifier_digest(ROOT)
    except TrustRootError:
        running = None
    return loaded.policy, loaded.roles, loaded.provenance(running_digest=running)


def main() -> int:
    policy, roles, trust = _sources()
    registry = load_json(ROOT / "governance" / "registry" / "decisions.json")
    authorizations = load_json(ROOT / "governance" / "registry" / "authorizations.json")
    registry_verdict = verify_registry(registry)
    authorization_verdict = verify_registry(authorizations)
    decision = load_json(ROOT / "governance" / "fixtures" / "pep_cam_contract_002_proposed.json")
    try:
        candidate = load_json(ROOT / "governance" / "policy" / "governance_policy_v1.json")
    except (OSError, ValueError):
        candidate = {"schema_version": "unreadable-candidate"}
    verdict = evaluate_authorization(
        decision=decision,
        authorization=None,
        request={
            "decision_id": "PEP-CAM-CONTRACT-002",
            "repository": "HanzoRazer/CAM-Assist-Blueprint",
            "revision": decision["subject_revision"],
            "scope": ["r2-contract-publication"],
        },
        trusted_policy=policy,
        candidate_policy=candidate,
        trusted_roles=roles,
        mode="production",
    )
    enrolled = 0
    for role in roles.get("roles", []):
        if isinstance(role, dict):
            enrolled += len(role.get("github_user_ids") or [])
    report = {
        "authorization_registry": authorization_verdict.to_dict(),
        "decision_registry": registry_verdict.to_dict(),
        "evidence_verification": {
            "enrolled_production_identities": enrolled,
            "live_github": False,
            "resolver": "not_configured",
        },
        "interchange_r2": verdict.to_dict(),
        "pilot": True,
        "policy_digest": digest_of(policy),
        "production_authorization_operational": False,
        "trust_root": trust,
    }
    json.dump(report, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    if registry_verdict.code == 2 or authorization_verdict.code == 2:
        return 2
    return verdict.code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — CLI boundary, fail closed
        sys.stderr.write(f"verifier error: {exc}\n")
        sys.exit(4)
