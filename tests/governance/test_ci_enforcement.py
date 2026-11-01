"""Workflow contract tests. They do not claim branch protection is active."""

from __future__ import annotations

import json
import subprocess
import sys

from governance.kernel.trust_root import assess_deployment, assess_workflow_text

PILOT = ".github/workflows/governance-check.yml"
TRUSTED = ".github/workflows/governance-trusted.yml"


def test_pilot_workflow_is_path_filtered(root):
    text = (root / PILOT).read_text(encoding="utf-8")
    assert "paths:" in text
    assert "not the protected production gate" in text


def test_trusted_workflow_checks_out_the_base_sha(root):
    text = (root / TRUSTED).read_text(encoding="utf-8")
    contract = assess_workflow_text(text)
    assert contract.ok, contract.reasons
    assert "pull_request_target:" in text
    assert "github.event.pull_request.base.sha" in text
    assert "github.event.pull_request.head" not in text
    assert "paths:" not in text


def test_candidate_workflow_edit_fails_the_contract(root):
    original = (root / TRUSTED).read_text(encoding="utf-8")
    mutated = original.replace("pull_request_target:", "pull_request:")
    refused = assess_workflow_text(mutated)
    assert refused.ok is False
    assert assess_workflow_text(original).ok is True
    skipped = original.replace("governance-trusted:", "governance-skipped:")
    assert assess_workflow_text(skipped).ok is False


def test_unverified_protection_is_not_deployment(root):
    report = assess_deployment(
        repo=root,
        trust_commit=None,
        workflow_text=(root / TRUSTED).read_text(encoding="utf-8"),
        required_checks=None,
        protection_error="protection_unverified",
    )
    assert report["deployment_status"] == "NOT_DEPLOYED"
    assert report["required_check_confirmed"] is False
    assert report["production_authorization_operational"] is False
    assert report["protection_state"] == "unverified"


def test_deployment_cli_stays_inactive(root):
    completed = subprocess.run(
        [sys.executable, "scripts/governance/verify_deployment.py"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    body = json.loads(completed.stdout)
    assert body["deployment_status"] == "NOT_DEPLOYED"
    assert body["activation_permitted"] is False
    assert body["production_authorization_operational"] is False
