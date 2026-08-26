# Truss Rod Channel Strategy

## Purpose

CAM Assist can turn a reviewed specification for a **straight, constant-width,
flat-bottom truss rod channel** into a deterministic manufacturing-strategy
package.

The package tells a reviewer:

```text
where the channel is
how wide it is
how deep it is
which tool is recommended
whether that tool physically fits
how depth should be approached
what the human must review
```

CAM Assist does not generate G-code, cutter-center offsets, DXF files, or
machine execution authority.

## Supported Geometry

CAM-A30 v1 supports:

```text
straight channel
constant width
constant final depth
flat bottom
single centerline
```

Classification:

```text
operation_type       = truss_rod_channel
geometry_type        = 2.5D
strategy_complexity  = simple
cut_intent           = channel
```

## Inputs

Canonical creator input: `examples/operations/truss_rod_channel_example.json`.

Required:

* `operation_type` = `truss_rod_channel`
* `strategy_id`
* `units` (`inches` or `mm`)
* `coordinate_frame` (`origin`, `x_axis`, `y_axis`)
* `channel.start` / `channel.end` (`x`, `y`)
* `channel.width` (positive)
* `channel.depth` (positive)
* `blank_thickness` (positive; must exceed channel depth).
  `blank_thickness_inches` is accepted as an alias only when `units` are
  `inches`. If both are present they must agree.
* `tool.diameter` (positive, must not exceed width)
* `maximum_pass_depth` (positive)
* `material_context.material_class`
* `provenance.created_at` (pinned so serialization is deterministic)

Optional:

* `access_direction`
* `tool.tool_type`, `tool.description`
* `target_feature` (defaults to `neck`)

`residual_material` is `blank_thickness − channel.depth` and must be greater
than zero. Missing `blank_thickness` is a validation failure, not an
unresolved assumption.

CAM Assist does not invent truss-rod physical dimensions from a brand or rod
type.

## Geometry Intent

The line from `start` to `end` is centerline intent in XY. Width and depth
define the material-removal envelope. The operation is an open path, not a
closed pocket polygon. Start and end are XY points; Z is rejected because
depth is `channel.depth`.

`geometry.dxf_file` remains in the strategy contract (`geometry.dxf`, layer
`TRUSS_ROD_CHANNEL`). `geometry.generated` is `false`: the filename is a
contract slot, not a claim that a DXF file was generated or packaged. A30
does not generate a physical DXF. Assembled `source_geometry_files` remains
empty.

Coordinates are design intent relative to the strategy coordinate frame. They
are not fixture zero, G54/G55, stock origin, or machine home.

## Depth Strategy

Depth passes come from the shared, operation-agnostic helper:

```text
scripts/_shared/depth_passes.py
compute_depth_passes(final_depth, maximum_pass_depth)
```

The helper knows only those two numbers. Example:

```text
final_depth = 9
maximum_pass_depth = 4
passes = [4, 8, 9]
```

The last pass reaches requested final depth. No pass exceeds it.

## Tool Recommendation

Recommendation is advisory (`recommended` / `compatible`).

```text
tool_diameter >  channel_width  → validation failure
tool_diameter == channel_width  → width_strategy = centerline_cut,
                                  width_clearing_required = false
tool_diameter <  channel_width  → width_strategy = width_clearing_required,
                                  width_clearing_required = true
```

Width clearing is a strategy statement. No cutter-offset toolpath is generated.
A30 does not derive feeds or speeds from material.

## Review Requirements

The review packet exposes channel width, depth, start/end, required blank
thickness, residual material (`blank_thickness − final_depth`), access
direction when supplied, tool compatibility including
`width_clearing_required`, and the depth-pass sequence.

## Example

```bash
python scripts/create_truss_rod_channel_strategy.py \
  examples/operations/truss_rod_channel_example.json \
  --out examples/valid/truss_rod_channel_strategy.json --force

python scripts/create_truss_rod_channel_strategy.py \
  --input examples/operations/truss_rod_channel_example.json \
  --out examples/valid/truss_rod_channel_strategy.json --force

python scripts/assemble_strategy_package.py \
  examples/valid/truss_rod_channel_strategy.json \
  --out examples/packages/truss_rod_channel_strategy_example --force

python scripts/validate_strategy_package.py \
  examples/valid/truss_rod_channel_strategy.json

python scripts/inspect_strategy_package.py \
  examples/packages/truss_rod_channel_strategy_example/

python scripts/audit_package_coherence.py \
  --package examples/packages/truss_rod_channel_strategy_example --json
```

Assembled package contents:

```text
strategy.json
manifest.json
review_packet.md
```

## Validation

* Positive width, depth, tool diameter, blank thickness, and maximum pass depth
* Non-zero centerline length
* Tool diameter must not exceed channel width
* Residual material must equal `blank_thickness − channel depth` and be `> 0`
* `width_clearing_required` must match tool/channel fit
* Exactly one `channel_cut` phase with `order` 1
* Duplicated width/depth/pass/tool fields must agree
* `geometry.dxf_file` is the contract filename `geometry.dxf` with
  `geometry.generated = false`
* Depth-pass sequence must match the shared helper
* `geometry_type` = `2.5D`, `strategy_complexity` = `simple`
* Non-execution declarations remain required

## Limitations

v1 does not support curved channels, compound depth profiles, dual-action rod
pockets, independent adjustment-nut cavities, anchor pockets, spoke-wheel
recesses, multiple rods, carbon-fiber channels, or access-end allowance as
independent geometry.

A30 does not schedule this operation relative to fret slots, neck profiling,
fretboard glue-up, or neck carve.

## Non-Execution Boundary

```text
strategy ≠ toolpath
recommendation ≠ approval
coherence ≠ machine readiness
package ≠ G-code
CAM Assist ≠ post processor
```

## Future Variants

Later work may add curved channels, access pockets, or compound sequencing.
Compound rough/finish pocketing (pickup routes) is a separate capability and
is not assigned by CAM-A30.
