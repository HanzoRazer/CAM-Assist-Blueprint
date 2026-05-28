# Federated Review Annotations

## Overview

Review annotations are portable, sidecar files that carry reviewer observations
across federated manufacturing workflows. They travel alongside strategy packages
without mutating the source package contents.

**Constitutional principle:** CAM Assist is a federal courier, not emperor.
Annotations transport information — they do not create or transfer authority.

## Authority Model

Annotations are **informational only**:

- Annotations do not grant execution authority
- Annotations do not constitute approval
- Annotations do not modify the source package
- Annotations require explicit authority declarations

Every annotations file must include:

```json
{
  "record_type": "cam_assist_review_annotations",
  "record_version": "1.0.0",
  "authority": {
    "annotations_are_informational": true
  }
}
```

## File Format

Annotations use a JSON sidecar pattern:

```json
{
  "record_type": "cam_assist_review_annotations",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:rosette-001",
  "created_at": "2026-05-28T00:00:00Z",
  "authority": {
    "annotations_are_informational": true
  },
  "annotations": [
    {
      "annotation_id": "ann-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "reviewer": "acoustic-review-agent",
      "jurisdiction": "acoustic_review",
      "timestamp": "2026-05-28T00:00:00Z",
      "severity": "warning",
      "category": "acoustic",
      "message": "V-carve depth may affect resonance.",
      "recommended_action": "Verify with master luthier."
    }
  ]
}
```

### Package Reference

The `package_reference` field accepts multiple formats:

- **Federated ID:** `origin-system:domain:local-id` (preferred)
- **Relative path:** `../packages/my_package`
- **Package name:** `ltb_vcarve_synthetic_example`

When using the creation CLI, federated package ID is auto-detected from
the package manifest if available.

### Severity Levels

| Level      | Meaning                                            |
|------------|---------------------------------------------------|
| `info`     | Informational note, no action required            |
| `warning`  | Potential issue, warrants attention               |
| `concern`  | Significant issue, should be addressed            |
| `blocking` | Critical issue, must be resolved before proceeding |

### Annotation ID Format

Each annotation has a unique identifier: `ann-<uuid>`

Example: `ann-a1b2c3d4-e5f6-7890-abcd-ef1234567890`

### Categories

Categories are free-text but common values include:

- `tooling` — bit selection, speeds, feeds
- `geometry` — dimensions, tolerances, clearances
- `acoustic` — tonal impact, resonance considerations
- `safety` — depth limits, material stress
- `material` — species-specific concerns
- `review` — general review observations

## CLI Usage

### Creating Annotations

```bash
python scripts/create_review_annotations.py \
    --package examples/packages/ltb_vcarve_synthetic_example \
    --reviewer "acoustic-review-agent" \
    --severity warning \
    --category acoustic \
    --message "V-carve depth may affect resonance" \
    --recommended-action "Verify with master luthier"
```

Optional flags:

- `--jurisdiction <text>` — review jurisdiction (e.g., `manufacturing_review`)
- `--out <path>` — custom output path
- `--force` — overwrite existing file instead of appending
- `--quiet` — output only the annotation ID

### Validating Annotations

```bash
python scripts/validate_review_annotations.py \
    examples/review_annotations/ltb_vcarve_synthetic_example_annotations.json
```

### Inspecting with Annotations

```bash
python scripts/inspect_strategy_package.py \
    examples/packages/ltb_vcarve_synthetic_example \
    --annotations examples/review_annotations/ltb_vcarve_synthetic_example_annotations.json
```

## File Location Convention

Annotations follow a predictable path convention:

```
examples/
├── packages/
│   └── ltb_vcarve_synthetic_example/
│       ├── manifest.json
│       └── strategy.json
└── review_annotations/
    └── ltb_vcarve_synthetic_example_annotations.json
```

When `--out` is not specified, annotations are created at:
`<package_parent>/review_annotations/<package_name>_annotations.json`

## Integration with Review Decisions

Annotation files can be referenced in review decision records:

```json
{
  "decision_id": "dec-...",
  "annotation_files": [
    "review_annotations/ltb_vcarve_synthetic_example_annotations.json"
  ]
}
```

This links the decision to the annotations that informed it, without
embedding the annotations or granting them additional authority.

## Schema

See `schemas/review_annotations.schema.json` for the complete JSON Schema.

## Non-Execution Guarantee

Annotations explicitly disclaim execution authority:

1. `record_type: cam_assist_review_annotations` — artifact identity
2. `annotations_are_informational: true` — observations only
3. Sidecar pattern — source package is never modified
4. No toolpath data — annotations carry text, not G-code

A downstream system that treats annotations as execution authority
is violating the federation protocol.
