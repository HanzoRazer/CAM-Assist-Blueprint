# CAM-Assist-Blueprint — Roadmap

Reconstructed 2026-08-07 from repository evidence only. See
`SESSION_RECOVERY_2026-08-07.md` for why, and `LEDGER.md` for per-capability
evidence.

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

Test baseline on `main`: **875 collected**.

---

## In flight

### CAM-A23 — Creation Studio Capability Profile — **PR Open**

```text
branch   cam-a23-creation-studio-capability-profile @ 3c3c139
commits  7  (728e62a..3c3c139)
diff     14 files, +3440 / -2
tests    1018 collected on the branch (875 baseline + 143)
pushed   YES       PR  #30 (2026-08-08)      merged  NO
```

The inbound complement of CAM-A22: a read-only contract in which
CAM-Creation-Studio declares what it is capable of authoring. Schema, validator,
creator, tool-generated example, inspector detection, integration doc, dev order,
and README section are all present on the branch.

**It has still shipped nothing.** A PR is not a merge; until #30 lands, CAM-A23
is not part of `main`. Next action is review — not further implementation.

### A19/A20 parity follow-up — **Published, unmerged**

```text
branch   cam-a19-a20-created-at-schema-parity @ 38e0665
commits  1 ahead of main
pushed   YES  (on origin)      PR  #24 merged at 3126c9a, then closed
```

A post-merge documentation fix, committed **and pushed** to the PR #24 branch
after that PR had already merged — so no open PR ever carried it to `main`.
**Preserved pending review.** Not cherry-picked, not folded into the recovery
artifacts. Whether it still applies is an open question, and it should be
resolved on its own terms.

---

## Unverified — must be re-derived before it can become work

```text
review_annotations   annotation timestamp     accepts blank   ?
review_decision_record.reviewed_at            accepts blank   ?
strategy.approval.timestamp                   accepts blank   ?
```

These were asserted in conversation and are **not** substantiated by repository
evidence. Confirming or refuting them against `schemas/` is a prerequisite to any
dev order that references them. If confirmed, they are maintenance work in the
same family as PR #26 — **not** a new capability, and not automatically the next
numbered item.

---

## Unassigned

### A24+ — **not yet authorized**

```text
branch      none
dev order   none
schema      none
script      none
test        none
PR          none
```

There is **no repository evidence of any kind** for A24 or beyond. The number is
not reserved, the scope is not defined, and nothing in this repository implies
what it should be.

A24 is **not** assumed to be next merely because A23 is the highest number in use.
The next capability will be determined from the clean baseline after these
recovery artifacts land and the repository evidence pass is re-run — not inferred
from conversation history.

---

## Cross-repository boundary

CAM-Assist-Blueprint owns two declared contracts touching CAM-Creation-Studio.
Both are CAM-Assist artifacts; neither imports any CAM-Creation-Studio
implementation, and neither creates a runtime dependency:

| Contract | Direction | Status |
| --- | --- | --- |
| CAM-A22 Capability Request | CAM Assist → Creation Studio (outbound, advisory) | Merged |
| CAM-A23 Capability Profile | Creation Studio → CAM Assist (inbound, informational) | PR Open (#30) |

> No CAM-Creation-Studio remediation, DXF-import, geometry-fidelity, G-code
> implementation, or CS-series sequencing is part of this roadmap merely because
> it appeared in a shared conversation. Any legitimate relationship must be
> re-established through CAM-Assist-owned contracts and repository evidence.

The consumer and producer sides of both contracts live in the CAM-Creation-Studio
repository and remain **deferred**. Their absence is not CAM-Assist work.

---

## Ordering constraint

Nothing new should be numbered or scoped until:

1. these recovery artifacts are reviewed and merged (PR #29);
2. the repository evidence pass is re-run from the recovery branch;
3. CAM-A23 is resolved — merged or withdrawn, not merely opened (PR #30);
4. the stranded `38e0665` is reviewed on its own terms;
5. the three Unverified claims are confirmed or refuted against `schemas/`.

Steps 3, 4 and 5 are independent of one another and can proceed in any order.
