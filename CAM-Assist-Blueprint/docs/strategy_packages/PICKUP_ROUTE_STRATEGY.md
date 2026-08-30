# Pickup Route Strategy

## Purpose

CAM Assist can turn a reviewed specification for a **flat-bottom, constant-depth
pickup cavity** into a deterministic two-phase manufacturing-strategy package.

The package tells a reviewer:

```text
where the cavity is centered
how long and wide it is
what corner radius is requested
how deep it is
which roughing and finishing tools are recommended
whether those tools physically fit
how roughing approaches depth
that finishing completes at the same final depth
what the human must review
```

CAM Assist does not generate G-code, cutter-center offsets, DXF files, or
machine execution authority.

## Supported Geometry

CAM-A31 v1 supports:

```text
axis-aligned rectangle or rounded rectangle
constant final depth
flat bottom
explicit mounting tabs (zero, one, or many)
```

Classification:

```text
operation_type       = pickup_route
geometry_type        = 2.5D
strategy_complexity  = compound
cut_intent           = pocket
```

The taxonomy family remains closed polygon / compound. v1 does not implement
stepped depths.

## Inputs

Canonical creator input: `examples/operations/pickup_route_example.json`.

Required:

* `operation_type` = `pickup_route`
* `strategy_id`
* `units` (`inches` or `mm`)
* `coordinate_frame` (`origin`, `x_axis`, `y_axis`)
* `cavity.reference_point` (`x`, `y`) — geometric center
* `cavity.length` (positive, along X)
* `cavity.width` (positive, along Y)
* `cavity.corner_radius` (`>= 0` and `<= min(length, width) / 2`)
* `cavity.final_depth` (positive)
* `roughing.tool_diameter` (positive, must fit the cavity envelope)
* `roughing.maximum_pass_depth` (positive)
* `roughing.finish_allowance` (`>= 0`; wall stock only)
* `finishing.tool_diameter` (positive, must fit the cavity envelope)
* `material_context.material_class`
* `provenance.created_at` (pinned so serialization is deterministic)

Optional:

* `cavity.mounting_tabs` (defaults to `[]`)
* `blank_thickness` (when supplied must exceed `final_depth`)
* `roughing.tool_type`, `roughing.description`
* `finishing.tool_type`, `finishing.description`
* `target_feature` (defaults to `body`)

`blank_thickness` is not inherited from the truss-channel residual-material
contract. If omitted, CAM Assist does not invent it and does not create an
unresolved-assumption failure solely because it is absent.

CAM Assist does not invent pickup-type presets or clearance.

## Geometry Intent

`cavity.reference_point` is the cavity center in the declared coordinate
frame. The main envelope is derived symmetrically around that center.

Each mounting tab `{x, y, length, width, corner_radius}` is a rounded
rectangle whose `(x, y)` is its center in the same frame. Tabs must
intersect or touch the main cavity envelope. Isolated floating rectangles
are rejected. This is part-geometry validation, not a toolpath operation.

`geometry.dxf_file` remains in the strategy contract (`geometry.dxf`, layer
`PICKUP_ROUTE`). `geometry.generated` is `false`: the filename is a
contract slot, not a claim that a DXF file was generated or packaged. A31
does not generate a physical DXF. Assembled `source_geometry_files` remains
empty.

Coordinates are design intent relative to the strategy coordinate frame. They
are not fixture zero, a work offset, or machine home.

## Depth Strategy

Roughing owns the plunge and depth progression. Depth passes come from the
shared, operation-agnostic helper:

```text
scripts/_shared/depth_passes.py
compute_depth_passes(final_depth, maximum_pass_depth)
```

Example:

```text
final_depth = 15
maximum_pass_depth = 6
passes = [6, 12, 15]
```

Finishing `depth_strategy` is only:

```json
{ "final_depth": <same final depth> }
```

There is no repeated roughing pass list and no artificial `[final_depth]`
sequence.

## Finish Allowance and Corner Fit

`finish_allowance` is wall stock only. `0` is valid. Negative values fail.
Roughing still targets `final_depth`. There is no floor stock in v1.

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

Both cutters must always fit the cavity envelope
(`diameter <= length` and `diameter <= width`). Oversized or incompatible
tools hard-fail. Design geometry is never silently enlarged.

Both roughing and finishing cutters are required. They may be equal.
Omission of a finishing cutter is not an implicit “same cutter.”

## Review Requirements

The review packet exposes cavity center, length, width, corner radius,
final depth, both tool diameters, finishing tool radius, finish allowance,
roughing passes, finishing final depth, mounting tabs, tool-limited-sharp
notice when radius is 0, and residual material when `blank_thickness` is
supplied.

## Example

```bash
python scripts/create_pickup_route_strategy.py \
  examples/operations/pickup_route_example.json \
  --out examples/valid/pickup_route_strategy.json --force

python scripts/create_pickup_route_strategy.py \
  --input examples/operations/pickup_route_example.json \
  --out examples/valid/pickup_route_strategy.json --force

python scripts/assemble_strategy_package.py \
  examples/valid/pickup_route_strategy.json \
  --out examples/packages/pickup_route_strategy_example --force

python scripts/validate_strategy_package.py \
  examples/valid/pickup_route_strategy.json

python scripts/inspect_strategy_package.py \
  examples/packages/pickup_route_strategy_example/

python scripts/audit_package_coherence.py \
  --package examples/packages/pickup_route_strategy_example --json
```

Assembled package contents:

```text
strategy.json
manifest.json
review_packet.md
```

## Validation

* Positive length, width, final depth, and tool diameters
* Corner radius `>= 0` and `<= min(length, width) / 2`
* Finish allowance `>= 0`
* Both cutters fit the cavity envelope
* Positive corner-radius compatibility follows the finish-allowance invariant
* Tabs, when present, contact the main cavity envelope
* Optional `blank_thickness` must exceed `final_depth` when supplied
* Exactly two phases: `rough` order 1, `finish` order 2
* Finishing `depth_strategy` contains only `final_depth`
* Top-level `depth_strategy` matches the shared helper
* `geometry.dxf_file` is the contract filename `geometry.dxf` with
  `geometry.generated = false`
* `geometry_type` = `2.5D`, `strategy_complexity` = `compound`
* Non-execution declarations remain required

## Limitations

v1 does not support rotation, non-rectangular cavities, stepped depths, 3D
cavities, floor stock, pickup-type presets, cutter-center offsets, or
lead-in/lead-out.

A31 does not schedule this operation relative to neck pocket, control cavity,
or body outline.

## Non-Execution Boundary

```text
strategy ≠ toolpath
recommendation ≠ approval
coherence ≠ machine readiness
package ≠ G-code
CAM Assist ≠ post processor
```

## Future Variants

Later work may add stepped depths, rotated cavities, or named pickup
presets. Those variants are not assigned by CAM-A31.
