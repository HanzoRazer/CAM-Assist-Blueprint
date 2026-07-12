# CAM-A22 — Alternate Handoff (Superseded Historical Reference)

**Status: SUPERSEDED — historical reference only. Not corrective authority.**

An alternate CAM-A22 engineering handoff ("Creation Studio Request Export
(Read-Only)") was circulated *after* CAM-A22 was implemented, verified, and merged
(PR #27). It describes an **earlier conceptual form** of the capability. It does
**not** revise the shipped contract and must not be used to reshape it.

The authoritative CAM-A22 contract is the implementation merged in **PR #27**:

- Schema: `schemas/creation_studio_request.schema.json`
- Dev order: `docs/dev_orders/CAM-A22.md`
- Capability doc: `docs/integration/CAM_CREATION_STUDIO_REQUEST.md`

## Why the alternate handoff is not adopted

Adopting it would be a **breaking change to a merged, shipped contract** (schema
constant, authority block, example, every test, inspector JSON key), with no
functional gain over the verified implementation. The differences are conceptual
drift from an earlier draft, not corrections.

## Divergences (alternate handoff → shipped, authoritative)

| Aspect | Alternate handoff (superseded) | Shipped in PR #27 (authoritative) |
| --- | --- | --- |
| `record_type` | `creation_studio_request` | `cam_assist_creation_studio_request` (matches `cam_assist_*` sibling records) |
| Authority block | 4 flags: `non_execution`, `reference_only`, `requires_human_authoring`, `does_not_authorize_gcode` | 5 flags: `is_informational`, `does_not_authorize_execution`, `does_not_bypass_human_review`, `does_not_confirm_machine_readiness`, `does_not_require_gcode_generation` (mirrors A20 handoff) |
| Capability model | none (plain package export) | `requested_capabilities` controlled enum + `request_direction` — central to the request contract |
| Filename convention | `<pkg>_creation_request.json` | `<pkg>_request.json` |
| Capability doc | `docs/integration/CREATION_STUDIO_REQUEST.md` | `docs/integration/CAM_CREATION_STUDIO_REQUEST.md` |
| Example-regression test | `tests/test_creation_studio_request_example.py` | added additively (this branch), pinning the **shipped** example |

## Disposition

- **Keep PR #27 exactly as implemented.** The shipped contract stands.
- The `requires_human_authoring` notion and the plain-export model are **not**
  adopted; the merged authority block and capability vocabulary are load-bearing
  to the non-execution doctrine and the request's purpose.
- The one genuinely additive idea from the alternate handoff — an
  example-regression test — has been folded in against the shipped contract
  (`tests/test_creation_studio_request_example.py`), not the handoff's shape.

This file exists so the divergence is recorded and future readers are not misled
into treating the earlier draft as authoritative.

## Maintenance

This document describes the contract **as shipped in PR #27**. The authoritative
source is always the schema, validator, and creator — never this file. If CAM-A22
later evolves (a new `record_version`, an added authority flag, a renamed slot),
whoever makes that change owns updating the "shipped, authoritative" column of the
divergence table above, or deleting this file if the comparison is no longer
useful. The `record_version` in `schemas/creation_studio_request.schema.json` is
the signal that this note may be stale. This doc is documentation only: no test
depends on it, so a drift here cannot break the build — which is exactly why it
needs a human owner at change time.
