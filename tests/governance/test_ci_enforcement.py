"""Workflow contract tests. They do not claim branch protection is active."""

from __future__ import annotations

import json
import subprocess
import sys

from governance.kernel.trust_root import (
    ProtectionAssessment,
    ProtectionProbe,
    RulesetFetch,
    assess_deployment,
    assess_workflow_text,
    interpret_protection,
)

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
    protection = ProtectionAssessment("unverified", (), ("branch_protection_http_403",))
    report = assess_deployment(repo=root, trust_commit=None, protection=protection)
    assert report["deployment_status"] == "NOT_DEPLOYED"
    assert report["authority_established"] is False
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
    assert body["authority_established"] is False
    assert body["production_authorization_operational"] is False
    assert body["protection_state"] == "unverified"


def _ruleset(ruleset_id, include, context, enforcement="active"):
    return {
        "conditions": {"ref_name": {"exclude": [], "include": include}},
        "enforcement": enforcement,
        "id": ruleset_id,
        "rules": [
            {
                "parameters": {"required_status_checks": [{"context": context}]},
                "type": "required_status_checks",
            }
        ],
        "target": "branch",
    }


def test_forbidden_protection_is_not_an_absent_check():
    probe = ProtectionProbe(
        branch_protection_status=403,
        branch_protection_body=None,
        ruleset_list_status=200,
        ruleset_details=(),
    )
    result = interpret_protection(probe)
    assert result.state == "unverified"
    assert result.state != "not_required"


def test_missing_ruleset_document_does_not_prove_absence():
    probe = ProtectionProbe(
        branch_protection_status=404,
        branch_protection_body=None,
        ruleset_list_status=200,
        ruleset_details=(RulesetFetch(9, None, "ruleset_http_404"),),
    )
    result = interpret_protection(probe)
    assert result.state == "unverified"
    assert "ruleset_detail_unread" in result.evidence


def test_check_is_absent_only_after_complete_reads():
    probe = ProtectionProbe(
        branch_protection_status=404,
        branch_protection_body=None,
        ruleset_list_status=200,
        ruleset_details=(
            RulesetFetch(4, _ruleset(4, ["refs/heads/other"], "governance-trusted")),
        ),
    )
    result = interpret_protection(probe)
    assert result.state == "not_required"
    assert "governance-trusted" not in result.required_checks


def test_applicable_ruleset_requires_the_check():
    probe = ProtectionProbe(
        branch_protection_status=404,
        branch_protection_body=None,
        ruleset_list_status=200,
        ruleset_details=(
            RulesetFetch(4, _ruleset(4, ["~DEFAULT_BRANCH"], "governance-trusted")),
        ),
    )
    result = interpret_protection(probe)
    assert result.state == "required"
    assert "governance-trusted" in result.required_checks


def test_disabled_ruleset_does_not_require_the_check():
    probe = ProtectionProbe(
        branch_protection_status=404,
        branch_protection_body=None,
        ruleset_list_status=200,
        ruleset_details=(
            RulesetFetch(
                4,
                _ruleset(4, ["refs/heads/main"], "governance-trusted", enforcement="disabled"),
            ),
        ),
    )
    result = interpret_protection(probe)
    assert result.state == "not_required"


def test_branch_protection_context_requires_the_check():
    probe = ProtectionProbe(
        branch_protection_status=200,
        branch_protection_body={
            "required_status_checks": {"checks": [{"context": "governance-trusted"}], "contexts": []}
        },
        ruleset_list_status=200,
        ruleset_details=(),
    )
    result = interpret_protection(probe)
    assert result.state == "required"
    assert result.required_checks == ("governance-trusted",)
