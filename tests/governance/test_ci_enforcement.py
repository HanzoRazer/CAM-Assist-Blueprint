"""Workflow contract tests. They do not claim branch protection is active."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from governance.kernel.trust_root import (
    EVALUATOR_RUN,
    GITHUB_ACTIONS_APP_ID,
    ProtectionAssessment,
    ProtectionProbe,
    RulesetFetch,
    assess_deployment,
    assess_workflow_text,
    interpret_protection,
    provenance_from_annotations,
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


def test_workflow_comment_cannot_satisfy_the_contract():
    forged = """
# pull_request_target:
# contents: read
# pull-requests: read
# github.event.pull_request.base.sha
# persist-credentials: false
# governance-trusted
on:
  workflow_dispatch:
permissions:
  contents: read
  pull-requests: read
jobs:
  governance-trusted:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
"""
    assert "pull_request_target:" in forged
    assert "github.event.pull_request.base.sha" in forged
    assert "persist-credentials: false" in forged
    contract = assess_workflow_text(forged)
    assert contract.ok is False
    assert "MISSING_PULL_REQUEST_TARGET" in contract.reasons


def test_mutable_action_and_head_checkout_fail_closed(root):
    original = (root / TRUSTED).read_text(encoding="utf-8")
    mutable = original.replace(
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/checkout@v4",
    )
    assert assess_workflow_text(mutable).ok is False
    assert "MUTABLE_ACTION" in assess_workflow_text(mutable).reasons
    head = original.replace(
        "github.event.pull_request.base.sha",
        "github.event.pull_request.head.sha",
    )
    refused = assess_workflow_text(head)
    assert refused.ok is False
    assert "CANDIDATE_SHA_CHECKOUT" in refused.reasons or "BASE_SHA_NOT_PINNED" in refused.reasons


def test_echo_or_ignored_verdict_does_not_execute_the_evaluator(root):
    original = (root / TRUSTED).read_text(encoding="utf-8")
    assert "python scripts/governance/report_governance.py" in EVALUATOR_RUN
    comment = original.replace(
        "          python scripts/governance/report_governance.py >",
        "          # python scripts/governance/report_governance.py\n          exit 0 >",
        1,
    )
    assert comment != original
    refused = assess_workflow_text(comment)
    assert refused.ok is False
    assert "EVALUATOR_NOT_ENFORCED" in refused.reasons
    ignored = original.replace('if [ "$code" -ne 1 ]; then', "if false; then", 1)
    assert ignored != original
    ignored_contract = assess_workflow_text(ignored)
    assert ignored_contract.ok is False
    assert "EVALUATOR_NOT_ENFORCED" in ignored_contract.reasons
    other_program = original.replace(
        "python scripts/governance/report_governance.py",
        "python scripts/governance/check_authorization.py",
        1,
    )
    assert assess_workflow_text(other_program).ok is False


def test_annotation_sha_is_the_only_executed_revision():
    pin = "a" * 40
    other = "b" * 40
    assert provenance_from_annotations([]) == (None, None, True)
    assert provenance_from_annotations(
        [
            {"message": pin, "title": "executed-trust-commit"},
            {"message": "48", "title": "executed-pull-number"},
        ]
    ) == (pin, 48, True)
    assert provenance_from_annotations(
        [
            {"message": pin, "title": "executed-trust-commit"},
            {"message": other, "title": "executed-trust-commit"},
            {"message": "48", "title": "executed-pull-number"},
        ]
    ) == (None, None, False)
    assert provenance_from_annotations(
        [{"message": pin, "title": "executed-trust-commit"}]
    ) == (None, None, False)
    assert provenance_from_annotations(
        [
            {"message": pin, "title": "executed-trust-commit"},
            {"message": pin, "title": "executed-trust-commit"},
            {"message": "48", "title": "executed-pull-number"},
        ]
    ) == (None, None, False)


def test_run_step_cannot_fetch_the_candidate_head(root):
    original = (root / TRUSTED).read_text(encoding="utf-8")
    anchor = "        run: python -m pip install"
    for command in (
        'git fetch origin "refs/pull/${{ github.event.number }}/head" && git checkout FETCH_HEAD',
        'git checkout "${{ github.head_ref }}"',
        'git checkout "${{ github.event.pull_request.merge_commit_sha }}"',
    ):
        mutated = original.replace(anchor, f"        run: {command} && python -m pip install", 1)
        assert mutated != original
        refused = assess_workflow_text(mutated)
        assert refused.ok is False
        assert "CANDIDATE_SHA_CHECKOUT" in refused.reasons


def test_governance_workflows_pin_actions_and_hashes(root):
    trusted = (root / TRUSTED).read_text(encoding="utf-8")
    pilot = (root / PILOT).read_text(encoding="utf-8")
    checkout = "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
    setup = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
    for text in (trusted, pilot):
        assert checkout in text
        assert setup in text
        assert "@v4" not in text
        assert "@v5" not in text
        assert "--require-hashes" in text
    assert "requirements/governance-trusted.txt" in trusted
    assert "requirements/governance-check.txt" in pilot
    for name in ("requirements/governance-trusted.txt", "requirements/governance-check.txt"):
        lock = (root / name).read_text(encoding="utf-8")
        assert "--hash=sha256:" in lock
        assert "jsonschema==4.26.0" in lock
    assert "PyYAML==6.0.1" in (root / "requirements/governance-trusted.txt").read_text(encoding="utf-8")
    assert "pytest==9.1.1" in (root / "requirements/governance-check.txt").read_text(encoding="utf-8")


def test_unverified_protection_is_not_deployment(root):
    protection = ProtectionAssessment("unverified", (), ("branch_protection_http_403",))
    report = assess_deployment(repo=root, trust_commit=None, protection=protection)
    assert report["deployment_status"] == "NOT_DEPLOYED"
    assert report["authority_established"] is False
    assert report["required_check_confirmed"] is False
    assert report["production_authorization_operational"] is False
    assert report["protection_state"] == "unverified"


def test_deployment_cli_stays_inactive(root, tmp_path):
    # No GitHub credential: the result must not depend on who runs the suite.
    env = {key: value for key, value in os.environ.items() if key not in {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN"}}
    env["GH_CONFIG_DIR"] = str(tmp_path / "gh-config")
    completed = subprocess.run(
        [sys.executable, "scripts/governance/verify_deployment.py"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 1
    body = json.loads(completed.stdout)
    assert body["deployment_status"] == "NOT_DEPLOYED"
    assert body["activation_permitted"] is False
    assert body["authority_established"] is False
    assert body["production_authorization_operational"] is False
    assert body["protection_state"] == "unverified"


def _ruleset(ruleset_id, include, context, enforcement="active", integration_id=GITHUB_ACTIONS_APP_ID):
    check = {"context": context}
    if integration_id is not None:
        check["integration_id"] = integration_id
    return {
        "conditions": {"ref_name": {"exclude": [], "include": include}},
        "enforcement": enforcement,
        "id": ruleset_id,
        "rules": [
            {
                "parameters": {"required_status_checks": [check]},
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
            "required_status_checks": {
                "checks": [{"app_id": GITHUB_ACTIONS_APP_ID, "context": "governance-trusted"}],
                "contexts": ["governance-trusted"],
            }
        },
        ruleset_list_status=200,
        ruleset_details=(),
    )
    result = interpret_protection(probe)
    assert result.state == "required"
    assert result.required_checks == ("governance-trusted",)


def test_check_name_any_source_is_not_required_protection():
    # A required name without the GitHub Actions source can be satisfied by
    # any commit status that reuses the job name.
    for checks in (
        [{"app_id": None, "context": "governance-trusted"}],
        [{"app_id": -1, "context": "governance-trusted"}],
        [{"app_id": 999, "context": "governance-trusted"}],
        [{"context": "governance-trusted"}],
    ):
        probe = ProtectionProbe(
            branch_protection_status=200,
            branch_protection_body={"required_status_checks": {"checks": checks, "contexts": ["governance-trusted"]}},
            ruleset_list_status=200,
            ruleset_details=(),
        )
        result = interpret_protection(probe)
        assert result.state == "required_any_source"
        assert "trusted_check_source_unpinned" in result.evidence
    legacy = ProtectionProbe(
        branch_protection_status=200,
        branch_protection_body={"required_status_checks": {"contexts": ["governance-trusted"]}},
        ruleset_list_status=200,
        ruleset_details=(),
    )
    assert interpret_protection(legacy).state == "required_any_source"
    unbound = ProtectionProbe(
        branch_protection_status=404,
        branch_protection_body=None,
        ruleset_list_status=200,
        ruleset_details=(
            RulesetFetch(4, _ruleset(4, ["~DEFAULT_BRANCH"], "governance-trusted", integration_id=None)),
        ),
    )
    assert interpret_protection(unbound).state == "required_any_source"
    report = assess_deployment(
        repo=None,
        trust_commit=None,
        protection=interpret_protection(unbound),
    )
    assert report["required_check_confirmed"] is False
    assert report["authority_established"] is False
