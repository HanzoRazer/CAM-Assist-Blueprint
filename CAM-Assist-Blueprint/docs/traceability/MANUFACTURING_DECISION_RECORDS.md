# Manufacturing Decision Records

## Overview

A manufacturing decision record (MDR) is a portable, sidecar file that captures
*why* a manufacturing decision was made and *who* prepared and reviewed it. It
travels alongside a strategy package without mutating the package or any linked
sidecars.

An MDR captures a **human declaration**. It does not enforce approval authority and
does not authorize machine execution. Approval authority is not enforced by CAM
Assist — the record documents a decision; it does not gate one.

## Authority Model

- The record is a human declaration, not an enforcement mechanism
- It does not authorize machine execution
- It does not bypass required human review
- It does not mutate the package or linked traceability sidecars

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
  "record_type": "cam_assist_manufacturing_decision_record",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
  "created_at": "2026-06-14T00:00:00Z",
  "prepared_by": "Manufacturing Engineer",
  "reviewed_by": "Senior Reviewer",
  "decision": "approved",
  "rationale": "Tooling, fixturing, and material assumptions reviewed against identified risks.",
  "assumptions_file": "examples/traceability/manufacturing_assumptions_example.json",
  "risk_file": "examples/traceability/risk_assessment_example.json",
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true
  }
}
```

Required fields: `record_type`, `record_version`, `package_reference`, `prepared_by`,
`reviewed_by`, `decision`, `rationale`.

`decision` must be one of: `approved`, `needs_revision`, `rejected`.

`assumptions_file` and `risk_file` are optional references to the assumptions and
risk-assessment sidecars that informed the decision. They are referenced only; the
linked files are never modified.

## Creating a Decision Record

```bash
python scripts/create_manufacturing_decision_record.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --decision approved --prepared-by "Manufacturing Engineer" \
  --reviewed-by "Senior Reviewer" \
  --rationale "Tooling, fixturing, and material assumptions reviewed against identified risks." \
  --assumptions-file examples/traceability/manufacturing_assumptions_example.json \
  --risk-file examples/traceability/risk_assessment_example.json \
  --out examples/traceability/manufacturing_decision_record_example.json
```

## Validating a Decision Record

```bash
python scripts/validate_manufacturing_decision_record.py \
  examples/traceability/manufacturing_decision_record_example.json
```

Exit codes: `0` valid, `1` validation failed, `2` file/read error.

## Linking from a Review Decision

`record_review_decision.py` can reference the traceability sidecars that informed a
review decision, without mutating them:

```bash
python scripts/record_review_decision.py <package_dir> \
  --decision approve_for_downstream_cam --reviewer "Human Reviewer" \
  --assumptions-file examples/traceability/manufacturing_assumptions_example.json \
  --risk-file examples/traceability/risk_assessment_example.json
```

## Conventional Location

```text
<package_parent>/traceability/<package_name>_decision_record.json
```

For packages under `examples/packages/<name>`, the convention is
`examples/traceability/<name>_decision_record.json`. The inspector reports the
sidecar under the `Traceability:` section.

## Related

- `MANUFACTURING_ASSUMPTIONS.md`
- `RISK_ASSESSMENT.md`
