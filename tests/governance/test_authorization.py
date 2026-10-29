"""Authorization verdicts, including the merged-PR negative case."""

from __future__ import annotations

import copy
from datetime import timedelta, timezone

from governance.kernel.evaluate import EvidenceUnavailable, evaluate_authorization, load_json
from tests.governance.conftest import as_of, resolver_for


def _eval(policy, bundle, **overrides):
    decision = overrides.pop("decision", bundle["decision"])
    authorization = overrides.pop("authorization", bundle["authorization"])
    request = overrides.pop("request", bundle["request"])
    roles = overrides.pop("trusted_roles", bundle["authority"])
    resolver = overrides.pop("evidence_resolver", resolver_for(bundle["evidence"]))
    mode = overrides.pop("mode", "synthetic")
    when = overrides.pop("when", as_of(bundle))
    candidate = overrides.pop("candidate_policy", policy)
    return evaluate_authorization(
        decision=decision,
        authorization=authorization,
        request=request,
        trusted_policy=policy,
        candidate_policy=candidate,
        trusted_roles=roles,
        evidence_resolver=resolver,
        mode=mode,
        as_of=when,
        **overrides,
    )


def test_merged_proposed_adr_is_blocked(root, policy, production_roles):
    decision = load_json(root / "governance" / "fixtures" / "invalid_merged_as_approved.json")
    pr_merged = True
    adr_status = decision["status"]
    implementation_authorization = None
    assert pr_merged is True
    assert adr_status == "PROPOSED"
    assert implementation_authorization is None
    verdict = evaluate_authorization(
        decision=decision,
        authorization=implementation_authorization,
        request={
            "decision_id": decision["decision_id"],
            "repository": decision["subject_repository"],
            "revision": decision["subject_revision"],
            "scope": ["r2-contract-publication"],
        },
        trusted_policy=policy,
        candidate_policy=policy,
        trusted_roles=production_roles,
        mode="production",
    )
    assert verdict.verdict == "BLOCKED"
    assert verdict.code == 1
    assert "MERGED_PR_NOT_APPROVAL" in verdict.reason_codes
    assert "DECISION_NOT_ACCEPTED" in verdict.reason_codes
    assert "MISSING_IMPLEMENTATION_AUTHORIZATION" in verdict.reason_codes


def test_accepted_decision_without_authorization_is_blocked(policy, synthetic_bundle):
    decision = copy.deepcopy(synthetic_bundle["decision"])
    decision["implementation_authorization_ref"] = None
    verdict = _eval(policy, synthetic_bundle, decision=decision, authorization=None)
    assert verdict.verdict == "BLOCKED"
    assert "MISSING_IMPLEMENTATION_AUTHORIZATION" in verdict.reason_codes


def test_forged_identity_is_blocked(root, policy, synthetic_bundle):
    authorization = load_json(root / "governance" / "fixtures" / "invalid_forged_approval.json")
    evidence = {
        "forged-review": {
            "available": True,
            "kind": "github_pull_request_review",
            "identity": "forged-approver",
            "review_state": "APPROVED",
            "commit_id": authorization["approved_decision_revision"],
        }
    }
    decision = copy.deepcopy(synthetic_bundle["decision"])
    decision["decision_id"] = authorization["decision_id"]
    decision["subject_revision"] = authorization["approved_decision_revision"]
    request = {
        "decision_id": authorization["decision_id"],
        "repository": authorization["authorized_repository"],
        "revision": authorization["approved_decision_revision"],
        "scope": authorization["implementation_scope"],
    }
    verdict = _eval(
        policy,
        synthetic_bundle,
        decision=decision,
        authorization=authorization,
        request=request,
        evidence_resolver=resolver_for(evidence),
    )
    assert verdict.verdict == "BLOCKED"
    assert "UNRECOGNIZED_IDENTITY" in verdict.reason_codes


def test_unauthorized_reviewer_is_blocked(policy, synthetic_bundle):
    authorization = copy.deepcopy(synthetic_bundle["authorization"])
    authorization["approvals"][0]["identity"] = "unassigned-reviewer"
    evidence = copy.deepcopy(synthetic_bundle["evidence"])
    evidence["synthetic-implementation-review"]["identity"] = "unassigned-reviewer"
    verdict = _eval(
        policy,
        synthetic_bundle,
        authorization=authorization,
        evidence_resolver=resolver_for(evidence),
    )
    assert verdict.verdict == "BLOCKED"
    assert "UNRECOGNIZED_IDENTITY" in verdict.reason_codes


def test_revision_mismatch_is_blocked(policy, synthetic_bundle):
    authorization = copy.deepcopy(synthetic_bundle["authorization"])
    authorization["approved_decision_revision"] = "b" * 40
    verdict = _eval(policy, synthetic_bundle, authorization=authorization)
    assert verdict.verdict == "BLOCKED"
    assert "REVISION_MISMATCH" in verdict.reason_codes


def test_scope_mismatch_is_blocked(policy, synthetic_bundle):
    request = copy.deepcopy(synthetic_bundle["request"])
    request["scope"] = ["r2-contract-publication"]
    verdict = _eval(policy, synthetic_bundle, request=request)
    assert verdict.verdict == "BLOCKED"
    assert "SCOPE_MISMATCH" in verdict.reason_codes


def test_missing_evidence_is_unavailable(policy, synthetic_bundle):
    verdict = _eval(policy, synthetic_bundle, evidence_resolver=resolver_for({}))
    assert verdict.code == 3
    assert verdict.verdict == "EVIDENCE_UNAVAILABLE"
    assert "MISSING_EVIDENCE" in verdict.reason_codes


def test_evidence_service_unavailable(policy, synthetic_bundle):
    def resolve(_ref: str):
        raise EvidenceUnavailable("down")

    verdict = _eval(policy, synthetic_bundle, evidence_resolver=resolve)
    assert verdict.code == 3
    assert verdict.verdict == "EVIDENCE_UNAVAILABLE"
    assert "EVIDENCE_SERVICE_UNAVAILABLE" in verdict.reason_codes


def test_expired_authorization_is_blocked(policy, synthetic_bundle):
    when = as_of(synthetic_bundle) + timedelta(days=4000)
    when = when.replace(tzinfo=timezone.utc)
    verdict = _eval(policy, synthetic_bundle, when=when)
    assert verdict.verdict == "BLOCKED"
    assert "AUTHORIZATION_EXPIRED" in verdict.reason_codes


def test_revoked_authorization_is_blocked(policy, synthetic_bundle):
    authorization = copy.deepcopy(synthetic_bundle["authorization"])
    authorization["revoked"] = True
    verdict = _eval(policy, synthetic_bundle, authorization=authorization)
    assert verdict.verdict == "BLOCKED"
    assert "AUTHORIZATION_REVOKED" in verdict.reason_codes


def test_execution_authority_claim_is_invalid(root, policy, synthetic_bundle):
    authorization = load_json(root / "governance" / "fixtures" / "invalid_execution_authority.json")
    verdict = _eval(policy, synthetic_bundle, authorization=authorization)
    assert verdict.code == 2
    assert verdict.verdict == "INVALID"
    assert "EXECUTION_AUTHORITY_CLAIM" in verdict.reason_codes


def test_comment_evidence_is_untrusted(policy, synthetic_bundle):
    evidence = copy.deepcopy(synthetic_bundle["evidence"])
    evidence["synthetic-implementation-review"]["kind"] = "pull_request_comment"
    verdict = _eval(policy, synthetic_bundle, evidence_resolver=resolver_for(evidence))
    assert verdict.verdict == "BLOCKED"
    assert "UNTRUSTED_EVIDENCE_KIND" in verdict.reason_codes


def test_synthetic_authorization_is_isolated(policy, production_roles, synthetic_bundle):
    verdict = _eval(policy, synthetic_bundle)
    assert verdict.code == 0
    assert verdict.verdict == "AUTHORIZED"
    assert verdict.synthetic_only is True
    assert verdict.production_authorization_operational is False
    again = _eval(policy, synthetic_bundle)
    assert verdict.to_json() == again.to_json()
    production = _eval(policy, synthetic_bundle, mode="production", trusted_roles=production_roles)
    assert production.code != 0
    assert production.verdict == "BLOCKED"
    assert "SYNTHETIC_NOT_PRODUCTION" in production.reason_codes
    assert "PRODUCTION_AUTHORIZATION_NOT_OPERATIONAL" in production.reason_codes


def test_pep_cam_contract_002_r2_is_blocked(policy, production_roles, pep_decision):
    verdict = evaluate_authorization(
        decision=pep_decision,
        authorization=None,
        request={
            "decision_id": "PEP-CAM-CONTRACT-002",
            "repository": "HanzoRazer/CAM-Assist-Blueprint",
            "revision": "5f736e567dab31439df9b2b66fc5de43bec032f2",
            "scope": ["r2-contract-publication"],
        },
        trusted_policy=policy,
        candidate_policy=policy,
        trusted_roles=production_roles,
        mode="production",
    )
    assert verdict.verdict == "BLOCKED"
    assert verdict.code == 1
    assert pep_decision["status"] == "PROPOSED"
    assert pep_decision["pr_merged"] is True
    assert pep_decision["implementation_authorization_ref"] is None


def test_policy_edit_cannot_self_authorize(policy, synthetic_bundle):
    candidate = copy.deepcopy(policy)
    candidate["merged_pull_request_is_approval"] = True
    verdict = _eval(policy, synthetic_bundle, candidate_policy=candidate)
    assert verdict.verdict == "BLOCKED"
    assert verdict.code == 1
    assert "POLICY_SELF_MODIFICATION" in verdict.reason_codes
    loosened = copy.deepcopy(policy)
    loosened["merged_pull_request_is_approval"] = True
    refused = evaluate_authorization(
        decision=synthetic_bundle["decision"],
        authorization=synthetic_bundle["authorization"],
        request=synthetic_bundle["request"],
        trusted_policy=loosened,
        candidate_policy=loosened,
        trusted_roles=synthetic_bundle["authority"],
        evidence_resolver=resolver_for(synthetic_bundle["evidence"]),
        mode="synthetic",
        as_of=as_of(synthetic_bundle),
    )
    assert refused.code == 4
    assert refused.verdict == "VERIFIER_ERROR"
    assert "POLICY_INVARIANT_VIOLATION" in refused.reason_codes


def test_production_flag_in_policy_cannot_enable_the_gate(policy, synthetic_bundle):
    claimed = copy.deepcopy(policy)
    claimed["production_authorization_operational"] = True
    verdict = evaluate_authorization(
        decision=synthetic_bundle["decision"],
        authorization=synthetic_bundle["authorization"],
        request=synthetic_bundle["request"],
        trusted_policy=claimed,
        candidate_policy=claimed,
        trusted_roles=synthetic_bundle["authority"],
        evidence_resolver=resolver_for(synthetic_bundle["evidence"]),
        mode="production",
        as_of=as_of(synthetic_bundle),
    )
    assert verdict.code == 4
    assert verdict.verdict != "AUTHORIZED"
    assert "POLICY_CLAIMS_PRODUCTION_AUTHORITY" in verdict.reason_codes


def test_expiry_is_exclusive_at_boundary(policy, synthetic_bundle):
    from governance.kernel.evaluate import parse_time

    authorization = copy.deepcopy(synthetic_bundle["authorization"])
    boundary = parse_time(authorization["expires_at"])
    verdict = _eval(policy, synthetic_bundle, authorization=authorization, when=boundary)
    assert verdict.verdict == "BLOCKED"
    assert "AUTHORIZATION_EXPIRED" in verdict.reason_codes


def test_default_clock_checks_expiry(policy, synthetic_bundle):
    authorization = copy.deepcopy(synthetic_bundle["authorization"])
    authorization["effective_date"] = "2000-01-01T00:00:00Z"
    authorization["expires_at"] = "2001-01-01T00:00:00Z"
    verdict = _eval(policy, synthetic_bundle, authorization=authorization, when=None)
    assert verdict.verdict == "BLOCKED"
    assert "AUTHORIZATION_EXPIRED" in verdict.reason_codes


def test_naive_as_of_fails_closed(policy, synthetic_bundle):
    from datetime import datetime

    verdict = _eval(policy, synthetic_bundle, when=datetime(2026, 1, 1))
    assert verdict.code == 4
    assert "INVALID_AS_OF_TIME" in verdict.reason_codes
