# Synthetic V-Carve Workflow — Expected Outputs

Running `scripts/run_cam_assist_demo.py` performs the following steps in order,
each a real public CLI invoked as a subprocess. A non-zero exit from any step
aborts the run.

## Steps

| # | Step | Script |
| --- | --- | --- |
| 1 | `import_strategy` | `import_ltb_cam_output.py` |
| 2 | `validate_strategy` | `validate_strategy_package.py` |
| 3 | `generate_review_packet` | `generate_review_packet.py` |
| 4 | `assemble_package` | `assemble_strategy_package.py` |
| 5 | `inspect_package` | `inspect_strategy_package.py` |
| 6 | `archive_package` | `archive_strategy_package.py` |
| 7 | `validate_archive` | `validate_package_archive.py` |
| 8 | `stage_package` | `stage_strategy_package.py` |
| 9 | `review_queue` | `index_staged_packages.py` |
| 10 | `record_review_decision` | `record_review_decision.py` |
| 11 | `review_annotations` | `create_review_annotations.py` |
| 12 | `manufacturing_assumptions` | `create_manufacturing_assumptions.py` |
| 13 | `risk_assessment` | `create_risk_assessment.py` |
| 14 | `decision_record` | `create_manufacturing_decision_record.py` |
| 15 | `revision_lineage` | `create_revision_lineage.py` |
| 16 | `traceability_bundle` | `create_traceability_bundle.py` |
| 17 | `validate_bundle` | `validate_traceability_bundle.py` |
| 18 | `production_shop_handoff` | `create_production_shop_handoff.py` |
| 19 | `validate_handoff` | `validate_production_shop_handoff.py` |
| 20 | `inspect_final` | `inspect_strategy_package.py` |
| 21 | `verify_non_execution_invariant` | `verify_non_execution_invariant.py` |

## Artifacts (relative to the workspace)

```text
strategy.json
package/strategy.json
package/review_packet.md
package/manifest.json
package.zip
staged/package/                                (staged copy)
staged/package.review_decision.json
review_annotations/package_annotations.json
traceability/package_assumptions.json
traceability/package_risk.json
traceability/package_decision_record.json
traceability/package_lineage.json
traceability/package_bundle.json
production_shop/package_handoff.json
demo_summary.json
```

## Demo summary

The runner writes `demo_summary.json` — a demonstration report (not a product
contract; no schema). Its shape:

```json
{
  "record_type": "cam_assist_demo_summary",
  "record_version": "1.0.0",
  "status": "passed",
  "input": "synthetic_vcarve_ltb_output.json",
  "steps": [
    { "name": "import_strategy", "exit_code": 0, "status": "passed" }
  ],
  "artifacts": { "strategy": "strategy.json" },
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_confirm_machine_readiness": true,
    "does_not_generate_gcode": true
  }
}
```

The generated sidecars carry their own creation timestamps, so byte-for-byte
output is not identical between runs; the **step sequence, artifact set, and
non-execution authority** are what remain stable.
