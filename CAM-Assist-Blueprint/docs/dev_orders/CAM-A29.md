# Dev Order — CAM-A29

## Traceability Reference Path Canonicalization

## Classification

```text
maintenance-class
contract-coherence hardening
not a new product capability
```

CAM-A29 occupies an A-number by explicit authorization, the same way CAM-A24
and CAM-A27 did. It is **not** a product capability. It does not add a
traceability artifact, schema, CLI option, or manufacturing decision.

It repairs an internal consistency defect surfaced by CAM-A28: mixed
inter-artifact reference conventions.

## Predecessor baseline

```text
Baseline            CAM-Assist-Blueprint main @ 65e9f4c
Latest capability   CAM-A28 — Package Coherence Audit
                    (merged PR #36 → 65e9f4c)
Latest maintenance  CAM-A27 — Capability Map Runtime Hardening
                    (merged PR #35 → 7f20320)
CAM-A29             defined by this dev order, and by nothing preceding it
```

CAM-A28 is on `main`. The committed example still exhibits the
declaring-file-relative `MISSING_REFERENCE` findings that authorized this
work. This branch does not stack on an open A28 PR.

## Scope

Canonicalize CAM Assist traceability-file references so every relative
reference is interpreted consistently:

```text
relative to the file that declares the reference
```

Authorized work:

1. Establish declaring-file-relative resolution as the canonical rule.
2. Inventory all reference-bearing CAM Assist traceability fields.
3. Correct committed examples that violate the canonical rule.
4. Ensure creators emit canonical references.
5. Ensure completeness validators resolve using exactly the same rule.
6. Ensure CAM-A28 consumes the same rule.
7. Remove any repository-root fallback if one was introduced outside the
   approved architecture.
8. Add cross-artifact tests preventing mixed reference conventions from
   returning.
9. Update documentation to state the rule once and consistently.
10. Re-run the committed package-coherence example.
11. Update governance status (A28 → Merged; A29 maintenance; A30+ unassigned).

Out of scope:

* a second path-resolution fallback or repository-root-relative convention;
* absolute artifact paths;
* automatic bulk migration of historical records;
* reference URI schemes;
* path-security sandboxing or package-root escape policy;
* package identity changes;
* traceability schema redesign;
* content changes to assumptions, risk, decisions, lineage, or authority;
* CAM-A25 / CAM-A26 reconciliation changes;
* capability-map changes;
* Production Shop or Creation Studio runtime work;
* A12 `record_review_decision.py` rewrite;
* manifest `strategy_file` / `review_packet_file` rewrite;
* assigning CAM-A30.

## Core objective

> Can a CAM Assist artifact be moved with its surrounding package and still
> resolve every declared traceability reference according to one
> deterministic rule, without repository-root assumptions or silent
> fallback behavior?

Yes is the completion criterion.

## Design decisions recorded at authorization time

### Canonical rule

Every relative artifact reference is resolved as:

```text
resolve_declared_reference(declaring_file, value)
    = normalize(declaring_file.parent / value)
```

Writers store:

```text
relative_reference(output_file, target_file)
```

which is the path from `output_file.parent` to `target_file`, serialized
with forward slashes.

Central invariant:

```text
resolve_declared_reference(
    output_file,
    relative_reference(output_file, target_file)
)
== normalized target_file
```

### Shared module

```text
scripts/_shared/artifact_references.py
```

This file owns `relative_reference()`, `resolve_declared_reference()`, and
`normalize_reference_string()`. Creators, completeness validators, and
CAM-A28 call it. They do not keep parallel path arithmetic.

Do not place this logic in the capability-map module.

### Creator output contract

Stored JSON references are computed from the output artifact to the
resolved target. They do **not** preserve the raw CLI string.

Same-directory targets become bare filenames. Sibling or nested
directories use `..` as needed. Serialized separators are `/`.

### Bundle `--base`

`validate_traceability_bundle.py --base` remains an explicit operator
override of the resolution root. Default behavior is declaring-file-relative
(`path.parent`). `--base` is not a silent repository-root fallback and is
not removed in CAM-A29.

### No repository-root fallback

Do not try declaring-file-relative and then fall back to repository root.
Malformed references must remain invalid.

### No working-directory semantics

Resolution must not depend on `os.getcwd()`. A file resolves identically
regardless of where the validator or auditor process was launched.

### No absolute paths

Committed traceability references remain portable between checkouts.

### Writer scope

Migrate:

* manufacturing decision record
* revision lineage (any emitted `related_records`; creator currently seeds
  a root revision without related-record paths)
* traceability bundle
* Production Shop handoff
* Creation Studio request (already emits references)

Inventory but do not rewrite:

* A12 `record_review_decision.py`
* manifest `strategy_file` / `review_packet_file`

### Existing artifact content remains authoritative

CAM-A29 may change only reference strings required for canonical path
correctness. Changing a malformed relative path in a committed example is a
fixture/contract correction, not a rewrite of the manufacturing decision.

### CAM-A28 is the coherence witness

After corrections, the canonical committed example ecosystem should pass
CAM-A28's reference-coherence checks without fallback logic.

If the three currently known path failures are the only error-level
findings, `--json --fail-on-errors` should exit 0. If unrelated A28 errors
remain, classify them separately. Do not weaken A28.

### Constitutional boundary

CAM-A29 changes path representation and reference consistency only. It
must not change manufacturing decisions, rewrite rationale, alter risk or
assumptions, infer artifact authority, approve packages, authorize
execution, or change package identity.

## Phase 0 gate (recorded)

```text
main SHA              65e9f4c
A28 merge PR          #36
working-tree          clean at branch creation
open PR count         0 (A26/A27/A28 merged)
```

A28 real-example findings that authorized this work, still present on
`main` at branch creation:

```text
decision_record.assumptions_file
    examples/traceability/ltb_vcarve_synthetic_example_assumptions.json
decision_record.risk_file
    examples/traceability/ltb_vcarve_synthetic_example_risk.json
revision_lineage.revisions[1].related_records.risk_file
    examples/traceability/ltb_vcarve_synthetic_example_risk.json
```

Those files live under `examples/traceability/`. Declaring-file-relative
resolution correctly fails because the stored strings are
repository-root-style.

## Phase 2 inventory

| Artifact | Field | Writer | Consumer | Pre-A29 convention | Canonical? |
| --- | --- | --- | --- | --- | --- |
| manufacturing decision record | `assumptions_file`, `risk_file`, `lineage_file` | `create_manufacturing_decision_record.py` (assumptions/risk; no `--lineage-file`) | structural type-check; A28 existence | CLI string stored verbatim | after A29: writer emits declaring-file-relative |
| revision lineage | `revisions[].related_records.*` | creator does not emit related_records | structural type-check; A28 existence | committed example was repo-root-style | fixture corrected; creator unchanged for emission |
| traceability bundle | `bundle_contents.*` | `create_traceability_bundle.py` | `--check-references`; A28 | already declaring-file-relative | yes; now uses shared helper |
| Production Shop handoff | `contents.*` | `create_production_shop_handoff.py` | `--check-references`; A28 | already declaring-file-relative | yes; now uses shared helper |
| Creation Studio request | `contents.*` | `create_creation_studio_request.py` | `--check-references`; A28 | already declaring-file-relative | yes; now uses shared helper |
| A12 review decision | `assumptions_file`, `risk_file`, `lineage_file` | `record_review_decision.py` | structural | CLI string stored verbatim | **out of rewrite**; inventoried only |
| package manifest | `strategy_file`, `review_packet_file` | package assembly | manifest validator; A28 | relative to manifest | **out of rewrite**; inventoried only |

## Phase 6 characterization (before fixture correction)

After shared resolution was in place and before committed examples were
edited, `audit_package_coherence.py --json` against
`examples/packages/ltb_vcarve_synthetic_example` reported exactly three
error-level findings: the three `MISSING_REFERENCE` slots listed in Phase 0.
No unrelated A28 errors. After fixture correction those findings are gone
and `--json --fail-on-errors` exits 0.

## Non-goals

See Scope. Additional coherence defects exposed while running CAM-A28
must be recorded separately unless they are directly caused by the
reference convention fixed here.
