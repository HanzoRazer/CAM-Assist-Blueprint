# PEM-GOV-PLATFORM-002 deployment packet

This packet is the administrator procedure for draft pull request #46.
Merging that pull request publishes the trusted workflow. It does not
establish governance authority, and it does not enable production
authorization. An authorized repository administrator performs the
protection change. The development credential must not call the branch
protection write API.

## Deployment and authorization stay separate

| State | What it means | How this packet treats it |
| --- | --- | --- |
| Published | `.github/workflows/governance-trusted.yml` is on `main` and a later pull request shows the check | Step 2 merge, then the disposable test pull request |
| Enforced | Live protection requires the check context `governance-trusted` | Step 5, only after the test pull request shows a completed check |
| Attested | The pin is the default branch or a byte-identical ancestor, protection requires the check, and one successful run is bound to this workflow file | Step 6 |
| Operational | Enrolled reviewers can authorize a scope | Out of scope. Remains disabled |

`production_authorization_operational` stays false. `activation_permitted`
stays false. PEP-CAM-CONTRACT-002 R2 stays `BLOCKED`. No GitHub user ids
are enrolled here.

## Publication before enforcement

`governance-trusted` is a `pull_request_target` workflow. GitHub runs the
copy on the default branch. Requiring the check before that file is on
`main` can block every merge, because the check is never published.

1. Finish the security review of pull request #46 and confirm its tests pass.
2. The repository owner authorizes the merge. Merge #46 with production authorization disabled. Record the merge commit. That commit is the verifier pin. Do not use a branch name or a tag.
3. Open a disposable test pull request against `main`. Use a change that does not match the pilot path filter, so the only governance job that can run is the trusted workflow. Record the pull request number, its base SHA, and the Actions run id. The run must be workflow file `.github/workflows/governance-trusted.yml` with event `pull_request_target`, and its check must complete successfully. A check that only reuses the name `governance-trusted` does not count. The disposable pull request proves the check publishes and executes. It does not activate production authorization.
4. Stop if the check does not appear or does not complete. Do not enable the requirement. Follow the publication recovery section.
5. The administrator, with an account that can administer `main`, requires the check context `governance-trusted` on a branch protection rule or an active ruleset that applies to `refs/heads/main`. Set the check's expected source to GitHub Actions (app id `15368`). A required name with "any source" can be satisfied by any commit status that reuses the name, and the attestation reports it as `required_any_source`, not `required`. Restrict bypass actors to the smallest set the owner accepts. Do not grant the workflow write, workflow, or administration scopes.
6. From a checkout of the merge commit, rerun the attestation with that authorized credential and keep the JSON:

```text
git rev-parse HEAD
python3 scripts/governance/verify_deployment.py --trust-commit <merge-sha>
```

Exit 0 requires every item below. If any GitHub API read is unavailable or
the payloads disagree, `authority_established` stays false and the command
exits 1.

- `running_verifier_matches_pin` is true and `workflow_contract_ok` is true. The contract is the parsed workflow, not a comment that contains the expected words.
- `required_check_confirmed` is true. `protection_state` is `required`, which means the required `governance-trusted` entry is bound to GitHub Actions. Protection is read for the live default branch. A `--branch` other than the default branch reports `unverified`.
- `deployment_evidence.pin_relationship` is `exact`, or it is `ancestor` and `bytes_match.verifier`, `bytes_match.policy`, `bytes_match.roles`, and `bytes_match.workflow` are all true. Matching the workflow file alone does not attest an ancestor. `verifier` covers the kernel, the package initializers, the JSON schemas, and the `scripts/governance` entry points the trusted job runs. `workflow` covers the workflow file and `requirements/governance-trusted.txt`.
- `deployment_evidence.trusted_check_bound` is true. The successful run is bound to `pull_number`, `base_sha`, `workflow_path`, `workflow_id`, and `run_id`. `base_sha` is the pin or the current default-branch tip. The check does not have to be attached to the pin SHA itself, because `pull_request_target` reports it on the pull request head.
- `deployment_status` is `DEPLOYED_NOT_ACTIVATED`.
- `production_authorization_operational` and `activation_permitted` are false.

A commit SHA alone does not establish authority. Exit 0 is deployment
verification, not production authorization. `.gitattributes` keeps the
verifier paths LF, so a Windows checkout with `core.autocrlf=true` matches
the pin. A checkout made before that file existed needs a fresh checkout. The administrator installs the
reviewed lock before running the probe:

```text
python3 -m pip install --require-hashes -r requirements/governance-check.txt
```

If enabling the requirement blocks legitimate merges, restore the previous
protection configuration before further investigation.

## Exact names

| Item | Value |
| --- | --- |
| Repository | `HanzoRazer/CAM-Assist-Blueprint` |
| Pull request | #46 |
| Trusted workflow | `.github/workflows/governance-trusted.yml` |
| Check context and job name | `governance-trusted` |
| Event | `pull_request_target` only |
| Checkout action | `actions/checkout@11d5960a326750d5838078e36cf38b85af677262` (v4.4.0) |
| Python setup action | `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065` (v5.6.0) |
| Checkout ref | `github.event.pull_request.base.sha` |
| Verifier lock | `requirements/governance-trusted.txt` |
| Test lock | `requirements/governance-check.txt` |
| Job permissions | `contents: read`, `pull-requests: read`, `persist-credentials: false` |
| Policy file | `governance/policy/governance_policy_v1.json` |
| Policy version | `governance-policy-v1` |
| Canonicalization | `canonical-json-sha256-v1` |
| Policy digest | `3c0236cd2cb61682b835fd34210ae37a022f7d891d84106fa1ff060631020769` |
| Roles file | `governance/policy/authorized_roles_v1.json` |
| Enrolled GitHub user ids | none |
| Predecessor without this verifier | `85ae01599d6aa435d3327517f6c23787fdb79adc` |

Do not require the path-filtered pilot job `governance`. A pull request that
avoids those paths would not report that job. The enforced context is
`governance-trusted`.

The attestation command reads live branch protection and the full document
for every listed ruleset. It reads the workflow from the pinned commit, not
from the worktree. A ruleset id whose document was not read leaves the result
unverified. Do not treat HTTP 403 as evidence that the branch is unprotected.

## Administrator evidence to keep

Record these with the date and the account that performed the change:

- Pull request #46 review conclusion and the merge commit SHA.
- The disposable test pull request number and URL, its base SHA, the workflow id, the successful run id, and the check URL. The workflow path must be `.github/workflows/governance-trusted.yml`.
- The protection or ruleset change: rule name, include ref `refs/heads/main`, required context `governance-trusted`, and bypass actors.
- The `verify_deployment.py` JSON after that change.
- The previous protection settings, so they can be restored.

## Publication recovery

Use this when the workflow file is on `main` and a test pull request does
not show a completed `governance-trusted` check.

1. Leave required checks unchanged. Do not add `governance-trusted`.
2. Confirm the default branch contains `.github/workflows/governance-trusted.yml` at the recorded merge commit.
3. Confirm the test pull request targets `main` and that the run is `pull_request_target`, not the path-filtered pilot workflow.
4. Read the Actions log for the base SHA checkout. A verifier error, exit 4, is a failed publication. A missing job is also a failed publication.
5. Fix the workflow on a new pull request, or revert `main` to `85ae01599d6aa435d3327517f6c23787fdb79adc` if the published file must be removed. Revert is safe only while the check is not required.
6. Repeat the disposable test pull request. Return to the enforcement step only after a successful completion.

## Protection rollback

Use this when requiring the check blocks legitimate merges.

1. Remove `governance-trusted` from required checks, or restore the protection settings recorded before the change.
2. Confirm a normal pull request can merge again.
3. Keep the workflow file on `main` unless publication itself failed.
4. Run `verify_deployment.py --trust-commit <merge-sha>` and expect `NOT_DEPLOYED` with `authority_established` false.
5. Leave `production_authorization_operational` false.

Remove the requirement before reverting the workflow. Reverting the file
while the check is still required blocks merges.

## What this procedure does not do

- It does not set `production_authorization_operational` to true.
- It does not add entries to `github_user_ids`.
- It does not authorize PEP-CAM-CONTRACT-002 R2.
- It does not grant G-code generation, machine execution, material removal, or production-policy activation.
- It does not ask the development agent to merge pull request #46 or to change branch protection.

Enrollment and activation are a later owner decision after this attestation
exists.
