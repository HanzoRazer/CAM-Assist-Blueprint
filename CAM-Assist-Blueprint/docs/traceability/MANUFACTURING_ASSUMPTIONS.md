# Manufacturing Assumptions

## Overview

Manufacturing assumptions are portable, sidecar files that capture the assumptions
which influenced a manufacturing decision. They travel alongside strategy packages
without mutating the source package contents.

Assumptions record *reasoning*, not authorization. They explain what was taken for
granted (about tooling, material, fixturing, geometry) when a decision was made.

## Authority Model

Assumptions are **informational only**:

- They do not grant execution authority
- They do not constitute approval
- They do not modify the source package
- They do not bypass required human review

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
  "record_type": "cam_assist_manufacturing_assumptions",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
  "created_at": "2026-06-14T00:00:00Z",
  "assumptions": [
    {
      "category": "tooling",
      "statement": "Tool rigidity is adequate for selected depth of cut."
    },
    {
      "category": "material",
      "statement": "Material certification supplied by customer."
    }
  ],
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true
  }
}
```

Each assumption requires `category` and `statement`. An optional `rationale` may be
added.

## Creating Assumptions

```bash
python scripts/create_manufacturing_assumptions.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --assumption tooling "Tool rigidity is adequate for selected depth of cut." \
  --assumption material "Material certification supplied by customer." \
  --out examples/traceability/ltb_vcarve_synthetic_example_assumptions.json
```

`package_reference` is resolved from the package manifest's
`federation.federated_package_id`, falling back to the package directory name.

## Validating Assumptions

```bash
python scripts/validate_manufacturing_assumptions.py \
  examples/traceability/ltb_vcarve_synthetic_example_assumptions.json
```

Exit codes: `0` valid, `1` validation failed, `2` file/read error.

## Conventional Location

When no path is given explicitly, tools look for the sidecar at:

```text
<package_parent>/traceability/<package_name>_assumptions.json
```

For packages under `examples/packages/<name>`, the convention is
`examples/traceability/<name>_assumptions.json`.

The inspector reports the sidecar under the `Traceability:` section. See
`MANUFACTURING_DECISION_RECORDS.md` for how assumptions link into a decision.
