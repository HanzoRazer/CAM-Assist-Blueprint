# CAM Assist Blueprint

**Human-guided lutherie manufacturing intelligence**

CAM Assist is not a CAM system. It is a strategy assistant that helps luthiers translate instrument design intent into reviewable, portable manufacturing strategies.

## What CAM Assist Does

- Translates lutherie operations into explicit, portable strategy packages
- Produces DXF geometry + strategy metadata + human review checklists
- Keeps humans in authority over all manufacturing decisions
- Makes manufacturing intent visible before any machine runs

## What CAM Assist Does Not Do

- Generate G-code directly
- Control machines
- Replace CAM software
- Make autonomous manufacturing decisions
- Produce toolpaths without human approval

## First Implementation Slice

**Strategy Export Assistant** for fret slot operations.

Produces:
- DXF geometry with slot positions
- Strategy JSON with operation parameters
- Human review checklist
- Approval workflow metadata

See [docs/CAM_ASSIST_SYSTEM_DEFINITION.md](docs/CAM_ASSIST_SYSTEM_DEFINITION.md) for full product definition.

## Repository Structure

```
docs/
  CAM_ASSIST_SYSTEM_DEFINITION.md    # Product identity and boundaries
  LUTHERIE_WORKFLOW_MODEL.md         # How lutherie manufacturing works
  CAM_ASSIST_OPERATION_TAXONOMY.md   # Supported operation types
  HUMAN_AUTHORITY_MODEL.md           # Human approval requirements
  ADOPTED_CAM_CAPABILITIES.md        # What CAM capabilities we adopt vs. avoid

schemas/
  operation.schema.json              # Operation definition schema
  strategy.schema.json               # Strategy package schema

samples/
  fret-slot-strategy/                # Reference implementation
```

## Design Principles

1. **Human authority is non-negotiable** — Every manufacturing decision requires human approval
2. **Intent before execution** — Strategy packages make intent explicit before any machine runs
3. **Lutherie-specific** — Designed for instrument making, not generic manufacturing
4. **Portable output** — DXF + JSON can be used with any downstream CAM/machine
5. **Reviewable** — Every strategy includes a human-readable checklist

## Project Status

**CAM-A0: Repository Foundation and System Definition**

Current milestone establishes:
- Product identity and boundaries
- Non-goals (explicit)
- First operation slice (fret slots)
- Strategy export model
- Human authority model
- Adopted CAM capabilities map
