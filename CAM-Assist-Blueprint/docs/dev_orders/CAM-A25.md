# Dev Order — CAM-A25

## Capability Reconciliation (Read-Only Comparison of Two Boundary Contracts)

## Predecessor baseline

```text
Baseline            CAM-Assist-Blueprint main @ 311d6a6
Latest capability   CAM-A23 — Creation Studio Capability Profile
Latest maintenance  CAM-A24 — Date-Time Blank-Value Hardening
CAM-A25             defined by this dev order, and by nothing preceding it
```

Nothing from the 2026-08-07 contamination window, the abandoned A24 attempt, or
earlier speculative numbering contributes to this scope.

## Scope

Close the loop opened by CAM-A22 and CAM-A23 by **comparing two contracts that
already exist**:

```text
CAM-A22 Creation Studio Request
              │
              │ requested_capabilities
              ▼
       CAM-A25 Reconciler
              ▲
              │ declared capabilities
              │
CAM-A23 Capability Profile

              │
              ▼
     Ephemeral Reconciliation
     ├─ satisfied
     ├─ unsatisfied
     └─ declared_but_unrequested

              │
        ┌─────┴─────┐
        ▼           ▼
 Human report    JSON stdout
                    │
                 optional CI
             --fail-on-unsatisfied
```

CAM-A22 records what CAM Assist asks for. CAM-A23 records what Creation Studio
declares it can author. Neither has ever been read against the other, although
`CAM-A23.md` and `docs/integration/CREATION_STUDIO_CAPABILITY_PROFILE.md` both
name **request compatibility checking** as a consumption purpose. CAM-A25 is that
check.

### Classification

CAM-A25 is a **capability**, not maintenance. Unlike CAM-A24 it adds new system
behaviour: CAM Assist gains the ability to evaluate compatibility between two
existing boundary contracts. `LEDGER.md` records it in the capability table.

It is the first capability since CAM-A23.

## Core Objective

> Given a CAM-A22 request and a CAM-A23 profile, can CAM Assist report which
> requested capabilities are declared, which are not, and which are declared
> without being requested — without inferring anything beyond identifier
> equality?

## The calculation

Exact set comparison over capability identifiers. Nothing else.

```text
satisfied                = requested ∩ declared
unsatisfied              = requested − declared
declared_but_unrequested = declared − requested
```

`declared_but_unrequested` is deliberately **not** named `undeclared`, which
would be confusable with the unsatisfied case — a capability that *was* requested
and is *not* declared.

Inputs are the identifiers already established by the two contracts:

| Source | Field | Vocabulary |
| --- | --- | --- |
| CAM-A22 request | `requested_capabilities[]` | closed enum, CAM-Assist-owned |
| CAM-A23 profile | `capabilities[].capability_id` | open pattern, Creation-Studio-owned |

## Derived advisory finding — `namespace_divergence`

One derived diagnosis, emitted only when all three hold:

```text
requested     is non-empty
declared      is non-empty
intersection  is empty
```

It is a **distinct finding, not commentary**, because it describes a materially
different architectural state. *"Two capabilities are missing"* and *"the two
vocabularies share zero identifiers"* are not the same condition and must not
render identically.

`severity: warning`. It does **not** gate `--fail-on-unsatisfied` — see Exit
codes.

### Why this finding is expected on the shipped contracts

Measured against `main @ 311d6a6`, the two vocabularies **share no identifiers at
all**:

```text
A22 requestable (closed, 8)          A23 declared in the shipped example (open, 7)
  feeds_speeds_recommendation          feeds_speeds_authoring
  tooling_review                       gcode_tutorial_generation
  operation_sequence_analysis          machining_lesson_playback
  cycle_time_estimation                post_processor_education
  simulation_request                   simulation_support
  gcode_explanation                    strategy_visualization
  toolpath_development_request         tool_library_editing
  workholding_review

intersection: EMPTY
```

This is structural rather than accidental. The near-misses —
`feeds_speeds_recommendation` against `feeds_speeds_authoring`,
`simulation_request` against `simulation_support` — show two different
ontologies: A22 requests **outcomes**, A23 declares **authoring features**.

It also cannot self-correct. A22's enum is closed and CAM-Assist-owned; A23's
vocabulary is open and Creation-Studio-owned precisely so Studio can evolve it
without a CAM Assist schema change. That design guarantees Studio will not emit
CAM Assist's request identifiers except by coincidence.

**A25 reports this truthfully rather than papering over it.** A first result of
"nothing matches, and here is precisely why" is useful evidence, not a failure of
the reconciler.

## Non-goals

> **A25 does not define semantic equivalence between A22 request identifiers and
> A23 capability identifiers.**

No synonym mapping. No alias table. No ontology translation. No semantic
inference. No fuzzy or prefix matching. No version compatibility inference — see
below.

Also out of scope: package coherence auditing, additional machining operation
types, any persisted reconciliation record, and any Creation Studio runtime
dependency.

## Authority invariants

Two statements are explicit invariants of this capability and **must be tested**:

> **An unsatisfied capability is a compatibility finding, not a prohibition.**
>
> **A satisfied capability is a declaration match, not authorization.**

The evidence boundary is narrow and must be stated in the output itself:
`satisfied` means **only** that the requested capability identifier appears in the
supplied A23 profile. It does **not** mean Creation Studio is installed,
reachable, operational, correctly configured, machine-ready, safe, or capable of
producing acceptable machining output.

A25 grants no execution authority, makes no approval decision, and does not
select capabilities on anyone's behalf.

## Versions

Identifiers are reconciled; **versions are not interpreted**.

`profile_version`, `record_version`, `studio_reference`, and `package_reference`
are surfaced for traceability so a reader can tell which inputs produced a given
result. CAM Assist does not infer compatibility from Creation Studio's version
numbering — `profile_version` is Creation-Studio-owned, and encoding assumptions
about it here would recreate the coupling A23's open vocabulary exists to avoid.

## Output

Two modes over one calculation. The JSON is an **ephemeral serialization of the
computation, not a repository contract, schema, or stored sidecar.**

### Human report

```text
Requested:                8
Satisfied:                0
Unsatisfied:              8
Declared but unrequested: 7

[WARNING] namespace_divergence
The request and capability-profile vocabularies are both non-empty
but share no identifiers.

ADVISORY ONLY — identifier matches do not imply execution authority,
machine readiness, or downstream availability.
```

### JSON (`--json`)

```json
{
  "satisfied": [],
  "unsatisfied": [
    "feeds_speeds_recommendation",
    "simulation_request"
  ],
  "declared_but_unrequested": [
    "feeds_speeds_authoring",
    "simulation_support"
  ],
  "findings": [
    {
      "code": "namespace_divergence",
      "severity": "warning",
      "message": "The request and capability-profile vocabularies are both non-empty but share no identifiers."
    }
  ]
}
```

Deterministic: all three sets are **sorted**, so output depends only on input
content and never on file or argument order. `findings` is a list so later
diagnoses can be added without reshaping the output.

## CLI and input resolution

**One package directory is the primary input.** Both artifacts are derived from
that single anchor, so a caller never manually joins two scopes:

```bash
python scripts/reconcile_creation_studio_capabilities.py \
  --package examples/packages/ltb_vcarve_synthetic_example
```

### Derivation

The request is **package-scoped**; the profile is **installation-scoped**. The
CLI resolves both from the package anchor:

```text
base    = conventional_base(package_dir, "creation_studio")
request = <base>/<package_name>_request.json
profile = <base>/capability_profile.json
          else, walking up from package_dir:
          <ancestor>/creation_studio/capability_profile.json   (first match wins)
```

`conventional_base` is the helper already used by the CAM-A22 and CAM-A20
creators: for `examples/packages/<name>` the sibling roots live under
`examples/`, otherwise beside the package directory. Reusing it means the
reconciler reads exactly where the request creator writes.

In the shipped repository layout both artifacts already resolve to the same
directory — `examples/creation_studio/` holds `capability_profile.json` and
`ltb_vcarve_synthetic_example_request.json` — so the common case needs no upward
walk at all. The walk exists for the genuine installation-scoped case, where the
profile sits at a workspace root above the package.

Profile resolution is deterministic: the first `capability_profile.json` found,
searching the conventional base and then package ancestors nearest-first. The
filename is fixed by CAM-A23, so a `creation_studio/` directory holding only
requests is skipped rather than mistaken for a profile location.

> **Derivation is path resolution only. It does not imply package ownership of
> the profile.** The profile remains installation-scoped and authoritative at its
> own location; the reconciler merely knows where to look.

### Overrides

```text
--request <path>
--profile <path>
```

Resolution precedence is **explicit override, else conventional derivation**, per
input independently — overriding one does not disable derivation of the other.

A derived or overridden input that is missing, unreadable, or not a valid record
of its type is an **input failure → exit 2**, never a reconciliation result. An
absent profile in particular must not be reported as "nothing declared."

Reconciliation is read-only. Neither input is mutated, and no file is written.

## Exit codes

| Condition | Exit |
| --- | --- |
| Reconciliation computed | 0 |
| Reconciliation computed, `unsatisfied` non-empty, `--fail-on-unsatisfied` | 1 |
| Input missing, unreadable, or not a valid record of its type | 2 |

`--fail-on-unsatisfied` fails because **`unsatisfied` is non-empty**, never
because `namespace_divergence` is present. The divergence finding is diagnostic
evidence, not a second hard gate. This mirrors the opt-in
`--fail-on-reference-warnings` escalation already established in the A19/A20
validators: default execution reports, and CI chooses its own strictness.

An input that fails its own contract is an argument error (exit 2), not a
reconciliation result. A25 does not re-implement A22 or A23 validation; it
requires enough structure to read the identifiers and otherwise defers.

## Rollout (phased)

1. Dev order (this file).
2. Reconciler core + tests — pure set logic, filesystem-free.
3. CLI: `--package` anchor with derivation, `--request` / `--profile` overrides,
   human report, `--json`, `--fail-on-unsatisfied`, exit codes + tests.
4. Documentation: `docs/integration/CAPABILITY_RECONCILIATION.md`, README
   section, `LEDGER.md`, `ROADMAP.md`.

Per-commit greenness applies: a test file may depend only on artifacts from its
own commit or earlier.

## Completion Criteria

The reconciler computes the three sets by exact identifier comparison; output is
deterministic and sorted; `namespace_divergence` fires on exactly the three
stated conditions and on no others; `--fail-on-unsatisfied` keys on `unsatisfied`
alone; a single `--package` anchor derives both inputs, with per-input overrides
taking precedence; a missing input exits 2 rather than reconciling; both
authority invariants are asserted by test; no schema, creator, example sidecar,
or persisted derived state is introduced; no execution authority is granted; the
full suite passes.

## Forward-looking note

> If repeated reconciliation shows persistent namespace divergence, a later
> separately authorized capability may define vocabulary alignment, aliases, or
> semantic mappings. **A25 must not preempt that decision.**

A25's job is to make the divergence visible and measurable. Deciding what to do
about it is a different capability, and one this dev order deliberately declines
to scope.
