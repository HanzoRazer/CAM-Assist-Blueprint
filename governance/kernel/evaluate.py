"""Fail-closed governance evaluation.

Trusted policy is the only policy that can satisfy an authorization check.
A candidate policy with a different digest cannot authorize the change that
introduces it. Production mode never returns authorized: this build is a
non-authoritative pilot, and a JSON flag cannot turn that off.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from jsonschema import Draft202012Validator

from governance.kernel.canonical import CANONICALIZATION, digest_of
from governance.kernel.verdict import (
    AUTHORIZED,
    BLOCKED,
    CODE_AUTHORIZED,
    CODE_BLOCKED,
    CODE_EVIDENCE,
    CODE_INVALID,
    CODE_VERIFIER,
    EVIDENCE_UNAVAILABLE,
    INVALID,
    VERIFIER_ERROR,
    Verdict,
    make_verdict,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "governance" / "schemas"
DECISION_SCHEMA_VERSION = "governance-decision-v1"
AUTHORIZATION_SCHEMA_VERSION = "governance-authorization-v1"
POLICY_SCHEMA_VERSION = "governance-policy-v1"
ROLES_SCHEMA_VERSION = "governance-roles-v1"
TRUSTED_EVIDENCE_KIND = "github_pull_request_review"

EvidenceResolver = Callable[[str], Mapping[str, Any]]


class EvidenceUnavailable(Exception):
    """The evidence service could not be consulted."""


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _schema(name: str) -> dict:
    return load_json(SCHEMA_DIR / name)


def _decision_id(decision: Mapping[str, Any] | None) -> str | None:
    if isinstance(decision, Mapping):
        value = decision.get("decision_id")
        if isinstance(value, str):
            return value
    return None


def _production_flag(policy: Mapping[str, Any] | None) -> bool:
    if not isinstance(policy, Mapping):
        return False
    return policy.get("production_authorization_operational") is True


def parse_time(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError("timestamp requires a timezone")
    return parsed


def policy_invariants(policy: Mapping[str, Any]) -> list[str]:
    """Return verifier errors for a trust root that would weaken the pilot."""
    reasons: list[str] = []
    if policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        reasons.append("UNKNOWN_POLICY_VERSION")
    if policy.get("canonicalization") != CANONICALIZATION:
        reasons.append("UNSUPPORTED_CANONICALIZATION")
    if policy.get("merged_pull_request_is_approval") is not False:
        reasons.append("POLICY_INVARIANT_VIOLATION")
    if policy.get("pr_comment_is_approval") is not False:
        reasons.append("POLICY_INVARIANT_VIOLATION")
    if policy.get("editable_approved_boolean_is_evidence") is not False:
        reasons.append("POLICY_INVARIANT_VIOLATION")
    if policy.get("execution_authority_claim_allowed") is not False:
        reasons.append("POLICY_INVARIANT_VIOLATION")
    if policy.get("decision_status_authorizes_implementation") is not False:
        reasons.append("POLICY_INVARIANT_VIOLATION")
    if policy.get("production_authorization_operational") is not False:
        reasons.append("POLICY_CLAIMS_PRODUCTION_AUTHORITY")
    if policy.get("trusted_evidence_kind") != TRUSTED_EVIDENCE_KIND:
        reasons.append("POLICY_INVARIANT_VIOLATION")
    required = policy.get("required_prohibited_capabilities")
    if not isinstance(required, list) or not required:
        reasons.append("POLICY_INVARIANT_VIOLATION")
    return sorted(set(reasons))


def _schema_invalid(instance: Any, schema: dict) -> bool:
    validator = Draft202012Validator(schema)
    return next(validator.iter_errors(instance), None) is not None


def _identities_for(roles: Mapping[str, Any], role_name: str) -> set[str] | None:
    found = None
    for role in roles.get("roles", []):
        if isinstance(role, Mapping) and role.get("role") == role_name:
            found = role
            break
    if found is None:
        return None
    identities = found.get("identities")
    if not isinstance(identities, list) or not all(isinstance(item, str) for item in identities):
        return None
    return set(identities)


def _resolve(resolver: EvidenceResolver | None, evidence_ref: str) -> tuple[Mapping[str, Any] | None, str | None]:
    if resolver is None:
        return None, "EVIDENCE_SERVICE_UNAVAILABLE"
    try:
        payload = resolver(evidence_ref)
    except EvidenceUnavailable:
        return None, "EVIDENCE_SERVICE_UNAVAILABLE"
    except Exception:
        return None, "VERIFIER_ERROR"
    if not isinstance(payload, Mapping) or payload.get("available") is not True:
        return None, "MISSING_EVIDENCE"
    return payload, None


def verify_registry(document: Mapping[str, Any]) -> Verdict:
    reasons: list[str] = []
    if document.get("schema_version") != "governance-registry-v1":
        reasons.append("UNKNOWN_SCHEMA_VERSION")
    if document.get("canonicalization") != CANONICALIZATION:
        reasons.append("UNSUPPORTED_CANONICALIZATION")
    expected = document.get("registry_digest")
    actual = digest_of(dict(document), omit_key="registry_digest")
    if not isinstance(expected, str) or expected != actual:
        reasons.append("REGISTRY_DIGEST_MISMATCH")
    records = document.get("records")
    if not isinstance(records, list):
        reasons.append("SCHEMA_INVALID")
    else:
        for entry in records:
            if not isinstance(entry, Mapping):
                reasons.append("SCHEMA_INVALID")
                continue
            body = entry.get("decision", entry.get("authorization"))
            claimed = entry.get("record_digest")
            if not isinstance(body, Mapping) or not isinstance(claimed, str):
                reasons.append("SCHEMA_INVALID")
                continue
            if digest_of(dict(body)) != claimed:
                reasons.append("REGISTRY_DIGEST_MISMATCH")
    if reasons:
        code = CODE_INVALID if "UNKNOWN_SCHEMA_VERSION" in reasons or "SCHEMA_INVALID" in reasons or "REGISTRY_DIGEST_MISMATCH" in reasons else CODE_VERIFIER
        verdict = INVALID if code == CODE_INVALID else VERIFIER_ERROR
        return make_verdict(code, verdict, reasons, decision_id=None, production_operational=False)
    return make_verdict(
        CODE_BLOCKED,
        BLOCKED,
        ["REGISTRY_INTACT_NOT_AN_AUTHORIZATION"],
        decision_id=None,
        production_operational=False,
    )


def evaluate_authorization(
    *,
    decision: Mapping[str, Any],
    authorization: Mapping[str, Any] | None,
    request: Mapping[str, Any],
    trusted_policy: Mapping[str, Any],
    trusted_roles: Mapping[str, Any],
    candidate_policy: Mapping[str, Any] | None = None,
    evidence_resolver: EvidenceResolver | None = None,
    mode: str = "production",
    as_of: datetime | None = None,
) -> Verdict:
    decision_id = _decision_id(decision)
    production = False
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        return make_verdict(CODE_VERIFIER, VERIFIER_ERROR, ["INVALID_AS_OF_TIME"], decision_id=decision_id, production_operational=False)
    if mode not in {"production", "synthetic"}:
        return make_verdict(
            CODE_VERIFIER,
            VERIFIER_ERROR,
            ["UNKNOWN_EVALUATION_MODE"],
            decision_id=decision_id,
            production_operational=False,
        )
    invariant_failures = policy_invariants(trusted_policy)
    if invariant_failures:
        return make_verdict(
            CODE_VERIFIER,
            VERIFIER_ERROR,
            invariant_failures,
            decision_id=decision_id,
            production_operational=False,
        )
    if trusted_roles.get("schema_version") != ROLES_SCHEMA_VERSION:
        return make_verdict(
            CODE_VERIFIER,
            VERIFIER_ERROR,
            ["UNKNOWN_ROLES_VERSION"],
            decision_id=decision_id,
            production_operational=False,
        )

    reasons: list[str] = []
    evidence_reasons: list[str] = []
    candidate = trusted_policy if candidate_policy is None else candidate_policy
    if digest_of(dict(candidate)) != digest_of(dict(trusted_policy)):
        reasons.append("POLICY_SELF_MODIFICATION")

    if decision.get("schema_version") != DECISION_SCHEMA_VERSION:
        return make_verdict(
            CODE_INVALID,
            INVALID,
            ["UNKNOWN_SCHEMA_VERSION"],
            decision_id=decision_id,
            production_operational=production,
        )
    if _schema_invalid(decision, _schema("decision_record_v1.schema.json")):
        return make_verdict(
            CODE_INVALID,
            INVALID,
            ["SCHEMA_INVALID"],
            decision_id=decision_id,
            production_operational=production,
        )
    if "approved" in decision:
        reasons.append("EDITABLE_APPROVAL_BOOLEAN")

    if decision.get("pr_merged") is True:
        reasons.append("MERGED_PR_NOT_APPROVAL")
    if decision.get("status") != "ACCEPTED":
        reasons.append("DECISION_NOT_ACCEPTED")
    elif decision.get("decision_owner") in (None, ""):
        reasons.append("MISSING_DECISION_OWNER")
    elif not decision.get("approval_evidence"):
        reasons.append("MISSING_DECISION_APPROVAL")

    if request.get("decision_id") != decision.get("decision_id"):
        reasons.append("DECISION_ID_MISMATCH")
    if request.get("repository") != decision.get("subject_repository"):
        reasons.append("REPOSITORY_MISMATCH")
    if request.get("revision") != decision.get("subject_revision"):
        reasons.append("REVISION_MISMATCH")

    if authorization is None:
        reasons.append("MISSING_IMPLEMENTATION_AUTHORIZATION")
    else:
        if authorization.get("schema_version") != AUTHORIZATION_SCHEMA_VERSION:
            return make_verdict(
                CODE_INVALID,
                INVALID,
                ["UNKNOWN_SCHEMA_VERSION"],
                decision_id=decision_id,
                production_operational=production,
            )
        if _schema_invalid(authorization, _schema("authorization_record_v1.schema.json")):
            extra = ["SCHEMA_INVALID"]
            if authorization.get("execution_authority_claim") is True:
                extra.append("EXECUTION_AUTHORITY_CLAIM")
            return make_verdict(
                CODE_INVALID,
                INVALID,
                extra,
                decision_id=decision_id,
                production_operational=production,
            )
        if authorization.get("execution_authority_claim") is not False:
            reasons.append("EXECUTION_AUTHORITY_CLAIM")
        if authorization.get("decision_id") != decision.get("decision_id"):
            reasons.append("DECISION_ID_MISMATCH")
        if authorization.get("approved_decision_revision") != request.get("revision"):
            reasons.append("REVISION_MISMATCH")
        if authorization.get("authorized_repository") != request.get("repository"):
            reasons.append("REPOSITORY_MISMATCH")
        if authorization.get("policy_digest") != digest_of(dict(trusted_policy)):
            reasons.append("POLICY_DIGEST_MISMATCH")
        if authorization.get("revoked") is True:
            reasons.append("AUTHORIZATION_REVOKED")
        if authorization.get("superseded_by") not in (None, ""):
            reasons.append("AUTHORIZATION_SUPERSEDED")
        required = set(trusted_policy.get("required_prohibited_capabilities") or [])
        prohibited = set(authorization.get("prohibited_capabilities") or [])
        if not required.issubset(prohibited):
            reasons.append("MISSING_PROHIBITED_CAPABILITY")
        requested_scope = request.get("scope")
        authorized_scope = set(authorization.get("implementation_scope") or [])
        if not isinstance(requested_scope, list) or not requested_scope or not set(requested_scope).issubset(authorized_scope):
            reasons.append("SCOPE_MISMATCH")
        try:
            effective = parse_time(authorization["effective_date"])
            if as_of < effective:
                reasons.append("AUTHORIZATION_NOT_YET_EFFECTIVE")
            expires_at = authorization.get("expires_at")
            if isinstance(expires_at, str) and as_of >= parse_time(expires_at):
                reasons.append("AUTHORIZATION_EXPIRED")
        except (KeyError, TypeError, ValueError):
            reasons.append("SCHEMA_INVALID")
        if mode == "production":
            if authorization.get("synthetic") is True or authorization.get("production_eligible") is True:
                reasons.append("SYNTHETIC_NOT_PRODUCTION")
            reasons.append("PRODUCTION_AUTHORIZATION_NOT_OPERATIONAL")
        else:
            if authorization.get("synthetic") is not True or authorization.get("production_eligible") is not False:
                reasons.append("SYNTHETIC_NOT_ISOLATED")
            if trusted_roles.get("synthetic") is not True:
                reasons.append("SYNTHETIC_AUTHORITY_REQUIRED")
        _check_approvals(
            authorization.get("approvals") or [],
            role_name="implementation_authorizer",
            roles=trusted_roles,
            resolver=evidence_resolver,
            expected_revision=str(request.get("revision")),
            reasons=reasons,
            evidence_reasons=evidence_reasons,
        )

    if decision.get("status") == "ACCEPTED":
        _check_decision_evidence(
            decision.get("approval_evidence") or [],
            roles=trusted_roles,
            resolver=evidence_resolver,
            expected_revision=str(decision.get("subject_revision")),
            reasons=reasons,
            evidence_reasons=evidence_reasons,
        )

    if mode == "production":
        reasons.append("PRODUCTION_AUTHORIZATION_NOT_OPERATIONAL")

    if evidence_reasons:
        reasons.extend(evidence_reasons)
    evidence_only = {"MISSING_EVIDENCE", "EVIDENCE_SERVICE_UNAVAILABLE"}
    if reasons and set(reasons) <= evidence_only:
        return make_verdict(
            CODE_EVIDENCE,
            EVIDENCE_UNAVAILABLE,
            reasons,
            decision_id=decision_id,
            production_operational=production,
        )
    if "VERIFIER_ERROR" in reasons:
        return make_verdict(
            CODE_VERIFIER,
            VERIFIER_ERROR,
            reasons,
            decision_id=decision_id,
            production_operational=production,
        )
    if reasons:
        code = CODE_INVALID if "SCHEMA_INVALID" in reasons else CODE_BLOCKED
        verdict = INVALID if code == CODE_INVALID else BLOCKED
        return make_verdict(
            code,
            verdict,
            reasons,
            decision_id=decision_id,
            production_operational=production,
        )
    if mode != "synthetic":
        return make_verdict(
            CODE_BLOCKED,
            BLOCKED,
            ["PRODUCTION_AUTHORIZATION_NOT_OPERATIONAL"],
            decision_id=decision_id,
            production_operational=production,
        )
    return make_verdict(
        CODE_AUTHORIZED,
        AUTHORIZED,
        ["SYNTHETIC_ONLY"],
        decision_id=decision_id,
        production_operational=False,
        synthetic_only=True,
    )


def _check_decision_evidence(
    evidence_refs: list,
    *,
    roles: Mapping[str, Any],
    resolver: EvidenceResolver | None,
    expected_revision: str,
    reasons: list[str],
    evidence_reasons: list[str],
) -> None:
    identities = _identities_for(roles, "decision_approver")
    if identities is None:
        reasons.append("UNKNOWN_ROLE")
        return
    if not evidence_refs:
        return
    for ref in evidence_refs:
        if not isinstance(ref, Mapping):
            reasons.append("SCHEMA_INVALID")
            continue
        if ref.get("kind") != TRUSTED_EVIDENCE_KIND:
            reasons.append("UNTRUSTED_EVIDENCE_KIND")
            continue
        payload, problem = _resolve(resolver, str(ref.get("evidence_id")))
        if problem == "VERIFIER_ERROR":
            reasons.append("VERIFIER_ERROR")
            continue
        if problem is not None or payload is None:
            evidence_reasons.append(problem or "MISSING_EVIDENCE")
            continue
        _match_evidence(payload, identities, expected_revision, reasons)


def _check_approvals(
    approvals: list,
    *,
    role_name: str,
    roles: Mapping[str, Any],
    resolver: EvidenceResolver | None,
    expected_revision: str,
    reasons: list[str],
    evidence_reasons: list[str],
) -> None:
    identities = _identities_for(roles, role_name)
    if identities is None:
        reasons.append("UNKNOWN_ROLE")
        return
    for approval in approvals:
        if not isinstance(approval, Mapping):
            reasons.append("SCHEMA_INVALID")
            continue
        if approval.get("role") != role_name:
            reasons.append("WRONG_APPROVAL_ROLE")
        claimed = approval.get("identity")
        if not isinstance(claimed, str) or claimed not in identities:
            reasons.append("UNRECOGNIZED_IDENTITY")
        payload, problem = _resolve(resolver, str(approval.get("evidence_ref")))
        if problem == "VERIFIER_ERROR":
            reasons.append("VERIFIER_ERROR")
            continue
        if problem is not None or payload is None:
            evidence_reasons.append(problem or "MISSING_EVIDENCE")
            continue
        if payload.get("identity") != claimed:
            reasons.append("UNRECOGNIZED_IDENTITY")
        _match_evidence(payload, identities, expected_revision, reasons)


def _match_evidence(
    payload: Mapping[str, Any],
    identities: set[str],
    expected_revision: str,
    reasons: list[str],
) -> None:
    if payload.get("kind") != TRUSTED_EVIDENCE_KIND:
        reasons.append("UNTRUSTED_EVIDENCE_KIND")
        return
    if payload.get("review_state") != "APPROVED":
        reasons.append("REVIEW_NOT_APPROVED")
    identity = payload.get("identity")
    if not isinstance(identity, str) or identity not in identities:
        reasons.append("UNRECOGNIZED_IDENTITY")
    if payload.get("commit_id") != expected_revision:
        reasons.append("REVISION_MISMATCH")
