"""Report whether a protected governance deployment is in place.

Exit 0 is reserved for a confirmed required check, a matching verifier pin,
and a workflow contract that still leaves production authorization disabled.
This development checkout does not satisfy that bar.
"""

from __future__ import annotations

import argparse
import json
import sys

from _runtime import ROOT
from governance.kernel.trust_root import TRUSTED_JOB_NAME, TRUSTED_WORKFLOW_PATH, assess_deployment


def _probe(repository: str) -> tuple[list[str] | None, str | None]:
    import subprocess

    protection = subprocess.run(
        ["gh", "api", f"repos/{repository}/branches/main/protection"],
        capture_output=True,
        text=True,
        check=False,
    )
    if protection.returncode != 0:
        return None, "protection_unverified"
    try:
        body = json.loads(protection.stdout)
    except json.JSONDecodeError:
        return None, "protection_unverified"
    checks = (
        body.get("required_status_checks", {}).get("checks")
        or body.get("required_status_checks", {}).get("contexts")
        or []
    )
    names: list[str] = []
    for item in checks:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and isinstance(item.get("context"), str):
            names.append(item["context"])
    rules = subprocess.run(
        ["gh", "api", f"repos/{repository}/rulesets"],
        capture_output=True,
        text=True,
        check=False,
    )
    if rules.returncode == 0:
        try:
            payload = json.loads(rules.stdout)
        except json.JSONDecodeError:
            payload = []
        if isinstance(payload, list):
            for ruleset in payload:
                if not isinstance(ruleset, dict):
                    continue
                for rule in ruleset.get("rules") or []:
                    if not isinstance(rule, dict):
                        continue
                    parameters = rule.get("parameters") or {}
                    for check in parameters.get("required_status_checks") or []:
                        if isinstance(check, dict) and isinstance(check.get("context"), str):
                            names.append(check["context"])
    return names, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trust-commit", default=None)
    parser.add_argument("--repository", default="HanzoRazer/CAM-Assist-Blueprint")
    parser.add_argument("--probe-github", action="store_true")
    args = parser.parse_args(argv)
    workflow = (ROOT / TRUSTED_WORKFLOW_PATH).read_text(encoding="utf-8")
    required: list[str] | None = None
    error = None
    if args.probe_github:
        required, error = _probe(args.repository)
    report = assess_deployment(
        repo=ROOT,
        trust_commit=args.trust_commit,
        workflow_text=workflow,
        required_checks=required,
        protection_error=error,
    )
    report["production_authorization_operational"] = False
    report["trusted_job"] = TRUSTED_JOB_NAME
    json.dump(report, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    if (
        report["deployment_status"] == "DEPLOYED_NOT_ACTIVATED"
        and report["production_authorization_operational"] is False
        and report["workflow_contract_ok"] is True
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
