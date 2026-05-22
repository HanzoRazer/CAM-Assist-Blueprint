# CAM-Assist-Blueprint

Human-guided manufacturing intelligence for CNC lutherie workflows.

---

## Overview

CAM Assist Blueprint is a research and architecture project exploring how software can augment expert lutherie manufacturing workflows through:

- geometry-aware machining assistance
- operational review tooling
- manufacturing strategy packaging
- process intelligence
- topology-sensitive workflow guidance
- human-supervised CAM review systems

The project focuses on helping instrument builders transform design intent into:

```
reviewable
manufacturable
portable
human-approved
```

manufacturing strategy packages.

CAM Assist is intentionally designed as an **assistance system**, not an autonomous manufacturing engine.

---

## Current Project Status

```
Blueprint / Architecture Phase
```

This repository currently defines:

- manufacturing strategy schemas
- validation contracts
- review packet generation
- package manifests
- provenance-aware assembly workflows
- human authority boundaries

No production CAM runtime or machine execution engine exists in this repository.

---

## Core Philosophy

CAM Assist is built around a simple principle:

```
Manufacturing assistance does not imply manufacturing authority.
```

The system may:

- analyze
- validate
- organize
- review
- package
- annotate

manufacturing intent.

The system may not:

- autonomously authorize machining
- claim execution authority
- replace operator review
- generate unattended manufacturing execution

---

## Non-Goals

CAM Assist is **not**:

- autonomous manufacturing AI
- a push-button CNC generator
- a machine controller
- a generic CAM replacement
- unattended machining automation
- a self-authoring manufacturing system

This project intentionally preserves:

```
human review
operator authority
craft expertise
manufacturing accountability
```

---

## Current Architecture

### CAM-A0 — Repository Foundation

Established:

- repository identity
- workflow philosophy
- non-goals
- operation taxonomy direction
- human authority model

---

### CAM-A1 — Fret Slot Strategy Contract

Introduced the first bounded manufacturing strategy:

```
fret_slot_strategy
```

Including:

- strategy schema
- coordinate frame definition
- provenance requirements
- material context
- safety boundary metadata
- review requirements

---

### CAM-A2 — Strategy Validation

Added executable validation:

- schema enforcement
- authority rejection
- execution-authority blocking
- review requirement enforcement
- validation CLI tooling

Critical rule enforced:

```
execution_authority_claim == false
```

---

### CAM-A3 — Review Packet Generator

Generates human-readable review packets from validated strategy packages.

Outputs include:

- operation summaries
- material assumptions
- safety boundaries
- review checklists
- warnings
- explicit non-execution declarations

---

### CAM-A4 — Strategy Package Manifest

Introduced portable package manifests that bundle:

- strategy JSON
- review packet
- provenance metadata
- authority constraints

---

### CAM-A5 — Strategy Package Assembly

Assembles complete reviewable package directories from validated manufacturing strategies.

Package contents:

```
strategy.json
review_packet.md
manifest.json
```

---

### CAM-A6 — Strategy Package Inspection

Read-only inspection utility for assembled packages.

Provides:

- package type and operation summary
- authority status verification
- file presence checking
- provenance display
- human-readable and JSON output

---

### CAM-A7 — Strategy Package Index

Generates navigable indexes of package collections.

Provides:

- recursive package discovery
- validity summary
- Markdown index output
- optional JSON index
- collection-level metadata

---

## Repository Structure

```
docs/
  operations/           # Operation-specific documentation
  strategy_packages/    # Package format documentation
  workflow/             # Workflow models
  vision/               # Future direction

examples/
  valid/                # Valid strategy examples
  invalid/              # Invalid examples for testing
  packages/             # Assembled package examples

schemas/                # JSON Schema definitions

scripts/                # CLI tools
  validate_strategy_package.py
  generate_review_packet.py
  validate_manifest.py
  assemble_strategy_package.py
  inspect_strategy_package.py
  index_strategy_packages.py
  version.py

tests/                  # Test suite
```

---

## First Operation Focus

The first bounded operation is:

```
fret_slot_strategy
```

This operation was chosen because it is:

- lutherie-specific
- mathematically constrained
- high-value
- reviewable
- does not require full 3D CAM generation

---

## Strategy Package Flow

```
strategy JSON
    |
    v
validation (A2)
    |
    v
review packet generation (A3)
    |
    v
manifest generation (A4)
    |
    v
portable review package (A5)
    |
    v
package inspection (A6)
    |
    v
package index (A7)
    |
    v
human review
    |
    v
downstream CAM tooling
```

---

## CLI Tools

### Validate Strategy

```bash
python scripts/validate_strategy_package.py examples/valid/fret_slot_strategy.json
```

### Generate Review Packet

```bash
python scripts/generate_review_packet.py examples/valid/fret_slot_strategy.json
```

### Validate Manifest

```bash
python scripts/validate_manifest.py examples/valid/fret_slot_strategy_manifest.json
```

### Assemble Package

```bash
python scripts/assemble_strategy_package.py examples/valid/fret_slot_strategy.json
python scripts/assemble_strategy_package.py strategy.json --out ./my_package --force
```

### Inspect Package

```bash
python scripts/inspect_strategy_package.py examples/packages/fret_slot_strategy_example/
python scripts/inspect_strategy_package.py <package_dir> --json
python scripts/inspect_strategy_package.py <package_dir> --quiet
```

### Index Packages

```bash
python scripts/index_strategy_packages.py examples/packages/
python scripts/index_strategy_packages.py examples/packages/ --json-out index.json
```

### Run Tests

```bash
pytest
```

---

## Design Direction

CAM Assist is evolving toward:

```
geometry-aware manufacturing cognition
for lutherie workflows
```

The long-term goal is not generic CAM replacement.

The long-term goal is:

- manufacturing strategy assistance
- topology-aware operation planning
- setup validation
- review systems
- fixture-aware workflow support
- expert manufacturing augmentation

---

## Future Areas

Planned exploration areas include:

- neck profiling strategies
- binding channel workflows
- rosette machining strategies
- fixture modeling
- topology-sensitive operations
- manufacturability review systems
- simulation guidance
- machine capability abstraction

---

## License

TBD

---

## Status Notice

This repository is currently:

```
research
architecture
workflow design
manufacturing strategy exploration
```

It is not production machining software.
