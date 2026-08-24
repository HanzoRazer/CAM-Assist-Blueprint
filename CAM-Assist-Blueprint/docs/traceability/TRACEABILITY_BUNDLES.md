# Traceability Bundles

## Overview

A traceability bundle is a portable, sidecar file that aggregates a package's
traceability records — manufacturing assumptions, risk assessment, manufacturing
decision record, review annotations, and revision lineage — into a single
reference-only artifact. It lets an entire manufacturing review story move
between systems as one unit, and lets a reviewer ask *"do we possess a complete
traceability story?"*

The bundle travels alongside a strategy package without mutating it.

## Scope: navigational index, NOT a source of truth

A bundle is a **navigational index**, not an authoritative record.

- The bundle **references** the traceability sidecars; it does not own, copy,
  cache, or supersede their content.
- The referenced **sidecars remain authoritative**. To read what was assumed,
  what risks were identified, or why a decision was made, you read the sidecar —
  not the bundle.
- Letting a bundle carry or duplicate record data would invert the dependency
  (`bundle owns records`) and is explicitly out of scope.

## Authority Model

A bundle is **informational only**:

- It does not grant execution authority
- It does not constitute approval
- It does not modify the source package
- It does not bypass required human review
- It does not enforce workflow or governance

When present, the `authority` block must declare these constraints, and every
flag must be `true`:

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
  "record_type": "cam_assist_traceability_bundle",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
  "created_at": "2026-06-20T00:14:32.066221Z",
  "bundle_contents": {
    "assumptions_file": "ltb_vcarve_synthetic_example_assumptions.json",
    "risk_file": "ltb_vcarve_synthetic_example_risk.json",
    "decision_record_file": "ltb_vcarve_synthetic_example_decision_record.json",
    "lineage_file": "ltb_vcarve_synthetic_example_lineage.json",
    "annotations_file": "../review_annotations/ltb_vcarve_synthetic_example_annotations.json"
  },
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true
  }
}
```

Required: `record_type`, `record_version`, `package_reference`, `bundle_contents`.
Optional: `created_at`, `authority`.

`bundle_contents` is an object whose keys are drawn from a fixed set of known
slots; each value is a string path **reference**, resolved relative to the
bundle file's own location (the canonical declaring-file-relative rule in
`docs/integration/ARTIFACT_REFERENCE_PATHS.md`). The known slots are:

| Slot | References |
| --- | --- |
| `assumptions_file` | a manufacturing assumptions sidecar |
| `risk_file` | a risk assessment sidecar |
| `decision_record_file` | a manufacturing decision record sidecar |
| `annotations_file` | a review annotations sidecar |
| `lineage_file` | a revision lineage sidecar |

All slots are optional and `bundle_contents` may be empty — **missing sidecars
are allowed**. Unknown slot names are rejected.

## Discovery Convention

When no path is given explicitly, tools look for the bundle at:

```text
<package_parent>/traceability/<package_name>_bundle.json
```

For packages under `examples/packages/<name>`, the convention is
`examples/traceability/<name>_bundle.json`.

The creator discovers sidecars at the same conventional locations the inspector
uses:

```text
traceability/<package>_assumptions.json       -> assumptions_file
traceability/<package>_risk.json              -> risk_file
traceability/<package>_decision_record.json   -> decision_record_file
traceability/<package>_lineage.json           -> lineage_file
review_annotations/<package>_annotations.json -> annotations_file
```

Each discovered file is recorded as a path relative to the bundle output
file (forward-slashed); absent sidecars are omitted. See
`docs/integration/ARTIFACT_REFERENCE_PATHS.md`.

## Creating a Bundle

```bash
python scripts/create_traceability_bundle.py \
  --package examples/packages/ltb_vcarve_synthetic_example
```

The creator auto-discovers the conventionally-located sidecars and records a
reference to each one found. Use `--empty` to seed an empty `bundle_contents`
without scanning (for hand-authoring), and `--force` to overwrite an existing
bundle. The source package is never modified.

## Validation

**Structural validity and reference completeness are separate concerns**, and a
`PASS` speaks only to the first unless you opt in to the second:

- **Structural validity** — the bundle record conforms to the required contract.
- **Reference completeness** — each declared path in `bundle_contents` resolves
  on disk.

A structurally valid bundle is **not** by itself a statement that its references
exist. Validation has two layers.

### Structural validation (default)

```bash
python scripts/validate_traceability_bundle.py \
  examples/traceability/ltb_vcarve_synthetic_example_bundle.json
```

```text
PASS: traceability bundle is structurally valid
```

The structural layer is **filesystem-free**: it opens only the bundle file and
checks `record_type`, `record_version`, a non-empty `package_reference`, the
`bundle_contents` object shape (known slots only, string values), and the
`authority` block when present. A bundle whose references do not exist still
passes structurally — reference existence is a *completeness* concern, not a
structural one.

The record is a **closed contract**: both the JSON Schema and the structural
validator reject any unrecognized top-level field and any undeclared flag inside
`authority`, so a stray or contradictory flag cannot ride along. `created_at` and
`authority` remain optional but recognized.

### Completeness witness (`--check-references`)

```bash
python scripts/validate_traceability_bundle.py \
  examples/traceability/ltb_vcarve_synthetic_example_bundle.json \
  --check-references
```

The opt-in completeness layer resolves each **declared** reference relative to
the bundle file's own directory using the shared declaring-file-relative rule.
`--base <dir>` is an explicit operator override of that resolution directory,
not a silent repository-root fallback. Completeness findings are **warnings**:

- a declared reference that **does not resolve** on disk;
- a known sidecar slot that is **absent** from `bundle_contents` (an omission —
  e.g. `completeness: annotations_file not present in bundle`);
- a resolved sidecar whose own `package_reference` **differs** from the
  bundle's (a cross-artifact consistency finding).

For the consistency check the layer performs a single **best-effort** read of
each resolved sidecar to compare its `package_reference`; it does **not**
otherwise open, parse, or validate sidecar contents, and it mutates nothing.
Parse failures during this read are ignored — validating a sidecar's structure
is that sidecar's own validator's job.

Completeness findings are **warnings only**: they never change structural
validity, and by default never change the exit code. A structurally valid bundle
with omissions, unresolved references, or a reference mismatch still exits `0`.

### `--fail-on-reference-warnings` (CI enforcement)

For automation that must treat a bundle pointing at missing files as a failure,
add `--fail-on-reference-warnings` alongside `--check-references`:

```bash
python scripts/validate_traceability_bundle.py \
  examples/traceability/ltb_vcarve_synthetic_example_bundle.json \
  --check-references --fail-on-reference-warnings
```

This escalates **only unresolved declared references** to errors (exit `1`).
Omissions (a missing sidecar is allowed by design) and `package_reference`
mismatches deliberately **remain advisory** — they never fail the run. The flag
changes nothing else: default behavior is unchanged, no structural rule is
altered, and it has no effect without `--check-references`.

Exit codes: `0` structurally valid (and, in strict mode, declared references
resolved), `1` validation failed, `2` file/read error.

## Inspector Behavior

The inspector reports the bundle under its own section, as **detection only**:

```text
Traceability Bundle:
  present
```

or:

```text
Traceability Bundle:
  not declared
```

The inspector is a **discovery surface**, not a validator. It does not open,
parse, validate, or completeness-check the bundle — a bundle with unparseable
contents is still reported as `present`. `present` means only that a bundle file
was found at the resolved path; it is **not** a claim that the bundle is
structurally valid or that its references resolve. Those are separate questions:
use the validator for structural validity and `--check-references` for
completeness. An explicit path may be supplied with `--bundle`; otherwise the
conventional location is used.

## Non-Execution Doctrine

A traceability bundle never authorizes machine execution, never constitutes
approval, never enforces workflow, and never modifies a package. It is a
navigational index over authoritative, informational sidecars. Human review
remains required before any downstream CAM use.
