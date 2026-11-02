"""Load governance policy from a commit, never from the candidate worktree.

The running process is the pinned verifier only when its source digest equals
the digest of those same paths at the named commit. A matching digest does not
activate production authorization and does not prove a required check.
"""

from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

from governance.kernel.canonical import digest_of

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_BLOB_PATH = re.compile(r"^[A-Za-z0-9_./-]+$")

POLICY_PATH = "governance/policy/governance_policy_v1.json"
ROLES_PATH = "governance/policy/authorized_roles_v1.json"
VERIFIER_PATHS = (
    "governance/kernel/canonical.py",
    "governance/kernel/evaluate.py",
    "governance/kernel/github_evidence.py",
    "governance/kernel/trust_root.py",
    "governance/kernel/verdict.py",
)
TRUSTED_WORKFLOW_PATH = ".github/workflows/governance-trusted.yml"
TRUSTED_JOB_NAME = "governance-trusted"


class TrustRootError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GitTrustRoot:
    commit: str
    policy: dict[str, Any]
    roles: dict[str, Any]
    policy_digest: str
    verifier_digest: str

    def provenance(self, *, running_digest: str | None) -> dict[str, Any]:
        matches = running_digest == self.verifier_digest
        return {
            "candidate_worktree_is_trust_root": False,
            "commit": self.commit,
            "established": False,
            "policy_digest": self.policy_digest,
            "reason": "PIN_MATCHES_RUNNING_CODE" if matches else "VERIFIER_PIN_MISMATCH",
            "running_verifier_matches_pin": matches,
            "source": "git-commit",
        }


@dataclass(frozen=True)
class WorkflowContract:
    ok: bool
    reasons: tuple[str, ...]


def verifier_digest(blobs: Mapping[str, bytes]) -> str:
    manifest = {
        path: hashlib.sha256(blobs[path]).hexdigest()
        for path in sorted(blobs)
    }
    return digest_of(manifest)


def running_verifier_digest(root: Path) -> str:
    blobs: dict[str, bytes] = {}
    for path in VERIFIER_PATHS:
        file = root / path
        if not file.is_file():
            raise TrustRootError("VERIFIER_SOURCE_MISSING")
        blobs[path] = file.read_bytes()
    return verifier_digest(blobs)


def git_blob(repo: Path, commit: str, path: str) -> bytes:
    if _COMMIT.fullmatch(commit) is None:
        raise TrustRootError("UNKNOWN_TRUST_COMMIT")
    if _BLOB_PATH.fullmatch(path) is None or ".." in path.split("/"):
        raise TrustRootError("UNTRUSTED_BLOB_PATH")
    probe = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0:
        raise TrustRootError("UNKNOWN_TRUST_COMMIT")
    shown = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        capture_output=True,
        check=False,
    )
    if shown.returncode != 0:
        raise TrustRootError("MISSING_TRUST_BLOB")
    return shown.stdout


def load_git_trust_root(
    repo: Path,
    commit: str,
    *,
    expected_policy_digest: str | None = None,
) -> GitTrustRoot:
    """Read policy, roles, and verifier bytes from ``commit`` only."""
    policy_bytes = git_blob(repo, commit, POLICY_PATH)
    roles_bytes = git_blob(repo, commit, ROLES_PATH)
    blobs = {path: git_blob(repo, commit, path) for path in VERIFIER_PATHS}
    try:
        policy = json.loads(policy_bytes)
        roles = json.loads(roles_bytes)
    except json.JSONDecodeError as exc:
        raise TrustRootError("TRUST_BLOB_INVALID") from exc
    if not isinstance(policy, dict) or not isinstance(roles, dict):
        raise TrustRootError("TRUST_BLOB_INVALID")
    policy_digest = digest_of(policy)
    if expected_policy_digest is not None and policy_digest != expected_policy_digest:
        raise TrustRootError("WRONG_POLICY_DIGEST")
    return GitTrustRoot(
        commit=commit,
        policy=policy,
        roles=roles,
        policy_digest=policy_digest,
        verifier_digest=verifier_digest(blobs),
    )


def unresolved_trust_root(policy_digest: str | None) -> dict[str, Any]:
    """Provenance for a process that was not given an outside commit."""
    return {
        "candidate_worktree_is_trust_root": False,
        "commit": None,
        "established": False,
        "policy_digest": policy_digest,
        "reason": "TRUST_ROOT_NOT_ESTABLISHED",
        "running_verifier_matches_pin": False,
        "source": "candidate-checkout-rejected",
    }


def trust_commit_from_env() -> str | None:
    value = os.environ.get("GOVERNANCE_TRUST_COMMIT")
    if value is None or value == "":
        return None
    if _COMMIT.fullmatch(value) is None:
        raise TrustRootError("UNKNOWN_TRUST_COMMIT")
    return value


def assess_workflow_text(text: str) -> WorkflowContract:
    """Accept only a read-only pull_request_target workflow pinned to the base SHA."""
    reasons: list[str] = []
    if "pull_request_target:" not in text:
        reasons.append("MISSING_PULL_REQUEST_TARGET")
    if re.search(r"(?m)^\s*pull_request:\s*$", text):
        reasons.append("CANDIDATE_WORKFLOW_EVENT")
    if "paths:" in text:
        reasons.append("PATH_FILTER")
    if "contents: read" not in text or "pull-requests: read" not in text:
        reasons.append("PERMISSIONS_NOT_READ_ONLY")
    if "contents: write" in text or "pull-requests: write" in text:
        reasons.append("WRITE_PERMISSION")
    if "github.event.pull_request.base.sha" not in text:
        reasons.append("BASE_SHA_NOT_PINNED")
    if "github.event.pull_request.head" in text or "github.sha" in text:
        reasons.append("CANDIDATE_SHA_CHECKOUT")
    if "persist-credentials: false" not in text:
        reasons.append("CREDENTIALS_PERSISTED")
    if TRUSTED_JOB_NAME not in text:
        reasons.append("UNSTABLE_JOB_NAME")
    return WorkflowContract(ok=not reasons, reasons=tuple(sorted(set(reasons))))


@dataclass(frozen=True)
class RulesetFetch:
    """One ruleset list entry and the detail read that must follow it."""

    ruleset_id: int
    detail: Mapping[str, Any] | None
    error: str | None = None


@dataclass(frozen=True)
class ProtectionProbe:
    """Raw GitHub responses. An unread source cannot prove a check is absent."""

    branch_protection_status: int | None
    branch_protection_body: Mapping[str, Any] | None
    ruleset_list_status: int | None
    ruleset_details: tuple[RulesetFetch, ...]


@dataclass(frozen=True)
class ProtectionAssessment:
    state: str
    required_checks: tuple[str, ...]
    evidence: tuple[str, ...]


def _ref_matches(pattern: str, branch: str, default_branch: str) -> bool:
    if pattern == "~ALL":
        return True
    if pattern == "~DEFAULT_BRANCH":
        return branch == default_branch
    full = f"refs/heads/{branch}"
    if pattern in {full, branch}:
        return True
    if "*" in pattern:
        return fnmatch.fnmatch(full, pattern)
    return False


def ruleset_applies_to_branch(ruleset: Mapping[str, Any], branch: str, default_branch: str) -> bool:
    """Active branch rulesets whose ref rules include ``branch``."""
    if ruleset.get("target") not in {None, "branch"}:
        return False
    if ruleset.get("enforcement") != "active":
        return False
    conditions = ruleset.get("conditions")
    ref_name = conditions.get("ref_name") if isinstance(conditions, Mapping) else None
    if not isinstance(ref_name, Mapping):
        return False
    include = ref_name.get("include")
    exclude = ref_name.get("exclude")
    included = [item for item in include if isinstance(item, str)] if isinstance(include, list) else []
    excluded = [item for item in exclude if isinstance(item, str)] if isinstance(exclude, list) else []
    if not any(_ref_matches(item, branch, default_branch) for item in included):
        return False
    if any(_ref_matches(item, branch, default_branch) for item in excluded):
        return False
    return True


def _check_names(values: Any) -> list[str]:
    names: list[str] = []
    if not isinstance(values, list):
        return names
    for item in values:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, Mapping) and isinstance(item.get("context"), str):
            names.append(item["context"])
    return names


def contexts_from_branch_protection(body: Mapping[str, Any]) -> list[str]:
    block = body.get("required_status_checks")
    if not isinstance(block, Mapping):
        return []
    return _check_names(block.get("checks")) + _check_names(block.get("contexts"))


def contexts_from_ruleset(ruleset: Mapping[str, Any]) -> list[str]:
    names: list[str] = []
    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        return names
    for rule in rules:
        if not isinstance(rule, Mapping) or rule.get("type") != "required_status_checks":
            continue
        parameters = rule.get("parameters")
        if not isinstance(parameters, Mapping):
            continue
        names.extend(_check_names(parameters.get("required_status_checks")))
    return names


def interpret_protection(
    probe: ProtectionProbe,
    *,
    branch: str = "main",
    default_branch: str = "main",
) -> ProtectionAssessment:
    """Combine classic protection and full ruleset documents.

    ``not_required`` is returned only after both sources were read completely.
    A list of ruleset ids without their documents stays ``unverified``.
    """
    if probe.branch_protection_status not in {200, 404} or probe.ruleset_list_status != 200:
        status = probe.branch_protection_status
        rules = probe.ruleset_list_status
        return ProtectionAssessment(
            "unverified",
            (),
            (f"branch_protection_http_{status}", f"ruleset_list_http_{rules}"),
        )
    checks: list[str] = []
    evidence: list[str] = []
    if probe.branch_protection_status == 404:
        evidence.append("branch_protection_absent")
    else:
        if not isinstance(probe.branch_protection_body, Mapping):
            return ProtectionAssessment("unverified", (), ("branch_protection_body_unreadable",))
        checks.extend(contexts_from_branch_protection(probe.branch_protection_body))
        evidence.append("branch_protection_read")
    for fetch in probe.ruleset_details:
        if fetch.detail is None:
            return ProtectionAssessment("unverified", (), ("ruleset_detail_unread",))
        if ruleset_applies_to_branch(fetch.detail, branch, default_branch):
            checks.extend(contexts_from_ruleset(fetch.detail))
            evidence.append(f"ruleset_{fetch.ruleset_id}_applied")
        else:
            evidence.append(f"ruleset_{fetch.ruleset_id}_not_applicable")
    unique = tuple(sorted(set(checks)))
    if TRUSTED_JOB_NAME in unique:
        return ProtectionAssessment("required", unique, tuple(evidence))
    return ProtectionAssessment("not_required", unique, tuple(evidence))


def assess_deployment(
    *,
    repo: Path,
    trust_commit: str | None,
    protection: ProtectionAssessment,
) -> dict[str, Any]:
    """Describe deployment. The workflow bytes come from ``trust_commit``.

    A commit SHA does not establish authority. Authority also requires the
    live protection assessment to be ``required``. Production authorization
    stays disabled in every result.
    """
    matches = False
    policy_digest = None
    contract_ok = False
    workflow_reasons: list[str] = []
    reason = "TRUST_ROOT_NOT_ESTABLISHED"
    if trust_commit:
        try:
            loaded = load_git_trust_root(repo, trust_commit)
            policy_digest = loaded.policy_digest
            matches = running_verifier_digest(repo) == loaded.verifier_digest
            reason = "PIN_MATCHES_RUNNING_CODE" if matches else "VERIFIER_PIN_MISMATCH"
            text = git_blob(repo, trust_commit, TRUSTED_WORKFLOW_PATH).decode("utf-8")
            contract = assess_workflow_text(text)
            contract_ok = contract.ok
            workflow_reasons = list(contract.reasons)
        except TrustRootError as exc:
            reason = exc.code
    required = protection.state == "required"
    authority = bool(matches and contract_ok and required and reason == "PIN_MATCHES_RUNNING_CODE")
    status = "DEPLOYED_NOT_ACTIVATED" if authority else "NOT_DEPLOYED"
    return {
        "activation_permitted": False,
        "authority_established": authority,
        "deployment_status": status,
        "policy_digest": policy_digest,
        "production_authorization_operational": False,
        "protection_evidence": list(protection.evidence),
        "protection_state": protection.state,
        "required_check_confirmed": required,
        "running_verifier_matches_pin": matches,
        "trust_commit": trust_commit,
        "trust_reason": reason,
        "workflow_contract_ok": contract_ok,
        "workflow_reasons": workflow_reasons,
        "workflow_source": "pinned-commit" if trust_commit else "unspecified",
    }
