# Risk Assessment

## Overview

Risk assessments are portable, sidecar files that capture known manufacturing risks
for a strategy package. They travel alongside the package without mutating its
contents.

Risk scoring is **informational only**. It records identified risks and an overall
risk level; it does not gate execution and grants no authority.

## Authority Model

- Risk assessments do not grant execution authority
- Risk scoring does not gate execution
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
  "record_type": "cam_assist_risk_assessment",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
  "created_at": "2026-06-14T00:00:00Z",
  "overall_risk": "medium",
  "risks": [
    {
      "category": "geometry",
      "severity": "warning",
      "description": "Thin wall section near soundhole may chatter at full feed."
    }
  ],
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true
  }
}
```

- `overall_risk` must be one of: `low`, `medium`, `high`.
- Each risk requires `category`, `severity`, and `description`. An optional
  `mitigation` may be added.
- Per-risk `severity` must be one of: `info`, `warning`, `concern`, `blocking`
  (consistent with review annotations).

## Creating a Risk Assessment

```bash
python scripts/create_risk_assessment.py \
  --package examples/packages/ltb_vcarve_synthetic_example --overall-risk medium \
  --risk geometry warning "Thin wall section near soundhole may chatter at full feed." \
  --out examples/traceability/risk_assessment_example.json
```

## Validating a Risk Assessment

```bash
python scripts/validate_risk_assessment.py \
  examples/traceability/risk_assessment_example.json
```

Exit codes: `0` valid, `1` validation failed, `2` file/read error.

## Conventional Location

```text
<package_parent>/traceability/<package_name>_risk.json
```

For packages under `examples/packages/<name>`, the convention is
`examples/traceability/<name>_risk.json`. The inspector reports the sidecar under
the `Traceability:` section.
