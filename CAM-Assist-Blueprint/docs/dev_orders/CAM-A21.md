# Dev Handoff — CAM-A21

## Product Identity and End-to-End Workflow Demonstration

## Scope

Make CAM Assist immediately understandable to a new user by demonstrating the
complete product workflow from manufacturing intent through reviewed, portable,
non-execution handoff.

CAM-A21 is a **product clarity and workflow demonstration order**. It does not add
a new authority layer or execution capability.

It answers, concretely:

```text
What is CAM Assist?
What does a user do with it?
What artifacts are created?
Where does CAM Assist stop?
What happens downstream?
```

The demonstrated workflow, as one coherent product:

```text
Manufacturing Strategy
→ Review Packet
→ Package Manifest
→ Package Assembly
→ Inspection
→ Archive
→ Staging
→ Review Decision
→ Review Annotations
→ Traceability Records
→ Traceability Bundle
→ Production Shop Handoff
```

## Decisions

| Decision                           | Outcome                                        |
| ---------------------------------- | ---------------------------------------------- |
| Primary purpose                    | Product identity and workflow clarity          |
| New schemas                        | No                                             |
| New authority model                | No                                             |
| Machine execution                  | Forbidden                                      |
| G-code generation                  | Forbidden                                      |
| Post-processing                    | Forbidden                                      |
| Production Shop runtime dependency | Forbidden                                      |
| Existing examples                  | Reuse where valid                              |
| New example content                | Minimal and explicitly synthetic               |
| Workflow automation                | Demonstration only                             |
| CLI orchestration                  | Read-only wrapper permitted                    |
| CAM-Creation-Studio relationship   | Documented as downstream companion, not merged |

## Core Product Statement

> A review-first manufacturing strategy and traceability platform that packages
> manufacturing intent, assumptions, risks, decisions, and handoff metadata
> without generating machine instructions or granting execution authority.

It is not a CAM engine, a post processor, a G-code generator, a CNC controller, or
an execution approval system.

## Deliverables

1. `docs/product/WHY_CAM_ASSIST_EXISTS.md` — problem, boundary, ownership, users,
   workflow, human authority, portability, relationship to downstream CAM.
2. `docs/product/CAM_ASSIST_WORKFLOW.md` — the synthetic V-Carve example walked
   with **verified** repository commands (no inferred flags).
3. `docs/product/CAM_ASSIST_VS_CAM_SOFTWARE.md` — capability comparison; note that
   traditional CAM traceability is often vendor-specific or external.
4. `docs/product/CAM_ASSIST_AND_CAM_CREATION_STUDIO.md` — companion-product
   relationship; contract-first; merger remains an open product decision.
5. `scripts/run_cam_assist_demo.py` — reproducible demonstration runner that
   orchestrates the existing public CLIs as subprocesses. No G-code, no CAM
   engine, no machine, no source mutation; temporary workspace by default.
6. `examples/workflows/ltb_vcarve_synthetic/` — README + WORKFLOW_OUTPUTS
   documenting the input and expected generated artifacts (runner generates into a
   temporary directory; no duplicate committed packages).

## Verification Discipline

Do not accept documentation as correct merely because it resembles prior commands.
Before finalizing: run every documented command, capture the actual exit code,
compare generated files to documented outputs, and confirm CI runs on the true
repository root. The CAM-A21 verdict is based on the actual demonstration run.

## Rollout Order

```text
1  Product identity documents
2  CLI inventory (verify every --help; do not commit inferred flags)
3  Workflow guide (verified commands only)
4  Demo runner (public CLI orchestration)
5  Demo tests (success, failure propagation, source immutability)
6  Workflow example directory
7  Documentation tests (boundary language + command references)
8  README integration (What It Is / Is Not / Quick Workflow / Creation Studio)
9  Full verification (suite, demo end-to-end, non-execution invariant, CI)
10 PR (no merge/tag/release without separate authorization)
```

## Completion Criteria

```text
- product identity is explicit
- CAM Assist/CAM distinction is clear
- CAM-Creation-Studio relationship is documented
- verified end-to-end workflow exists
- demo runner exercises existing public CLIs
- demo creates full review and traceability flow
- no G-code or execution behavior is introduced
- source examples remain immutable
- non-execution invariant passes
- full suite passes
- CI runs on the actual repository root
```

## Branch

```text
cam-a21-product-workflow-demo
```

## Implementation Note (as delivered)

The demonstration is driven from `examples/ltb_import/synthetic_vcarve_ltb_output.json`.
During verification, the import was found to compose `strategy_id` directly from
`operation_type` (`v_carve`), leaking an underscore that `strategy_id` (lowercase
alphanumeric + hyphens only) forbids — which also left the committed canonical
strategy failing `validate_strategy_package.py`. As a prerequisite bug fix, the
import now slugifies `strategy_id` (`v_carve` → `v-carve`) and the one committed
canonical strategy id was corrected accordingly. No schema, authority, or
execution behavior was changed.
