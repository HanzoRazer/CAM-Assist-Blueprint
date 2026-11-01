# PEM-GOV-PLATFORM-002 deployment packet

This packet is for a repository administrator. Following it is a separate
action from merging the development pull request. Production governance
authorization stays disabled after deployment. Activation is a later owner
decision.

## States

| State | Meaning | This repository today |
| --- | --- | --- |
| Implemented | Verifier, resolver, and workflow file exist in git | Development pull request |
| Deployed and enforced | Default branch runs the trusted workflow from a pinned commit and branch protection requires `governance-trusted` | Not done |
| Operational | Enrolled reviewers can authorize a scope | Not done. Must remain disabled |

## What the administrator pins

| Item | Value |
| --- | --- |
| Repository | `HanzoRazer/CAM-Assist-Blueprint` |
| Trusted workflow | `.github/workflows/governance-trusted.yml` |
| Job name | `governance-trusted` |
| Event | `pull_request_target` only |
| Checkout | `github.event.pull_request.base.sha` |
| Permissions | `contents: read`, `pull-requests: read` |
| Credentials | `persist-credentials: false` |
| Policy file | `governance/policy/governance_policy_v1.json` |
| Policy version | `governance-policy-v1` |
| Canonicalization | `canonical-json-sha256-v1` |
| Pilot policy digest | `3c0236cd2cb61682b835fd34210ae37a022f7d891d84106fa1ff060631020769` |
| Roles file | `governance/policy/authorized_roles_v1.json` |
| Enrolled GitHub user ids | none |
| Verifier commit | The merge commit the administrator accepts. Do not use a branch name or a tag |
| Predecessor | `85ae01599d6aa435d3327517f6c23787fdb79adc` contains the pilot and does not contain this verifier |

Record the deployed commit:

```text
git rev-parse HEAD
python3 scripts/governance/verify_deployment.py --trust-commit <that-sha> --probe-github
```

`verify_deployment.py` exits 0 only when the running tree matches that commit,
the workflow contract passes, and the protection API lists `governance-trusted`
as a required check. Exit 0 still reports `production_authorization_operational`
false and `activation_permitted` false.

## Required GitHub permissions

The trusted job uses the default `GITHUB_TOKEN` with read access to contents
and pull requests. It does not need administration rights. An administrator
token is required only for the separate step that configures branch protection.

Live review verification, when enabled later, needs permission to read pull
request reviews and collaborator permission. Do not grant the job write,
workflow, or administration scopes.

## Required check

After the trusted workflow file is on the default branch:

1. Confirm a pull request runs `governance-trusted` from the base SHA, including a pull request that only edits the workflow file.
2. Add a branch protection rule or ruleset on `main` that requires the check context `governance-trusted`.
3. Require a review from people the owner has enrolled. This packet does not name those people.
4. Run `verify_deployment.py --trust-commit <deployed-sha> --probe-github`.
5. Expect `deployment_status` `DEPLOYED_NOT_ACTIVATED` and `required_check_confirmed` true.

Do not mark the path-filtered pilot workflow `governance` as the production gate. A pull request that avoids those paths would not report that job.

## What deployment does not do

- It does not set `production_authorization_operational` to true.
- It does not add entries to `github_user_ids`.
- It does not authorize PEP-CAM-CONTRACT-002 R2.
- It does not grant G-code generation, machine execution, material removal, or production-policy activation.

A candidate pull request must not be the place those switches are turned on.

## Rollback

1. Remove `governance-trusted` from required checks.
2. Revert the default branch to the previously recorded verifier commit.
3. Run `verify_deployment.py` again and expect `NOT_DEPLOYED` or a pin mismatch.
4. Leave production authorization false.

Reverting the workflow without removing the required check will block merges. Remove the requirement first.

## Development-time observation

The credential used while writing this packet could not read branch protection
(`administration=read` returned HTTP 403). An empty ruleset list is not proof
that the branch is unprotected. Treat enforcement as unconfirmed until the
probe above succeeds for an administrator.
