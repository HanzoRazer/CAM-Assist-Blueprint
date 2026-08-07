# Session Recovery — 2026-08-07

**Repository scope: CAM-Assist-Blueprint only.**

This notice records a repository-context contamination event, freezes the
authoritative baseline, and re-derives the A-series inventory from repository
evidence. It changes no capability semantics and reverts no verified commit.

---

## 1. Contamination window

Planning derived after CAM-Creation-Studio **CS-008 / CS-008R** implementation
state entered the CAM-Assist planning thread is **non-authoritative** for this
repository and must be independently re-derived before it influences any decision
here.

The contamination ran in two directions:

1. CAM-Assist work was discussed as though it belonged to CAM-Creation-Studio.
2. CAM-Creation-Studio audit and re-audit findings were then allowed to steer
   CAM-Assist planning.

CAM Assist and CAM-Creation-Studio are **separate products with separate
constitutions.** They are deliberately adjacent, but they are not one engineering
backlog.

## 2. Cross-repository warning

> No CAM-Creation-Studio remediation, DXF-import, geometry-fidelity, G-code
> implementation, or CS-series sequencing is part of the CAM-Assist-Blueprint
> roadmap merely because it appeared in the contaminated conversation. Any
> legitimate relationship must be re-established through CAM-Assist-owned
> contracts and repository evidence.

CAM-Assist owns exactly two declared contracts touching that product, both of
which are CAM-Assist artifacts and neither of which imports any CAM-Creation-Studio
implementation: the **CAM-A22 Capability Request** (outbound, merged) and the
**CAM-A23 Capability Profile** (inbound, read-only, not yet published). Nothing in
the CS-series changes their scope.

## 3. Evidence hierarchy

**Authoritative**

```text
git history
merged and open PRs belonging to CAM-Assist-Blueprint
docs/dev_orders/
schemas/
scripts/
examples/
tests/
repository architecture and governance documentation
```

**Non-authoritative until re-derived**

```text
conversational roadmap claims
"next authorized work" statements
cross-repository implementation assumptions
dev orders written during the contaminated window
```

## 4. Preserved engineering

No verified CAM-Assist commit is reverted. Contaminated *planning* is discarded;
contaminated *code* does not exist, because every commit in this repository
remains attributable to a numbered capability with repository evidence.

Sentence-by-sentence salvage of the contaminated window was explicitly **not**
attempted. The window is treated like a failed CI run: discard the derived
planning, keep the verified commits, regenerate planning from the repository.

---

## 5. A-series inventory

Statuses are defined in `LEDGER.md` and used consistently across all recovery
artifacts. Full per-capability detail lives there; this is the summary.

| Bucket | Capabilities |
| --- | --- |
| Merged | A0–A18, A19, A20, A21, A22 |
| PR Open | *(none — `gh pr list` returns empty for this repository)* |
| Local Only | **CAM-A23 Creation Studio Capability Profile**; A19/A20 parity follow-up `38e0665` |
| Specified | *(none — every dev order A18–A23 has an implementation)* |
| Unverified | three blank-accepting date-time fields (§8) |

Test baseline: **875 collected on `main`**; 1018 on the unpublished CAM-A23 branch.

---

## 6. CAM-A23 designation collision — recorded and ruled

The A23 number was used twice in repository artifacts:

```text
PR #26   874fcb0   cam-a23-created-at-schema-consistency      MERGED to main
                   no dev order, no README section

local    3c3c139   cam-a23-creation-studio-capability-profile LOCAL ONLY
                   docs/dev_orders/CAM-A23.md, README section, 7 commits
```

Reading `main`'s history and reading `docs/dev_orders/` produced two different
answers for "what is CAM-A23".

### Ruling

- PR #26 / created_at schema consistency is **maintenance and governance work,
  not an A-series capability.** It is retro-designated as such and **no longer
  occupies the A23 capability number.**
- **CAM-A23 remains Creation Studio Capability Profile**, because that is the
  numbered dev order and implementation branch already established in repository
  artifacts.
- **Historical merged capabilities are not renumbered.** PR #26's commits stay
  exactly where they are; only its *designation* changes.

The collision is recorded in `LEDGER.md` under supersession/maintenance mapping so
that a future reader encountering `cam-a23-created-at-schema-consistency` in the
git history can resolve it without re-deriving this analysis.

---

## 7. Orphaned commit — preserved, not folded in

```text
branch  cam-a19-a20-created-at-schema-parity @ 38e0665
        "docs: decouple created_at description from validator internals (PR #24)"
        1 commit ahead of main, never published
PR #24  MERGED at head 3126c9a
```

A post-merge documentation fix was committed locally after PR #24 merged and never
reached `main`. It is **preserved as a separate local-only follow-up pending
review.** It has deliberately **not** been folded into these recovery artifacts,
cherry-picked, or merged. Whether it still applies is a separate decision.

---

## 8. Unverified claims

The following originated in conversation, not repository evidence, and are
**Unverified** until confirmed by direct schema inspection:

```text
review_annotations   annotation timestamp     accepts blank
review_decision_record.reviewed_at            accepts blank
strategy.approval.timestamp                   accepts blank
```

They must not be promoted to a dev order until re-derived from `schemas/`.

---

## 9. Front-door documentation gaps

Five merged capabilities had no README capability section, so the front-door index
under-reported shipped work. Reconciled in this recovery (see `LEDGER.md` "README"
column):

```text
CAM-A13  LTB Bridge Infrastructure
CAM-A17  Manufacturing Decision Traceability
CAM-A18  Revision Lineage
CAM-A19  Traceability Bundle
CAM-A21  Product Identity and Workflow Demo
```

A maintenance note for PR #26 was added rather than presenting it as a capability.
No historical capability semantics were rewritten.

Separately: dev orders exist only from A18 onward. A0–A17 predate the convention.
This is an asymmetry, not a defect, and no retrospective dev orders were invented.

---

## 10. A24 and beyond

**A24+ has no repository evidence of any kind.** No branch, no dev order, no
schema, no script, no test, no PR.

The next capability number and scope are **not assigned by this recovery.** They
are to be determined from the clean baseline after these artifacts land and the
repository evidence pass is re-run from the recovery branch — not inherited from
the contaminated conversation, and not assumed to be "A24" merely because A23 is
the highest number currently in use.

---

## 11. Recovery completion criteria

```text
[x] A-series inventory rebuilt from repository evidence
[x] every capability carries an evidence-backed status
[x] open PRs and local-only branches identified separately
[x] constitutional gaps identified
[ ] next dev order regenerated from the clean baseline   <- deliberately NOT done here
```

The final item is intentionally outstanding. Planning resumes only after these
artifacts are reviewed and the evidence pass is re-run.
