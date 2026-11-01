"""Trust-root loading ignores the candidate worktree."""

from __future__ import annotations

import json
import subprocess
import sys

from governance.kernel.canonical import digest_of
from governance.kernel.trust_root import (
    POLICY_PATH,
    ROLES_PATH,
    VERIFIER_PATHS,
    TrustRootError,
    assess_deployment,
    load_git_trust_root,
    running_verifier_digest,
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
    for path in (*VERIFIER_PATHS, POLICY_PATH, ROLES_PATH):
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


def test_matching_pin_still_does_not_activate_production(tmp_path, root):
    repo, sha = _pin_repo(tmp_path, root)
    workflow = (root / ".github/workflows/governance-trusted.yml").read_text(encoding="utf-8")
    report = assess_deployment(
        repo=repo,
        trust_commit=sha,
        workflow_text=workflow,
        required_checks=["governance-trusted"],
    )
    assert report["deployment_status"] == "DEPLOYED_NOT_ACTIVATED"
    assert report["running_verifier_matches_pin"] is True
    assert report["production_authorization_operational"] is False
    assert report["activation_permitted"] is False
    source = repo / "governance/kernel/evaluate.py"
    source.write_text(source.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    drifted = assess_deployment(
        repo=repo,
        trust_commit=sha,
        workflow_text=workflow,
        required_checks=["governance-trusted"],
    )
    assert drifted["deployment_status"] == "NOT_DEPLOYED"
    assert drifted["trust_reason"] == "VERIFIER_PIN_MISMATCH"
