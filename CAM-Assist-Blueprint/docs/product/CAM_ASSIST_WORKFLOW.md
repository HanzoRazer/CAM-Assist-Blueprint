# CAM Assist End-to-End Workflow

This guide walks the complete CAM Assist workflow using the canonical synthetic
V-Carve example and **real repository commands**. Every command below is exercised
by the demonstration runner (`scripts/run_cam_assist_demo.py`) and the test suite,
so the workflow reflects executable reality rather than description.

> Reproduce the entire flow in one command:
>
> ```bash
> python scripts/run_cam_assist_demo.py --workspace .tmp/cam_assist_demo --keep
> ```
>
> The steps below are what that runner performs, in order.

Throughout, `WS` is a scratch workspace and `WS/package` is the assembled package.
Sidecars (traceability, annotations, handoff) are written to conventional sibling
directories of the package (`WS/traceability/`, `WS/review_annotations/`,
`WS/production_shop/`), which is how the inspector later discovers them.

Non-execution holds at every step: no command generates G-code, executes a
machine, or claims machine readiness.

## Preliminary — Import manufacturing intent

The workflow begins from an LTB CAM output (the manufacturing intent). Import it
into a CAM Assist strategy:

```bash
python scripts/import_ltb_cam_output.py \
  examples/ltb_import/synthetic_vcarve_ltb_output.json \
  --out WS/strategy.json
```

## 1. Validate strategy

```bash
python scripts/validate_strategy_package.py WS/strategy.json
```

Structural, non-executing validation of the strategy against the canonical schema.

## 2. Generate review packet

```bash
python scripts/generate_review_packet.py WS/strategy.json --out WS/review_packet.md
```

Produces a human-readable, advisory review packet. No G-code, no toolpaths.

## 3. Assemble package

```bash
python scripts/assemble_strategy_package.py WS/strategy.json --out WS/package
```

Assembles `strategy.json`, `review_packet.md`, and `manifest.json` into a portable
package directory.

## 4. Inspect package

```bash
python scripts/inspect_strategy_package.py WS/package
```

Read-only inspection: type, operation summary, authority status, file presence.

## 5. Archive package

```bash
python scripts/archive_strategy_package.py WS/package --out WS/package.zip
```

## 6. Validate archive

```bash
python scripts/validate_package_archive.py WS/package.zip
```

## 7. Stage archive

```bash
python scripts/stage_strategy_package.py WS/package.zip --out WS/staged
```

Validates and extracts the archive into a local review directory.

## 8. Generate review queue

```bash
python scripts/index_staged_packages.py WS/staged
```

## 9. Record review decision

```bash
python scripts/record_review_decision.py WS/staged/package \
  --decision approve_for_downstream_cam \
  --reviewer "Demo Reviewer" \
  --notes "Reviewed scale, tooling, and workholding assumptions."
```

Records a human decision as a sibling file; the package is never mutated.

## 10. Create review annotations

```bash
python scripts/create_review_annotations.py --package WS/package \
  --reviewer "Demo Reviewer" --severity info --category tooling \
  --message "Verify bit runout before downstream toolpath development."
```

## 11. Create manufacturing assumptions

```bash
python scripts/create_manufacturing_assumptions.py --package WS/package \
  --assumption tooling "Tool rigidity is adequate for the selected depth of cut."
```

## 12. Create risk assessment

```bash
python scripts/create_risk_assessment.py --package WS/package \
  --overall-risk medium \
  --risk geometry warning "Thin wall section may chatter."
```

## 13. Create manufacturing decision record

```bash
python scripts/create_manufacturing_decision_record.py --package WS/package \
  --decision approved --prepared-by "Manufacturing Engineer" \
  --reviewed-by "Senior Reviewer" \
  --rationale "Tooling, fixturing, and material assumptions reviewed."
```

## 14. Create revision lineage

```bash
python scripts/create_revision_lineage.py --package WS/package \
  --summary "Initial manufacturing strategy review."
```

## 15. Create traceability bundle

```bash
python scripts/create_traceability_bundle.py --package WS/package
```

Auto-discovers the conventionally-located sidecars and records a reference to each.

## 16. Validate bundle completeness

```bash
python scripts/validate_traceability_bundle.py \
  WS/traceability/package_bundle.json --check-references
```

Structural validation plus an existence witness for the declared references.

## 17. Create Production Shop handoff

```bash
python scripts/create_production_shop_handoff.py --package WS/package \
  --out WS/production_shop/package_handoff.json
```

A reference-only, outbound handoff. It does not authorize execution or confirm
machine readiness.

## 18. Validate handoff

```bash
python scripts/validate_production_shop_handoff.py \
  WS/production_shop/package_handoff.json --check-references
```

## 19. Inspect final package state

```bash
python scripts/inspect_strategy_package.py WS/package
```

The final inspection now reports the traceability sidecars, the traceability
bundle, and the Production Shop handoff — all discovered conventionally:

```text
Traceability:
  assumptions: present
  risk assessment: present
  decision record: present
  revision lineage: present

Traceability Bundle:
  present

Production Shop Handoff:
  present
```

## Verify the non-execution invariant

```bash
python scripts/verify_non_execution_invariant.py WS/package
```

Confirms the package carries no machine execution authority.

## Where CAM Assist stops

The workflow ends at a reviewed, portable, non-execution handoff. Everything
downstream — toolpath generation, simulation, G-code, post-processing, machine
execution — lives in traditional CAM and with the operator, never in CAM Assist.
See [CAM_ASSIST_VS_CAM_SOFTWARE.md](CAM_ASSIST_VS_CAM_SOFTWARE.md) and
[WHY_CAM_ASSIST_EXISTS.md](WHY_CAM_ASSIST_EXISTS.md).
