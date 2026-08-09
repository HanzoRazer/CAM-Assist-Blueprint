# Creation Studio Capability Profile

Record type: `creation_studio_capability_profile` · Version `1.0.0` · CAM-A23

## Purpose

The Creation Studio Capability Profile is a portable, **read-only capability
contract** published by the separate CAM-Creation-Studio product. It lets Creation
Studio declare, in machine-readable form, **what it is capable of authoring** —
strategy visualization, feeds & speeds authoring, tool library editing, G-code
tutorial generation, simulation support, post-processor education, machining
lesson playback, and whatever it adds next.

> The profile is **descriptive**. It records what Creation Studio *can author* —
> never what has been authored, approved, or executed. **No capability implies
> approval.**

CAM Assist references the profile for three things only:

```text
informational display        request compatibility checking        documentation
```

Never for execution decisions.

## The Second Integration Seam

CAM-A22 established *"what CAM Assist is asking Creation Studio to do."*
CAM-A23 establishes *"what Creation Studio declares it can do."*

```text
CAM Assist
    │  Creation Studio Request (CAM-A22)          outbound, advisory
    ▼
CAM-Creation-Studio
    │  Capability Profile (CAM-A23)               inbound, informational
    ▼
CAM Assist
```

Together they complete the first bidirectional **information exchange** between
the repositories while preserving the one-way flow of **authority**:

```text
Authority       CAM Assist       →  Manufacturing Strategy
Capability      Creation Studio  →  Authoring Features
```

Neither artifact transfers manufacturing authority, execution authority, or
machine approval. CAM Assist and CAM-Creation-Studio **remain separate
repositories**; CAM-A23 adds no runtime integration and no CAM-Creation-Studio
dependency.

## Ownership

| Owner | Owns |
| --- | --- |
| Creation Studio | capability declarations, supported authoring features, supported educational workflows |
| CAM Assist | manufacturing strategy, review, traceability, approvals |

The producer implementation lives in the CAM-Creation-Studio repository and is
**deferred** — the creator here exists so the contract is executable and testable
from this side.

## Profile Artifact

One profile per Creation Studio **installation/version**. It is **not**
package-specific, so the discovery filename is fixed:

```text
creation_studio/
    capability_profile.json
```

The profile carries **no `created_at` timestamp**: the artifact is deterministic
so that regenerating it (delete → recreate) yields byte-identical output.
Auditability of *when* a profile was published belongs to the surrounding workflow
(git, filesystem), not the artifact body.

```json
{
  "record_type": "creation_studio_capability_profile",
  "record_version": "1.0.0",
  "profile_version": "1.0.0",
  "studio_reference": "cam-creation-studio",
  "publication_direction": "creation_studio_to_cam_assist",
  "capabilities": [
    {
      "capability_id": "feeds_speeds_authoring",
      "display_name": "Feeds & Speeds Authoring"
    },
    { "capability_id": "strategy_visualization" }
  ],
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true,
    "does_not_confirm_machine_readiness": true,
    "does_not_require_capability_use": true
  }
}
```

A capability entry requires only `capability_id`. Optional `display_name`,
`description`, and `documentation_reference` are informational. The entry is a
**closed** object: no approval, readiness, or authorization field can ride along.

## Two Independent Versions

| Field | Owner | Tracks |
| --- | --- | --- |
| `record_version` | CAM Assist (this schema) | the record **format** |
| `profile_version` | CAM-Creation-Studio | the published **capability set** |

`profile_version` is semantic and **independent of the CAM Assist version**.
Creation Studio increments it as its authoring capabilities evolve.

## Capability Identifiers

Identifiers are constrained by **pattern**, not by enumeration:

```text
^[a-z][a-z0-9_]*$
```

This is the deliberate inversion of CAM-A22. There, `requested_capabilities` is a
closed enum because CAM Assist owns what it asks for. Here, Creation Studio owns
what it declares, and its capability set evolves on its own release cadence — a
closed enum would force a CAM Assist schema change for every upstream feature,
coupling the two repositories exactly where the contract exists to keep them
apart.

Compatibility rests instead on:

- **stable identifiers** — once published, an identifier is never renamed
  (renaming is a breaking change requiring a `profile_version` major bump);
- **semantic versioning** of the profile.

Representative identifiers:

```text
strategy_visualization        simulation_support
feeds_speeds_authoring        post_processor_education
tool_library_editing          machining_lesson_playback
gcode_tutorial_generation
```

### Identifier uniqueness

Vanilla JSON Schema cannot express "unique by object property." The schema
declares `uniqueItems: true` (which catches wholly duplicated entries) and the
**structural validator** enforces full `capability_id` uniqueness. The split is
deliberate and documented in both layers.

## Creating a Profile

```bash
python scripts/create_creation_studio_capability_profile.py --root examples \
  --capability strategy_visualization \
  --capability "Feeds & Speeds Authoring" \
  --capability tool_library_editing \
  --capability gcode_tutorial_generation \
  --capability simulation_support \
  --capability post_processor_education \
  --capability machining_lesson_playback \
  --force
```

Default output: `<root>/creation_studio/capability_profile.json` (`--root`
defaults to `.`; `--out` overrides the path entirely).

`--capability` accepts either a **stable identifier** (recorded as-is) or a
**human-readable name**, normalized mechanically — lowercased, with each run of
non-alphanumeric characters folded to a single underscore
(`"Feeds & Speeds Authoring"` → `feeds_speeds_authoring`). When the supplied name
differs from its normalized identifier, the original is preserved as
`display_name`, because it carried information the identifier does not; when the
caller already supplied the identifier, no redundant `display_name` is emitted.
Normalization is mechanical, not clever: a caller who needs an exact identifier
should pass that identifier. A name that cannot yield a valid identifier is
**refused** rather than mangled — published identifiers are meant to be stable
forever.

The committed example uses both forms on purpose, so the normalization rule is
exercised by a real artifact.

Other flags: `--profile-version` (Creation-Studio-owned capability-set version),
`--studio-reference` (which installation/version this profile describes),
`--capability-doc NAME=PATH` (attach a relative documentation reference).

### Determinism

- capabilities are **sorted** by `capability_id` — supply order is not an input;
- duplicates (including duplicates that arise from normalization) collapse;
- no `created_at`.

The same capability **set** always yields byte-identical output.

## Validating a Profile

```bash
python scripts/validate_creation_studio_capability_profile.py \
  examples/creation_studio/capability_profile.json
```

Structural validation is filesystem-free: it opens only the profile file and never
resolves declared documentation references. Exit codes: `0` valid, `1` invalid (or
parse error / non-object root), `2` file not found.

## Completeness Witness

```bash
python scripts/validate_creation_studio_capability_profile.py \
  examples/creation_studio/capability_profile.json --check-references
```

An opt-in **existence** witness: for each declared `documentation_reference`, it
warns when the path does not resolve relative to the profile file's directory.
Existence only — it never opens, parses, or schema-checks a referenced file, and
reports no absent-reference findings (an omitted reference is allowed and silent).
Warnings never change validity or the exit code unless
`--fail-on-reference-warnings` is also given (which promotes unresolved references
to errors for CI).

## Inspector Detection

```bash
python scripts/inspect_strategy_package.py examples/packages/ltb_vcarve_synthetic_example
```

The inspector reports presence only:

```text
Creation Studio Capability Profile:
  present (detected, not validated)
```

It looks for an explicit `--capability-profile <path>` first, then the
conventional `creation_studio/capability_profile.json`. Detection only — it never
opens, parses, validates, or reads which capabilities are declared, and it never
echoes them. Because a profile is per-installation rather than per-package, one
profile serves every package under the same root.

The `(detected, not validated)` wording is deliberate: presence means a file was
found at the expected path, **not** that it is structurally valid and **not** that
any capability applies to the package being inspected. Run
`validate_creation_studio_capability_profile.py` for structural validity.

## Authority Model

The profile is **informational only.** The required authority block declares five
const-`true` flags:

| Flag | Meaning |
| --- | --- |
| `is_informational` | the record is informational only |
| `does_not_authorize_execution` | it does not authorize machine execution |
| `does_not_bypass_human_review` | it does not bypass required human review |
| `does_not_confirm_machine_readiness` | a declared capability asserts nothing about machine readiness |
| `does_not_require_capability_use` | declaring a capability never obliges or pre-selects CAM Assist to use it |

The block is **closed**: an undeclared flag — most importantly a contradictory,
execution-granting one — is rejected by both the schema and the validator.

## Non-Execution Doctrine

The capability profile never:

```text
authorizes execution        validates machining        approves strategies
requests execution          confirms machine readiness becomes manufacturing authority
```

Capability selection is never automatic. A declared capability is not a promise
about any particular package, not an endorsement of any strategy, and not a claim
that the capability's output is authoritative. CAM Assist remains upstream of
execution, and human review remains required.

## What CAM-A23 Does Not Do

```text
import strategies                    bidirectional synchronization
execution approval                   machine control
feeds & speeds generation            G-code generation
simulation execution                 controller integration
runtime negotiation                  automatic capability selection
```

Integration is **not** complete until a producer exists in the
CAM-Creation-Studio repository. The contract exists so that when it does, the
boundary between **manufacturing intent** and **manufacturing authoring** is
already explicit.
