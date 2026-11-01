"""GitHub review evidence comes from the API client, not candidate JSON."""

from __future__ import annotations

import copy

from governance.kernel.evaluate import evaluate_authorization
from governance.kernel.github_evidence import GitHubApiError, GitHubEvidenceResolver
from tests.governance.conftest import as_of

REPOSITORY = "HanzoRazer/CAM-Assist-Blueprint"
REVISION = "a" * 40


class FakeGitHub:
    def __init__(self, reviews, permission="write", boom=False):
        self.reviews = reviews
        self.permission = permission
        self.boom = boom

    def list_reviews(self, repository, pull_number):
        if self.boom:
            raise GitHubApiError("503")
        assert repository == REPOSITORY
        assert pull_number == 45
        return self.reviews

    def reviewer_permission(self, repository, login):
        if self.boom:
            raise GitHubApiError("503")
        assert repository == REPOSITORY
        return self.permission


def _review(review_id, user_id, state, commit, submitted, login="ada"):
    return {
        "commit_id": commit,
        "id": review_id,
        "state": state,
        "submitted_at": submitted,
        "user": {"id": user_id, "login": login},
    }


def _bundle_for(bundle, user_id=7):
    roles = copy.deepcopy(bundle["authority"])
    for role in roles["roles"]:
        role["identities"] = [str(user_id)]
        role["github_user_ids"] = [user_id]
        role["required_permission"] = "write"
    authorization = copy.deepcopy(bundle["authorization"])
    authorization["approvals"] = [
        {
            "evidence_ref": "80",
            "identity": str(user_id),
            "review_state": "APPROVED",
            "role": "implementation_authorizer",
        }
    ]
    decision = copy.deepcopy(bundle["decision"])
    decision["approval_evidence"] = [
        {
            "evidence_id": "80",
            "kind": "github_pull_request_review",
            "source": "api",
        }
    ]
    return decision, authorization, roles


def _verdict(policy, bundle, client, user_id=7):
    decision, authorization, roles = _bundle_for(bundle, user_id)
    return evaluate_authorization(
        decision=decision,
        authorization=authorization,
        request=bundle["request"],
        trusted_policy=policy,
        candidate_policy=policy,
        trusted_roles=roles,
        evidence_resolver=GitHubEvidenceResolver(client, repository=REPOSITORY, pull_number=45),
        mode="synthetic",
        as_of=as_of(bundle),
    )


def test_forged_candidate_json_is_not_evidence(policy, synthetic_bundle):
    forged = {"identity": "forged-approver", "review_state": "APPROVED", "approved": True}
    assert forged["approved"] is True
    client = FakeGitHub([_review(80, 7, "COMMENTED", REVISION, "2026-10-28T00:00:00Z")])
    verdict = _verdict(policy, synthetic_bundle, client)
    assert verdict.verdict == "BLOCKED"
    assert "REVIEW_NOT_APPROVED" in verdict.reason_codes


def test_dismissed_approval_is_blocked(policy, synthetic_bundle):
    client = FakeGitHub([_review(80, 7, "DISMISSED", REVISION, "2026-10-28T00:00:00Z")])
    verdict = _verdict(policy, synthetic_bundle, client)
    assert verdict.verdict == "BLOCKED"
    assert "REVIEW_DISMISSED" in verdict.reason_codes


def test_superseded_review_is_blocked(policy, synthetic_bundle):
    reviews = [
        _review(80, 7, "APPROVED", REVISION, "2026-10-28T00:00:00Z"),
        _review(81, 7, "CHANGES_REQUESTED", REVISION, "2026-10-28T01:00:00Z"),
    ]
    verdict = _verdict(policy, synthetic_bundle, FakeGitHub(reviews))
    assert verdict.verdict == "BLOCKED"
    assert "REVIEW_SUPERSEDED" in verdict.reason_codes


def test_unenrolled_reviewer_is_blocked(policy, synthetic_bundle):
    client = FakeGitHub([_review(80, 8, "APPROVED", REVISION, "2026-10-28T00:00:00Z")])
    verdict = _verdict(policy, synthetic_bundle, client, user_id=7)
    assert verdict.verdict == "BLOCKED"
    assert "UNRECOGNIZED_IDENTITY" in verdict.reason_codes


def test_reviewer_without_permission_is_blocked(policy, synthetic_bundle):
    client = FakeGitHub(
        [_review(80, 7, "APPROVED", REVISION, "2026-10-28T00:00:00Z")],
        permission="read",
    )
    verdict = _verdict(policy, synthetic_bundle, client)
    assert verdict.verdict == "BLOCKED"
    assert "INSUFFICIENT_PERMISSION" in verdict.reason_codes


def test_review_on_another_revision_is_blocked(policy, synthetic_bundle):
    client = FakeGitHub([_review(80, 7, "APPROVED", "b" * 40, "2026-10-28T00:00:00Z")])
    verdict = _verdict(policy, synthetic_bundle, client)
    assert verdict.verdict == "BLOCKED"
    assert "REVISION_MISMATCH" in verdict.reason_codes


def test_api_outage_is_evidence_unavailable(policy, synthetic_bundle):
    verdict = _verdict(policy, synthetic_bundle, FakeGitHub([], boom=True))
    assert verdict.code == 3
    assert verdict.verdict == "EVIDENCE_UNAVAILABLE"


def test_live_approval_does_not_enable_production(policy, production_roles, synthetic_bundle):
    client = FakeGitHub([_review(80, 7, "APPROVED", REVISION, "2026-10-28T00:00:00Z")])
    decision, authorization, _roles = _bundle_for(synthetic_bundle)
    verdict = evaluate_authorization(
        decision=decision,
        authorization=authorization,
        request=synthetic_bundle["request"],
        trusted_policy=policy,
        candidate_policy=policy,
        trusted_roles=production_roles,
        evidence_resolver=GitHubEvidenceResolver(client, repository=REPOSITORY, pull_number=45),
        mode="production",
        as_of=as_of(synthetic_bundle),
    )
    assert verdict.code == 1
    assert verdict.verdict == "BLOCKED"
    assert "PRODUCTION_AUTHORIZATION_NOT_OPERATIONAL" in verdict.reason_codes
    assert verdict.production_authorization_operational is False
