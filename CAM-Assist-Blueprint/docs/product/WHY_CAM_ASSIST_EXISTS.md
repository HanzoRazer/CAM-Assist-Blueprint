# Why CAM Assist Exists

## Problem

Manufacturing a one-off instrument part involves far more reasoning than a
toolpath captures. A luthier decides how a feature will be held, which tool is
appropriate, what the material can tolerate, where the risks are, and why one
approach was chosen over another. Traditional CAM software records almost none of
this: it turns geometry into machine instructions and discards the reasoning
along the way. When a part is revisited months later — or handed to another shop —
that reasoning is gone.

CAM Assist exists to **preserve manufacturing reasoning as a first-class,
portable, reviewable artifact**, separate from (and upstream of) machine
execution.

## Product Boundary

CAM Assist is a review-first manufacturing strategy and traceability platform. It
packages manufacturing intent, assumptions, risks, decisions, and handoff
metadata **without generating machine instructions or granting execution
authority**.

```text
CAM Assist preserves manufacturing reasoning.
It does not convert that reasoning into machine execution.
```

## What CAM Assist Owns

- Manufacturing **intent** and strategy (parameters, not toolpaths)
- Human-readable **review packets**
- Portable **package manifests** and assembled packages
- **Assumptions**, **risk assessments**, **decision records**, and **revision lineage**
- **Traceability bundles** that aggregate the review story
- A read-only, outbound **Production Shop handoff**
- The **human review** workflow and its recorded decisions

## What CAM Assist Does Not Own

- Toolpath generation
- Simulation
- **G-code generation** — CAM Assist generates no G-code
- Post-processing
- Machine execution or machine control
- Any claim that a package is machine-ready or approved for execution

These are downstream, execution-oriented responsibilities. CAM Assist stops
before them by design.

## Primary Users

- **Luthiers and manufacturing engineers** documenting and reviewing a strategy
  before anything is cut.
- **Reviewers** who need to see assumptions, risks, and rationale to make an
  informed human decision.
- **Downstream operators / CAM specialists** who receive a reviewed, portable
  package and take it into traditional CAM.

## Core Workflow

```text
Design Intent
  → Manufacturing Strategy
  → Review Packet
  → Portable Package (manifest + strategy + review)
  → Human Review + Decision
  → Traceability (assumptions, risk, decisions, lineage, bundle)
  → Production Shop Handoff (reference-only, non-execution)
  → Downstream CAM
```

See [CAM_ASSIST_WORKFLOW.md](CAM_ASSIST_WORKFLOW.md) for the same flow demonstrated
with real repository commands.

## Human Authority

Human authority over manufacturing decisions is non-negotiable. Every package is
advisory until a human records a review decision. No artifact in CAM Assist
authorizes execution, and nothing bypasses required human review.

## Why Portability Matters

A strategy package is a single, self-describing unit that can move between
systems, reviewers, and shops without a live connection to the tool that produced
it. Portability is what lets the *reasoning* — not just the geometry — survive the
handoff to whoever machines the part.

## Relationship to Downstream CAM

CAM Assist is **upstream of execution**. The contrast with traditional CAM:

```text
Traditional CAM:
CAD → CAM → Toolpath → Post → Machine

CAM Assist:
Design Intent → Manufacturing Strategy → Review → Portable Package
                                                   ↓
                                             Downstream CAM
```

Traditional CAM begins roughly where CAM Assist ends. The two are complementary:
CAM Assist captures and reviews the reasoning; downstream CAM turns an
already-reviewed strategy into machine motion. See
[CAM_ASSIST_VS_CAM_SOFTWARE.md](CAM_ASSIST_VS_CAM_SOFTWARE.md) for a capability
comparison and
[CAM_ASSIST_AND_CAM_CREATION_STUDIO.md](CAM_ASSIST_AND_CAM_CREATION_STUDIO.md) for
the companion-product relationship.
