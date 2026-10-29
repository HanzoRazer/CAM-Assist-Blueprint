# Governance pilot

This package is a non-authoritative governance kernel for
`HanzoRazer/CAM-Assist-Blueprint`. It does not make CAM-Assist the owner of
cross-repository engineering governance, and it does not approve
PEP-CAM-CONTRACT-002.

## Trust boundary

| Source | How the verifier treats it |
| --- | --- |
| Trusted policy file passed by the caller | The only policy that can be evaluated |
| Candidate policy with a different digest | Cannot authorize the change that carries it |
| Decision or authorization JSON | Untrusted claims |
| `approved: true` inside a record | Not a field. Extra properties fail schema validation |
| Pull request merge | Recorded as `pr_merged`. Never an approval |
| Pull request comment | Untrusted evidence kind |
| GitHub review | Trusted only when an injected resolver returns `github_pull_request_review` with state `APPROVED` for an identity enrolled in the authority file |
| Production role file | Enrolls no people. Production mode cannot return authorized |
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

## What this pilot is not

No Physical Engineering interchange schema, Toolbox serializer, CAM-Assist
admission adapter, manufacturing permission, or organization migration.
Passing these tests does not resolve the five open interchange decisions.
GitHub branch protection for this workflow was not visible to the credential
that added it, so a green run is not a required check.
