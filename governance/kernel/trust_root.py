"""Load governance policy from a commit, never from the candidate worktree.

The running process is the pinned verifier only when its source digest equals
the digest of those same paths at the named commit. A matching digest does not
activate production authorization and does not prove a required check.
"""

from __future__ import annotations

from dataclasses import dataclass
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


def assess_deployment(
    *,
    repo: Path,
    trust_commit: str | None,
    workflow_text: str,
    required_checks: list[str] | None,
    protection_error: str | None = None,
) -> dict[str, Any]:
    """Describe deployment. This function never sets production authorization."""
    contract = assess_workflow_text(workflow_text)
    protection_state = "unverified"
    required = False
    if protection_error:
        protection_state = "unverified"
    elif required_checks is None:
        protection_state = "unverified"
    elif TRUSTED_JOB_NAME in required_checks:
        protection_state = "required"
        required = True
    else:
        protection_state = "not_required"
    matches = False
    policy_digest = None
    commit = trust_commit
    reason = "TRUST_ROOT_NOT_ESTABLISHED"
    if trust_commit:
        try:
            loaded = load_git_trust_root(repo, trust_commit)
            policy_digest = loaded.policy_digest
            matches = running_verifier_digest(repo) == loaded.verifier_digest
            reason = "PIN_MATCHES_RUNNING_CODE" if matches else "VERIFIER_PIN_MISMATCH"
        except TrustRootError as exc:
            reason = exc.code
    deployed = bool(matches and contract.ok and required and protection_error is None)
    status = "DEPLOYED_NOT_ACTIVATED" if deployed else "NOT_DEPLOYED"
    return {
        "activation_permitted": False,
        "deployment_status": status,
        "policy_digest": policy_digest,
        "production_authorization_operational": False,
        "protection_state": protection_state,
        "required_check_confirmed": required and protection_error is None,
        "running_verifier_matches_pin": matches,
        "trust_commit": commit,
        "trust_reason": reason,
        "workflow_contract_ok": contract.ok,
        "workflow_reasons": list(contract.reasons),
    }
