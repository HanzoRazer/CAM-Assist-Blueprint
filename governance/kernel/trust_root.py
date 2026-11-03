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
# Everything the trusted job imports, loads, or executes. Package initializers,
# the JSON schemas the evaluator reads, and the script entry points change a
# verdict as surely as the kernel modules do.
VERIFIER_PATHS = (
    "governance/__init__.py",
    "governance/kernel/__init__.py",
    "governance/kernel/canonical.py",
    "governance/kernel/evaluate.py",
    "governance/kernel/github_evidence.py",
    "governance/kernel/trust_root.py",
    "governance/kernel/verdict.py",
    "governance/schemas/authorization_record_v1.schema.json",
    "governance/schemas/decision_record_v1.schema.json",
    "scripts/governance/_runtime.py",
    "scripts/governance/check_authorization.py",
    "scripts/governance/check_decision.py",
    "scripts/governance/report_governance.py",
)
TRUSTED_WORKFLOW_PATH = ".github/workflows/governance-trusted.yml"
TRUSTED_JOB_NAME = "governance-trusted"
TRUSTED_LOCK_PATH = "requirements/governance-trusted.txt"
# GitHub Actions. A required check without this source can be satisfied by
# any commit status that reuses the job name.
GITHUB_ACTIONS_APP_ID = 15368
BASE_SHA_EXPRESSION = "${{ github.event.pull_request.base.sha }}"
PINNED_ACTION = re.compile(r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([0-9a-f]{40})$")
TRUST_BYTE_PATHS = (
    *VERIFIER_PATHS,
    POLICY_PATH,
    ROLES_PATH,
    TRUSTED_WORKFLOW_PATH,
    TRUSTED_LOCK_PATH,
)


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


def _workflow_loader():
    import yaml

    class WorkflowLoader(yaml.SafeLoader):
        pass

    preserved = {
        key: [(tag, pattern) for tag, pattern in patterns if tag != "tag:yaml.org,2002:bool"]
        for key, patterns in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    WorkflowLoader.yaml_implicit_resolvers = preserved
    WorkflowLoader.add_implicit_resolver(
        "tag:yaml.org,2002:bool",
        re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
        list("tTfF"),
    )
    return WorkflowLoader


def _load_workflow_document(text: str) -> tuple[Mapping[str, Any] | None, str | None]:
    try:
        import yaml
    except ImportError:
        return None, "WORKFLOW_PARSER_UNAVAILABLE"
    try:
        documents = list(yaml.load_all(text, Loader=_workflow_loader()))
    except yaml.YAMLError:
        return None, "WORKFLOW_YAML_INVALID"
    if len(documents) != 1 or not isinstance(documents[0], Mapping):
        return None, "WORKFLOW_YAML_INVALID"
    if True in documents[0]:
        return None, "WORKFLOW_ON_KEY_COERCED"
    return documents[0], None


def _reason(reasons: list[str], code: str) -> None:
    if code not in reasons:
        reasons.append(code)


def _permissions_are_read_only(value: Any, reasons: list[str]) -> None:
    expected = {"contents": "read", "pull-requests": "read"}
    if value != expected:
        _reason(reasons, "PERMISSIONS_NOT_READ_ONLY")
    if isinstance(value, Mapping):
        for name, grant in value.items():
            if grant != "read" or name not in expected:
                _reason(reasons, "WRITE_PERMISSION")


def _trigger_is_exact(trigger: Any, reasons: list[str]) -> None:
    if trigger == "pull_request_target":
        return
    if not isinstance(trigger, Mapping) or list(trigger) != ["pull_request_target"]:
        _reason(reasons, "MISSING_PULL_REQUEST_TARGET")
        if isinstance(trigger, Mapping) and "pull_request" in trigger:
            _reason(reasons, "CANDIDATE_WORKFLOW_EVENT")
        return
    options = trigger.get("pull_request_target")
    if options in (None, {}):
        return
    _reason(reasons, "PATH_FILTER")


_CANDIDATE_REFERENCES = (
    "github.event.pull_request.head",
    "github.event.pull_request.merge_commit_sha",
    "github.head_ref",
    "github.sha",
    "github.ref",
    "refs/pull/",
)


def _reject_candidate_checkout(text: str, reasons: list[str]) -> None:
    if any(reference in text for reference in _CANDIDATE_REFERENCES):
        _reason(reasons, "CANDIDATE_SHA_CHECKOUT")


def _review_step(step: Any, reasons: list[str]) -> None:
    if not isinstance(step, Mapping):
        _reason(reasons, "WORKFLOW_STEP_INVALID")
        return
    if set(step) - {"name", "uses", "with", "run", "env"}:
        _reason(reasons, "WORKFLOW_STEP_INVALID")
    environment = step.get("env")
    if environment is not None and environment != {"GOVERNANCE_TRUST_COMMIT": BASE_SHA_EXPRESSION}:
        _reason(reasons, "WORKFLOW_STEP_INVALID")
    uses = step.get("uses")
    run = step.get("run")
    if (uses is None) == (run is None):
        _reason(reasons, "WORKFLOW_STEP_INVALID")
        return
    if isinstance(run, str):
        _reject_candidate_checkout(run, reasons)
        if "pip install" in run and (
            "--require-hashes" not in run or TRUSTED_LOCK_PATH not in run
        ):
            _reason(reasons, "UNPINNED_DEPENDENCY")
        return
    if not isinstance(uses, str):
        _reason(reasons, "MUTABLE_ACTION")
        return
    matched = PINNED_ACTION.fullmatch(uses)
    if matched is None:
        _reason(reasons, "MUTABLE_ACTION")
        return
    action_name = matched.group(1)
    if action_name not in {"actions/checkout", "actions/setup-python"}:
        _reason(reasons, "UNAPPROVED_ACTION")
        return
    options = step.get("with")
    if action_name == "actions/setup-python":
        if options != {"python-version": "3.11"}:
            _reason(reasons, "WORKFLOW_STEP_INVALID")
        return
    if not isinstance(options, Mapping):
        _reason(reasons, "BASE_SHA_NOT_PINNED")
        return
    allowed = {"ref", "persist-credentials", "fetch-depth"}
    if set(options) - allowed:
        _reason(reasons, "WORKFLOW_STEP_INVALID")
    ref = options.get("ref")
    if ref != BASE_SHA_EXPRESSION:
        _reason(reasons, "BASE_SHA_NOT_PINNED")
    if isinstance(ref, str):
        _reject_candidate_checkout(ref, reasons)
    if options.get("persist-credentials") is not False:
        _reason(reasons, "CREDENTIALS_PERSISTED")
    fetch_depth = options.get("fetch-depth")
    if fetch_depth is not None and fetch_depth != 1:
        _reason(reasons, "WORKFLOW_STEP_INVALID")


def assess_workflow_text(text: str) -> WorkflowContract:
    """Accept the trusted workflow only when its parsed structure matches.

    Comments are not fields. A mutable action tag, a second event, a write
    permission, or a checkout of the pull-request head fails closed.
    """
    document, problem = _load_workflow_document(text)
    if problem is not None or document is None:
        return WorkflowContract(ok=False, reasons=(problem or "WORKFLOW_YAML_INVALID",))
    reasons: list[str] = []
    if set(document) - {"name", "on", "permissions", "jobs"}:
        _reason(reasons, "WORKFLOW_STEP_INVALID")
    _trigger_is_exact(document.get("on"), reasons)
    _permissions_are_read_only(document.get("permissions"), reasons)
    jobs = document.get("jobs")
    if not isinstance(jobs, Mapping) or list(jobs) != [TRUSTED_JOB_NAME]:
        _reason(reasons, "UNSTABLE_JOB_NAME")
        job = None
    else:
        job = jobs.get(TRUSTED_JOB_NAME)
    if isinstance(job, Mapping):
        if set(job) - {"runs-on", "steps", "permissions"}:
            _reason(reasons, "WORKFLOW_STEP_INVALID")
        if job.get("runs-on") != "ubuntu-latest":
            _reason(reasons, "WORKFLOW_STEP_INVALID")
        if "permissions" in job:
            _permissions_are_read_only(job.get("permissions"), reasons)
        steps = job.get("steps")
        if not isinstance(steps, list) or not steps:
            _reason(reasons, "WORKFLOW_STEP_INVALID")
        else:
            for step in steps:
                _review_step(step, reasons)
            installs = [
                step.get("run")
                for step in steps
                if isinstance(step, Mapping) and isinstance(step.get("run"), str) and "pip install" in step.get("run")
            ]
            if not installs:
                _reason(reasons, "UNPINNED_DEPENDENCY")
    elif job is not None:
        _reason(reasons, "UNSTABLE_JOB_NAME")
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


def _check_names(values: Any, source_key: str) -> list[tuple[str, Any]]:
    """Required check names with the app that must publish each one.

    A bare string, or an entry without a source, accepts any publisher.
    """
    names: list[tuple[str, Any]] = []
    if not isinstance(values, list):
        return names
    for item in values:
        if isinstance(item, str):
            names.append((item, None))
        elif isinstance(item, Mapping) and isinstance(item.get("context"), str):
            names.append((item["context"], item.get(source_key)))
    return names


def contexts_from_branch_protection(body: Mapping[str, Any]) -> list[tuple[str, Any]]:
    block = body.get("required_status_checks")
    if not isinstance(block, Mapping):
        return []
    return _check_names(block.get("checks"), "app_id") + _check_names(block.get("contexts"), "app_id")


def contexts_from_ruleset(ruleset: Mapping[str, Any]) -> list[tuple[str, Any]]:
    names: list[tuple[str, Any]] = []
    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        return names
    for rule in rules:
        if not isinstance(rule, Mapping) or rule.get("type") != "required_status_checks":
            continue
        parameters = rule.get("parameters")
        if not isinstance(parameters, Mapping):
            continue
        names.extend(_check_names(parameters.get("required_status_checks"), "integration_id"))
    return names


def _bound_to_actions(source: Any) -> bool:
    return isinstance(source, int) and not isinstance(source, bool) and source == GITHUB_ACTIONS_APP_ID


def interpret_protection(
    probe: ProtectionProbe,
    *,
    branch: str = "main",
    default_branch: str = "main",
) -> ProtectionAssessment:
    """Combine classic protection and full ruleset documents.

    ``not_required`` is returned only after both sources were read completely.
    A list of ruleset ids without their documents stays ``unverified``.
    ``required`` also needs the check bound to the GitHub Actions app. A
    name that any publisher may satisfy is ``required_any_source``.
    """
    if probe.branch_protection_status not in {200, 404} or probe.ruleset_list_status != 200:
        status = probe.branch_protection_status
        rules = probe.ruleset_list_status
        return ProtectionAssessment(
            "unverified",
            (),
            (f"branch_protection_http_{status}", f"ruleset_list_http_{rules}"),
        )
    checks: list[tuple[str, Any]] = []
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
    unique = tuple(sorted({name for name, _source in checks}))
    trusted = [source for name, source in checks if name == TRUSTED_JOB_NAME]
    if any(_bound_to_actions(source) for source in trusted):
        return ProtectionAssessment("required", unique, tuple(evidence))
    if trusted:
        evidence.append("trusted_check_source_unpinned")
        return ProtectionAssessment("required_any_source", unique, tuple(evidence))
    return ProtectionAssessment("not_required", unique, tuple(evidence))


@dataclass(frozen=True)
class DeploymentWitness:
    """Live proof that the pin is what the default branch runs, and that a
    disposable pull request executed this workflow successfully."""

    relationship: str
    default_branch_sha: str | None
    verifier_bytes_match: bool
    policy_bytes_match: bool
    roles_bytes_match: bool
    workflow_bytes_match: bool
    pull_number: int | None
    base_sha: str | None
    workflow_path: str | None
    workflow_id: int | None
    run_id: int | None
    conclusion: str | None
    consistent: bool


def unverified_witness() -> DeploymentWitness:
    return DeploymentWitness(
        "unverified",
        None,
        False,
        False,
        False,
        False,
        None,
        None,
        None,
        None,
        None,
        None,
        False,
    )


def trust_bytes_match(
    pin_blobs: Mapping[str, bytes],
    tip_blobs: Mapping[str, bytes],
) -> dict[str, bool]:
    """Compare verifier, policy, roles, and workflow bytes. Workflow alone is not enough.

    The workflow group includes the hash lock its install step reads.
    """

    def same(paths: tuple[str, ...]) -> bool:
        return all(path in pin_blobs and pin_blobs.get(path) == tip_blobs.get(path) for path in paths)

    return {
        "policy": same((POLICY_PATH,)),
        "roles": same((ROLES_PATH,)),
        "verifier": same(VERIFIER_PATHS),
        "workflow": same((TRUSTED_WORKFLOW_PATH, TRUSTED_LOCK_PATH)),
    }


def relationship_from_compare(
    pin: str,
    tip: str | None,
    status: str | None,
    *,
    readable: bool,
) -> str:
    """Map a GitHub compare of ``pin...tip`` to exact, ancestor, unrelated, or unverified."""
    if not readable or tip is None or _COMMIT.fullmatch(pin) is None or _COMMIT.fullmatch(tip) is None:
        return "unverified"
    if pin == tip:
        if status not in {None, "identical"}:
            return "unverified"
        return "exact"
    if status == "identical":
        return "unverified"
    if status == "ahead":
        return "ancestor"
    if status in {"behind", "diverged"}:
        return "unrelated"
    return "unverified"


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def choose_bound_run(
    *,
    trust_commit: str,
    default_branch_sha: str,
    workflow_id: int,
    runs: list[Mapping[str, Any]],
    pulls_for_head: Mapping[str, list[Mapping[str, Any]]],
) -> tuple[dict[str, Any] | None, bool]:
    """Return one bound successful run, and whether the payload was consistent.

    A check that only reuses the job name is not this workflow. A mismatched
    path or pull-request head is inconsistent and cannot be ignored.
    """
    if not _positive_int(workflow_id):
        return None, False
    bound = None
    for run in runs:
        if not isinstance(run, Mapping):
            return None, False
        run_workflow = run.get("workflow_id")
        path = run.get("path")
        if run_workflow != workflow_id:
            if path == TRUSTED_WORKFLOW_PATH:
                return None, False
            continue
        if path != TRUSTED_WORKFLOW_PATH:
            return None, False
        if run.get("event") != "pull_request_target" or run.get("conclusion") != "success":
            continue
        head = run.get("head_sha")
        run_id = run.get("id")
        if not isinstance(head, str) or _COMMIT.fullmatch(head) is None or not _positive_int(run_id):
            return None, False
        pulls = pulls_for_head.get(head, [])
        if not isinstance(pulls, list):
            return None, False
        for pull in pulls:
            if not isinstance(pull, Mapping):
                return None, False
            number = pull.get("number")
            base_sha = pull.get("base_sha")
            pull_head = pull.get("head_sha")
            if (
                not _positive_int(number)
                or not isinstance(base_sha, str)
                or not isinstance(pull_head, str)
                or _COMMIT.fullmatch(base_sha) is None
                or _COMMIT.fullmatch(pull_head) is None
            ):
                return None, False
            if pull_head != head:
                continue
            if base_sha not in {trust_commit, default_branch_sha}:
                continue
            bound = {
                "base_sha": base_sha,
                "conclusion": "success",
                "pull_number": number,
                "run_id": run_id,
                "workflow_id": workflow_id,
                "workflow_path": TRUSTED_WORKFLOW_PATH,
            }
            break
        if bound is not None:
            break
    return bound, True


def witness_binds_pin(trust_commit: str, witness: DeploymentWitness) -> bool:
    """True only for an exact or byte-identical ancestor pin and a bound run."""
    if witness.consistent is not True:
        return False
    if witness.relationship not in {"exact", "ancestor"}:
        return False
    tip = witness.default_branch_sha
    if not isinstance(tip, str) or _COMMIT.fullmatch(trust_commit) is None or _COMMIT.fullmatch(tip) is None:
        return False
    bytes_ok = all(
        (
            witness.verifier_bytes_match,
            witness.policy_bytes_match,
            witness.roles_bytes_match,
            witness.workflow_bytes_match,
        )
    )
    if witness.relationship == "exact":
        if tip != trust_commit or not bytes_ok:
            return False
    elif tip == trust_commit or not bytes_ok:
        return False
    if witness.workflow_path != TRUSTED_WORKFLOW_PATH or witness.conclusion != "success":
        return False
    if not all(_positive_int(value) for value in (witness.workflow_id, witness.run_id, witness.pull_number)):
        return False
    if not isinstance(witness.base_sha, str) or _COMMIT.fullmatch(witness.base_sha) is None:
        return False
    return witness.base_sha in {trust_commit, tip}


def assess_deployment(
    *,
    repo: Path,
    trust_commit: str | None,
    protection: ProtectionAssessment,
    witness: DeploymentWitness | None = None,
) -> dict[str, Any]:
    """Describe deployment. The workflow bytes come from ``trust_commit``.

    A commit SHA does not establish authority. Authority requires the live
    protection assessment to be ``required``, the pin to be the default
    branch or a byte-identical ancestor, and a successful run of this
    trusted workflow bound to a pull request, base SHA, workflow id, and
    run id. Production authorization stays disabled in every result.
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
    if witness is None:
        witness = unverified_witness()
    bound = bool(trust_commit) and witness_binds_pin(trust_commit, witness)
    required = protection.state == "required"
    authority = bool(
        matches and contract_ok and required and reason == "PIN_MATCHES_RUNNING_CODE" and bound
    )
    status = "DEPLOYED_NOT_ACTIVATED" if authority else "NOT_DEPLOYED"
    return {
        "activation_permitted": False,
        "authority_established": authority,
        "deployment_evidence": {
            "base_sha": witness.base_sha,
            "bytes_match": {
                "policy": witness.policy_bytes_match,
                "roles": witness.roles_bytes_match,
                "verifier": witness.verifier_bytes_match,
                "workflow": witness.workflow_bytes_match,
            },
            "consistent": witness.consistent,
            "default_branch_sha": witness.default_branch_sha,
            "pin_relationship": witness.relationship,
            "pull_number": witness.pull_number,
            "run_conclusion": witness.conclusion,
            "run_id": witness.run_id,
            "trusted_check_bound": bound,
            "workflow_id": witness.workflow_id,
            "workflow_path": witness.workflow_path,
        },
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
