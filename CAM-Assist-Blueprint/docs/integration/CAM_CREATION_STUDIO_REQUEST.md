# CAM-Creation-Studio Capability Request

Record type: `cam_assist_creation_studio_request` · Version `1.0.0` · CAM-A22

## Purpose

The CAM-Creation-Studio Capability Request is a portable, reference-only artifact
that lets CAM Assist describe **what downstream machining-development assistance it
is requesting** from the separate CAM-Creation-Studio product — feeds/speeds,
tooling review, operation sequencing, simulation, toolpath development, and the
like. It is a contract-first interoperability probe: the smallest useful
interchange contract, implemented to observe whether the boundary between the two
products stays coherent under real use.

> The request records desired downstream assistance. It does not assert that
> CAM-Creation-Studio supports the capability, does not authorize execution, and
> does not make CAM Assist responsible for machining execution.

## Repository Boundary

CAM Assist and CAM-Creation-Studio **remain separate repositories.** CAM-A22 does
not merge them, does not add runtime integration, and introduces no
CAM-Creation-Studio dependency. Whether the products should eventually converge is
**not decided**; this contract exists to gather evidence for that decision rather
than to pre-empt it.

```text
CAM Assist              manufacturing intent, review, risk, and traceability
CAM-Creation-Studio     machining education, feeds/speeds, operation refinement,
                        simulation, G-code authoring, execution-adjacent analysis
```

The consumer side lives in the CAM-Creation-Studio repository and is **deferred** —
no consumer implementation is added here.

## Request Artifact

A reference-only manifest. Every reference is a path relative to the request file's
own location, forward-slashed. The request never owns, copies, caches, or mutates
the referenced files, and never modifies the source package.

The request carries **no `created_at` timestamp**: the artifact is deterministic so
that regenerating it (delete → recreate) yields byte-identical output. Auditability
of *when* a request was made belongs to the surrounding workflow (git, filesystem),
not the artifact body.

```json
{
  "record_type": "cam_assist_creation_studio_request",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
  "request_direction": "cam_assist_to_creation_studio",
  "requested_capabilities": ["feeds_speeds_recommendation", "tooling_review"],
  "contents": {
    "package_manifest_file": "../packages/<pkg>/manifest.json",
    "strategy_file": "../packages/<pkg>/strategy.json",
    "review_packet_file": "../packages/<pkg>/review_packet.md",
    "traceability_bundle_file": "../traceability/<pkg>_bundle.json",
    "production_shop_handoff_file": "../production_shop/<pkg>_handoff.json"
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
and `operator_notes`. It is omitted when no context is supplied.

## Requested Capabilities

A non-empty, unique list drawn from the v1 controlled vocabulary:

```text
feeds_speeds_recommendation   cycle_time_estimation       toolpath_development_request
tooling_review                simulation_request          workholding_review
operation_sequence_analysis   gcode_explanation
```

The vocabulary describes *requested* assistance only. **It does not guarantee that
CAM-Creation-Studio supports the capability** — capability support is the
consumer's concern, declared in its own repository.

## Creating a Request

```bash
python scripts/create_creation_studio_request.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --capability feeds_speeds_recommendation \
  --capability tooling_review \
  --capability operation_sequence_analysis \
  --force
```

The creator resolves `package_reference` from `manifest.federation.federated_package_id`
(else the directory name), always emits the core three references, and includes the
traceability bundle and production shop handoff when supplied explicitly
(`--traceability-bundle`, `--production-shop-handoff`) or discovered by convention.
Optional `--material`, `--machine-profile`, and `--operator-notes` populate
`request_context`. Default output: `creation_studio/<package>_request.json`.

## Validating a Request

```bash
python scripts/validate_creation_studio_request.py \
  examples/creation_studio/ltb_vcarve_synthetic_example_request.json
```

Structural validation is filesystem-free: it opens only the request file and never
resolves the referenced files. Exit codes: `0` valid, `1` invalid (or parse error /
non-object root), `2` file not found.

## Completeness Witness

```bash
python scripts/validate_creation_studio_request.py \
  examples/creation_studio/ltb_vcarve_synthetic_example_request.json \
  --check-references
```

An opt-in **existence** witness: for each declared reference, it warns when the
path does not resolve relative to the request file's directory. Existence only — it
never opens, parses, or schema-checks a referenced file, performs no capability
support check, and reports no absent-slot findings. Warnings never change validity
or the exit code unless `--fail-on-reference-warnings` is also given (which promotes
unresolved references to errors for CI).

## Inspector Detection

```bash
python scripts/inspect_strategy_package.py examples/packages/ltb_vcarve_synthetic_example
```

The inspector reports presence only:

```text
CAM-Creation-Studio Request:
  present
```

It looks for an explicit `--creation-studio-request <path>` first, then the
conventional `creation_studio/<package>_request.json`. Detection only — it never
opens, parses, validates, resolves references, or infers supported capabilities.

## Authority Model

The request is **advisory only.** The required authority block declares five
const-`true` non-execution flags: `is_informational`,
`does_not_authorize_execution`, `does_not_bypass_human_review`,
`does_not_confirm_machine_readiness`, and `does_not_require_gcode_generation`. The
request **does not grant execution authority** and **does not require G-code
generation** inside CAM Assist.

## Non-Execution Doctrine

CAM Assist remains upstream of execution. The request does not generate G-code,
does not authorize machine execution, does not confirm machine readiness, and does
not bypass human review. The **Production Shop handoff (CAM-A20) remains a
separate** outbound artifact with its own contract; the request may *reference* a
handoff but does not absorb, replace, or re-authorize it.

## Merger Evaluation Value

CAM-A22 answers a strategic question empirically:

> Do CAM Assist and CAM-Creation-Studio need to merge, or can a stable contract
> preserve their strengths as companion products?

The correct way to answer is not to merge first, but to implement the smallest
useful interchange contract and observe whether the boundary stays coherent. This
request is that probe. Integration is **not** complete until a consumer exists in
the CAM-Creation-Studio repository.
