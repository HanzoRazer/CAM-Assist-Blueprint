# Dev Order — CAM-A26

## Explicit Creation Studio Capability Vocabulary Bridge

## Predecessor baseline

```text
Baseline            CAM-Assist-Blueprint main @ cea7782
Latest capability   CAM-A25 — Creation Studio Capability Reconciliation
                    (merged PR #33)
CAM-A26             defined by this dev order, and by nothing preceding it
```

CAM-A25 must be on `main` before this work begins. It is. This capability does
not stack on an unmerged A25 branch.

## Classification

CAM-A26 is a **capability**, not maintenance. It adds a new contract and an
opt-in interpretive input to CAM-A25. `LEDGER.md` records it in the capability
table.

## Scope

CAM-A25 established that the shipped A22 request vocabulary and A23
capability-profile vocabulary have **zero exact identifier overlap**. CAM-A26
converts that observed incompatibility into an explicit, reviewable semantic
mapping.

```text
A22 requested outcome
        ↓
explicit A26 mapping
        ↓
A23 declared Creation Studio capability
```

CAM-A26 must not infer similarity from names, perform fuzzy matching, or
silently reinterpret either existing contract.

Authorized work:

1. Define a versioned capability-mapping contract.
2. Define explicit mappings between A22 request identifiers and A23 capability
   identifiers.
3. Validate mappings structurally.
4. Ensure all mapped request identifiers are legal A22 identifiers.
5. Allow A23 capability identifiers to remain open/extensible.
6. Extend CAM-A25 reconciliation with an opt-in mapped-reconciliation mode.
7. Preserve exact-match reconciliation as the default.
8. Report which match mechanism produced each satisfied result.
9. Add documentation and governance entries.
10. Add focused regression, schema, boundary, and negative tests.

## Core Objective

> Given an A22 request, an A23 profile, and an explicitly approved A26
> capability map, can CAM Assist deterministically report exactly satisfied
> requests, explicitly mapped satisfied requests, still-unsatisfied requests,
> declared-but-unrequested capabilities, raw namespace divergence, and mapping
> provenance — without inferring any mapping that is not written down?

## Design decisions recorded at implementation time

These choices were not fully prescribed by the handoff. They are recorded here
so a reviewer can accept or reject them without reverse-engineering the code.

### Canonical contract location

There is no established `contracts/` directory on `main`. CAM-A26 introduces
one:

```text
contracts/creation_studio_capability_map.json
```

This is the CAM-Assist-owned mapping registry. It is hand-authored, not
generated. A22/A23 examples remain under `examples/`; this file is not an
example. It is the policy artifact that says which A23 identifiers CAM Assist
will treat as satisfying which A22 identifiers.

### A22 source authority

Mapping sources are validated against the authoritative A22 enum extracted
from `schemas/creation_studio_request.schema.json` at validation time:

```text
properties.requested_capabilities.items.enum
```

The validator does not duplicate that enum as a Python list. A new A22
identifier is therefore legal as a mapping source the moment it is added to
the schema; an unknown identifier is a structural mapping error.

### A23 targets remain open

Mapped targets are strings matching the A23 identifier pattern
`^[a-z][a-z0-9_]*$`. They are not enumerated. A mapping may name an A23
capability that the supplied profile does not declare; that mapping remains
structurally valid and simply fails to satisfy during reconciliation.

### Initial canonical mappings are conservative

A26 exists because near-miss names are **not** matches. The initial registry
records only correspondences that are:

* exemplified by the A26 handoff, or
* the two near-miss pairs A25 already named as the architectural evidence
  that motivated a later mapping layer.

```text
feeds_speeds_recommendation  →  feeds_speeds_authoring
simulation_request           →  simulation_support
gcode_explanation            →  gcode_tutorial_generation
                             →  post_processor_education
```

The remaining A22 identifiers are **deliberately unmapped**:

```text
tooling_review
operation_sequence_analysis
cycle_time_estimation
toolpath_development_request
workholding_review
```

Leaving them unmapped is the honest statement. Tool-library editing is not
tooling review. Strategy visualization is not operation-sequence analysis.
No A23 identifier currently claims cycle-time estimation, toolpath
development, or workholding review. Adding those rows would be inference.

This is the principal human-review gate of CAM-A26. Reviewers may add rows;
the reconciler will not invent them.

### Exact `reconcile()` stays two-argument

CAM-A25 made non-participation of provenance structural:

```text
reconcile(requested, declared)     exact identifier comparison
reconcile_mapped(...)              exact first, then explicit map
```

Mapping is a third interpretive input. It is applied by `reconcile_mapped`,
not folded into `reconcile`. Exact-mode tests that inspect
`inspect.signature(reconcile)` remain true.

### `declared_but_unrequested` stays an exact-set

```text
declared_but_unrequested = declared − requested
```

A mapped A23 identifier was not requested by identifier, so it remains in
this set even when it satisfied a request via the map. That is evidence that
the namespaces remain different. Satisfaction details explain the mapped use.

### `namespace_divergence` is not removed or renamed

The CAM-A25 finding still fires on the **raw exact intersection**:

```text
requested non-empty AND declared non-empty AND exact intersection empty
```

Mapped satisfaction does not clear it. When a map is supplied and at least
one request is satisfied by mapping, a second finding is added:

```text
mapped_compatibility
```

severity `info`. The two findings together are the distinction the handoff
names `raw_namespace_divergence` / `mapped_compatibility` without deleting
the A25 code.

### Satisfaction details only in mapped mode

Exact-mode JSON remains the four-key core plus `inputs`. Mapped mode adds:

```text
inputs.capability_map.{path, record_version, map_version}
satisfaction_details[]
```

Each detail is:

```json
{
  "request_capability": "simulation_request",
  "method": "exact" | "mapped",
  "matched_capability": "simulation_support"
}
```

Precedence: **exact, then mapped**. An identical identifier is classified
`exact` even if a mapping also exists. Mapped details report **every**
declared target that the map names, sorted. Mapping-array order does not
affect output.

### Authority block

The map is advisory. Five const-true flags, closed:

```text
is_informational
does_not_authorize_execution
does_not_bypass_human_review
does_not_confirm_machine_readiness
does_not_grant_permission
```

A mapping cannot grant execution authority, machine readiness, approval, or
permission.

### Versions

`record_version` is the format version. `map_version` is the mapping-content
version. Both are surfaced for provenance. Neither is interpreted. No semver
compatibility logic is authorized.

### CLI

```bash
python scripts/reconcile_creation_studio_capabilities.py \
  --package examples/packages/ltb_vcarve_synthetic_example
```

is unchanged: exact comparison, no map.

```bash
python scripts/reconcile_creation_studio_capabilities.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --capability-map contracts/creation_studio_capability_map.json
```

is the opt-in. A missing or structurally invalid map is an input failure
(exit 2). `--fail-on-unsatisfied` still keys only on unresolved
`unsatisfied`.

## The calculation

Without a map (CAM-A25):

```text
satisfied                = requested ∩ declared
unsatisfied              = requested − declared
declared_but_unrequested = declared − requested
```

With a map:

```text
exact_satisfied          = requested ∩ declared
mapped_candidates        = unsatisfied after exact
mapped_satisfied         = { r in mapped_candidates
                             | mapping[r] ∩ declared ≠ ∅ }
satisfied                = exact_satisfied ∪ mapped_satisfied
unsatisfied              = requested − satisfied
declared_but_unrequested = declared − requested     (unchanged)
```

Any mapped target declared by the profile satisfies the request (`any_of`).
No `all_of` semantics.

## Authority invariants

The A25 invariants remain, and A26 adds one:

> **An unsatisfied capability is a compatibility finding, not a prohibition.**
>
> **A satisfied capability is a declaration match, not authorization.**
>
> **A mapped match is an explicit compatibility declaration, not approval,
> installation, reachability, machine readiness, or execution authority.**

## Non-goals

CAM-A26 does not authorize changing A22 identifiers, closing A23's
vocabulary, automatic vocabulary convergence, semantic inference, fuzzy
matching, LLM mapping, synonym discovery, semver compatibility logic,
dynamic mapping downloads, Creation Studio API calls, runtime capability
probing, execution testing, package coherence audits, persisted
reconciliation records, or assigning CAM-A27.

## Completion Criteria

The mapping contract exists; the canonical registry exists and is
hand-reviewed; sources are checked against the A22 schema enum; targets
remain open; rationale is required and non-blank; exact reconciliation is
the default and unchanged; mapped reconciliation requires `--capability-map`;
exact and mapped satisfaction are distinguishable; mapping provenance is
surfaced; raw `namespace_divergence` is not hidden; mapped compatibility can
coexist with raw divergence; strict mode keys on final `unsatisfied` only;
no A22/A23 schema is altered; no Creation Studio runtime is introduced; no
reconciliation artifact is persisted; documentation and governance are
updated; the suite and the non-execution invariant pass.

A reviewer should be able to answer:

> **Does CAM-A26 resolve the A22/A23 identifier-namespace mismatch through
> an explicit, auditable semantic bridge without hiding the underlying
> divergence or creating new execution authority?**

**Yes** is the completion criterion.
