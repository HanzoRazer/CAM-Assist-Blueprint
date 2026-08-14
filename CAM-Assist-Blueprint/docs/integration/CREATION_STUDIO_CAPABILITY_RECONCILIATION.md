# Creation Studio Capability Reconciliation (CAM-A25)

## Purpose

Compare what CAM Assist **asks** CAM-Creation-Studio for against what a supplied
capability profile **declares**, and report the difference.

```text
CAM-A22 Creation Studio Request
              │  requested_capabilities
              ▼
       CAM-A25 Reconciler
              ▲
              │  capabilities[].capability_id
CAM-A23 Capability Profile
```

Both inputs are CAM-Assist-owned boundary records. Reconciliation reads them and
nothing else: no network call, no CAM-Creation-Studio runtime, no installation
check, no execution.

The result is **derived and ephemeral**. It is recomputed from the two
authoritative inputs every run, and is never written to disk by this tool.

## Inputs

| Input | Contract | Field read |
| --- | --- | --- |
| Request | CAM-A22 | `requested_capabilities[]` |
| Profile | CAM-A23 | `capabilities[].capability_id` |

Only enough structure is read to extract identifiers. Reconciliation is **not** a
second validator — use `validate_creation_studio_request.py` and
`validate_creation_studio_capability_profile.py` for that.

## Package and installation scope

The two artifacts live at different scopes, and that asymmetry is deliberate:

```text
request   package-scoped        <package-parent>/creation_studio/<package>_request.json
profile   installation-scoped   <root>/creation_studio/capability_profile.json
```

One package directory anchors the CLI and both paths are derived from it:

```bash
python scripts/reconcile_creation_studio_capabilities.py \
  --package examples/packages/ltb_vcarve_synthetic_example
```

Profile discovery searches the conventional base first, then package ancestors
nearest-first, matching the **fixed file** `capability_profile.json`. A
`creation_studio/` directory holding only requests is skipped rather than
mistaken for a profile location.

> **Derivation is path resolution only. It does not imply package ownership of
> the profile.** The profile remains installation-scoped and authoritative at its
> own location.

Either input may be overridden; precedence is per input, independently:

```text
--request <path>     explicit beats derived
--profile <path>     explicit beats derived
```

A missing or unreadable input — derived or explicit — is an **input failure**,
never a reconciliation result. In particular, an absent profile is never reported
as "nothing declared".

## Reconciliation rules

Exact, case-sensitive comparison of capability identifiers:

```text
satisfied                = requested ∩ declared
unsatisfied              = requested − declared
declared_but_unrequested = declared − requested
```

All three sets are sorted, so output depends only on input content and never on
the order identifiers appear in a file.

### Satisfied

The requested identifier appears among the declared identifiers.

> **"Satisfied" means only that a requested capability identifier appears in the
> supplied capability profile.**

### Unsatisfied

The requested identifier does not appear among the declared identifiers.

### Declared but unrequested

The profile declares a capability this request did not ask for. Informational —
it describes the profile, not a problem with the request.

Named `declared_but_unrequested` rather than `undeclared`, which would be
confusable with the unsatisfied case: a capability that *was* requested and is
*not* declared.

## Namespace divergence

One derived advisory finding, emitted only when **all three** hold:

```text
requested     is non-empty
declared      is non-empty
intersection  is empty
```

```text
[WARNING] namespace_divergence
The request and capability-profile vocabularies are both non-empty
but share no identifiers.
```

An empty intersection alone is not sufficient. With an empty request or an empty
profile the intersection is trivially empty and says nothing about whether the
vocabularies agree.

The finding is **diagnostic evidence, not a gate** — see Strict CI mode.

## Human output

```text
Request: examples/creation_studio/ltb_vcarve_synthetic_example_request.json
Package: luthiers-toolbox:vcarve:les-paul-custom-2024
Request record version: 1.0.0

Profile: examples/creation_studio/capability_profile.json
Studio: cam-creation-studio
Profile version: 1.0.0
Profile record version: 1.0.0

Requested:                3
Satisfied:                0
Unsatisfied:              3
Declared but unrequested: 7

[WARNING] namespace_divergence
The request and capability-profile vocabularies are both non-empty
but share no identifiers.

ADVISORY ONLY - identifier matches do not imply execution authority,
machine readiness, or downstream availability.
```

Metadata that a record does not carry is omitted rather than shown as a
placeholder.

## JSON output

`--json` emits one JSON document on stdout **and nothing else**. Diagnostics go
to stderr, so a failing CI caller receives empty stdout rather than something
unparseable.

```json
{
  "inputs": {
    "request": {
      "path": "examples/creation_studio/ltb_vcarve_synthetic_example_request.json",
      "record_version": "1.0.0",
      "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024"
    },
    "profile": {
      "path": "examples/creation_studio/capability_profile.json",
      "record_version": "1.0.0",
      "profile_version": "1.0.0",
      "studio_reference": "cam-creation-studio"
    }
  },
  "satisfied": [],
  "unsatisfied": ["feeds_speeds_recommendation", "operation_sequence_analysis", "tooling_review"],
  "declared_but_unrequested": ["feeds_speeds_authoring", "gcode_tutorial_generation"],
  "findings": [
    {
      "code": "namespace_divergence",
      "severity": "warning",
      "message": "The request and capability-profile vocabularies are both non-empty but share no identifiers."
    }
  ]
}
```

**This is a process output, not a repository contract.** There is no
reconciliation schema, creator, example sidecar, or persisted directory, and
nothing validates a saved copy of it. Recompute rather than store: a saved result
can silently disagree with either input the moment that input changes.

## Input provenance

The `inputs` block belongs to the **ephemeral serialized report**, not to the
reconciliation model. The distinction is architectural:

```text
Reconciliation core        derived comparison only          4 keys
serialize_reconciliation   core result + input provenance   5 keys
```

Provenance is composed *around* the comparison, never folded into it. The pure
reconciler takes two identifier lists and nothing else, so a path or version has
no route by which to influence set membership.

It answers one question the sets cannot: **which request and which profile
produced this result.** Paths reflect resolution precedence, so an override is
reported rather than the location it replaced. Paths are forward-slashed and
repository-relative, so the same layout serializes identically on Windows and
Linux and carries no machine-specific root.

Versions are **surfaced, never interpreted**. `profile_version` is the
Creation-Studio-owned capability-set version; `record_version` is the format
version owned by this repository. CAM Assist performs no semantic-version
comparison, ordering, or compatibility inference — doing so would couple this
repository to CAM-Creation-Studio's release semantics, which is exactly what
CAM-A23's open vocabulary exists to avoid.

## Strict CI mode

```bash
python scripts/reconcile_creation_studio_capabilities.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --json --fail-on-unsatisfied
```

| Condition | Exit |
| --- | --- |
| Reconciliation computed | 0 |
| `unsatisfied` non-empty **and** `--fail-on-unsatisfied` | 1 |
| Input missing, unreadable, or unusable | 2 |

`--fail-on-unsatisfied` is **exit-status policy only**. It changes no
classification: the JSON payload is byte-identical with and without it. Failure
is attributable to `unsatisfied` alone — `namespace_divergence` never
independently changes the exit code.

## Authority boundary

> **An unsatisfied capability is a compatibility finding, not a prohibition.
> A satisfied capability is a declaration match, not authorization.**

A match does **not** establish that CAM-Creation-Studio is:

```text
installed        reachable        operational       correctly configured
machine-ready    safe             suitable          able to produce
                                                    acceptable machining output
```

Reconciliation grants no execution authority, makes no approval decision, and
selects no capability on anyone's behalf. Human authority over manufacturing
decisions is unchanged.

## Current vocabulary divergence

The shipped CAM-A22 and CAM-A23 vocabularies **share no exact identifiers**:

```text
A22 requestable (closed enum, CAM-Assist-owned)   A23 declared (open, Studio-owned)
  feeds_speeds_recommendation                       feeds_speeds_authoring
  tooling_review                                    gcode_tutorial_generation
  operation_sequence_analysis                       machining_lesson_playback
  cycle_time_estimation                             post_processor_education
  simulation_request                                simulation_support
  gcode_explanation                                 strategy_visualization
  toolpath_development_request                      tool_library_editing
  workholding_review
```

> **This does not mean CAM-Creation-Studio supports nothing. It means the two
> contracts currently use different identifier namespaces.**

The divergence is structural rather than accidental. A22 requests **outcomes**
(recommend, review, estimate); A23 declares **authoring features** (authoring,
visualization, editing, playback). A22's enum is closed and CAM-Assist-owned,
while A23's vocabulary is open and Creation-Studio-owned precisely so Studio can
evolve it without a CAM Assist schema change — so Studio will not emit CAM
Assist's request identifiers except by coincidence.

CAM-A25 reports this truthfully rather than concealing it behind a mapping layer.
A result of "nothing matches, and here is why" is useful evidence.

## Non-goals

> **CAM-A25 does not define semantic equivalence between CAM-A22 request
> identifiers and CAM-A23 capability identifiers.**

No synonym mapping, alias table, ontology translation, fuzzy or prefix matching,
case-insensitive matching, semantic-version rules, Creation Studio version
interpretation, runtime discovery, network access, installation validation,
capability execution testing, or persisted reconciliation state.

## Future vocabulary alignment

If repeated reconciliation shows persistent namespace divergence, a later
**separately authorized** capability may define vocabulary alignment, aliases, or
semantic mappings.

CAM-A25's job is to make the divergence visible and measurable. Deciding what to
do about it is a different capability, and CAM-A25 must not preempt that
decision.
