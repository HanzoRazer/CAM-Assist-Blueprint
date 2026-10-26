# PEP-CAM-SEAM-001

## Cross-repository Physical Engineering seam

```text
status                 inspection record
adapter                not implemented
owner approval         not recorded
R4                     blocked
```

CAM-Assist does not own these contracts. This document maps what was read
on Sunday, October 25, 2026 (witness clock `2026-10-26T04:11:09Z`,
11:11 PM CT). It does not promote an experimental or local contract into
canonical interchange authority.

## Heads inspected

| Repository | Ref | Commit | Commit time (CT) |
| --- | --- | --- | --- |
| `HanzoRazer/CAM-Assist-Blueprint` | `main` | `2b146ef1f325ae0db1377feac894eb6ae7e71316` | Tuesday, September 15, 2026, 3:15 AM |
| `HanzoRazer/luthiers-toolbox` | `main` | `02032884c32d871b8a5addc24021763748eae949` | Friday, October 23, 2026, 10:55 PM |
| `HanzoRazer/tap_tone_pi` | `main` | `52b8f3c9607cb61d384f30278cef04b8135c2c04` | Friday, October 2, 2026, 12:23 PM |
| `HanzoRazer/physical-engineering-mesh` | — | repository HTTP 404 | — |
| `HanzoRazer/tap-tone-pi` | — | repository HTTP 404; the public name is `tap_tone_pi` | — |

Also probed and HTTP 404 under `HanzoRazer`: `physical_engineering_mesh`,
`Physical-Engineering-Mesh`, `physical-engineering`. No upstream repository
was modified.

Luthiers Toolbox pull request `#428` (`cursor/pep-v1-harden-001-ffa7`)
merged `2026-10-05T18:41:46Z` (Sunday, October 5, 2026, 1:41 PM CT). The
advisory gate below is on `main`, not only on that branch. Later merged
work on the same package includes `#453` (beginner proposal harness),
`#454` (guided review stopped before a production route), and `#455`
(LTB-local stored evidence resolver, which is current `main`).

## Ownership matrix

| Contract | Where it was read | Identity and version | Maturity | Authority as written | CAM-Assist disposition |
| --- | --- | --- | --- | --- | --- |
| Physical Engineering Mesh repository | GitHub repo API | none | absent | no shared canonical owner exists under the probed names | do not invent a mesh package here |
| Advisory proposal gate | `luthiers-toolbox` `services/api/app/physical_engineering/proposal_v1.py`, blob `a35c5ccbf753b28e37f1c9a8164a879fe1a5a77b`. Identity check in `screening.py`, blob `c1d693c70d56156ebe117d6f3add93cb71a968f1` | `VALIDATOR_VERSION = pep-v1-harden-001`. Accepted proposal identity: `schema_id = physical_engineering_proposal`, `schema_version = 1.0`. Validation record: `schema_id = physical_engineering_validation`, `schema_version = 1.0`. Snapshot: `schema_id = physical_engineering_validation_snapshot`, `schema_version = 1.0` | Merged Python dataclasses. `docs/physical_engineering/PEP-V1-HARDEN-001.md` (blob `b6730b30dabcea2f1db4817c1e3928da00d000fc`) says canonical external serialization belongs to `PEP-V1-CONTRACT-002`. That path is not on `main`. The directory contains only the harden note. No physical-engineering or proposal `schema.json` exists in the `main` tree | `claimed_authority` must be `advisory_only` or the gate returns `rejected` / `ILLEGITIMATE_AUTHORITY_CLAIM`. `advisory_review_allowed` means human review only. The module docstring says this is not physical admissibility and does not authorize manufacture, material removal, brace modification, or measurement execution. Policy numbers are Phase I test thresholds, not production limits. The gate is not mounted on a route. Geometry is an untrusted claim until `PEP-MESH-SEAM-003`, which is not a file on `main` | do not reimplement the gate, and do not publish a CAM-Assist JSON stand-in for the deferred external contract |
| Evidence citation | `services/api/app/physical_engineering/evidence.py`, blob `162b68079e7a725dc1a8d52eb73b9aa6d970bbae` | `EvidenceRef` has `ref_id` and `expected_kind` only. `ResolvedEvidence` has no `schema_id`. The comment says schema identity waits for `PEP-V1-CONTRACT-002` | In-process protocol. `InMemoryEvidenceResolver` is a test fixture that recomputes SHA-256 | A digest proves bytes were not altered. It does not prove the measurement is true, calibrated, or the right specimen | CAM-Assist A29 resolves declaring-file paths. It is not this resolver, and this order does not make it one |
| LTB stored evidence | `services/api/app/physical_engineering/evidence_artifact_v1.py`, blob `730dc864b1f41f6680f623013af460a1b0136101` | `schema_id = ltb_stored_evidence_artifact`, `schema_version = 1.0` | The module docstring says: "LTB-local stored evidence. This is not a Physical Engineering Mesh schema." | No approval field. No engineering or manufacturing authority | not admissible as mesh evidence |
| Material evidence bundle | `luthiers-toolbox` `contracts/material_evidence.schema.json`, blob `7930eef106100b91bd4c9690ea6a0eed83dc6894`; registry blob `0131b114a22f868c61aba1706a04834c613512c6` | `$id` `https://luthierstoolbox.com/schemas/toolbox/material_evidence.schema.json`. `schema_id` const `material_evidence`. Registry version `1.0`. `research_only` const `true` | Research sidecar described by `docs/handoffs/MESH_MAT_001_MATERIAL_EVIDENCE_RESEARCH_2026-08-19.md`. Required fields are `specimen_id` and `values`. Description: "Research ingestion only; no CAM authority." The handoff says Tap Tone adapters are later | Research-only. Not a manufacturing proposal | not an admission package |
| Tap Tone platform vocabulary | `tap_tone_pi` `docs/platform-contracts/README.md`, blob `67f8571aba603b075d3f53f5ee0ec1902da1a152`; `authority-v1.schema.json`, blob `6813f95b25076d9a1255bd6206a4d30263f02559` | Version `1.0.0` in the README and `authority-v1.md`. Schema `$id` is `authority-v1.schema.json` | README status is **Draft**. It says the contracts are vocabulary convergence and that runtime integration needs an explicit dev order. Participating-repo table lists CAM-Assist-Blueprint as "Needs authority/review-decision mapping" | Prose says every class has "Can authorize execution: No". The JSON Schema types `can_authorize_execution` as a free boolean. The description says "always false"; the schema does not use `const: false` | prose and schema disagree, so this schema is not a fail-closed execution boundary CAM-Assist can adopt |
| Tap Tone evidence pack | `tap_tone_pi` `docs/contracts/EVIDENCE_PACK_CONTRACT_v1.md` | Normative reference for `viewer_pack_v1` spectra (`spectrum.csv`, `analysis.json`) | Measurement export for a viewer pack | Factual spectral records. Not an engineering-change proposal | not the PEP proposal package |
| CAM-Assist A29 | `scripts/_shared/artifact_references.py` | declaring-file-relative POSIX references | Current `main` behavior | Resolves strings. Does not validate engineering content and does not require the target to exist | unchanged |
| CAM-Assist A28 | `scripts/_shared/package_coherence.py` | `ARTIFACT_ORDER` is manifest, strategy, review packet, annotations, assumptions, risk, decision record, revision lineage, traceability bundle, production shop handoff, creation studio request | Coherence of those strategy-package slots | Explicitly "evidence consistency, not execution authority". No Physical Engineering slot | unchanged. No accepted PE relationship exists to add |
| CAM-Assist constitutional fields | strategy package manifest and validators already on `main` | `execution_authority_claim: false`, `non_execution_declaration: true`, `requires_human_review: true` | Enforced by existing validators | Human review. No machine authority | unchanged |

`contracts/schema_registry.json` on Luthiers Toolbox `main` lists
`qa_core`, `cam_policy`, `viewer_pack_v1`, telemetry and export envelopes,
`material_evidence`, `material_prediction`, and `prediction_residual`. It
does not list `physical_engineering_proposal`,
`physical_engineering_validation`, or `ltb_stored_evidence_artifact`.

## Upstream result vocabulary that was actually read

`ValidationResult` in `proposal_v1.py`:

```text
advisory_allowed
evidence_required
rejected
```

`screening.py` rejects `schema_id != physical_engineering_proposal` and
`schema_version != 1.0` as `INVALID_PROPOSAL_STRUCTURE` /
`rejected`. The proposal tests cover `schema_id = unknown` and
`schema_version = 2.0` on that path. There is no upstream enum value
`ADMISSIBLE_FOR_REVIEW`, `REFUSED`, or `UNSUPPORTED_CONTRACT`.

Other reason codes present in `screening.py` include
`ILLEGITIMATE_AUTHORITY_CLAIM`, `ACTION_NOT_YET_GOVERNED` (used for
`modify_brace`), `MISSING_REQUIRED_EVIDENCE_KIND`,
`AMBIGUOUS_REQUIRED_EVIDENCE`, `EVIDENCE_REFERENCE_NOT_FOUND`, and
`EVIDENCE_DIGEST_MISMATCH`. `remove_material` still depends on the
validator-owned resolver and on `ValidationPolicyV1` test thresholds.
Those thresholds are not constants of the gate.

## Why the receiving boundary is not implemented

A CAM-Assist admission adapter would have to do one of the following:

1. Treat the Luthiers Toolbox Python dataclasses as the interchange and
   re-run `validate_proposal` here. That copies a gate whose policy numbers
   are test thresholds, whose geometry seam is still open, and whose
   evidence resolver is owned by the validator in Luthiers Toolbox.
2. Design a JSON receiving profile in `schemas/` so CAM-Assist can validate
   files. Upstream text assigns that external serialization to
   `PEP-V1-CONTRACT-002`, and that contract is not on the inspected `main`.
   A profile written here would be a new CAM-Assist schema, which this
   order forbids until upstream contract authority is verified.
3. Admit Tap Tone `authority-v1` or `material_evidence` as the proposal
   package. They are a draft vocabulary and a research-only specimen
   bundle. Neither is a versioned engineering proposal plus evidence
   package.

All three conflict with A33-D03, A33-D04, and the rule that no placeholder
schema is committed to satisfy the file plan. R3 is this mapping. Owner
approval of a receiving profile is not recorded, so R4 does not start.

## What an approved later increment would still have to pin

This is a list of unresolved decisions, not an implementation sketch and
not an approved interface.

```text
which repository is the canonical owner of the shared contract
the published schema identifier, version, and JSON Schema text
whether CAM-Assist receives a raw proposal or an already-frozen snapshot
which evidence references are required, and who resolves them
how advisory_allowed maps to human review without becoming execution authority
serialized admission names, chosen after that contract exists
proof that unknown versions fail closed without a fallback reading
proof that the adapter writes no G-code and performs no machine action
```

Until those are pinned from source, CAM-Assist's manufacturing review
boundary stays the strategy-package path already on `main`. A29 and A28
are not extended. The constitutional declarations stay as they are.

## Files intentionally not added

```text
schemas/*physical*
scripts/validate_physical_engineering_admission.py
tests/test_physical_engineering_admission.py
examples/physical_engineering/
changes to scripts/_shared/artifact_references.py
changes to scripts/_shared/package_coherence.py
changes to docs/dev_orders/LEDGER.md
changes to docs/dev_orders/ROADMAP.md
```
