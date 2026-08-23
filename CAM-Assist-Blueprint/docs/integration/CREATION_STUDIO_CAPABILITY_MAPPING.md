# Creation Studio Capability Mapping (CAM-A26)

Record type: `cam_assist_creation_studio_capability_map` · Format `1.0.0` · Map `1.0.0`

## Purpose

CAM-A25 compares CAM-A22 request identifiers to CAM-A23 declared identifiers by
**exact equality**. The shipped vocabularies share none. CAM-A26 is the
explicit, reviewable bridge that says which Creation Studio capabilities CAM
Assist will treat as satisfying which request categories.

```text
A22 requested outcome
        ↓
explicit A26 mapping
        ↓
A23 declared Creation Studio capability
```

A mapping is a human decision recorded in a contract. It is never inferred
from names, never scored, and never generated.

## Ownership

| Owner | Owns |
| --- | --- |
| CAM Assist | A22 request identifiers, and therefore this map |
| Creation Studio | A23 capability identifiers (open vocabulary) |

The map lives in this repository because only CAM Assist can say what satisfies
its own request vocabulary. A23 does not need to change when CAM Assist
changes mapping policy.

Canonical registry:

```text
contracts/creation_studio_capability_map.json
```

There was no prior `contracts/` directory. CAM-A26 introduces it for
CAM-Assist-owned non-example policy artifacts. The file is hand-authored.

## What a mapping means

> CAM Assist has explicitly decided that a declared Creation Studio capability
> may satisfy a particular CAM Assist request category for
> **compatibility-reporting purposes**.

It does **not** mean:

```text
the capability is installed
the capability is reachable
the capability performed successfully
the resulting machining plan is correct
the machine is ready
a human approved execution
execution is authorized
```

## Contract

```json
{
  "record_type": "cam_assist_creation_studio_capability_map",
  "record_version": "1.0.0",
  "map_version": "1.0.0",
  "mappings": [
    {
      "request_capability": "simulation_request",
      "satisfied_by": ["simulation_support"],
      "rationale": "…"
    }
  ],
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true,
    "does_not_confirm_machine_readiness": true,
    "does_not_grant_permission": true
  }
}
```

Rules:

* `request_capability` must be a member of the A22 `requested_capabilities`
  enum in `schemas/creation_studio_request.schema.json`. The map schema does
  not copy that enum.
* `satisfied_by` is a non-empty unique list of A23-pattern identifiers
  (`^[a-z][a-z0-9_]*$`). The vocabulary stays open. A target need not appear
  in the supplied profile.
* `rationale` is required and non-blank.
* One request may map to many targets (`any_of`). One target may satisfy many
  requests.
* Duplicate source rows, and duplicate targets inside one row, are errors.
* `record_version` and `map_version` are surfaced, never interpreted.

## Initial registry

The first `map_version` is deliberately conservative. Only correspondences
that were already named as A25 near-misses or exemplified by the A26 handoff
are recorded:

```text
feeds_speeds_recommendation  →  feeds_speeds_authoring
simulation_request           →  simulation_support
gcode_explanation            →  gcode_tutorial_generation
                             →  post_processor_education
```

Unmapped A22 identifiers remain unsatisfied unless an exact A23 declaration
appears. That is the intended statement, not a gap in the reconciler.

## Validating a map

```bash
python scripts/validate_creation_studio_capability_map.py \
  contracts/creation_studio_capability_map.json
```

Structural only. Loading and indexing live in
`scripts/_shared/creation_studio_capability_map.py`; the validator and
reconciler are thin adapters and do not import one another. The shared
module does not walk the filesystem at import time; the A22 schema path is
resolved on first use.

Exit codes:

```text
0  structurally valid
1  invalid map content (including unparseable map JSON)
2  map file missing/unreadable, or authoritative A22 schema
   missing/unreadable/malformed
```

## Using a map in reconciliation

Exact matching remains the default. Mapping is opt-in:

```bash
python scripts/reconcile_creation_studio_capabilities.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --capability-map contracts/creation_studio_capability_map.json
```

Without `--capability-map`, CAM-A25 behaviour is unchanged.

With the flag:

* exact identifier matches are classified `exact` and win over a mapping
* remaining requests are satisfied only when the map names a declared target
* `namespace_divergence` still reports the **raw exact intersection**
* `mapped_compatibility` is added when at least one request is satisfied by
  mapping
* `declared_but_unrequested` remains `declared − requested`
* JSON adds `inputs.capability_map` and `satisfaction_details`

Human matches are labelled:

```text
[MATCH: exact]
simulation_support

[MATCH: mapped]
simulation_request
  → simulation_support
```

`--fail-on-unsatisfied` still keys only on unresolved `unsatisfied`.

A missing or structurally invalid map is an input failure for the reconciler
(exit 2, empty stdout under `--json`). Blank or whitespace-only request and
profile identifiers are rejected at the structural-minimum boundary; full
A22/A23 validation remains the dedicated validators' job. Map provenance
paths are POSIX-normalized without being absolutized, so equivalent relative
spellings collapse.

## Relationship to A22 / A23 / A25

```text
A22   closed request vocabulary          unchanged
A23   open declaration vocabulary        unchanged
A25   exact set comparison               default, unchanged
A26   explicit semantic bridge           opt-in third input
```

CAM-A25 does not define semantic equivalence. CAM-A26 does — and only for
rows written in the map.

The result is still ephemeral. Nothing is written to disk. No Creation Studio
runtime is contacted.

## Authority

A mapped match is an explicit compatibility declaration, not authorization.
Human authority over manufacturing decisions is unchanged.
