"""GitHub review evidence comes from the API client, not candidate JSON."""

from __future__ import annotations

import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from governance.kernel.evaluate import EvidenceUnavailable, evaluate_authorization
from governance.kernel.github_evidence import GitHubApiError, GitHubEvidenceResolver, UrllibGitHubClient
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


def test_latest_approval_is_synthetic_only(policy, synthetic_bundle):
    client = FakeGitHub([_review(80, 7, "APPROVED", REVISION, "2026-10-28T00:00:00Z")])
    verdict = _verdict(policy, synthetic_bundle, client)
    assert verdict.verdict == "AUTHORIZED"
    assert verdict.synthetic_only is True
    assert verdict.production_authorization_operational is False


def test_later_comment_supersedes_across_pages(policy, synthetic_bundle):
    reviews = [
        _review(80, 7, "APPROVED", REVISION, "2026-10-28T00:00:00Z"),
        _review(81, 7, "COMMENTED", REVISION, "2026-10-28T02:00:00Z"),
    ]
    verdict = _verdict(policy, synthetic_bundle, FakeGitHub(reviews))
    assert verdict.verdict == "BLOCKED"
    assert "REVIEW_SUPERSEDED" in verdict.reason_codes


def test_later_dismissal_and_change_request_supersede(policy, synthetic_bundle):
    for state in ("DISMISSED", "CHANGES_REQUESTED"):
        reviews = [
            _review(80, 7, "APPROVED", REVISION, "2026-10-28T00:00:00Z"),
            _review(81, 7, state, REVISION, "2026-10-28T02:00:00Z"),
        ]
        verdict = _verdict(policy, synthetic_bundle, FakeGitHub(reviews))
        assert verdict.verdict == "BLOCKED"
        assert "REVIEW_SUPERSEDED" in verdict.reason_codes


def test_timestamp_tie_uses_the_higher_review_id(policy, synthetic_bundle):
    stamp = "2026-10-28T00:00:00Z"
    reviews = [
        _review(90, 7, "APPROVED", REVISION, stamp),
        _review(80, 7, "CHANGES_REQUESTED", REVISION, stamp),
    ]
    blocked = _verdict(policy, synthetic_bundle, FakeGitHub(reviews))
    assert blocked.verdict == "BLOCKED"
    assert "REVIEW_SUPERSEDED" in blocked.reason_codes
    decision, authorization, roles = _bundle_for(synthetic_bundle)
    authorization["approvals"][0]["evidence_ref"] = "90"
    decision["approval_evidence"][0]["evidence_id"] = "90"
    verdict = evaluate_authorization(
        decision=decision,
        authorization=authorization,
        request=synthetic_bundle["request"],
        trusted_policy=policy,
        candidate_policy=policy,
        trusted_roles=roles,
        evidence_resolver=GitHubEvidenceResolver(FakeGitHub(reviews), repository=REPOSITORY, pull_number=45),
        mode="synthetic",
        as_of=as_of(synthetic_bundle),
    )
    assert verdict.verdict == "AUTHORIZED"
    assert verdict.production_authorization_operational is False


def test_pending_review_fails_closed(policy, synthetic_bundle):
    reviews = [
        _review(80, 7, "APPROVED", REVISION, "2026-10-28T00:00:00Z"),
        _review(81, 7, "PENDING", REVISION, "2026-10-28T03:00:00Z"),
    ]
    verdict = _verdict(policy, synthetic_bundle, FakeGitHub(reviews))
    assert verdict.code == 3
    assert verdict.verdict == "EVIDENCE_UNAVAILABLE"


def test_missing_timestamp_fails_closed(policy, synthetic_bundle):
    review = _review(80, 7, "APPROVED", REVISION, "2026-10-28T00:00:00Z")
    del review["submitted_at"]
    verdict = _verdict(policy, synthetic_bundle, FakeGitHub([review]))
    assert verdict.code == 3
    assert verdict.verdict == "EVIDENCE_UNAVAILABLE"


def _pages(factory):
    holder = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.endswith("/permission"):
                status, body, link = 200, {"permission": "write"}, None
            else:
                status, body, link = holder["pages"].get(self.path, (404, {"missing": True}, None))
            raw = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            if link:
                self.send_header("Link", link)
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, _format, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    holder["pages"] = factory(base)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, base


def test_review_pages_follow_link_and_stop_on_failure(policy, synthetic_bundle):
    first = "/repos/HanzoRazer/CAM-Assist-Blueprint/pulls/45/reviews?per_page=100"
    older = _review(80, 7, "APPROVED", REVISION, "2026-10-28T00:00:00Z")
    later = _review(81, 7, "COMMENTED", REVISION, "2026-10-28T04:00:00Z")

    def factory(base):
        second = "/repos/HanzoRazer/CAM-Assist-Blueprint/pulls/45/reviews?page=2"
        return {
            first: (200, [older], f'<{base}{second}>; rel="next"'),
            second: (200, [later], None),
        }

    server, base = _pages(factory)
    try:
        client = UrllibGitHubClient("governance-test-token", api_base=base)
        verdict = _verdict(policy, synthetic_bundle, client)
    finally:
        server.shutdown()
    assert verdict.verdict == "BLOCKED"
    assert "REVIEW_SUPERSEDED" in verdict.reason_codes

    def failing(base):
        second = "/repos/HanzoRazer/CAM-Assist-Blueprint/pulls/45/reviews?page=2"
        return {first: (200, [older], f'<{base}{second}>; rel="next"'), second: (503, {"error": True}, None)}

    server, base = _pages(failing)
    try:
        client = UrllibGitHubClient("governance-test-token", api_base=base)
        try:
            client.list_reviews(REPOSITORY, 45)
        except EvidenceUnavailable:
            failed = True
        else:
            failed = False
        verdict = _verdict(policy, synthetic_bundle, client)
    finally:
        server.shutdown()
    assert failed is True
    assert verdict.code == 3
    assert verdict.verdict == "EVIDENCE_UNAVAILABLE"


def test_review_page_link_cannot_leave_the_api_host():
    first = "/repos/HanzoRazer/CAM-Assist-Blueprint/pulls/45/reviews?per_page=100"

    def factory(base):
        return {first: (200, [], '<http://evil.example/reviews?page=2>; rel="next"')}

    server, base = _pages(factory)
    try:
        client = UrllibGitHubClient("governance-test-token", api_base=base)
        try:
            client.list_reviews(REPOSITORY, 45)
        except EvidenceUnavailable:
            refused = True
        else:
            refused = False
    finally:
        server.shutdown()
    assert refused is True


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
