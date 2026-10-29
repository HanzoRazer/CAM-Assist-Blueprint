# Dev Order — PEM-GOV-PLATFORM-001

## Cross-repository engineering governance control plane

```text
order id     PEM-GOV-PLATFORM-001
date         2026-10-28
pilot        HanzoRazer/CAM-Assist-Blueprint
status       non-authoritative kernel
production   not operational
```

This order builds a governance verifier. It does not approve the five open
PEP-CAM-CONTRACT-002 decisions, and it does not authorize interchange R2.

## Invariants

| ID | Rule |
| --- | --- |
| GOV-P04 | A merged pull request is not an approval event |
| GOV-P05 | Authorization binds exact repository, revision, and scope |
| GOV-P06 | Unknown or inconsistent evidence fails closed |
| GOV-P07 | Identities are checked against an authority file, not a display name |
| GOV-P08 | Governance cannot grant machine execution authority |
| GOV-P09 | Another repository adopts this policy only with that owner's consent |
| GOV-P10 | The Mesh real-tonewood-artifact hold stays an independent restriction |

Decision states are `PROPOSED`, `UNDER_REVIEW`, `ACCEPTED`, `DEFERRED`, and
`REJECTED`. `ACCEPTED` is not implementation authorization.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Authorized for the exact requested scope. Synthetic mode only in this pilot |
| 1 | Blocked by policy or missing approval |
| 2 | Invalid record or schema |
| 3 | Evidence unavailable or unverifiable |
| 4 | Configuration or verifier error |

## Rollout recorded here

| Phase | Result |
| --- | --- |
| R0 Inventory | No accessible approved PEM-GOV kernel. Mesh repository names returned HTTP 404 to this credential. That is not global nonexistence |
| R1–R4 Kernel | Decision and authorization checks, registry digests, PEP-CAM-CONTRACT-002 fixture returns blocked |
| R5 Regression | Run with the pilot tests, the CAM-Assist suite, and the non-execution check |
| R6 Draft PR | Pilot only. Not merged by this order |
| R7 Other repositories | Not started |

## Pilot limit

GitHub is the intended system of record for reviews. This build does not
enroll approvers and does not treat a workflow file as branch protection.
`production_authorization_operational` stays false.

No G-code, machine execution, material removal, production-policy
activation, or CAM-A32 reconstruction.
