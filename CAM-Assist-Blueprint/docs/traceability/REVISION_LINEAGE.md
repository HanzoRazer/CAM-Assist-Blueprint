# Revision Lineage

## Overview

Revision lineage is a portable, sidecar file that captures how a package's
manufacturing reasoning evolved across revisions, expressed as a supersession
graph — one or more chains of revisions linked by `supersedes` (forked lineage
with multiple roots is permitted). It travels alongside a strategy package
without mutating the source package contents. Array order is not significant;
the `supersedes` pointers define the relationships.

Lineage records a *narrative*: a sequence of human-declared revision checkpoints,
each optionally superseding a prior one, with a human summary of what changed.

## Scope: package-scoped, NOT artifact version control

Lineage is **scoped to the package**, not to individual traceability artifacts.

- A *revision* is a human-declared checkpoint in the package's manufacturing
  reasoning — not a version bump of a single artifact.
- Assumptions, risk assessments, and decision records may evolve at different
  rates. That differential evolution is captured by each revision's `summary`
  text and by optional `related_records` pointers to the artifacts associated
  with that revision.
- Lineage does **not** retain or reconstruct historical versions of assumption,
  risk, or decision sidecars. `related_records` points at *associated* files; it
  does not guarantee a file's historical state is preserved.

Lineage is therefore a narrative chain, not a versioning or governance system.
`record_version` is the record *format* version only — never a content-revision
counter.

## Authority Model

Lineage is **informational only**:

- It does not grant execution authority
- It does not constitute approval
- It does not modify the source package
- It does not bypass required human review

When present, the `authority` block must declare these constraints, and every flag
must be `true`:

```json
{
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true
  }
}
```

## File Format

```json
{
  "record_type": "cam_assist_revision_lineage",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
  "created_at": "2026-06-15T00:00:00Z",
  "revisions": [
    {
      "revision_id": "rev-1",
      "summary": "Initial manufacturing strategy review.",
      "revised_by": "Manufacturing Engineer"
    },
    {
      "revision_id": "rev-2",
      "supersedes": "rev-1",
      "summary": "Reduced depth of cut after thin-wall chatter risk flagged.",
      "revised_by": "Senior Reviewer",
      "related_records": {
        "risk_file": "ltb_vcarve_synthetic_example_risk.json"
      }
    }
  ],
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true
  }
}
```

Each revision requires `revision_id` (unique within the file) and `summary`.
Optional fields: `supersedes` (the `revision_id` this entry replaces; absent means
a root), `revised_by`, and `related_records` (optional pointers to
`assumptions_file` / `risk_file` / `decision_record_file`). Those pointers are
declaring-file-relative portable paths; see
`docs/integration/ARTIFACT_REFERENCE_PATHS.md`.

## Lineage Integrity

Validation enforces the structural integrity of the chain:

- `revision_id` values must be unique (no duplicates)
- `supersedes` must reference an existing `revision_id` (no dangling pointers)
- a revision may not supersede itself
- the supersession chain may not contain a cycle
- at least one **root** (a revision with no `supersedes`) must exist

A **forked** lineage (more than one root) is permitted but emits a *warning* — it
is flagged, not blocked. Treating forks as a hard error would move the system
toward workflow enforcement, which it does not do.

## Creating Lineage

```bash
python scripts/create_revision_lineage.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --revised-by "Manufacturing Engineer" \
  --summary "Initial manufacturing strategy review." \
  --out examples/traceability/ltb_vcarve_synthetic_example_lineage.json
```

The creator seeds a single root revision. Additional revisions are added by hand
(or by an upstream tool) as the package's reasoning evolves. `package_reference`
is resolved from the manifest's `federation.federated_package_id`, falling back to
the package directory name.

## Validating Lineage

```bash
python scripts/validate_revision_lineage.py \
  examples/traceability/ltb_vcarve_synthetic_example_lineage.json
```

Exit codes: `0` valid, `1` validation failed, `2` file/read error.

## Conventional Location

When no path is given explicitly, tools look for the sidecar at:

```text
<package_parent>/traceability/<package_name>_lineage.json
```

For packages under `examples/packages/<name>`, the convention is
`examples/traceability/<name>_lineage.json`.

The inspector reports the sidecar under the `Traceability:` section as
`revision lineage: present`. A decision record may reference a lineage sidecar via
`record_review_decision.py --lineage-file` (referenced, never mutated).
