# CAM-Assist-Blueprint — Roadmap

Reconstructed 2026-08-07 from repository evidence only. See
`SESSION_RECOVERY_2026-08-07.md` for why, and `LEDGER.md` for per-capability
evidence and current volatile status. PR, branch, SHA, and test-count facts below
are a dated 2026-08-08 snapshot, not a substitute for the ledger.

**This roadmap asserts nothing that the repository cannot substantiate.** No item
here was inherited from conversation. Status vocabulary is the ledger's:
`Merged` / `PR Open` / `Published, unmerged` / `Local Only` / `Specified` /
`Unverified`.

---

## Shipped

Capabilities present on authoritative `main`:

```text
A0   Repository Foundation                A12  Review Decision Record
A1   Fret Slot Strategy Contract          A13  LTB Bridge Infrastructure
A2   Strategy Validation                  A14  External Package Identity
A3   Review Packet Generator              A15  Federation Presentation + Preservation
A4   Strategy Package Manifest            A16  Portable Review Annotations
A5   Strategy Package Assembly            A17  Manufacturing Decision Traceability
A6   Strategy Package Inspection          A18  Revision Lineage
A7   Strategy Package Index               A19  Traceability Bundle
A8   Strategy Package Archive             A20  Production Shop Handoff
A9   Strategy Package Archive Validator   A21  Product Identity and Workflow Demo
A10  Strategy Package Import Staging      A22  CAM-Creation-Studio Capability Request
A11  Staged Package Review Queue Index
```

At the 2026-08-08 snapshot, `main` was `076c6dd` and collected **875 tests**.

---

## In flight

### CAM-A24 — Datetime Blank-Value Hardening — **maintenance-class**

```text
branch   cam-a24-datetime-blank-hardening
dev order docs/dev_orders/CAM-A24.md
```

Adds `minLength: 1` + `pattern: "\S"` to the last three date-time fields that
accepted blank and whitespace-only values, empties the `KNOWN_GAP` allowlist, and
mirrors the guard in `validate_review_annotations.py` — the only one of the three
with a hand validator that reaches the field.

**It is maintenance work, not a capability.** It adds no artifact, schema,
script, or contract. It occupies an A-number by explicit authorization on
2026-08-10 rather than by inference, exactly as the section below anticipated.
See `LEDGER.md`'s supersession and maintenance mapping.

### Landed since the 2026-08-08 snapshot

```text
PR #29  1673b94  recovery artifacts
PR #30  08b3d1b  CAM-A23 Creation Studio Capability Profile
PR #31  efcbb3d  datetime description contract + stranded 38e0665
```

CAM-A23 shipped. The A19/A20 parity follow-up shipped as a cherry-pick
(`d057be9`) inside PR #31, emptying the `Published, unmerged` bucket. `LEDGER.md`
carries current status; the snapshot blocks above are historical.

---

## Confirmed maintenance findings — closed by CAM-A24

```text
review_annotations   annotation timestamp     accepts blank   FIXED
review_decision_record.reviewed_at            accepts blank   FIXED
strategy.approval.timestamp                   accepts blank   FIXED
```

Re-verified directly against `schemas/` on 2026-08-08, then fixed by CAM-A24 on
2026-08-10. All twelve `format: date-time` fields in the repository now reject
empty and whitespace-only values.

They were maintenance work in the same family as PR #26 — **not** a new
capability, and not automatically the next numbered item. Numbering them A24 was
a deliberate authorization, which is why `LEDGER.md` records the classification
alongside the number.

---

## Unassigned

### A25+ — **not yet authorized**

```text
branch      none
dev order   none
schema      none
script      none
test        none
PR          none
```

There is **no repository evidence of any kind** for A25 or beyond. The number is
not reserved, the scope is not defined, and nothing in this repository implies
what it should be.

A25 is **not** assumed to be next merely because A24 is the highest number in
use. The next capability will be determined from the repository baseline — not
inferred from conversation history.

Note that A24 is maintenance work occupying an A-number by authorization, so the
next *capability* is the first since CAM-A23.

---

## Cross-repository boundary

CAM-Assist-Blueprint owns two declared contracts touching CAM-Creation-Studio.
Both are CAM-Assist artifacts; neither imports any CAM-Creation-Studio
implementation, and neither creates a runtime dependency:

| Contract | Direction | Status |
| --- | --- | --- |
| CAM-A22 Capability Request | CAM Assist → Creation Studio (outbound, advisory) | Merged |
| CAM-A23 Capability Profile | Creation Studio → CAM Assist (inbound, informational) | Merged — PR #30 |

> No CAM-Creation-Studio remediation, DXF-import, geometry-fidelity, G-code
> implementation, or CS-series sequencing is part of this roadmap merely because
> it appeared in a shared conversation. Any legitimate relationship must be
> re-established through CAM-Assist-owned contracts and repository evidence.

The consumer and producer sides of both contracts live in the CAM-Creation-Studio
repository and remain **deferred**. Their absence is not CAM-Assist work.

---

## Ordering constraint — satisfied 2026-08-10

Nothing new was to be numbered or scoped until:

1. ~~these recovery artifacts are reviewed and merged (PR #29)~~ — merged `1673b94`;
2. ~~the repository evidence pass is re-run from the recovery branch~~ — re-run;
3. ~~CAM-A23 is resolved — merged or withdrawn, not merely opened (PR #30)~~ — merged `08b3d1b`;
4. ~~the stranded `38e0665` is reviewed on its own terms~~ — reviewed, confirmed still
   needed, landed as `d057be9` in PR #31;
5. ~~the three confirmed date-time defects are separately scoped or explicitly
   deferred~~ — scoped as CAM-A24 and fixed.

All five are discharged. The constraint stays recorded rather than deleted: it is
the checklist the recovery used to decide when planning could resume, and a
future recovery should be able to see that it was followed rather than dropped.
