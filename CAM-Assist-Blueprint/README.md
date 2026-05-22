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

## CLI Tools

### Validate Strategy Package

```bash
python scripts/validate_strategy_package.py examples/valid/fret_slot_strategy.json
python scripts/validate_strategy_package.py examples/
```

Validates strategy packages against the schema contract. Rejects execution authority claims.

### Generate Review Packet

```bash
python scripts/generate_review_packet.py examples/valid/fret_slot_strategy.json
python scripts/generate_review_packet.py examples/valid/fret_slot_strategy.json --out /tmp/review.md
```

Generates a human-readable Markdown review packet from a validated strategy package.
See [docs/REVIEW_PACKET_FORMAT.md](docs/REVIEW_PACKET_FORMAT.md) for format details.

### Validate Strategy Package Manifest

```bash
python scripts/validate_manifest.py examples/valid/fret_slot_strategy_manifest.json
```

Validates a strategy package manifest that bundles strategy JSON, review packet, and geometry references.
See [docs/strategy_packages/STRATEGY_PACKAGE_MANIFEST.md](docs/strategy_packages/STRATEGY_PACKAGE_MANIFEST.md) for format details.

## Repository Structure

```
docs/
  CAM_ASSIST_SYSTEM_DEFINITION.md    # Product identity and boundaries
  LUTHERIE_WORKFLOW_MODEL.md         # How lutherie manufacturing works
  CAM_ASSIST_OPERATION_TAXONOMY.md   # Supported operation types
  HUMAN_AUTHORITY_MODEL.md           # Human approval requirements
  ADOPTED_CAM_CAPABILITIES.md        # What CAM capabilities we adopt vs. avoid
  REVIEW_PACKET_FORMAT.md            # Review packet documentation
  strategy_packages/
    STRATEGY_PACKAGE_MANIFEST.md     # Manifest format documentation

schemas/
  operation.schema.json              # Operation definition schema
  strategy.schema.json               # Strategy package schema (v1.2)
  strategy_package_manifest.schema.json  # Manifest schema (A4)

scripts/
  validate_strategy_package.py       # Schema validator (A2)
  generate_review_packet.py          # Review packet generator (A3)
  validate_manifest.py               # Manifest validator (A4)

examples/
  valid/                             # Valid strategy examples
  invalid/                           # Invalid examples for testing

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

| Milestone | Status | Description |
|-----------|--------|-------------|
| CAM-A0 | Complete | Repository foundation and system definition |
| CAM-A1 | Complete | Schema validation foundation |
| CAM-A2 | Complete | Strategy package contract enforcement |
| CAM-A3 | Complete | Review packet generator |
| CAM-A4 | Complete | Strategy package manifest |

Current capabilities:
- Strategy packages validated against semantic contract
- Execution authority claims rejected
- Human-readable review packets generated
- Strategy package manifests bundle artifacts for handoff
- Non-execution boundary enforced throughout
