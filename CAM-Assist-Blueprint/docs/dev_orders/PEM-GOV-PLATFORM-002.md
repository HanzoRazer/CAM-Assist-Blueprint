# Dev Order — PEM-GOV-PLATFORM-002

## Protected trust root and GitHub approval evidence

```text
order id     PEM-GOV-PLATFORM-002
date         2026-10-31
predecessor  PEM-GOV-PLATFORM-001, PR #45, merge 85ae01599d6aa435d3327517f6c23787fdb79adc
head before  63aaa40262838d6c0e0b79bbc78a4f21237517a0
status       development verifier
production   not operational
r2           BLOCKED
```

This order hardens the governance verifier. It does not approve the five open
PEP-CAM-CONTRACT-002 decisions, enroll production reviewers, or activate a
required merge gate.

## Decisions implemented here

| ID | Behavior in this change |
| --- | --- |
| GOV2-D01 | Policy and verifier bytes load from a named commit via `git show` |
| GOV2-D02 | Roles stay empty. Enrollment is an owner edit of the protected copy |
| GOV2-D03 | Worktree files are candidate data. `candidate_worktree_is_trust_root` is false |
| GOV2-D04 | `GitHubEvidenceResolver` reads review state, user id, permission, and commit |
| GOV2-D05 | Authorization still binds repository, decision, revision, scope, and policy digest |
| GOV2-D06 | UTC clock. Effective date inclusive. Expiration exclusive. Naive timestamps fail |
| GOV2-D07 | `governance-trusted.yml` has a stable job name and no path filter. It is not required yet |
| GOV2-D08 | `verify_deployment.py` cannot activate production |
| GOV2-D09 | Execution-authority claims stay invalid |
| GOV2-D10 | PEP-CAM-CONTRACT-002 remains `PROPOSED` and R2 remains blocked |

## Smallest enforceable design

Use a `pull_request_target` workflow that already exists on the protected
default branch. GitHub runs that file, not the candidate's copy. The job
checks out `github.event.pull_request.base.sha` with read-only permissions
and `persist-credentials: false`. It does not check out the pull-request head
and does not execute candidate scripts.

A reusable workflow in another repository, or a GitHub App check publisher,
would also move the trust root outside this candidate. Both need a separate
owner decision and are not created here.

The design is not deployed. Branch protection was not confirmed, so this
change does not claim the gate is enforced. The predecessor digest pin inside
the checkout remains defense in depth only.

## Stop conditions kept

No production identities were invented. Production authorization stays
disabled. The Mesh tonewood hold and the interchange decisions are untouched.
Manufacturing execution authority is unchanged.

## Rollout

| Phase | Result |
| --- | --- |
| R0–R7 | Development verifier, tests, trusted-workflow preparation, deployment packet |
| R8 | Administrator deploys the reviewed commit and required check |
| R9 | Owner activation decision. Not part of this order |

PR merge is not architecture acceptance. Architecture acceptance is not
implementation authorization. Implementation authorization is not
manufacturing execution authority.
