"""Report whether a protected governance deployment is in place.

The trusted workflow is read from the pinned commit. Live branch protection
and every listed ruleset document are required before a check can be reported
absent. Exit 0 is reserved for a pin that matches this tree, a workflow
contract that passes on that commit, and a live API confirmation that
``governance-trusted`` is required. Production authorization stays disabled.
A commit SHA alone does not establish authority.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from _runtime import ROOT
from governance.kernel.trust_root import (
    TRUSTED_JOB_NAME,
    ProtectionAssessment,
    ProtectionProbe,
    RulesetFetch,
    assess_deployment,
    interpret_protection,
)


def _split_http(stdout: str) -> tuple[int | None, str]:
    lines = stdout.splitlines()
    if not lines or not lines[0].startswith("HTTP/"):
        return None, stdout
    parts = lines[0].split()
    status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    body = stdout
    for index, line in enumerate(lines):
        if line.strip() == "":
            body = "\n".join(lines[index + 1 :])
            break
    return status, body


def _gh(path: str) -> tuple[int | None, str]:
    completed = subprocess.run(
        ["gh", "api", "-i", path],
        capture_output=True,
        text=True,
        check=False,
    )
    status, body = _split_http(completed.stdout)
    if status is None:
        return None, completed.stderr or completed.stdout
    return status, body


def _json_object(body: str) -> dict | None:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def probe_repository(repository: str) -> ProtectionProbe:
    """Read classic branch protection and the full document for every ruleset."""
    status, body = _gh(f"repos/{repository}/branches/main/protection")
    protection_body = _json_object(body) if status == 200 else None
    list_status, list_body = _gh(f"repos/{repository}/rulesets")
    details: list[RulesetFetch] = []
    if list_status == 200:
        try:
            payload = json.loads(list_body)
        except json.JSONDecodeError:
            payload = None
        if not isinstance(payload, list):
            list_status = None
        else:
            for item in payload:
                if not isinstance(item, dict) or not isinstance(item.get("id"), int):
                    list_status = None
                    details = []
                    break
                ruleset_id = item["id"]
                detail_status, detail_body = _gh(f"repos/{repository}/rulesets/{ruleset_id}")
                document = _json_object(detail_body) if detail_status == 200 else None
                error = None if document is not None else f"ruleset_http_{detail_status}"
                details.append(RulesetFetch(ruleset_id, document, error))
    return ProtectionProbe(
        branch_protection_status=status,
        branch_protection_body=protection_body,
        ruleset_list_status=list_status,
        ruleset_details=tuple(details),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trust-commit", default=None)
    parser.add_argument("--repository", default="HanzoRazer/CAM-Assist-Blueprint")
    parser.add_argument("--branch", default="main")
    args = parser.parse_args(argv)
    try:
        probe = probe_repository(args.repository)
        protection = interpret_protection(probe, branch=args.branch, default_branch=args.branch)
    except Exception:
        protection = ProtectionAssessment("unverified", (), ("protection_probe_failed",))
    report = assess_deployment(
        repo=ROOT,
        trust_commit=args.trust_commit,
        protection=protection,
    )
    report["production_authorization_operational"] = False
    report["trusted_job"] = TRUSTED_JOB_NAME
    json.dump(report, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    if (
        report["authority_established"] is True
        and report["deployment_status"] == "DEPLOYED_NOT_ACTIVATED"
        and report["production_authorization_operational"] is False
        and report["required_check_confirmed"] is True
    ):
        return 0
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — CLI boundary, fail closed
        sys.stderr.write(f"verifier error: {exc}\n")
        sys.exit(4)
