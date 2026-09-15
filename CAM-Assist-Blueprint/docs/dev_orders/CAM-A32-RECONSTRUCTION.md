# CAM-A32 Reconstruction — Indexed Surface Continuity Metrology

## Classification

```text
reconstruction program
Phase R0 only — provenance and evidence reconciliation
not recovered Git history
not publication
not merge
not schema implementation
```

This document is a **new reconstruction order**. It is not the lost
CAM-A32 Phase 12 Git object, and it is not a claim that that object was
found.

Logical identity:

```text
cam-a32-reconstructed-surface-metrology
```

Git identity (this branch):

```text
cursor/cam-a32-reconstructed-surface-metrology-4e0c
```

The logical name is the provenance-visible identity. The Git branch name
follows current Cloud Agent convention. Do not treat the `cursor/` prefix
or the `-4e0c` suffix as part of the historical CAM-A32 branch.

---

## Provenance declaration

```text
Original historical branch: cam-a32-indexed-surface-continuity-metrology
                            NOT RECOVERED
Historical Phase 12 SHA:    058abb169754ebbfa2c38458ffcc64fc6de96452
                            NOT RECOVERED
This branch:                reconstructed implementation (R0: order only)
Git identity:               new
Source of truth:            surviving accepted architecture
                            + current repo conventions
```

Do not reuse the unrecovered branch name without a `-reconstructed`
suffix. Do not assign `058abb1` or any other historical SHA to new
commits. Do not simulate the lost object graph.

---

## Authorization in force

Exact-history recovery of `058abb1` is **abandoned**. Reconstruction is
authorized as a **new Git lineage**.

This turn authorizes **Phase R0 only**:

* create this reconstruction order;
* record the three surviving evidence layers;
* mark `058abb1` unrecovered;
* reconcile original design vs later implementation vs Phase 12
  provenance;
* name what is still missing.

**Phase R1 remains blocked.** Do not write production schemas,
validators, processors, examples, or tests until the final contract
inventory and canonical synthetic input truth are recovered, or until
those missing inputs are separately and explicitly re-authorized as
reconstructed.

Publication status authorized for this reconstruction lineage:

```text
draft PR for review    authorized
mark-ready             not authorized
merge                  not authorized
```

`LEDGER.md` and `ROADMAP.md` CAM-A31 rows stay as they are. This order
does not silently repair unrelated ledger staleness. An A32
reconstruction row belongs in a later documentation phase, not in R0.

---

## What this document is allowed to use

Three evidence layers exist. They are **not** the same thing.

### Layer 1 — Original design authority

Cited surviving source (File Library; not a Git object on this
repository):

```text
CAM-A20 — Indexed Surface Continuity Metrology
```

This is the precursor design order that was later **renumbered** into
CAM-A32. It is **not** the shipped CAM-A20 on current `main`.

Current `main` already occupies `CAM-A20` as **Read-Only Production Shop
Handoff** (`docs/dev_orders/CAM-A20.md`, merged). That numbering collision
is why reconstruction continues as **CAM-A32**, not as a revival of the
A20 number.

Layer 1 is authority for:

* initial contracts and vocabulary;
* file / subsystem boundaries;
* physical intent;
* original synthetic slab case as *design* illustration.

Layer 1 is **not** a license to copy the original design verbatim where
later accepted implementation evidence superseded it.

### Layer 2 — Later accepted implementation evidence

Cited surviving source (File Library; not a Git object on this
repository):

```text
Gate 2 implementation audit
```

Layer 2 is authority for **what the final CAM-A32 implementation
actually enforced**, including:

* the D18–D46 compliance table as an audit of the lost implementation;
* accepted registration semantics;
* duplicate behavior;
* inheritance semantics;
* the canonical numerical **outputs** of the accepted synthetic case;
* two defects that were subsequently remediated (names not recovered in
  this workspace).

Where Layer 1 and Layer 2 disagree, **Layer 2 wins on implemented
behavior**. Layer 1 remains the physical-intent and vocabulary baseline
except where Layer 2 explicitly superseded it.

### Layer 3 — Historical provenance authority

Cited surviving source:

```text
Phase 12 evidence (ruling recoverability)
```

Layer 3 is the only authority for what may be called a **recovered
ruling**. Twelve ruling numbers have recoverable evidence. Twelve do
not. Missing IDs stay **explicitly unrecovered**. Do not backfill them
from Layer 1, from Layer 2 summaries, or from plausible interpretation.

### What this document is not

```text
NOT recovered Git history
NOT the lost schemas
NOT the lost canonical Scan A/B input corpus
NOT a claim that File Library files were recovered as Git objects
NOT authorization to invent production contracts
```

The File Library packet was cited by the owner as the strongest
surviving specification source. This workspace did **not** mount those
files. Extracts recorded here are **owner-cited conversation artifacts**
plus the CAM-A32-RECOVERY-003 reconstruction handoff, reconciled against
current `main`. They are not independently opened binaries and they are
not `058abb1`.

---

## Current `main` inventory (this reconstruction base)

Recorded against:

```text
base branch    origin/main
base HEAD      b01213c7367e901b3870dd5b30287f0b5c6aaedf
               Merge pull request #40 (AGENTS.md scaffolder)
```

CAM-A31 pickup-route support is already on this `main` (`8943989`,
PR #39). `LEDGER.md` still says A31 is PR Open. That mismatch is an
unrelated defect and is **left untouched**.

CAM-A32 inventory on this base:

```text
docs/dev_orders/CAM-A32.md          absent
docs/metrology/                     absent
schemas/surface_scan.schema.json    absent
schemas/setup_registration.schema.json  absent
schemas/surface_state.schema.json   absent
scripts/*surface*                   absent
examples/surface_metrology/         absent
tests/*surface* / *metrology*       absent
origin branches matching a32/metrology/reconstruction   none
```

`ROADMAP.md` still records A32+ as unassigned, with no repository
evidence. That statement is true of Git objects. It is no longer true
of **surviving specification evidence outside Git**. This reconstruction
order exists so those two facts stay distinct.

Current mechanics that later phases must adapt to (semantics stay
CAM-A32; mechanics follow current `main`):

```text
A29 reference authority   scripts/_shared/artifact_references.py
                          relative_reference()
                          resolve_declared_reference()
A28 coherence authority   scripts/_shared/package_coherence.py
                          ARTIFACT_ORDER
                          PACKAGE_SCOPED_IDENTITY
                          validator dispatch
                          no metrology recomputation
Bundle slots today        assumptions_file
                          risk_file
                          decision_record_file
                          annotations_file
                          lineage_file
                          (no surface_state_file / registration_file)
Creator flags             --force and --quiet already exist on
                          current creator CLIs
Example family layout     examples/<family>/ plus package-adjacent
                          conventional discovery
```

`scripts/_shared/metrology_io.py` is **not** justified yet. A29 already
owns portable references. R0 does not create a parallel IO helper.

---

## Frozen architectural boundary

These remain frozen for any later reconstruction phase. Reconstruction
on newer `main` is not a redesign license.

```text
Measurement:            offline / imported only
Live sensor control:    none
Coordinates:            canonical workpiece frame
Setup transform:        translation only
Plane fitting:          deterministic
Registration:           physical overlap, plane-to-plane
z_offset:               centroid-evaluated
Tilt / divergence:      explicit
Duplicate grid:         refuse (do not average)
Interpolation:          none
Reference planes:       declared or inherited
Inherited plane:        copied verbatim
Evidence family:        surface_metrology/
A29:                    sole reference-path authority
A28:                    provenance-coherence authority only
Inspector:              descriptive; no recomputation
Review packet:          advisory; no recomputation; no execution
                        authority
Machine execution:      none
G-code:                 none
Work-offset control:    none
Automatic surfacing:    none
```

---

## Phase 12 ruling recoverability

Layer 3. Do not assign meanings to unrecovered identifiers.

### Evidenced / recoverable ruling numbers

```text
D18  D19  D20  D21  D22  D23
D26
D28  D29
D35  D36
D45
```

The numbers are recovered. The **verbatim ruling definitions** were not
present as Git objects on this base, and were not independently opened
from File Library in this workspace. Later phases may quote Layer 2's
compliance table when that table is in hand. They may not invent
definitions for these IDs.

### Unrecovered definitions

```text
D24  D25  D27
D30  D31  D32  D33  D34
D37  D38
D44  D46
```

Keep these IDs listed as unrecovered. Do not infer their content from
Layer 1 vocabulary, from Gate 2 numerical witnesses, or from current
`main` conventions.

---

## Reconciliation table

Status vocabulary for the last column:

| Status | Meaning |
| --- | --- |
| **HOLD — Layer 1** | Original design still governs; not known to be superseded |
| **HOLD — Layer 2** | Later implementation evidence supersedes the original design |
| **HOLD — Layer 3** | Provenance rule; do not backfill |
| **SUPERSEDED** | Original design must not be copied verbatim |
| **STILL MISSING** | Needed before Phase R1 / later phases; do not invent |
| **CURRENT MAIN** | Reconstruct using current repository mechanics |

### Identity and provenance

| Topic | Original design (Layer 1) | Later implementation evidence (Layer 2) | Phase 12 / reconstruction (Layer 3) | Status |
| --- | --- | --- | --- | --- |
| Capability number | Titled **CAM-A20 — Indexed Surface Continuity Metrology** | Implemented as CAM-A32 | Reconstruct as CAM-A32. Do not reuse shipped A20 (Production Shop Handoff). | SUPERSEDED numbering; HOLD CAM-A32 |
| Historical Git branch | Not a Git fact in Layer 1 | Lost implementation lived on `cam-a32-indexed-surface-continuity-metrology` | Branch **NOT RECOVERED**. Do not reuse without `-reconstructed`. | HOLD — Layer 3 |
| Historical Phase 12 SHA | n/a | n/a | `058abb169754ebbfa2c38458ffcc64fc6de96452` **NOT RECOVERED** | HOLD — Layer 3 |
| This lineage | n/a | n/a | New Git identity; reconstructed implementation | HOLD — Layer 3 |

### Contracts and files

| Topic | Original design (Layer 1) | Later implementation evidence (Layer 2) | Phase 12 / reconstruction (Layer 3) | Status |
| --- | --- | --- | --- | --- |
| Three records | Surface scan, setup registration, surface state | Same three-record family enforced | Reconstruct the same three record contracts; no new schema version unless current governance requires it | HOLD — Layer 2 family; schemas STILL MISSING |
| `surface_scan.schema.json` | Example record shapes / partial samples | Final committed schema not recovered here | Do not write production schema in R0 | STILL MISSING |
| `setup_registration.schema.json` | Example record shapes / partial samples | Final committed schema not recovered here | Do not write production schema in R0 | STILL MISSING |
| `surface_state.schema.json` | Example record shapes / partial samples | Final committed schema not recovered here | Do not write production schema in R0 | STILL MISSING |
| Evidence family | Design-level file boundaries | `surface_metrology/` family accepted | Reconstruct under current example-sidecar convention (`examples/surface_metrology/` or current equivalent) | HOLD — Layer 2; path follows CURRENT MAIN |

### Reference planes and registration

| Topic | Original design (Layer 1) | Later implementation evidence (Layer 2) | Phase 12 / reconstruction (Layer 3) | Status |
| --- | --- | --- | --- | --- |
| `reference_plane.source` | Allowed `"overlap_fit" \| "declared" \| "bed_plane"` | Fitting a reference plane from the **current rough surface** was refused | Do not restore `overlap_fit` / current-rough fitting as a live source | SUPERSEDED |
| Inherited plane | Present in original design | Inherited plane copied **verbatim**; not modified by registration delta | Verbatim copy is required; falsify any mutation by registration delta | HOLD — Layer 2 |
| Registration model | `agreement` block | Plane-to-plane over the **declared overlap**; evidence includes `evaluated_at`, `z_offset`, separate tilts, `max_divergence` | Reconstruct Layer 2 evidence shape, not the original `agreement` block as the primary record | SUPERSEDED |
| Transform | Translation-only intent | Translation-only setup transform | Translation-only; no 6-DOF | HOLD — Layer 2 |
| `z_offset` | Physical continuity intent | Centroid-evaluated | Evaluate at overlap centroid | HOLD — Layer 2 |
| Overlap | Physical overlap registration | Declared overlap is the registration domain | Do not invent an undeclared overlap crawler | HOLD — Layer 2 |
| Verdict vocabulary | Original `agreement` framing | Canonical witness uses `verdict = agrees` | Closed enum besides `agrees` is not recovered here | STILL MISSING (full enum) |

### Surface classification and stock

| Topic | Original design (Layer 1) | Later implementation evidence (Layer 2) | Phase 12 / reconstruction (Layer 3) | Status |
| --- | --- | --- | --- | --- |
| Cell classes | Explicit five-class enum: `at_plane \| within_allowance \| stock_remains \| below_plane \| unmeasured` | Canonical counts reported as four measured buckets plus unmeasured | Keep the five named classes. Do **not** invent a mapping from `12/2/2/1` onto those names until Gate 2 table or input truth says which is which | HOLD — Layer 1 names; count-to-name map STILL MISSING |
| Remaining stock | Closed-form remaining-stock relation | Same physical intent; no interpolation | Closed-form only | HOLD — Layer 1 + Layer 2 |
| Interpolation | Forbidden | Forbidden | Forbidden. Falsify any averaging / interpolation of empty cells | HOLD — Layer 2 |
| Duplicate observations | Design-level refusal | Duplicate-grid refusal; no averaging; State A/B witnesses show `duplicates 0` | Refuse duplicates; do not average | HOLD — Layer 2 |
| Grid capture | Original synthetic slab case | Capture-tolerance / duplicate / unmatched behavior enforced | Threshold values not recovered here | STILL MISSING (numeric thresholds) |

### Canonical synthetic case

| Topic | Original design (Layer 1) | Later implementation evidence (Layer 2) | Phase 12 / reconstruction (Layer 3) | Status |
| --- | --- | --- | --- | --- |
| Slab identity | Original synthetic slab case (design illustration) | Gate 2 canonical **outputs** for Registration A→B, State A, State B | Outputs are accepted witnesses. They are **not** a substitute for committed point inputs | HOLD — Layer 2 outputs |
| Scan A / Scan B points | Partial samples only | Final Gate 2 canonical input corpus not recovered | Target names below; do not reconstruct schemas from expected summaries alone | STILL MISSING |
| Import / state / registration specs | Partial example shapes | Final input specs not recovered | Same | STILL MISSING |

Accepted **outputs** (Layer 2). Independently regenerate later from
committed synthetic truth; do not hardcode as the only source of truth:

```text
Registration A→B
evaluated_at    (108.0, 18.0)
z_offset        0.001
tilt_a          0.0001
tilt_b          0.0
max_divergence  0.0022
verdict         agrees

State A
18 total / 17 measured
12 / 2 / 2 / 1
1 unmeasured
max 0.020
min -0.004
coverage 17/18
unmatched 0
duplicates 0

State B
18 total / 17 measured
3 / 3 / 10 / 1
1 unmeasured
max 0.0918
min -0.0254
coverage 17/18
unmatched 1
duplicates 0
```

`previous_plane = 0.0 / 0.0`, `current_plane = 0.0001 / -0.0098`, and
sample counts `6 / 6` remain accepted registration witnesses from the
reconstruction handoff. Their exact field names in the lost schema are
**STILL MISSING**.

### Processors, packaging, and authority

| Topic | Original design (Layer 1) | Later implementation evidence (Layer 2) | Phase 12 / reconstruction (Layer 3) | Status |
| --- | --- | --- | --- | --- |
| Import | Offline measurement import; CLI shapes in the original order | CSV and JSON import; malformed-row refusal; extra-column policy | Reconstruct processors only after contracts exist. Extra-column policy text is not in this workspace | STILL MISSING (policy detail) |
| CLI (accepted reconstruction shape) | Original order defined CLIs | Same family of import / registration / state processors | `import_surface_scan.py`, `compute_setup_registration.py`, `compute_surface_state.py`; `--force` / `--quiet` only where current conventions support them | HOLD — Layer 2 + CURRENT MAIN |
| D45 replacement safety | n/a as recovered text | `--force` must not delete a previous file on failed replacement | Keep as a load-bearing falsification even without the verbatim D45 paragraph | HOLD — Layer 2 behavior; verbatim D45 text STILL MISSING |
| A29 | Not the later A29 maintenance order | Reference semantics delegated | A29 is sole reference authority; do not duplicate `relative_reference` / `resolve_declared_reference` | HOLD — Layer 2 + CURRENT MAIN |
| A28 | Not the later A28 capability | Provenance graph; optional artifacts; no numerical recomputation | Audit identity/reference coherence only | HOLD — Layer 2 + CURRENT MAIN |
| Bundle entry points | Design-level packaging | Optional designated `surface_state_file`, `registration_file` | Add only those optional slots when R8 is authorized | HOLD — Layer 2 |
| Inspector | Descriptive | No recomputation | Descriptive persisted evidence only | HOLD — Layer 2 |
| Review packet | Advisory | Optional Surface Metrology section; resolution stays outside the formatter; no execution-authority wording | Same | HOLD — Layer 2 |
| Execution | None | None | None. No G-code, work-offset, live laser, AI sensor control, or automatic flattening | HOLD — all layers |
| Two Gate 2 defects later remediated | n/a | Existence recorded; identities not recovered in this workspace | Do not guess the defect names | STILL MISSING |
| Orphan limitation | Known limitation in the lost program | Orphan out-of-scope behavior tested | Precise orphan write-up not recovered here | STILL MISSING (precise statement) |

---

## Remaining artifact search (narrow)

R1 stays blocked until these are recovered **or** separately
re-authorized as reconstructed:

```text
surface_scan.schema.json
setup_registration.schema.json
surface_state.schema.json

slab24_setup_a_capture.csv / JSON
slab24_setup_b_capture.csv / JSON
slab24_setup_a_import.json
slab24_setup_b_import.json
slab24_setup_a_state input spec
slab24_setup_b_state input spec
registration input spec
```

Search performed from this reconstruction workspace against current
`main`, `origin` heads, and owner GitHub code search: **none of the
above were present**. That is a Git-object result. It does not prove
the File Library packet lacks excerpts; it proves they are not in this
repository.

Also still missing for honest reconstruction, even after contracts
exist:

```text
verbatim evidenced ruling texts (D18–D23, D26, D28–D29, D35–D36, D45)
Gate 2 classification count → enum mapping
registration verdict enum besides "agrees"
grid origin / pitch / capture-tolerance numbers
extra-column import policy
the two remediated Gate 2 defect identities
precise orphan-limitation statement
```

Do not fill those from guesswork.

---

## Reconstruction program (later phases — not authorized by R0)

Keep the staged sequence. Each phase must be independently green before
the next. R0 does not start R1.

```text
Phase R0   provenance + reconciliation          THIS DOCUMENT
Phase R1   schemas / contracts                  BLOCKED
Phase R2   numerical kernel
Phase R3   validators + import
Phase R4   registration processor
Phase R5   surface-state processor
Phase R6   canonical synthetic evidence
Phase R7   A29 reference convergence
Phase R8   bundle / package integration
Phase R9   A28 provenance graph
Phase R10  inspector
Phase R11  review packet
Phase R12  documentation / governance
Phase R13  final reconstruction verification
```

Suggested later commit pattern (not used by this R0 commit except the
first line):

```text
docs: define CAM-A32 reconstruction provenance
feat: reconstruct CAM-A32 metrology contracts
feat: reconstruct deterministic surface metrology mathematics
feat: reconstruct CAM-A32 metrology processors
test: restore canonical CAM-A32 evidence
refactor: converge reconstructed metrology references on A29
feat: package reconstructed CAM-A32 evidence
feat: audit reconstructed metrology provenance
feat: inspect reconstructed surface metrology evidence
feat: present reconstructed metrology for human review
docs: document reconstructed CAM-A32 subsystem
test: verify reconstructed CAM-A32 end to end
```

---

## Non-goals

Do not add, in this order or in later reconstruction unless separately
authorized:

* claiming recovery of `058abb1`;
* fabricating old commits or assigning old SHAs to new code;
* assigning meanings to unrecovered ruling IDs;
* copying Layer 1 `overlap_fit` / `bed_plane` / `agreement` where Layer 2
  superseded them;
* writing production schemas during R0;
* inventing canonical Scan A/B points from the accepted output summaries;
* live laser / profiler integration;
* AI sensor control;
* automatic CNC flattening;
* G-code, toolpaths, work-offset writing;
* 6-DOF registration;
* interpolation or new surface classes;
* orphan scanning / generalized graph crawling;
* unrelated scaffolder work;
* cp1252 repair;
* CAM-A33;
* silently fixing the stale A31 ledger/roadmap rows;
* merge or mark-ready without a separate authorization.

---

## R0 completion criterion

Phase R0 is complete when this repository contains an **explicit
reconstruction order** that:

1. declares the lineage reconstructed, not recovered;
2. records the three evidence layers and their precedence;
3. shows where the original design must not be copied;
4. lists what is still missing;
5. leaves schemas, processors, and tests unwritten.

```text
ORIGINAL CAM-A32 HISTORY
058abb1: NOT RECOVERED

RECONSTRUCTION
branch:  cursor/cam-a32-reconstructed-surface-metrology-4e0c
base:    origin/main @ b01213c7367e901b3870dd5b30287f0b5c6aaedf
phase:   R0 only

contracts:             NOT STARTED (blocked)
math:                  NOT STARTED
processors:            NOT STARTED
canonical evidence:    OUTPUTS RECORDED; INPUTS MISSING
A29 / A28 / inspector / review packet: NOT STARTED
historical identity reused: NO
reconstruction provenance explicit: YES

VERDICT:
PHASE R0 COMPLETE — PHASE R1 BLOCKED
```

Then stop.
