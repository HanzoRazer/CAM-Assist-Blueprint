# ADR — PEP-CAM-CONTRACT-002

## Canonical Physical Engineering interchange

**Merge guard:** PR #44 remains unmerged until the decision owner explicitly
authorizes retaining this governance record. That documentation decision
does not accept the architecture or authorize R2. Draft state and this notice
are review controls, not runtime enforcement of the R2 gate.

```text
status              PROPOSED
approval            not recorded
implementation      not started
recording location  HanzoRazer/CAM-Assist-Blueprint
ownership effect    none
```

This file asks for an owner decision. Its presence in CAM-Assist-Blueprint
does not make CAM-Assist the canonical contract owner, and it does not
publish a schema. R2 remains blocked until the decisions below are approved.

Witness time: `2026-10-27T02:59:49Z` (Monday, October 26, 2026, 9:59 PM CT).
Repository-state claims in R0 describe that witness and its pinned revisions,
not the latest state of external repositories. The later R1-GOV-001 section
records a separate witness; its disposition does not rewrite the R0 history.

## State of each decision

The order's defaults become authoritative only after owner approval.
"Verified" means the current source says this. "Proposed" means this ADR
recommends it and does not enact it.

| ID | Question | State | Disposition in this increment |
| --- | --- | --- | --- |
| PCCI-D01 | Which repository owns the canonical interchange? | Unresolved | No owner designated. Schemas were not created in any repository |
| PCCI-D02 | Raw proposal or frozen validated snapshot? | Proposed | Frozen snapshot is the recommendation. Not approved |
| PCCI-D03 | Who screens proposals and resolves evidence? | Proposed confirmation of current Toolbox behavior | Toolbox does this today inside its process. Cross-repository responsibility is not approved |
| PCCI-D04 | Snapshot carries validator version, policy identity, and screening outcome | Proposed | The internal Toolbox snapshot already carries these fields. That encoding is not the external contract |
| PCCI-D05 | Evidence identity, kind, digest, specimen context, and source provenance | Proposed | Current `EvidenceRef` does not carry digest, specimen, or provenance. Do not pretend that it does |
| PCCI-D06 | Advisory screening is not manufacturing permission | Order constraint, already true of the inspected gate and of CAM-Assist | No new contract clause was published |
| PCCI-D07 | Unknown versions and unresolved required evidence fail closed | Order constraint. True of the internal Toolbox gate for its own schema id `1.0` | No interchange validator was published |
| PCCI-D08 | CAM-Assist must not reproduce Toolbox calculations | Order constraint | No consumer adapter was written |
| PCCI-D09 | Explicit versions and compatibility tests | Proposed | No version was issued |
| PCCI-D10 | No production execution authority | Order constraint, already true of CAM-Assist's constitutional fields | No execution path was added |

Approved schema text and version: none.

Implemented interchange files: none.

## R0 — verified repository state

### CAM-Assist-Blueprint

PR #42 is merged.

| Fact | Value |
| --- | --- |
| PR | https://github.com/HanzoRazer/CAM-Assist-Blueprint/pull/42 |
| State | `MERGED` |
| Merge commit | `ccad852d26bc6dd1a3eb03933b7a0a8e89b9928f` |
| Merged at | `2026-10-26T06:07:51Z` (Monday, October 26, 2026, 1:07 AM CT) |
| PR head | `e10758c63a397bc6b576f97bb1a978c32fe55924` |
| `origin/main` at this inspection | `ccad852d26bc6dd1a3eb03933b7a0a8e89b9928f` |

That merge is the CAM-A33 investigation record. It did not add an admission
adapter. This ADR does not reopen CAM-A32 recovery and does not edit
`LEDGER.md` or `ROADMAP.md`.

### Canonical mesh repository

Probed with this session's GitHub credential, `GET /repos/HanzoRazer/<name>`:

```text
physical-engineering-mesh          HTTP 404
physical_engineering_mesh          HTTP 404
Physical-Engineering-Mesh          HTTP 404
physical-engineering               HTTP 404
pep-mesh                           HTTP 404
engineering-mesh                   HTTP 404
physical-engineering-contracts     HTTP 404
pep-contracts                      HTTP 404
pep-cam-contracts                  HTTP 404
canonical-physical-engineering     HTTP 404
```

`gh repo list HanzoRazer` returned no repository with those names. A public
repository search for "physical engineering mesh" returned unrelated
projects and no `HanzoRazer` mesh repository.

HTTP 404 from this credential does not prove that a private repository
outside this token's access is absent. These requests did not establish an
accessible publication target at that witness. This increment
does not create a substitute repository and does not create a substitute
contract in CAM-Assist.

### Luthiers Toolbox

| Fact | Value |
| --- | --- |
| `main` | `02032884c32d871b8a5addc24021763748eae949` |
| Commit time | `2026-10-24T03:55:14Z` (Friday, October 23, 2026, 10:55 PM CT) |
| Subject | Merge pull request #455 |

These blobs on that `main` match the October 25 inspection. The advisory
gate did not move:

| Path | Blob |
| --- | --- |
| `services/api/app/physical_engineering/proposal_v1.py` | `a35c5ccbf753b28e37f1c9a8164a879fe1a5a77b` |
| `services/api/app/physical_engineering/screening.py` | `c1d693c70d56156ebe117d6f3add93cb71a968f1` |
| `services/api/app/physical_engineering/evidence.py` | `162b68079e7a725dc1a8d52eb73b9aa6d970bbae` |
| `services/api/app/physical_engineering/evidence_artifact_v1.py` | `730dc864b1f41f6680f623013af460a1b0136101` |
| `services/api/app/physical_engineering/snapshot.py` | `b68f4053682eea02cf2bf982793eff30e3664ba4` |
| `services/api/app/physical_engineering/policy.py` | `4359327e938e481584fd7d0857265a4eb6edc25d` |
| `docs/physical_engineering/PEP-V1-HARDEN-001.md` | `b6730b30dabcea2f1db4817c1e3928da00d000fc` |
| `contracts/schema_registry.json` | `0131b114a22f868c61aba1706a04834c613512c6` |
| `contracts/material_evidence.schema.json` | `7930eef106100b91bd4c9690ea6a0eed83dc6894` |

`docs/physical_engineering/` still contains only `PEP-V1-HARDEN-001.md`.
The schema registry still lists `qa_core`, `cam_policy`, `viewer_pack_v1`,
telemetry and export envelopes, `material_evidence`, `material_prediction`,
and `prediction_residual`. It does not list a physical-engineering proposal,
validation, or review-snapshot schema.

The repository's latest push at `2026-10-27T02:56:25Z` (Monday, October 26,
2026, 9:56 PM CT) moved `docs/shop-operating-loop-recovery-001`, three
commits ahead of `main`. The compare file list is an investigation packet.
It does not add a Physical Engineering interchange schema. That branch is
not `main` and is not adopted here.

Open pull request #456 (`cursor/ltb-mvs-validation-policy-004`, head
`7a42854e19a8e48aa8935dafc9c7a23502f9a84b`, not merged) stores an LTB-local
policy record. Its own README says `ltb_validation_policy` 1.0 is not a
Physical Engineering Mesh standard, and
`POLICY_FIELD_AUTHORITY.md` records no approved production value for
`max_test_removal_mm` or `min_test_remaining_thickness_mm`. The test
fixtures `0.6` and `2.5` are explicitly not sources. This ADR does not
merge that pull request and does not treat it as the interchange contract.

### Tap Tone Pi

| Fact | Value |
| --- | --- |
| `main` | `52b8f3c9607cb61d384f30278cef04b8135c2c04` |
| Commit time | `2026-10-02T17:23:06Z` (Friday, October 2, 2026, 12:23 PM CT) |
| `authority-v1.schema.json` blob | `6813f95b25076d9a1255bd6206a4d30263f02559` |

Unchanged since the CAM-A33 inspection. Platform contracts remain Draft.
Prose says execution authorization is never allowed. The schema types
`can_authorize_execution` as a boolean without `const: false`. That
disagreement is still unresolved. This schema is not the engineering
review snapshot.

### CAM Creation Studio

`HanzoRazer/CAM-Creation-Studio` `main` at the R0 witness is
`374fa5832e571cebb470c5dc2e57f43b71e71226` (Monday, October 26, 2026,
5:11 PM CT). `CS-PEP-001` there is a traceable planning boundary for
Creation Studio. The shared letters are a name collision. It is not this
interchange contract.

## What the Toolbox gate actually is

Verified at Toolbox `02032884c32d871b8a5addc24021763748eae949` using
`proposal_v1.py`, `screening.py`, `evidence.py`,
`evidence_artifact_v1.py`, and `snapshot.py`; the exact blob IDs are in
the R0 table above.

`FrozenValidationSnapshotV1` freezes the proposal, resolved evidence, policy,
validator version, contradiction-rule version, resolution status, and
validation. `replay_validation_snapshot` recomputes from that record and
takes no live resolver. `VALIDATOR_VERSION` is `pep-v1-harden-001`.
Accepted proposal identity inside `screening.py` is
`schema_id = physical_engineering_proposal` and `schema_version = 1.0`.
Validation results are only:

```text
advisory_allowed
evidence_required
rejected
```

`claimed_authority` other than `advisory_only` returns `rejected` /
`ILLEGITIMATE_AUTHORITY_CLAIM`. `advisory_review_allowed` is human review
only. `snapshot.py` says the digest is a temporary internal encoding and
that canonical external serialization belongs to `PEP-V1-CONTRACT-002`.
That document is not a file on `main`. The digest function hashes
compact sorted JSON. The caller leaves `validation.snapshot_sha256` unset
before hashing. The function itself is not a published wire canonicalization,
and a SHA-256 match proves byte integrity of that internal payload. It does
not prove measurement truth, calibration, specimen identity, or
manufacturing permission.

`EvidenceRef` is `ref_id` and `expected_kind` only. Digest, specimen, and
provenance live on validator-owned resolved or stored records
(`ResolvedEvidence`, `LtbStoredEvidenceArtifactV1`). The stored-evidence
module says it is not a Physical Engineering Mesh schema. Its id is
`ltb_stored_evidence_artifact` / `1.0`.

`material_evidence` remains `research_only: true` and is a specimen bundle,
not a review snapshot.

## Recommendation, not a decision

Preferred shape, still unapproved:

```text
canonical owner     a Physical Engineering Mesh repository whose identity
                    is still unset
producer            Luthiers Toolbox serializes an actual screening record
measurement source  Tap Tone Pi, or another measurement system, supplies
                    evidence the producer resolves
consumer            CAM-Assist validates the frozen snapshot and may mark
                    it eligible for human manufacturing review
```

CAM-Assist would receive the frozen snapshot, not a raw proposal to
rescreen. It would not import Toolbox Python classes, would not re-run
thickness or removal arithmetic, and would not read Phase I test thresholds
as production policy.

Result vocabulary stays `advisory_allowed`, `evidence_required`, and
`rejected`. This ADR does not introduce `ADMISSIBLE_FOR_REVIEW`, `REFUSED`,
or `UNSUPPORTED_CONTRACT`.

Any future snapshot eligible for review would have to encode the equivalent
non-execution invariants below. These field names are illustrative local
spellings, not approved interchange fields; GOV-D05 remains unresolved:

```json
{
  "execution_authority_claim": false,
  "non_execution_declaration": true,
  "requires_human_review": true
}
```

`advisory_allowed` would mean eligible for human review. It would not mean
the physical action is admissible and it would not authorize cutting.

## Why R2 did not start

The mandatory stop conditions that are still open:

```text
canonical repository or owner unresolved
no approved schema text and version
evidence-resolver responsibility not confirmed for the interchange
raw proposal versus frozen snapshot not approved
Tap Tone authority schema cannot fail-closed on execution authorization
```

Creating `physical_engineering_review_snapshot_v1.schema.json` in
CAM-Assist would choose those semantics without an owner. The files in the
contract-publication plan were not added:

```text
docs/contracts/PEP-CAM-CONTRACT-002.md
schemas/physical_engineering_review_snapshot_v1.schema.json
schemas/physical_engineering_evidence_manifest_v1.schema.json
schemas/physical_engineering_contract_registry.json
examples/physical_engineering/
tests/test_physical_engineering_contract_v1.py
Toolbox serialization adapter
CAM-Assist admission validator
```

`docs/integration/PEP-CAM-SEAM-001.md` is unchanged. An adoption addendum
belongs to a later consumer increment, after a contract exists.

## Approval required before any schema

An approval that unblocks R2 has to name all of the following in one
decision:

1. The repository that owns the contract, and confirmation that this
   credential can write there.
2. The schema identifier and the first version string.
3. Frozen snapshot, or an explicit rejection of that recommendation.
4. The component that resolves evidence and asserts digest integrity.
5. The serialized authority fields and the result enum, limited to the
   upstream vocabulary unless a new value is written down on purpose.
6. Canonical JSON rules, including which field is excluded from the digest.
7. A statement that Phase I test thresholds are not production policy.

Until that decision exists, Toolbox remains the in-process advisory gate it
already is, and CAM-Assist's manufacturing review boundary remains the
strategy-package path already on `main`.

## Authorization boundary

Contract publication is not manufacturing authorization. This increment
adds no G-code, machine execution, material removal, production-policy
activation, or CAM-A32 reconstruction.

## R1-GOV-001 decision disposition

Witness: `2026-10-28T00:31:14Z` (October 27, 2026, 7:31 PM America/Chicago).
This section is later than the R1 proposal above.
It does not replace that proposal, appoint a decision owner, or approve
any architectural choice.

```text
decision_id: PEP-CAM-CONTRACT-002
status: proposed
decision_owner: null
effective_date: null

canonical_repository:
  identity: unresolved
  authority: unapproved

interchange:
  artifact_choice: proposed_frozen_snapshot
  schema_id: unresolved
  schema_version: unresolved
  canonicalization: unresolved

evidence:
  resolution_owner: proposed_luthiers_toolbox
  digest_integrity_protocol: unresolved

authority:
  execution_authority_claim: false
  non_execution_declaration: true
  requires_human_review: true

r2_authorized: false
```

This fenced status block is a declarative governance record, not a schema,
approval artifact, or executable gate. Its `authority` entries describe
local invariants; they do not settle the external field names in GOV-D05.

`status: proposed` stays proposed after a documentation merge. Merging this
file does not set `status` to accepted, does not fill `decision_owner`, and
does not set `r2_authorized` to true. A later change may record approval
only by citing an attributable owner decision, the exact text approved, and
the repository revision that decision names.

### PR #43 is merged, and that merge is not acceptance

Verified against [PR #43](https://github.com/HanzoRazer/CAM-Assist-Blueprint/pull/43)
on this witness:

| Fact | Value |
| --- | --- |
| State | `MERGED` |
| Draft flag at the witness | `false`; the current flag alone does not establish its state at merge |
| Head | `5f736e567dab31439df9b2b66fc5de43bec032f2`, unchanged |
| Merge commit | `77716972169827e12ce99f6e2aeda5b1f9532586` |
| Merged at | `2026-10-27T18:21:11Z` (Tuesday, October 27, 2026, 1:21 PM CT) |
| Parents | `ccad852d26bc6dd1a3eb03933b7a0a8e89b9928f`, `5f736e567dab31439df9b2b66fc5de43bec032f2` |
| Merged by | `HanzoRazer` |
| Approving reviews | none |

`HanzoRazer` [commented](https://github.com/HanzoRazer/CAM-Assist-Blueprint/pull/43#issuecomment-6450167126)
at `2026-10-27T18:20:50Z` that a local
ADR edit existed only on a machine branch named `pr43-review`, was not
committed or pushed, and that merging the proposed ADR is safe only if the
merge is not treated as design approval or as the start of R2. That
comment is evidence of intent about the merge. It is not an approval of
GOV-D01 through GOV-D05. The proposed edits described in that comment are
not part of `5f736e5`; a local-only report is not a committed approval record.

### R2 entry decisions and invariant checklist

GOV-D01 through GOV-D05 remain unresolved architectural decisions. The
additional rows distinguish existing invariants and the other unresolved
requirements already identified in R1 or the PR #43 comment. Existing local
invariants do not constitute an approved interchange clause. Every R2 entry
remains blocked; a checkmark in this file would not be approval.

| ID | Decision | Recorded result | R2 entry |
| --- | --- | --- | --- |
| GOV-D01 | Canonical repository and owner | Unresolved. Probed `HanzoRazer/physical-engineering-mesh`, `physical_engineering_mesh`, `Physical-Engineering-Mesh`, and `physical-engineering`. Each returned HTTP 404 to this credential. The accessible `HanzoRazer` repository list has no matching name. A 404 does not prove a private repository outside this token is absent | Blocked |
| GOV-D02 | Schema identifier, version, and publication location | Unresolved. No version was allocated | Blocked |
| GOV-D03 | Frozen snapshot versus raw proposal | Still the R1 recommendation only | Blocked |
| GOV-D04 | Who resolves evidence and who checks the portable digest | Proposed: Toolbox resolves before publication; CAM-Assist would check declared integrity without rescreening. Protocol text is not approved | Blocked |
| GOV-D05 | Serialized authority and result vocabulary | Proposed retention of `advisory_allowed`, `evidence_required`, and `rejected`, plus the three non-execution declarations. Field names are not approved | Blocked |
| GOV-D06 | Advisory screening grants no execution authority | Existing local invariant, not independently satisfied as a published interchange clause; R2 remains blocked | Blocked |
| GOV-D07 | Unknown versions and missing required evidence fail closed | Existing internal Toolbox behavior for `physical_engineering_proposal` / `1.0`, not independently satisfied as an interchange clause; no interchange validator exists | Blocked |
| GOV-D08 | ADR acceptance and R2 authorization are separate | This section records that separation. R2 is not authorized | Blocked |
| GOV-D09 | Canonical JSON and digest exclusion rules | Unresolved. Required by item 6 of the original approval list; no portable encoding is approved | Blocked |
| GOV-D10 | Phase I test thresholds are not production policy | Existing limitation; its explicit treatment in the approved interchange is unresolved. Required by item 7 of the original approval list | Blocked |
| GOV-D11 | Relationship to Toolbox's deferred `PEP-V1-CONTRACT-002` | Unresolved. The PR #43 comment identifies this naming question; this record does not equate or replace the two orders | Blocked |
| GOV-D12 | Tap Tone authority-schema gap disposition | Unresolved. A stop condition in R1; an attributable decision must record its remediation or explain why the future interchange does not depend on that schema. Silence does not clear it | Blocked |

`r2_authorized` is false. Outcome B means governance is incomplete and R2
remains blocked. The original seven-item approval list remains binding;
the later five-decision summary does not replace or shorten it.

### Mesh hold

#### What was searched

This order cites a prior Mesh hold that waits on a documented, processed
real tonewood artifact. This run searched CAM-Assist-Blueprint and the
pinned Toolbox filename inventory; it did not establish the authoritative
source of that hold. GitHub code search for the phrase returned HTTP 429,
which is unavailable search evidence, not a negative witness.

#### What was found at the disposition witness

On Luthiers Toolbox `main`
`cc8e13ae2b82065ade95b3a92ec5c6ed2d79d22d` (Tuesday, October 27, 2026,
12:31 AM CT), `docs/tonewood/` is a species reference library and
`MESH-MAT-001` remains the research-only material-evidence sidecar. A
filename search of that tree for a mesh/tonewood hold document did not
return the cited hold.

#### Why the evidence does not clear the hold

Neither failure to locate the hold nor a species reference library proves
that the required artifact exists or that an owner lifted the hold. Its
source and any clearing decision must be attributable. The hold remains
uncleared in this record; resolving the architectural choices alone does
not clear it. This increment does not publish a Mesh
schema in CAM-Assist in its place. Toolbox `main` has moved since the R1
baseline `02032884` for shop-operation records. The compare from
`02032884` to `cc8e13ae` does not change `physical_engineering/`,
`contracts/schema_registry.json`, `PEP-V1-HARDEN-001.md`, or
`material_evidence.schema.json`. Spot checks: `proposal_v1.py` is still
`a35c5ccbf753b28e37f1c9a8164a879fe1a5a77b`, the registry is still
`0131b114a22f868c61aba1706a04834c613512c6`, and the harden note is still
`b6730b30dabcea2f1db4817c1e3928da00d000fc`. Tap Tone Pi `main` is still
`52b8f3c9607cb61d384f30278cef04b8135c2c04`.

### Files this governance increment does not add

No approval record, because no attributable owner approval is recorded in
this revision.
`docs/decisions/PEP-CAM-CONTRACT-002-APPROVAL.md` is intentionally absent.
`docs/integration/PEP-CAM-SEAM-001.md` has no adoption note, because
ownership is not decided. Phase B contract files are not created. No
schema, fixture, registry, producer serializer, or CAM-Assist admission
validator is added. `LEDGER.md`, `ROADMAP.md`, A28, and A29 are unchanged.

For governance purposes in this repository revision,
`PEP-CAM-CONTRACT-002` is not treated as an authorization or replacement for
Toolbox's deferred `PEP-V1-CONTRACT-002`.
The relationship between those two names is one of the items an owner
approval still has to settle. This section does not settle it.
