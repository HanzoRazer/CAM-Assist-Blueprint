"""Report the registered PEP-CAM-CONTRACT-002 verdict.

The report is a pilot observation. It is not an implementation authorization.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _runtime import ROOT, emit, load_json, policy_paths
from governance.kernel.canonical import digest_of
from governance.kernel.evaluate import evaluate_authorization, verify_registry


def main() -> int:
    root = ROOT
    policy, roles = policy_paths(root)
    registry = load_json(root / "governance" / "registry" / "decisions.json")
    authorizations = load_json(root / "governance" / "registry" / "authorizations.json")
    registry_verdict = verify_registry(registry)
    authorization_verdict = verify_registry(authorizations)
    decision = load_json(root / "governance" / "fixtures" / "pep_cam_contract_002_proposed.json")
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
        candidate_policy=policy,
        trusted_roles=roles,
        mode="production",
    )
    report = {
        "authorization_registry": authorization_verdict.to_dict(),
        "decision_registry": registry_verdict.to_dict(),
        "interchange_r2": verdict.to_dict(),
        "pilot": True,
        "policy_digest": digest_of(policy),
        "production_authorization_operational": False,
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
