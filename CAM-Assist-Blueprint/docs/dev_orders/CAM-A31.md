# Dev Order — CAM-A31

## Pickup Route Strategy Support

## Classification

```text
product capability
manufacturing strategy
not execution authority
```

CAM-A31 is a **product capability**. It adds the first compound
manufacturing-strategy operation: a flat-bottom pickup cavity classified as
P2 / 2.5D / closed region / compound (rough → finish).

CAM Assist defines and documents manufacturing strategy. It does not generate
machine-specific G-code, post-process output, cutter-center offsets, or
authorize execution.

## Predecessor baseline

```text
Baseline            CAM-Assist-Blueprint main @ 31e9c68
Latest capability   CAM-A30 — Truss Rod Channel Strategy Support
                    (merged PR #38 → 31e9c68)
Open PRs at gate    0
Working tree        clean
CAM-A31             defined by this dev order, and by nothing preceding it
```

CAM-A30 is on `main`. This work branches from that merge and does not stack
on an open A30 branch.

The operation taxonomy still identifies pickup routes as:

```text
Geometry type:       2.5D
Geometry:            closed polygon
Priority:            P2
Strategy complexity: compound (rough + finish)
```

A31 v1 implements a **flat-bottom, constant-depth** cavity. The taxonomy
family classification is not changed.

## Architecture reconciliation (Phase 2, recorded before code)

A30 established the reusable path A31 must follow:

```text
operation input
    ↓
create_*_strategy.py
    ↓
strategy.json
    ↓
assemble_strategy_package.py
    ↓
manifest + review packet
```

Reuse, do not fork:

* `scripts/_shared/depth_passes.py` — `compute_depth_passes()`
* generic `depth_strategy` / `strategy_phases`
* operation-dispatched review packets
* required `geometry.dxf_file` + `geometry.generated = false`
* no physical DXF
* no feeds/speeds derivation
* `operation.schema.json` remains unused by runtime validators; the live
  contract is `strategy.schema.json` plus
  `validate_strategy_package.py`. A31 extends both, as A30 did.

## Scope

Authorized work:

1. Operation identity `pickup_route`.
2. Axis-aligned rectangular or rounded-rectangular cavity, constant depth.
3. Explicit optional mounting-tab rectangles (zero, one, or many).
4. Two-phase strategy: rough, then finish.
5. Shared `compute_depth_passes()` for roughing only.
6. Finishing `depth_strategy` is `{ "final_depth": <same> }` only.
7. Creator, validator, review dispatch, example package, tests, docs,
   taxonomy note, ledger, roadmap.
8. Open the CAM-A31 PR and stop for review.

Out of scope:

* CAM-A32 and later.
* Merge, tag, or release.
* Feeds/speeds derivation.
* Physical DXF generation.
* G-code, posts, cutter-center offsets, lead-in/lead-out.
* Pickup-type presets.
* Floor stock / Z-axis finish allowance.
* Rotation, non-rectangular cavities, stepped depths, 3D cavities.
* Cross-operation scheduling.
* A dedicated `pickup_route_strategy.schema.json`.

## Locked decisions

These rulings close the A31 model. Do not reopen them during
implementation.

### Cavity reference point

`cavity.reference_point` is the **geometric center** of the main pickup
cavity in the declared `coordinate_frame`. Length is along X. Width is
along Y. The main cavity envelope is derived symmetrically around that
center. There is no rotation in v1.

### Mounting-tab coordinates

Each tab `{x, y, length, width, corner_radius}` is an explicitly
positioned rounded rectangle whose `(x, y)` is its **center**, in the same
coordinate frame as the cavity reference point. Tab coordinates are not
relative to a cavity corner.

Tabs must **intersect or touch** the main cavity envelope. Isolated
floating rectangles are rejected. Each tab is also validated on its own
dimensions and radius. This is part-geometry validation, not a toolpath
operation.

### Finish allowance and corner-fit

`finish_allowance` is **wall stock only**. `0` is valid. Negative values
fail. Roughing still targets `final_depth`. There is no floor stock in
v1.

Corner-fit invariant:

```text
finish_allowance > 0
    → roughing may leave final wall stock
    → finishing cutter governs exact positive corner-radius compatibility

finish_allowance = 0
    → roughing also claims final walls
    → roughing and finishing cutters must both satisfy positive
      corner-radius compatibility

corner_radius = 0
    → tool-limited-sharp semantics
    → preserve design radius 0
    → do not hard-fail on radius
    → surface finishing tool radius in review evidence
```

When `corner_radius > 0`, a cutter that claims final wall geometry must
satisfy `tool_radius <= corner_radius`. Oversized or incompatible tools
hard-fail. Design geometry is never silently enlarged.

Both roughing and finishing cutters are required. They may be equal.
Omission of a finishing cutter is not an implicit “same cutter.”

### Blank thickness

`blank_thickness` is **optional**. If supplied:

```text
blank_thickness > final_depth
```

must hold, and residual material may be surfaced for review. If omitted,
do not invent it and do not create an unresolved-assumption failure solely
because it is absent. Pickup route does not inherit the truss-channel
residual-material requirement as a mandatory contract.

### Finishing depth strategy

Use only:

```json
{
  "final_depth": <same final depth>
}
```

No repeated roughing pass list and no artificial `[final_depth]` sequence.
Roughing owns the plunge/depth progression via
`compute_depth_passes(final_depth, maximum_pass_depth)`. Finishing
expresses completion at the already-established target depth.

### A30-style defaults

Required creator fields:

* `strategy_id`
* `units`
* `coordinate_frame`
* `material_context.material_class`
* `provenance.created_at`

`target_feature` defaults to `body`.

DXF contract:

```text
geometry.dxf_file = geometry.dxf
geometry.generated = false
layer = PICKUP_ROUTE
```

Phase IDs and order:

```text
1 rough
2 finish
```

Exactly two phases. No optional third cleanup phase.

CLI:

```text
positional input
--input
--out
--force
--quiet
```

### Publication

Branch from current `main` at or after `31e9c68`. Implement CAM-A31 only.
Open PR #39 if that is the next available PR number. Stop for review. No
merge, no tag/release, no A32.

## Geometry contract

Main cavity:

* `reference_point.{x, y}` — cavity center
* `length` — X extent, must be `> 0`
* `width` — Y extent, must be `> 0`
* `corner_radius` — `>= 0` and `<= min(length, width) / 2`
* `final_depth` — `> 0`
* `mounting_tabs` — array, may be empty

Each mounting tab:

* `{x, y}` — tab center
* `length`, `width` — `> 0`
* `corner_radius` — `>= 0` and `<= min(tab length, tab width) / 2`
* must intersect or touch the main cavity AABB envelope (inclusive)

Roughing:

* `tool_diameter` — `> 0` and `<= length` and `<= width`
* `maximum_pass_depth` — `> 0`
* `finish_allowance` — `>= 0`

Finishing:

* `tool_diameter` — `> 0` and `<= length` and `<= width`

If `finish_allowance > 0`, only the finishing cutter is checked against a
positive corner radius. If `finish_allowance = 0`, both cutters are
checked. Envelope fit applies to both cutters in either case.

## Strategy JSON shape

Align with A30 field names:

* `operation_intent.operation_type` = `pickup_route`
* `operation_intent.geometry_type` = `2.5D`
* `operation_intent.strategy_complexity` = `compound`
* `operation_intent.cut_intent` = `pocket`
* `operation_intent.target_feature` = `body` unless supplied
* `operation.type` = `pocket_cut`
* `operation.sequence` = `rough_then_finish`
* `operation.tool` = finishing tool (claims final walls)
* top-level `cavity` — validated geometry plus `bottom_profile: flat`
* top-level `depth_strategy` — full roughing strategy
  (`final_depth`, `maximum_pass_depth`, `pass_count`, `passes`)
* `strategy_phases[0]` — `phase_id: rough`, `order: 1`, roughing tool,
  full depth strategy
* `strategy_phases[1]` — `phase_id: finish`, `order: 2`, finishing tool,
  `{ "final_depth": <same> }` only
* `tool_compatibility` — both cutters, envelope fit, corner-fit flags,
  `claims_final_walls` per phase
* `review_requirements.evidence` — placement, extents, corner radius,
  final depth, both tool diameters, finish allowance, rough passes,
  finishing tool radius, tool-limited-sharp notice when radius is 0,
  tabs, optional residual
* `setup_assumptions.cross_operation_scheduling` = `not_specified`
* `warnings` = `[]`
* `approval_state` = `pending`
* `safety_boundary.execution_authority_claim` = `false`

Forbidden authority tokens continue to walk string values. Do not put
`approved`, `machine_ready`, `G0`, or `G54` in strategy text.

## Files

Create:

* `scripts/_shared/pickup_route.py`
* `scripts/create_pickup_route_strategy.py`
* `examples/operations/pickup_route_example.json`
* `examples/valid/pickup_route_strategy.json` (creator-generated)
* `examples/packages/pickup_route_strategy_example/`
* `tests/test_pickup_route_strategy.py`
* `tests/test_pickup_route_strategy_creator.py`
* `tests/test_pickup_route_strategy_review.py`
* `tests/test_pickup_route_strategy_example.py`
* `docs/strategy_packages/PICKUP_ROUTE_STRATEGY.md`

Modify:

* `schemas/operation.schema.json` — additive `pickup_route` `allOf`
* `schemas/strategy.schema.json` — additive cavity fields and
  `pickup_route` `allOf`
* `scripts/validate_strategy_package.py` — dispatch `pickup_route`
* `scripts/generate_review_packet.py` — Pickup Route Summary; keep
  fret-slot and truss-rod golden text unchanged
* `docs/operations/OPERATION_TAXONOMY.md` — implementation note only
* `README.md` — A31 pointer after A30
* `LEDGER.md` — A30 → Merged PR #38 → `31e9c68`; A31 → PR Open
* `ROADMAP.md` — record A31; do not assign A32

## Review packet

Add a **Pickup Route Summary**. Do not change the fret-slot or truss-rod
summary headings or their existing body text.

Dispatch:

```text
if pickup_route → Pickup Route Summary
elif truss_rod_channel → Truss Rod Channel Summary
else → Fret Slot Summary
```

Fret slots remain the default for unknown types.

## Tests that must pass

1. JSON Schema + `validate_strategy_package` + assembled package on the
   committed example.
2. Creator output is byte-identical for a pinned `created_at`.
3. Depth helper: roughing `15 / 6 → [6, 12, 15]`.
4. Finishing `depth_strategy` contains only `final_depth`.
5. Corner-fit invariant for `finish_allowance > 0` and `= 0`.
6. `corner_radius = 0` is tool-limited-sharp, not a hard fail.
7. Zero, one, and many tabs; floating tabs fail; touching tabs pass.
8. Omitted `blank_thickness` does not fail; supplied value must be
   greater than `final_depth`.
9. Negative finish allowance fails.
10. Oversized tools fail.
11. Fret-slot review still contains `Fret Slot Summary`.
12. Truss-rod review still contains `Truss Rod Channel Summary`.
13. Pickup review contains `Pickup Route Summary`.
14. A28: `audit_package_coherence.py --package
    examples/packages/pickup_route_strategy_example --json
    --fail-on-errors` → 0 errors.
15. Full pytest suite and
    `ci_verify_non_execution_invariant.py`.

## Publication sequence

1. Commit this file alone.
2. Implement CAM-A31 only.
3. Generate the example through the creator and assembler.
4. Run the full suite and A28 / A29 / A30 witnesses.
5. Open the CAM-A31 PR. Prefer #39 if that number is next.
6. Stop for review.

Do not merge. Do not tag. Do not start CAM-A32.
