"""Registry digest and command-line witnesses."""

from __future__ import annotations

import copy
import json
import subprocess
import sys

from governance.kernel.evaluate import load_json, verify_registry


def test_registry_digest_detects_tampering(root):
    document = load_json(root / "governance" / "registry" / "decisions.json")
    intact = verify_registry(document)
    assert intact.code == 1
    assert "REGISTRY_DIGEST_MISMATCH" not in intact.reason_codes
    tampered = copy.deepcopy(document)
    tampered["records"][0]["decision"]["status"] = "ACCEPTED"
    verdict = verify_registry(tampered)
    assert verdict.code == 2
    assert verdict.verdict == "INVALID"
    assert "REGISTRY_DIGEST_MISMATCH" in verdict.reason_codes


def test_authorization_registry_starts_empty(root):
    document = load_json(root / "governance" / "registry" / "authorizations.json")
    assert document["records"] == []
    verdict = verify_registry(document)
    assert "REGISTRY_DIGEST_MISMATCH" not in verdict.reason_codes
    assert verdict.verdict != "AUTHORIZED"


def test_cli_blocks_pep_case_and_isolates_synthetic(root):
    blocked = subprocess.run(
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
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode == 1
    payload = json.loads(blocked.stdout)
    assert payload["verdict"] == "BLOCKED"
    assert payload["production_authorization_operational"] is False
    report = subprocess.run(
        [sys.executable, "scripts/governance/report_governance.py"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert report.returncode == 1
    body = json.loads(report.stdout)
    assert body["production_authorization_operational"] is False
    assert body["interchange_r2"]["verdict"] == "BLOCKED"
    assert body["pilot"] is True
    synthetic = subprocess.run(
        [
            sys.executable,
            "scripts/governance/check_authorization.py",
            "--decision",
            "governance/fixtures/valid_synthetic_authorization.json",
            "--allow-synthetic",
            "--repository",
            "HanzoRazer/CAM-Assist-Blueprint",
            "--revision",
            "a" * 40,
            "--scope",
            "governance-kernel-test",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert synthetic.returncode == 4
