# Dev Order — CAM-A22

## CAM-Creation-Studio Interchange Contract Probe

## Scope

Define and prove the first **contract-first interoperability seam** between CAM
Assist Blueprint and the separate CAM-Creation-Studio repository.

CAM-A22 does **not** merge the repositories and does **not** add runtime
integration. It creates a portable, non-execution **capability request artifact**
that lets CAM Assist describe what downstream machining-development assistance is
being requested, while preserving the boundary between:

```text
CAM Assist              manufacturing intent, review, risk, and traceability
CAM-Creation-Studio     machining education, feeds/speeds, operation refinement,
                        simulation, G-code authoring, execution-adjacent analysis
```

The purpose is to gather executable evidence about whether the products should
remain companions or eventually converge — by implementing the smallest useful
interchange contract and observing whether the boundary stays coherent.

## Core Objective

> Can CAM Assist describe a downstream machining-development request without
> absorbing CAM-Creation-Studio's execution-oriented responsibilities?

The request may express needs such as feeds/speeds recommendation, tooling
review, operation sequencing, cycle-time estimation, simulation, G-code
explanation, or toolpath development. It must **not** claim that any result is
approved, safe, machine-ready, or executable.

## New Artifact

| Field | Value |
| --- | --- |
| Canonical name | CAM-Creation-Studio Capability Request |
| Record type | `cam_assist_creation_studio_request` |
| Version | `1.0.0` |
| Direction | `cam_assist_to_creation_studio` (outbound only) |
| Authority | Advisory only; five const-true non-execution flags |

## Design Decisions

| Decision | Outcome |
| --- | --- |
| Repository merger | Not part of CAM-A22 |
| Integration model | Contract-first |
| Direction | CAM Assist → CAM-Creation-Studio |
| Returned results | Deferred |
| Artifact type | Informational request manifest |
| Machine execution | Forbidden |
| G-code generation inside CAM Assist | Forbidden |
| Request authority | Advisory only |
| Production Shop handoff | Remains separate |
| Existing packages | Not mutated |
| CAM-Creation-Studio dependency | None |
| Consumer implementation | Deferred to its own repo |

### `created_at` is intentionally omitted

Unlike the production-shop handoff and traceability bundle, the request record
carries **no `created_at` timestamp**. A22's verification discipline requires the
tool-generated example to regenerate **byte-identically** (`delete → regenerate →
diff clean`). A wall-clock timestamp would defeat that on every run. The request
is a transient, reproducible interchange probe — not an audit record — so
determinism is favoured over a creation stamp. Auditability of *when* a request
was made belongs to the surrounding workflow (git, filesystem mtime), not the
artifact body.

## Artifact Shape

```json
{
  "record_type": "cam_assist_creation_studio_request",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
  "request_direction": "cam_assist_to_creation_studio",
  "requested_capabilities": [
    "feeds_speeds_recommendation",
    "tooling_review",
    "operation_sequence_analysis"
  ],
  "contents": {
    "package_manifest_file": "../packages/ltb_vcarve_synthetic_example/manifest.json",
    "strategy_file": "../packages/ltb_vcarve_synthetic_example/strategy.json",
    "review_packet_file": "../packages/ltb_vcarve_synthetic_example/review_packet.md",
    "traceability_bundle_file": "../traceability/ltb_vcarve_synthetic_example_bundle.json",
    "production_shop_handoff_file": "../production_shop/ltb_vcarve_synthetic_example_handoff.json"
  },
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true,
    "does_not_confirm_machine_readiness": true,
    "does_not_require_gcode_generation": true
  }
}
```

`request_context` (optional) may add informational `material`, `machine_profile`,
and `operator_notes` fields. It is omitted when no context is supplied so the
default example stays minimal and reproducible.

## Requested Capability Vocabulary (v1)

```text
feeds_speeds_recommendation
tooling_review
operation_sequence_analysis
cycle_time_estimation
simulation_request
gcode_explanation
toolpath_development_request
workholding_review
```

The vocabulary describes *requested* assistance only. It does not guarantee that
CAM-Creation-Studio supports the capability.

## Schema Requirements

- Required top-level: `record_type`, `record_version`, `package_reference`,
  `request_direction`, `requested_capabilities`, `contents`, `authority`.
- Constants: `record_type == cam_assist_creation_studio_request`,
  `request_direction == cam_assist_to_creation_studio`.
- `authority` required; all five flags const-`true`; closed (no undeclared flags).
- `requested_capabilities`: array, ≥1 entry, unique, known values only.
- `contents`: required object; five allowed slots; no slot individually required;
  each supplied value a non-empty string. `production_shop_handoff_file` is the
  fifth slot, distinguishing this contract from the handoff's four.
- `request_context`: optional object; `material`, `machine_profile`,
  `operator_notes`; informational only; closed.
- Closed top-level contract (`additionalProperties: false`).

## Boundary Invariants

The request records desired downstream assistance. It does not assert that
CAM-Creation-Studio supports the capability, does not authorize execution, does
not confirm machine readiness, does not require G-code generation, and does not
make CAM Assist responsible for machining execution. No CAM-Creation-Studio
consumer, runtime import, or G-code generation is introduced by CAM-A22.

## Rollout (phased)

0. Base gate — CAM-A20 merged to `main` (confirmed: PR #21).
1. Dev order (this file).
2. Schema + schema tests.
3. Structural validator + tests (filesystem-free).
4. Creator + tests (explicit and conventional reference discovery).
5. Tool-generated example + deterministic-regeneration witness.
6. Completeness witness (`--check-references`, existence only) + tests.
7. Inspector detection (`--creation-studio-request`) + tests (detection only).
8. Documentation (integration doc; patch relationship/product/workflow docs).
9. Full verification (targeted + full suite + non-execution invariant).
10. PR — no merge, tag, release, or CAM-Creation-Studio repo change without
    separate authorization.

## Completion Criteria

Contract, creator, validator, completeness witness, tool-generated example, and
inspector detection all exist; product boundary documented; no consumer
implementation, no G-code, no execution authority, no package mutation
introduced; full suite passes.
