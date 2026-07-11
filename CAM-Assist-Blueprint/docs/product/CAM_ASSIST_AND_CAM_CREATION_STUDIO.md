# CAM Assist and CAM-Creation-Studio

CAM Assist and CAM-Creation-Studio are **separate repositories** and **companion
products**. This document records the current architectural relationship. It does
**not** declare a permanent merger or a permanent separation — that remains an
open product decision.

## Division of responsibility

```text
CAM Assist
  owns:
    intent
    review
    risk
    rationale
    traceability
    portable handoff

CAM-Creation-Studio
  may own:
    machining education
    feeds and speeds
    operation refinement
    toolpath understanding
    G-code authoring
    simulation
    execution-adjacent validation
```

CAM Assist stays upstream of execution; CAM-Creation-Studio is where
execution-oriented, machining-development assistance would live. CAM-Creation-Studio
is **not** defined as the Production Shop runtime — that is a separate concept and
has not been ratified here.

## Boundary statement

```text
A shared workflow does not require a shared repository.
Integration should be contract-first.
A future merger remains a product decision, not an architectural assumption.
```

## Contract-first seam

The relationship is intended to be **contract-first**: CAM Assist describes what
downstream assistance is desired through a portable, non-execution artifact, and a
future consumer may act on it — without either repository importing the other's
runtime.

```text
CAM Assist package
→ Creation Studio capability request
→ optional future Creation Studio consumer
```

The capability-request artifact itself is scoped to a separate order (CAM-A22) and
is not part of this document. **Integration is not complete**: no CAM-Creation-Studio
consumer exists in this repository, and this repository introduces no
CAM-Creation-Studio runtime dependency.

## Why not merge first

Merging two products is a decision that should be made *after* observing whether a
stable contract preserves their strengths — not assumed up front. Keeping the
repositories separate and connecting them through an explicit, reviewable contract
lets each product remain coherent while the companion-vs-converge question is
answered by real use.
