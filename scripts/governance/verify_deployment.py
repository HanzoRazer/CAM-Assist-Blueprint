"""Report whether a protected governance deployment is in place.

The trusted workflow is read from the pinned commit. Live branch protection
and every listed ruleset document are required before a check can be reported
absent. Exit 0 also requires the pin to be the default branch, or an ancestor
whose verifier, policy, roles, and workflow bytes still match the tip, plus
one successful run of this workflow file bound to a pull request number, base
SHA, workflow id, and run id. A check name alone is not that proof. Missing
or inconsistent API evidence exits 1. Production authorization stays disabled.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from _runtime import ROOT
from governance.kernel.trust_root import (
    TRUST_BYTE_PATHS,
    TRUSTED_JOB_NAME,
    TRUSTED_WORKFLOW_PATH,
    DeploymentWitness,
    ProtectionAssessment,
    ProtectionProbe,
    RulesetFetch,
    assess_deployment,
    choose_bound_run,
    interpret_protection,
    relationship_from_compare,
    trust_bytes_match,
    unverified_witness,
)


def _split_http(stdout: str) -> tuple[int | None, dict[str, str], str]:
    lines = stdout.splitlines()
    if not lines or not lines[0].startswith("HTTP/"):
        return None, {}, stdout
    parts = lines[0].split()
    status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    headers: dict[str, str] = {}
    body_at = len(lines)
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "":
            body_at = index + 1
            break
        key, separator, value = line.partition(":")
        if separator:
            headers[key.strip().lower()] = value.strip()
    return status, headers, "\n".join(lines[body_at:])


def _gh(path: str) -> tuple[int | None, dict[str, str], str]:
    completed = subprocess.run(
        ["gh", "api", "-i", path],
        capture_output=True,
        text=True,
        check=False,
    )
    status, headers, body = _split_http(completed.stdout)
    if status is None:
        return None, {}, completed.stderr or completed.stdout
    return status, headers, body


def _next_link(header: str) -> str | None:
    if header.strip() == "":
        return None
    found = None
    for part in header.split(","):
        url_part, _, params = part.strip().partition(";")
        url_part = url_part.strip()
        if not (url_part.startswith("<") and ">" in url_part):
            continue
        candidate = url_part[1 : url_part.index(">")]
        rels = []
        for param in params.split(";"):
            key, _, value = param.strip().partition("=")
            if key.strip() == "rel":
                rels.append(value.strip().strip('"'))
        if "next" in rels:
            found = candidate
    if found is None:
        return None
    if not found.startswith("https://api.github.com/"):
        raise RuntimeError("workflow run page left the api host")
    return found


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
    status, _headers, body = _gh(f"repos/{repository}/branches/main/protection")
    protection_body = _json_object(body) if status == 200 else None
    list_status, _headers, list_body = _gh(f"repos/{repository}/rulesets")
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
                detail_status, _headers, detail_body = _gh(f"repos/{repository}/rulesets/{ruleset_id}")
                document = _json_object(detail_body) if detail_status == 200 else None
                error = None if document is not None else f"ruleset_http_{detail_status}"
                details.append(RulesetFetch(ruleset_id, document, error))
    return ProtectionProbe(
        branch_protection_status=status,
        branch_protection_body=protection_body,
        ruleset_list_status=list_status,
        ruleset_details=tuple(details),
    )


def _blob(repository: str, path: str, ref: str) -> bytes | None:
    status, _headers, body = _gh(f"repos/{repository}/contents/{quote(path, safe='/')}?ref={quote(ref, safe='')}")
    if status != 200:
        return None
    document = _json_object(body)
    if document is None or document.get("encoding") != "base64" or not isinstance(document.get("content"), str):
        return None
    try:
        return base64.b64decode("".join(document["content"].split()), validate=True)
    except ValueError:
        return None


def _pulls_for_run(repository: str, run: dict) -> list[dict] | None:
    embedded = run.get("pull_requests")
    if isinstance(embedded, list) and embedded:
        return [_flat_pull(item) for item in embedded]
    head = run.get("head_sha")
    if not isinstance(head, str):
        return None
    status, _headers, body = _gh(f"repos/{repository}/commits/{head}/pulls")
    if status != 200:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    return [_flat_pull(item) for item in payload]


def _flat_pull(item: object) -> dict:
    if not isinstance(item, dict):
        raise RuntimeError("pull request payload is unreadable")
    base = item.get("base")
    head = item.get("head")
    number = item.get("number")
    base_sha = base.get("sha") if isinstance(base, dict) else None
    head_sha = head.get("sha") if isinstance(head, dict) else None
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise RuntimeError("pull request number is unreadable")
    if not isinstance(base_sha, str) or not isinstance(head_sha, str):
        raise RuntimeError("pull request sha is unreadable")
    return {"base_sha": base_sha, "head_sha": head_sha, "number": number}


def _workflow_runs(repository: str, workflow_id: int) -> list[dict] | None:
    path = (
        f"repos/{repository}/actions/workflows/{workflow_id}/runs"
        "?event=pull_request_target&status=success&per_page=50"
    )
    collected: list[dict] = []
    seen: set[str] = set()
    while path:
        if path in seen or len(seen) >= 10:
            return None
        seen.add(path)
        status, headers, body = _gh(path)
        if status != 200:
            return None
        document = _json_object(body)
        if document is None or not isinstance(document.get("workflow_runs"), list):
            return None
        for item in document["workflow_runs"]:
            if not isinstance(item, dict):
                return None
            collected.append(item)
        try:
            path = _next_link(headers.get("link", "")) or ""
        except RuntimeError:
            return None
        if path == "":
            break
    return collected


def collect_witness(repository: str, trust_commit: str | None) -> DeploymentWitness:
    """Read default-branch identity and one bound trusted run. Fail closed."""
    if not isinstance(trust_commit, str) or len(trust_commit) != 40:
        return unverified_witness()
    try:
        return _collect_witness(repository, trust_commit)
    except Exception:
        return unverified_witness()


def _collect_witness(repository: str, trust_commit: str) -> DeploymentWitness:
    status, _headers, body = _gh(f"repos/{repository}")
    repository_document = _json_object(body) if status == 200 else None
    if repository_document is None or not isinstance(repository_document.get("default_branch"), str):
        return unverified_witness()
    branch = repository_document["default_branch"]
    status, _headers, body = _gh(f"repos/{repository}/commits/{quote(branch, safe='')}")
    commit_document = _json_object(body) if status == 200 else None
    tip = commit_document.get("sha") if commit_document else None
    if not isinstance(tip, str):
        return unverified_witness()
    compare_status = None
    readable = True
    if tip != trust_commit:
        status, _headers, body = _gh(f"repos/{repository}/compare/{trust_commit}...{tip}")
        compared = _json_object(body) if status == 200 else None
        if compared is None or not isinstance(compared.get("status"), str):
            readable = False
        else:
            compare_status = compared["status"]
    relationship = relationship_from_compare(
        trust_commit,
        tip,
        compare_status,
        readable=readable,
    )
    matches = {"policy": False, "roles": False, "verifier": False, "workflow": False}
    if relationship == "exact":
        matches = {key: True for key in matches}
    elif relationship == "ancestor":
        pin_blobs: dict[str, bytes] = {}
        tip_blobs: dict[str, bytes] = {}
        for path in TRUST_BYTE_PATHS:
            pin_blob = _blob(repository, path, trust_commit)
            tip_blob = _blob(repository, path, tip)
            if pin_blob is None or tip_blob is None:
                return unverified_witness()
            pin_blobs[path] = pin_blob
            tip_blobs[path] = tip_blob
        matches = trust_bytes_match(pin_blobs, tip_blobs)
    workflow_name = Path(TRUSTED_WORKFLOW_PATH).name
    status, _headers, body = _gh(f"repos/{repository}/actions/workflows/{quote(workflow_name, safe='')}")
    workflow = _json_object(body) if status == 200 else None
    workflow_id = workflow.get("id") if workflow else None
    if (
        workflow is None
        or workflow.get("path") != TRUSTED_WORKFLOW_PATH
        or workflow.get("state") != "active"
        or isinstance(workflow_id, bool)
        or not isinstance(workflow_id, int)
    ):
        return _witness(relationship, tip, matches, None, False)
    runs = _workflow_runs(repository, workflow_id)
    if runs is None:
        return _witness(relationship, tip, matches, None, False)
    normalized_runs = []
    pulls_for_head: dict[str, list[dict]] = {}
    for run in runs:
        normalized_runs.append(
            {
                "conclusion": run.get("conclusion"),
                "event": run.get("event"),
                "head_sha": run.get("head_sha"),
                "id": run.get("id"),
                "path": run.get("path"),
                "workflow_id": run.get("workflow_id"),
            }
        )
        if run.get("workflow_id") != workflow_id or run.get("path") != TRUSTED_WORKFLOW_PATH:
            continue
        if run.get("event") != "pull_request_target" or run.get("conclusion") != "success":
            continue
        head = run.get("head_sha")
        if not isinstance(head, str):
            return _witness(relationship, tip, matches, None, False)
        pulls = _pulls_for_run(repository, run)
        if pulls is None or any(item is None for item in pulls):
            return _witness(relationship, tip, matches, None, False)
        pulls_for_head[head] = [item for item in pulls if item is not None]
    bound, consistent = choose_bound_run(
        trust_commit=trust_commit,
        default_branch_sha=tip,
        workflow_id=workflow_id,
        runs=normalized_runs,
        pulls_for_head=pulls_for_head,
    )
    return _witness(relationship, tip, matches, bound, consistent)


def _witness(relationship: str, tip: str, matches: dict[str, bool], bound: dict | None, consistent: bool) -> DeploymentWitness:
    return DeploymentWitness(
        relationship,
        tip,
        bool(matches.get("verifier")),
        bool(matches.get("policy")),
        bool(matches.get("roles")),
        bool(matches.get("workflow")),
        None if bound is None else bound.get("pull_number"),
        None if bound is None else bound.get("base_sha"),
        None if bound is None else bound.get("workflow_path"),
        None if bound is None else bound.get("workflow_id"),
        None if bound is None else bound.get("run_id"),
        None if bound is None else bound.get("conclusion"),
        consistent,
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
    witness = collect_witness(args.repository, args.trust_commit)
    report = assess_deployment(
        repo=ROOT,
        trust_commit=args.trust_commit,
        protection=protection,
        witness=witness,
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
