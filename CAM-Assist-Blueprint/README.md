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

## What CAM Assist Is

A review-first manufacturing strategy and traceability platform that packages manufacturing intent, assumptions, risks, decisions, and handoff metadata — without generating machine instructions or granting execution authority.

See [docs/product/WHY_CAM_ASSIST_EXISTS.md](docs/product/WHY_CAM_ASSIST_EXISTS.md).

## What CAM Assist Is Not

- a CAM engine, post processor, or **G-code generator** (CAM Assist generates no G-code)
- a CNC controller or execution approval system

How it differs from traditional CAM: [docs/product/CAM_ASSIST_VS_CAM_SOFTWARE.md](docs/product/CAM_ASSIST_VS_CAM_SOFTWARE.md).

## Quick Workflow

Reproduce the entire product workflow — manufacturing intent → review → traceability → non-execution handoff — with one command:

```bash
python scripts/run_cam_assist_demo.py --workspace .tmp/cam_assist_demo --keep
```

The same flow is documented command by command in [docs/product/CAM_ASSIST_WORKFLOW.md](docs/product/CAM_ASSIST_WORKFLOW.md).

## Relationship to CAM-Creation-Studio

CAM Assist and CAM-Creation-Studio are separate, companion products. CAM Assist owns intent, review, risk, rationale, and traceability; downstream, execution-oriented assistance would live in CAM-Creation-Studio. Integration is intended to be contract-first, and a future merger remains an open product decision.

See [docs/product/CAM_ASSIST_AND_CAM_CREATION_STUDIO.md](docs/product/CAM_ASSIST_AND_CAM_CREATION_STUDIO.md).

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

### CAM-A8 — Strategy Package Archive

Creates portable `.zip` archives from validated packages.

Provides:

- validation before archiving
- package-relative paths
- overwrite protection
- portable distribution format

---

### CAM-A9 — Strategy Package Archive Validator

Validates archived `.zip` packages before import or review.

Provides:

- archive path safety checks (traversal, absolute paths)
- required file verification
- authority constraint validation
- suspicious file warnings
- safe temporary extraction
- no execution or import side effects

---

### CAM-A10 — Strategy Package Import Staging

Stages validated archives into local review directories.

Provides:

- archive validation before staging
- controlled extraction into review root
- overwrite protection
- subdirectory preservation
- no execution or modification of staged content

---

### CAM-A11 — Staged Package Review Queue Index

Generates review queue indexes from staged packages.

Provides:

- recursive staged package discovery
- validity and warning summary
- human review requirement visibility
- Markdown and JSON queue output
- no execution or approval authority

---

### CAM-A12 — Review Decision Record

Records human review decisions for staged packages.

Provides:

- decision recording (approve, reject, needs_revision)
- reviewer identification
- decision authority constraints
- sibling file output (package not mutated)
- no machine execution authorization

---

### CAM-A14 — External Package Identity

Optional federated identity metadata for cross-system interchange.

Provides:

- origin system identification
- authority domain tagging
- review jurisdiction metadata
- federated package ID

---

### CAM-A15 — Federation Presentation + Preservation

Renders and preserves federated identity through inspection and staging.

Provides:

- federated identity section in inspection output
- archive round-trip preservation
- staging flow preservation
- CI invariant compatibility

---

### CAM-A16 — Portable Review Annotations

External sidecar annotation files for federated review workflows.

Provides:

- reviewer annotations without package mutation
- severity levels (info, warning, concern, blocking)
- conventional path auto-discovery
- review decision linkage
- annotation validation

---

### CAM-A20 — Production Shop Handoff

Read-only, outbound export of a reviewed package toward a future Production Shop runtime.

Provides:

- reference-only handoff sidecar (`CAM Assist → Production Shop`)
- required non-execution authority block (incl. machine-readiness disclaimer)
- structural validation plus an opt-in `--check-references` existence witness
- inspector detection (`Production Shop Handoff: present / not declared`)
- no Production Shop runtime dependency and no execution authority

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
  review_decisions/     # Example review decisions

schemas/                # JSON Schema definitions

scripts/                # CLI tools
  validate_strategy_package.py
  generate_review_packet.py
  validate_manifest.py
  assemble_strategy_package.py
  inspect_strategy_package.py
  index_strategy_packages.py
  archive_strategy_package.py
  validate_package_archive.py
  stage_strategy_package.py
  index_staged_packages.py
  record_review_decision.py
  create_review_annotations.py
  validate_review_annotations.py
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
package archive (A8)
    |
    v
archive validation (A9)
    |
    v
import staging (A10)
    |
    v
review queue (A11)
    |
    v
human review
    |
    v
review decision (A12)
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

### Archive Package

```bash
python scripts/archive_strategy_package.py examples/packages/fret_slot_strategy_example/
python scripts/archive_strategy_package.py <package_dir> --out /tmp/archive.zip --force
```

### Validate Archive

```bash
python scripts/validate_package_archive.py package.zip
python scripts/validate_package_archive.py package.zip --json
python scripts/validate_package_archive.py package.zip --quiet
```

### Stage Package

```bash
python scripts/stage_strategy_package.py package.zip
python scripts/stage_strategy_package.py package.zip --out ./staging/ --force
python scripts/stage_strategy_package.py package.zip --quiet
```

### Generate Review Queue

```bash
python scripts/index_staged_packages.py staged_packages/
python scripts/index_staged_packages.py staged_packages/ --json-out review_queue.json
python scripts/index_staged_packages.py staged_packages/ --quiet
```

### Record Review Decision

```bash
python scripts/record_review_decision.py staged_packages/package \
    --decision approve_for_downstream_cam \
    --reviewer "Reviewer Name" \
    --notes "All checks passed."
```

### Create Review Annotation

```bash
python scripts/create_review_annotations.py \
    --package examples/packages/ltb_vcarve_synthetic_example \
    --reviewer "Manufacturing Reviewer" \
    --severity warning \
    --category tooling \
    --message "Tool deflection risk near tight radius."
```

### Validate Annotations

```bash
python scripts/validate_review_annotations.py examples/review_annotations/ltb_vcarve_synthetic_example_annotations.json
```

### Create Traceability Bundle

```bash
python scripts/create_traceability_bundle.py \
    --package examples/packages/ltb_vcarve_synthetic_example
```

### Validate Traceability Bundle

```bash
python scripts/validate_traceability_bundle.py \
    examples/traceability/ltb_vcarve_synthetic_example_bundle.json --check-references
```

### Create Production Shop Handoff

```bash
python scripts/create_production_shop_handoff.py \
    --package examples/packages/ltb_vcarve_synthetic_example \
    --out examples/production_shop/ltb_vcarve_synthetic_example_handoff.json --force
```

### Validate Production Shop Handoff

```bash
python scripts/validate_production_shop_handoff.py \
    examples/production_shop/ltb_vcarve_synthetic_example_handoff.json --check-references
```

### Run Tests

```bash
pytest
```

---

## Optional Federated Identity

Strategy packages may include optional federated identity metadata for cross-system interchange, such as origin system, authority domain, review jurisdiction, and federated package ID.

These fields are informational only. They do not grant execution authority, validate origin legitimacy, or bypass human review.

See `docs/federation/PACKAGE_IDENTITY_CONVENTIONS.md`.

---

## Review Annotation Sidecars

CAM Assist packages may have external review annotation files that record reviewer concerns, warnings, or notes without modifying the package.

Annotation files are informational only. They do not grant execution authority, validate reviewer legitimacy, or bypass human review.

See `docs/review/REVIEW_ANNOTATIONS.md`.

---

## Manufacturing Decision Traceability

CAM Assist packages may carry external traceability sidecars that capture the manufacturing assumptions, risk assessments, decision records, and revision lineage behind a manufacturing decision — without modifying the package.

- **Manufacturing assumptions** — what was assumed about tooling, material, and fixturing.
- **Risk assessment** — known risks and an overall risk level (informational; does not gate execution).
- **Manufacturing decision record** — a human declaration of *why* a decision was made, optionally linking the assumptions, risk, and lineage sidecars.
- **Revision lineage** — a package-scoped record of *how* the manufacturing reasoning evolved across revisions (a supersession graph of one or more chains; not artifact version control).

These records are informational only. They do not grant execution authority, do not enforce approval authority, and do not bypass human review. The inspector reports them under a `Traceability:` section (explicit `--assumptions` / `--risk` / `--decision-record` / `--lineage` paths first, then a conventional `traceability/` lookup).

See `docs/traceability/MANUFACTURING_ASSUMPTIONS.md`, `docs/traceability/RISK_ASSESSMENT.md`, `docs/traceability/MANUFACTURING_DECISION_RECORDS.md`, and `docs/traceability/REVISION_LINEAGE.md`.

---

## Traceability Bundles (CAM-A19)

A traceability bundle is a portable, **reference-only** sidecar that aggregates a package's traceability records (assumptions, risk, decision record, annotations, lineage) into a single artifact, so the complete review story can move between systems as one unit.

The bundle is a **navigational index**, not a source of truth: it references the sidecars, which remain authoritative. It is informational only — it does not grant execution authority, constitute approval, or modify the package. Validation is two-layered: structural (filesystem-free) by default, plus an opt-in completeness witness (`--check-references`) that warns on unresolved references without changing validity. The inspector reports it under a `Traceability Bundle: present / not declared` section (detection only).

See `docs/traceability/TRACEABILITY_BUNDLES.md`.

---

## Production Shop Handoff (CAM-A20)

A production shop handoff is a portable, **reference-only** sidecar that exports a reviewed package toward a future Production Shop runtime, aggregating references to the package manifest, strategy, review packet, and (when available) its traceability bundle into a single outbound artifact. Direction is outbound only (`CAM Assist → Production Shop`).

The handoff is **informational only**: it does not authorize execution, does not confirm machine readiness, does not mutate packages, and requires no Production Shop runtime code. Its non-execution `authority` block is required, with all four flags `true` (including `does_not_confirm_machine_readiness`). Validation is two-layered: structural (filesystem-free) by default, plus an opt-in existence witness (`--check-references`) that warns on unresolved references without changing validity — or, for CI enforcement, `--fail-on-reference-warnings` to make unresolved references fatal. The inspector reports it under a `Production Shop Handoff: present / not declared` section (detection only).

See `docs/integration/PRODUCTION_SHOP_HANDOFF.md`.

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
