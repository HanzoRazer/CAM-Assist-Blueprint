# Dev Order — CAM-A30

## Truss Rod Channel Strategy Support

## Classification

```text
product capability
manufacturing strategy
not execution authority
```

CAM-A30 is a **product capability**. It adds the first post-fret-slot
manufacturing-strategy operation: a straight, constant-width, flat-bottom
truss rod channel classified as P2 / 2.5D / open path / simple.

CAM Assist defines and documents manufacturing strategy. It does not generate
machine-specific G-code, post-process output, or authorize execution.

## Predecessor baseline

```text
Baseline            CAM-Assist-Blueprint main @ 0cfa5e9
Latest capability   CAM-A28 — Package Coherence Audit
                    (merged PR #36 → 65e9f4c)
Latest maintenance  CAM-A29 — Traceability Reference Path Canonicalization
                    (merged PR #37 → 0cfa5e9)
Open PRs at gate    0
Working tree        clean
CAM-A30             defined by this dev order, and by nothing preceding it
```

CAM-A29 is on `main`. This work does not stack on an open A29 branch.

The operation taxonomy still identifies the truss rod channel as:

```text
Geometry type:       2.5D
Geometry:            open path
Depth profile:       flat bottom
Priority:            P2
Strategy complexity: simple
```

## Architecture reconciliation (Phase 2, recorded before code)

Repository reality at the A29 merge, versus a naive reading of the original
handoff:

* There is **no** fret-slot strategy creator. Fret slots are a hand-authored
  `strategy.json` plus `assemble_strategy_package.py`. CAM-A30 therefore
  introduces the first operation-strategy generator.
* `truss_rod_channel` already appears in `schemas/operation.schema.json` as an
  enum member, but that schema is unused by validators and scripts. The live
  contract is `schemas/strategy.schema.json` plus
  `scripts/validate_strategy_package.py`. `operation_intent.operation_type` is a
  free string. A30 extends both schemas; it does **not** create
  `truss_rod_channel_strategy.schema.json`.
* Strategy geometry still requires `geometry.dxf_file` and `primary_layer`.
  A30 retains those filename fields and does **not** generate or commit a
  `.dxf`.
* Review packet generation currently hard-codes a fret-slot summary. A30
  dispatches on `operation_intent.operation_type`. Fret-slot rendering stays
  on the existing path so golden fret-slot text is unchanged.
* No `docs/operations/` tree exists. Operation documentation lives at
  `docs/strategy_packages/TRUSS_ROD_CHANNEL_STRATEGY.md`.
* Existing `create_*.py` tools write sidecars for assembled packages. A30's
  creator writes **strategy JSON only**, then reuses CAM-A5 assembly.
* Manifest `operation_type` is derived as `{operation}_strategy` by the
  assembler. Strategy JSON uses `truss_rod_channel`; the assembled manifest
  therefore uses `truss_rod_channel_strategy`.

## Scope

Authorized work:

1. Authoritative operation identity `truss_rod_channel`.
2. Straight centerline, constant width, constant final depth, flat bottom.
3. Operation-agnostic shared depth-pass helper.
4. Advisory tool/channel compatibility with hard failure on oversized tools.
5. Generic `depth_strategy` / `strategy_phases` fields reusable by later
   compound operations, populated here with a single simple phase.
6. Creator CLI → existing assembler → committed example package
   (`strategy.json`, `manifest.json`, `review_packet.md` only).
7. Operation-dispatched review packet.
8. Deterministic validation and tests.
9. Documentation, taxonomy status, README, ledger, and roadmap.

Out of scope:

* curved, tapered, variable-depth, or dual truss-rod channels;
* access-end cavities, anchor pockets, spoke-wheel recesses as independent
  geometry;
* carbon-fiber reinforcement channels;
* neck-carve interaction;
* fret-slot coupling or cross-operation scheduling;
* material-derived feeds/speeds;
* DXF generation;
* cutter-center offsets, G-code, post processors, machine communication;
* CAM-Creation-Studio or Production Shop runtime changes;
* assigning or implementing CAM-A31.

## Core objective

> Can CAM Assist express a deterministic, reviewable truss-rod-channel
> manufacturing strategy without generating machine execution instructions
> or introducing a parallel operation architecture?

## Design decisions recorded at authorization time

### Identifier

```text
truss_rod_channel
```

No aliases (`truss_channel`, `trussrod`, `rod_slot`).

### Classification

```text
geometry_type        = "2.5D"
strategy_complexity  = "simple"
cut_intent           = "channel"
```

### Geometry

Open centerline plus width and depth metadata. Not a closed pocket polygon.

### Depth passes

Shared helper:

```text
scripts/_shared/depth_passes.py
compute_depth_passes(final_depth, maximum_pass_depth) -> [cumulative depths]
```

Operation-agnostic from day one. Numeric inputs only. Deterministic. Never
exceeds `final_depth`. Final pass reaches the requested depth within repository
numeric tolerance. `maximum_pass_depth` is a required input; A30 does not
invent it from tool or material.

### Tool fit

```text
tool_diameter >  channel_width  → validation failure (no strategy)
tool_diameter == channel_width  → centerline_cut
tool_diameter <  channel_width  → width_clearing_required (described, no offsets)
```

Recommendation language is `recommended` / `compatible`. Never approved,
machine-ready, or safe-to-execute.

### DXF

Keep required `geometry.dxf_file` in the strategy contract. Do not generate
a physical DXF. Assembled `source_geometry_files` remains empty, matching
the fret-slot example package.

### Feeds and speeds

A30 does not derive or emit material-based feeds/speeds.

### Residual material

When `blank_thickness` is supplied, residual = blank − channel depth and must
be positive. When absent, record an explicit unresolved assumption. Do not
invent truss-rod physical dimensions from brand or rod type.

### Access-end allowance

Not present in current operation inputs. Omitted in v1.

### Package architecture

Reuse CAM-A5 assembly, CAM-A2 validation, CAM-A3 review packets, CAM-A6
inspection, CAM-A28 coherence, and CAM-A29 declaring-file-relative paths.
No parallel package format.

### Review dispatch

`generate_review_packet.py` branches on `operation_type`. The fret-slot
path remains the default for `fret_slots` (and any pre-A30 operation that
already rendered that way). `truss_rod_channel` gets its own summary.

### Pipeline

```text
examples/operations/truss_rod_channel_example.json
        ↓
scripts/create_truss_rod_channel_strategy.py
        ↓
strategy.json
        ↓
scripts/assemble_strategy_package.py
        ↓
examples/packages/truss_rod_channel_strategy_example/
```

### A31-safe reuse (approved, not implemented here)

A30 exposes generic `strategy_phases` / `depth_strategy` and the shared
depth helper so a future compound `pickup_route` operation can add
rough → finish without a second mini-application. This order does **not**
assign CAM-A31, implement pickup routes, or introduce finish-allowance
semantics in A30.

Locked future pickup-route rulings (recorded only, not implemented):

* finish allowance is walls-only;
* finishing tool is required and may equal the roughing tool;
* `corner_radius = 0` means tool-limited sharpness, not a silently altered
  design radius;
* mounting tabs are explicit rounded rectangles;
* oversized / inside-corner-incompatible tools hard-fail.

## Interfaces

```text
scripts/_shared/depth_passes.py
scripts/_shared/truss_rod_channel.py
scripts/create_truss_rod_channel_strategy.py
  <input.json>
  --out <strategy.json>     optional
  --force                   optional
  --quiet                   optional
```

Exit codes follow existing creators: `0` success, `1` validation/argument,
`2` file/usage.

## Authority boundary

A truss-rod-channel strategy describes where the channel is, how wide and
deep it is, which tool is recommended, whether that tool physically fits,
how depth should be approached, and what a human must review.

```text
strategy ≠ toolpath
recommendation ≠ approval
coherence ≠ machine readiness
package ≠ G-code
CAM Assist ≠ post processor
```

## Non-goals

No G-code, post processors, machine communication, execution approval,
cross-operation scheduling, DXF generation, material-derived feeds/speeds,
or CAM-A31 implementation.

## Completion criterion

> **Can CAM Assist express a deterministic, reviewable truss-rod-channel
> manufacturing strategy without generating machine execution instructions
> or introducing a parallel operation architecture?**

**Yes.**
