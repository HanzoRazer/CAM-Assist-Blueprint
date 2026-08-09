# Dev Order — CAM-A23

## Creation Studio Capability Profile (Read-Only Capability Contract)

## Scope

Define the **second integration seam** between CAM Assist Blueprint and the
separate CAM-Creation-Studio repository, completing the pair started by CAM-A22.

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

Together the two artifacts form a **bidirectional information exchange** while
preserving a strictly **one-way flow of authority**. Neither transfers
manufacturing authority, execution authority, or machine approval.

CAM-A23 does **not** merge the repositories, add runtime integration, or
introduce a CAM-Creation-Studio dependency.

## Core Objective

> Does CAM Assist now have a stable, read-only contract for understanding what
> CAM-Creation-Studio is capable of, without granting it any manufacturing or
> execution authority?

The profile is **descriptive**: it records what Creation Studio is capable of
*authoring*, never what has been authored, approved, or executed. CAM Assist
consumes it only for informational display, request compatibility checking, and
documentation — never for execution decisions.

## New Artifact

| Field | Value |
| --- | --- |
| Canonical name | Creation Studio Capability Profile |
| Record type | `creation_studio_capability_profile` |
| Record version | `1.0.0` |
| Direction | `creation_studio_to_cam_assist` (inbound publication only) |
| Authority | Informational only; five const-true non-authority flags |
| Discovery | `creation_studio/capability_profile.json` |

## Design Decisions

| Decision | Outcome |
| --- | --- |
| Ownership | Creation Studio owns capability declarations; CAM Assist owns strategy, review, traceability, approvals |
| Direction | One-way publication (Creation Studio → CAM Assist) |
| Reference model | Reference-only; no imported executable artifacts |
| Scope of a profile | One per Creation Studio installation/version — **not** package-specific |
| Capability vocabulary | **Open** (pattern-constrained identifiers), not a closed enum |
| Profile versioning | Semantic; independent of the CAM Assist version |
| Machine execution | Forbidden |
| Capability use | Never required by the profile |
| Existing packages | Not mutated |
| CAM-Creation-Studio dependency | None |
| Producer implementation | Lives in the CAM-Creation-Studio repo; deferred |

### Why the vocabulary is open (unlike CAM-A22)

CAM-A22's `requested_capabilities` is a **closed enum** because CAM Assist owns
what it asks for. CAM-A23 inverts ownership: Creation Studio owns what it
declares, and its capability set evolves on its own release cadence. A closed
enum here would force a CAM Assist schema change for every Creation Studio
feature — coupling the two repositories exactly where the contract exists to keep
them apart.

The compatibility risk is instead mitigated by **stable identifiers** (a
`^[a-z][a-z0-9_]*$` pattern, never renamed once published) plus **semantic
versioning** of the profile.

### `created_at` is intentionally omitted

As with CAM-A22, the record carries **no `created_at` timestamp**. The
tool-generated example must regenerate **byte-identically**
(`delete → regenerate → diff clean`), and a wall-clock stamp would defeat that on
every run. The profile is a reproducible capability declaration, not an audit
record; auditability of *when* a profile was published belongs to the surrounding
workflow (git, filesystem mtime), not the artifact body.

### Identifier uniqueness is enforced by the validator

Vanilla JSON Schema cannot express "unique by object property." The schema
declares `uniqueItems: true` (which catches wholly duplicated entries) and the
structural validator enforces full `capability_id` uniqueness. This split is
deliberate and documented in both layers.

## Artifact Shape

```json
{
  "record_type": "creation_studio_capability_profile",
  "record_version": "1.0.0",
  "profile_version": "1.0.0",
  "studio_reference": "cam-creation-studio",
  "publication_direction": "creation_studio_to_cam_assist",
  "capabilities": [
    {"capability_id": "feeds_speeds_authoring", "display_name": "Feeds & Speeds Authoring"},
    {"capability_id": "strategy_visualization"}
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
`description`, and `documentation_reference` (a relative path) are informational.

## Capability Categories

The profile records only **declared support**. Representative identifiers:

```text
strategy_visualization        simulation_support
feeds_speeds_authoring        post_processor_education
tool_library_editing          machining_lesson_playback
gcode_tutorial_generation
```

**No capability implies approval.** A declared capability is not a promise about
any particular package, is not an endorsement of a strategy, and does not make
the capability's output authoritative.

## Schema Requirements

- Required top-level: `record_type`, `record_version`, `profile_version`,
  `studio_reference`, `publication_direction`, `capabilities`, `authority`.
- Constants: `record_type == creation_studio_capability_profile`,
  `publication_direction == creation_studio_to_cam_assist`.
- `record_version` and `profile_version`: semantic version strings.
- `capabilities`: array, ≥1 entry, `uniqueItems`; each entry a closed object
  requiring a pattern-valid `capability_id`.
- `documentation_reference`: relative path only (no absolute or drive-rooted
  path) — same portability rule as CAM-A22's content references.
- `authority` required; all five flags const-`true`; closed (no undeclared flags).
- Closed top-level contract (`additionalProperties: false`).
- No `created_at`.

## Boundary Invariants

The profile is descriptive, informational, and advisory. It never authorizes
execution, requests execution, validates machining, approves strategies, or
becomes manufacturing authority.

```text
Authority       CAM Assist  →  Manufacturing Strategy
Capability      Creation Studio  →  Authoring Features
```

CAM Assist consumes the profile for informational display, request compatibility
checking, and documentation **only**. The inspector detects the profile without
parsing it. No consumer logic infers execution readiness from a capability.

## Rollout (phased)

1. Dev order (this file).
2. Schema + schema tests.
3. Structural validator + tests (filesystem-free).
4. Creator + tests (deterministic, sorted capability list).
5. Tool-generated example + regression tests (byte-identical regeneration).
6. Inspector detection (`--capability-profile`) + tests (detection only).
7. Documentation (integration doc; README) + final full regression.

## Completion Criteria

Schema, creator, validator, tool-generated example, inspector detection, and
documentation all exist; the generated profile validates; the inspector detects
the profile without parsing its contents; README updated; no execution authority
introduced; full suite passes.
