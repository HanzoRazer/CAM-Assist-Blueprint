"""Trust-root loading ignores the candidate worktree."""

from __future__ import annotations

import json
import subprocess
import sys

from governance.kernel.canonical import digest_of
from governance.kernel.trust_root import (
    POLICY_PATH,
    ROLES_PATH,
    TRUSTED_WORKFLOW_PATH,
    VERIFIER_PATHS,
    DeploymentWitness,
    ProtectionAssessment,
    TrustRootError,
    assess_deployment,
    choose_bound_run,
    load_git_trust_root,
    relationship_from_compare,
    running_verifier_digest,
    trust_bytes_match,
)
from governance.kernel.evaluate import load_json

BASELINE = "85ae01599d6aa435d3327517f6c23787fdb79adc"


def _git(repo, *args):
    subprocess.check_call(["git", "-C", str(repo), *args], stdout=subprocess.DEVNULL)


def _pin_repo(tmp_path, root):
    repo = tmp_path / "protected"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "governance-test@example.com")
    _git(repo, "config", "user.name", "Governance Test")
    for path in (*VERIFIER_PATHS, POLICY_PATH, ROLES_PATH, TRUSTED_WORKFLOW_PATH):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / path).read_bytes())
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "pin verifier")
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    return repo, sha


def test_candidate_policy_edit_does_not_change_the_pin(tmp_path, root):
    repo, sha = _pin_repo(tmp_path, root)
    trusted = load_git_trust_root(repo, sha)
    policy_path = repo / POLICY_PATH
    edited = load_json(policy_path)
    edited["merged_pull_request_is_approval"] = True
    policy_path.write_text(json.dumps(edited), encoding="utf-8")
    again = load_git_trust_root(repo, sha)
    assert again.policy_digest == trusted.policy_digest
    assert again.policy["merged_pull_request_is_approval"] is False
    assert digest_of(edited) != trusted.policy_digest


def test_candidate_verifier_edit_does_not_replace_the_pin(tmp_path, root):
    repo, sha = _pin_repo(tmp_path, root)
    trusted = load_git_trust_root(repo, sha)
    source = repo / "governance/kernel/evaluate.py"
    source.write_text(source.read_text(encoding="utf-8") + "\n# candidate\n", encoding="utf-8")
    again = load_git_trust_root(repo, sha)
    assert again.verifier_digest == trusted.verifier_digest
    assert running_verifier_digest(repo) != trusted.verifier_digest


def test_rewritten_digest_constant_cannot_repin_the_commit(tmp_path, root):
    repo, sha = _pin_repo(tmp_path, root)
    trusted = load_git_trust_root(repo, sha)
    (repo / "PIN.txt").write_text("0" * 64, encoding="utf-8")
    policy_path = repo / POLICY_PATH
    edited = load_json(policy_path)
    edited["pilot_status"] = "forged"
    policy_path.write_text(json.dumps(edited), encoding="utf-8")
    loaded = load_git_trust_root(repo, sha, expected_policy_digest=trusted.policy_digest)
    assert loaded.policy_digest == trusted.policy_digest


def test_unknown_commit_is_a_verifier_error(tmp_path, root):
    repo, _sha = _pin_repo(tmp_path, root)
    try:
        load_git_trust_root(repo, "a" * 40)
    except TrustRootError as exc:
        assert exc.code == "UNKNOWN_TRUST_COMMIT"
    else:
        raise AssertionError("unknown commit was accepted")


def test_wrong_policy_digest_is_a_verifier_error(tmp_path, root):
    repo, sha = _pin_repo(tmp_path, root)
    try:
        load_git_trust_root(repo, sha, expected_policy_digest="0" * 64)
    except TrustRootError as exc:
        assert exc.code == "WRONG_POLICY_DIGEST"
    else:
        raise AssertionError("wrong digest was accepted")


def test_baseline_commit_is_not_this_verifier(root):
    # A full clone is missing the new verifier blobs. A shallow CI checkout
    # does not have the predecessor object at all. Both refuse the pin.
    try:
        load_git_trust_root(root, BASELINE)
    except TrustRootError as exc:
        assert exc.code in {"MISSING_TRUST_BLOB", "UNKNOWN_TRUST_COMMIT"}
    else:
        raise AssertionError("predecessor commit was treated as this verifier")


def test_cli_refuses_baseline_commit_as_running_verifier(root):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/governance/check_authorization.py",
            "--decision",
            "governance/fixtures/pep_cam_contract_002_proposed.json",
            "--repository",
            "HanzoRazer/CAM-Assist-Blueprint",
            "--revision",
            "5f736e567dab31439df9b2b66fc5de43bec032f2",
            "--scope",
            "r2-contract-publication",
            "--trust-commit",
            BASELINE,
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 4
    assert "MISSING_TRUST_BLOB" in completed.stderr or "UNKNOWN_TRUST_COMMIT" in completed.stderr


def _witness(sha, **overrides):
    payload = {
        "relationship": "exact",
        "default_branch_sha": sha,
        "verifier_bytes_match": True,
        "policy_bytes_match": True,
        "roles_bytes_match": True,
        "workflow_bytes_match": True,
        "pull_number": 46,
        "base_sha": sha,
        "workflow_path": TRUSTED_WORKFLOW_PATH,
        "workflow_id": 123,
        "run_id": 456,
        "conclusion": "success",
        "consistent": True,
    }
    payload.update(overrides)
    return DeploymentWitness(**payload)


def test_matching_pin_still_does_not_activate_production(tmp_path, root):
    repo, sha = _pin_repo(tmp_path, root)
    required = ProtectionAssessment("required", ("governance-trusted",), ("branch_protection_read",))
    report = assess_deployment(
        repo=repo,
        trust_commit=sha,
        protection=required,
        witness=_witness(sha),
    )
    assert report["deployment_status"] == "DEPLOYED_NOT_ACTIVATED"
    assert report["authority_established"] is True
    assert report["workflow_source"] == "pinned-commit"
    assert report["running_verifier_matches_pin"] is True
    assert report["production_authorization_operational"] is False
    assert report["activation_permitted"] is False
    source = repo / "governance/kernel/evaluate.py"
    source.write_text(source.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    drifted = assess_deployment(repo=repo, trust_commit=sha, protection=required)
    assert drifted["deployment_status"] == "NOT_DEPLOYED"
    assert drifted["authority_established"] is False
    assert drifted["trust_reason"] == "VERIFIER_PIN_MISMATCH"


def test_sha_without_a_required_check_is_not_authority(tmp_path, root):
    repo, sha = _pin_repo(tmp_path, root)
    absent = ProtectionAssessment("not_required", (), ("branch_protection_absent",))
    report = assess_deployment(
        repo=repo,
        trust_commit=sha,
        protection=absent,
        witness=_witness(sha),
    )
    assert report["running_verifier_matches_pin"] is True
    assert report["workflow_contract_ok"] is True
    assert report["authority_established"] is False
    assert report["deployment_status"] == "NOT_DEPLOYED"
    assert report["production_authorization_operational"] is False


def test_worktree_workflow_edit_does_not_supply_the_contract(tmp_path, root):
    repo, sha = _pin_repo(tmp_path, root)
    workflow = repo / TRUSTED_WORKFLOW_PATH
    workflow.write_text("pull_request:\njobs: {}\n", encoding="utf-8")
    required = ProtectionAssessment("required", ("governance-trusted",), ("branch_protection_read",))
    report = assess_deployment(
        repo=repo,
        trust_commit=sha,
        protection=required,
        witness=_witness(sha),
    )
    assert report["workflow_source"] == "pinned-commit"
    assert report["workflow_contract_ok"] is True
    assert report["authority_established"] is True
    assert report["production_authorization_operational"] is False


def test_undeployed_commit_cannot_pass_attestation(tmp_path, root):
    repo, sha = _pin_repo(tmp_path, root)
    required = ProtectionAssessment("required", ("governance-trusted",), ("branch_protection_read",))
    missing = assess_deployment(repo=repo, trust_commit=sha, protection=required)
    assert missing["authority_established"] is False
    assert missing["deployment_evidence"]["pin_relationship"] == "unverified"
    unrelated = assess_deployment(
        repo=repo,
        trust_commit=sha,
        protection=required,
        witness=_witness(sha, relationship="unrelated", default_branch_sha="b" * 40, base_sha="b" * 40),
    )
    assert unrelated["authority_established"] is False
    assert unrelated["deployment_status"] == "NOT_DEPLOYED"
    assert unrelated["production_authorization_operational"] is False


def test_ancestor_pin_requires_verifier_policy_roles_and_workflow(tmp_path, root):
    repo, sha = _pin_repo(tmp_path, root)
    tip = "b" * 40
    required = ProtectionAssessment("required", ("governance-trusted",), ("branch_protection_read",))
    for flag in (
        "verifier_bytes_match",
        "policy_bytes_match",
        "roles_bytes_match",
        "workflow_bytes_match",
    ):
        witness = _witness(sha, relationship="ancestor", default_branch_sha=tip, base_sha=tip, **{flag: False})
        report = assess_deployment(repo=repo, trust_commit=sha, protection=required, witness=witness)
        assert report["authority_established"] is False
        assert report["deployment_evidence"]["trusted_check_bound"] is False
    accepted = assess_deployment(
        repo=repo,
        trust_commit=sha,
        protection=required,
        witness=_witness(sha, relationship="ancestor", default_branch_sha=tip, base_sha=tip),
    )
    assert accepted["authority_established"] is True
    assert accepted["deployment_status"] == "DEPLOYED_NOT_ACTIVATED"
    assert accepted["production_authorization_operational"] is False
    assert accepted["deployment_evidence"]["pull_number"] == 46
    assert accepted["deployment_evidence"]["run_id"] == 456


def test_check_name_without_workflow_identity_does_not_bind():
    pin = "a" * 40
    tip = "b" * 40
    head = "c" * 40
    spoof = {
        "conclusion": "success",
        "event": "pull_request_target",
        "head_sha": head,
        "id": 9,
        "path": ".github/workflows/other.yml",
        "workflow_id": 999,
    }
    pulls = {head: [{"base_sha": pin, "head_sha": head, "number": 7}]}
    bound, consistent = choose_bound_run(
        trust_commit=pin,
        default_branch_sha=tip,
        workflow_id=123,
        runs=[spoof],
        pulls_for_head=pulls,
    )
    assert bound is None
    assert consistent is True
    contradicted, ok = choose_bound_run(
        trust_commit=pin,
        default_branch_sha=tip,
        workflow_id=123,
        runs=[{**spoof, "path": TRUSTED_WORKFLOW_PATH, "workflow_id": 999}],
        pulls_for_head=pulls,
    )
    assert contradicted is None
    assert ok is False


def test_bound_run_records_pull_request_base_and_workflow():
    pin = "a" * 40
    head = "c" * 40
    run = {
        "conclusion": "success",
        "event": "pull_request_target",
        "head_sha": head,
        "id": 77,
        "path": TRUSTED_WORKFLOW_PATH,
        "workflow_id": 123,
    }
    pulls = {head: [{"base_sha": pin, "head_sha": head, "number": 48}]}
    bound, consistent = choose_bound_run(
        trust_commit=pin,
        default_branch_sha=pin,
        workflow_id=123,
        runs=[run],
        pulls_for_head=pulls,
    )
    assert consistent is True
    assert bound == {
        "base_sha": pin,
        "conclusion": "success",
        "pull_number": 48,
        "run_id": 77,
        "workflow_id": 123,
        "workflow_path": TRUSTED_WORKFLOW_PATH,
    }
    assert relationship_from_compare(pin, pin, "identical", readable=True) == "exact"
    assert relationship_from_compare(pin, "b" * 40, "ahead", readable=True) == "ancestor"
    assert relationship_from_compare(pin, "b" * 40, "diverged", readable=True) == "unrelated"
    assert relationship_from_compare(pin, "b" * 40, None, readable=False) == "unverified"
    pin_blobs = {path: b"same" for path in (*VERIFIER_PATHS, POLICY_PATH, ROLES_PATH, TRUSTED_WORKFLOW_PATH)}
    tip_blobs = dict(pin_blobs)
    tip_blobs[VERIFIER_PATHS[0]] = b"different"
    compared = trust_bytes_match(pin_blobs, tip_blobs)
    assert compared["workflow"] is True
    assert compared["verifier"] is False
    assert compared["policy"] is True
