"""Decision lifecycle tests."""

from __future__ import annotations

import copy

from governance.kernel.canonical import digest_of
from governance.kernel.evaluate import evaluate_authorization, load_json, verify_registry


def _request(decision: dict, scope: list[str] | None = None) -> dict:
    return {
        "decision_id": decision["decision_id"],
        "repository": decision["subject_repository"],
        "revision": decision["subject_revision"],
        "scope": scope or ["r2-contract-publication"],
    }


def test_proposed_record_is_registered_and_not_authorized(root, policy, production_roles, pep_decision):
    registry = load_json(root / "governance" / "registry" / "decisions.json")
    integrity = verify_registry(registry)
    assert integrity.code != 0
    assert "REGISTRY_DIGEST_MISMATCH" not in integrity.reason_codes
    stored = registry["records"][0]
    assert stored["decision"]["decision_id"] == "PEP-CAM-CONTRACT-002"
    assert stored["decision"]["status"] == "PROPOSED"
    assert stored["record_digest"] == digest_of(pep_decision)
    verdict = evaluate_authorization(
        decision=pep_decision,
        authorization=None,
        request=_request(pep_decision),
        trusted_policy=policy,
        candidate_policy=policy,
        trusted_roles=production_roles,
        mode="production",
    )
    assert verdict.verdict == "BLOCKED"
    assert verdict.code == 1
    assert verdict.production_authorization_operational is False


def test_unknown_schema_version_is_invalid(policy, production_roles, pep_decision):
    decision = copy.deepcopy(pep_decision)
    decision["schema_version"] = "governance-decision-v9"
    verdict = evaluate_authorization(
        decision=decision,
        authorization=None,
        request=_request(decision),
        trusted_policy=policy,
        candidate_policy=policy,
        trusted_roles=production_roles,
    )
    assert verdict.code == 2
    assert verdict.verdict == "INVALID"
    assert "UNKNOWN_SCHEMA_VERSION" in verdict.reason_codes


def test_editable_approval_boolean_is_not_evidence(policy, production_roles, pep_decision):
    decision = copy.deepcopy(pep_decision)
    decision["approved"] = True
    verdict = evaluate_authorization(
        decision=decision,
        authorization=None,
        request=_request(decision),
        trusted_policy=policy,
        candidate_policy=policy,
        trusted_roles=production_roles,
    )
    assert verdict.code == 2
    assert verdict.verdict == "INVALID"
    assert verdict.verdict != "AUTHORIZED"


def test_missing_decision_owner_blocks_acceptance(policy, synthetic_bundle):
    decision = copy.deepcopy(synthetic_bundle["decision"])
    decision["decision_owner"] = None
    verdict = evaluate_authorization(
        decision=decision,
        authorization=None,
        request={
            "decision_id": decision["decision_id"],
            "repository": decision["subject_repository"],
            "revision": decision["subject_revision"],
            "scope": ["governance-kernel-test"],
        },
        trusted_policy=policy,
        candidate_policy=policy,
        trusted_roles=synthetic_bundle["authority"],
        evidence_resolver=lambda ref: synthetic_bundle["evidence"][ref],
        mode="synthetic",
    )
    assert verdict.verdict == "BLOCKED"
    assert "MISSING_DECISION_OWNER" in verdict.reason_codes
