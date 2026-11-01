# Governance pilot

This package is a non-authoritative governance kernel for
`HanzoRazer/CAM-Assist-Blueprint`. It does not make CAM-Assist the owner of
cross-repository engineering governance, and it does not approve
PEP-CAM-CONTRACT-002.

## Trust boundary

Three states stay separate: the verifier is implemented in this tree, deployment is confirmed only by `scripts/governance/verify_deployment.py`, and production authorization stays off.

| Source | How the verifier treats it |
| --- | --- |
| `GOVERNANCE_TRUST_COMMIT` or `--trust-commit` | Policy, roles, and verifier bytes are read with `git show` from that commit |
| Candidate worktree, including this checkout | Not a trust root. `candidate_worktree_is_trust_root` stays false |
| Checkout policy digest pin | Rejects drift in the pilot observation path. A pull request can still edit the pin and the verifier together, so the pin is not deployment |
| Decision or authorization JSON | Untrusted claims |
| `approved: true` inside a record | Not a field. Extra properties fail schema validation |
| Pull request merge | Recorded as `pr_merged`. Never an approval |
| Pull request comment | Untrusted evidence kind |
| GitHub review | Used only when `GitHubEvidenceResolver` reads the API. Login is display text. Enrollment is the numeric user id. Dismissed, superseded, under-permissioned, and wrong-revision reviews block |
| Production role file | Enrolls no people and no GitHub user ids. Production mode cannot return authorized |
| `.github/workflows/governance-check.yml` | Pilot tests. Path-filtered. Checks out the pull request. Not a protected gate |
| `.github/workflows/governance-trusted.yml` | Prepared `pull_request_target` job pinned to `base.sha`. It does not run until it is on the default branch, and it is not a required check until an administrator confirms that |
| Synthetic bundle | Exit 0 only in explicit synthetic mode, and that result is not production authorization |

`production_authorization_operational` is false in policy and in code. Setting
the JSON flag to true makes the trusted policy a verifier error. It does not
open the gate.

A decision status of `ACCEPTED` does not authorize implementation. Implementation
requires a separate authorization record. This pilot has none.

## Lifecycle

`PROPOSED`, `UNDER_REVIEW`, `ACCEPTED`, `DEFERRED`, `REJECTED`.

## Digests

Canonicalization id: `canonical-json-sha256-v1`.

UTF-8 JSON, sorted keys, compact separators. A registry digest omits only the
top-level `registry_digest` field. Nested record digests stay inside the hash.

## Commands

From the repository root:

```text
python3 scripts/governance/report_governance.py
python3 scripts/governance/check_authorization.py \
  --decision governance/fixtures/pep_cam_contract_002_proposed.json \
  --repository HanzoRazer/CAM-Assist-Blueprint \
  --revision 5f736e567dab31439df9b2b66fc5de43bec032f2 \
  --scope r2-contract-publication
```

The PEP-CAM-CONTRACT-002 witness exits `1` with verdict `BLOCKED`. Exit `0`
is reserved for `--allow-synthetic` with a synthetic authority file. The
production registry does not load that result.

```text
python3 scripts/governance/verify_deployment.py
python3 scripts/governance/check_authorization.py \
  --trust-commit <40-hex-sha> \
  --decision governance/fixtures/pep_cam_contract_002_proposed.json \
  --repository HanzoRazer/CAM-Assist-Blueprint \
  --revision 5f736e567dab31439df9b2b66fc5de43bec032f2 \
  --scope r2-contract-publication
```

`--trust-commit` fails closed when that commit does not contain this verifier.
`verify_deployment.py` exits `1` while the required check is unconfirmed.
Neither command turns on production authorization.

## What this pilot is not

No Physical Engineering interchange schema, Toolbox serializer, CAM-Assist
admission adapter, manufacturing permission, or organization migration.
Passing these tests does not resolve the five open interchange decisions.
GitHub branch protection for this workflow was not visible to the credential
that added it, so a green run is not a required check.
