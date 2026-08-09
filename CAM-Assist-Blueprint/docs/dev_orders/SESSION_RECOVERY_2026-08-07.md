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
| PR Open | **CAM-A23 Creation Studio Capability Profile** — PR #30, opened 2026-08-08 |
| Published, unmerged | A19/A20 parity follow-up `38e0665` — on `origin`, no open PR |
| Local Only | *(none)* |
| Specified | *(none — every dev order A18–A23 has an implementation)* |
| Unverified | three blank-accepting date-time fields (§8) |

Statuses above are current as of 2026-08-08; see §12 for what changed and why.

Test baseline: **875 collected on `main`**; 1018 on the unmerged CAM-A23 branch.

---

## 6. CAM-A23 designation collision — recorded and ruled

The A23 number was used twice in repository artifacts:

```text
PR #26   874fcb0   cam-a23-created-at-schema-consistency      MERGED to main
                   no dev order, no README section

PR #30   3c3c139   cam-a23-creation-studio-capability-profile OPEN, not merged
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

## 7. Stranded commit — preserved, not folded in

```text
branch  cam-a19-a20-created-at-schema-parity @ 38e0665
        "docs: decouple created_at description from validator internals (PR #24)"
        1 commit ahead of main
        PUSHED — present on origin at refs/heads/cam-a19-a20-created-at-schema-parity
PR #24  MERGED at head 3126c9a, closed
```

A post-merge documentation fix was committed **and pushed** to the PR #24 branch
after that PR had already merged. Because the PR was closed, the commit never had
an open PR to carry it, and it never reached `main`.

It is therefore **published but unmerged** — not local-only, and not orphaned in
the git sense. Its true state has no open PR attached to it, which is precisely
why it went unnoticed.

It is **preserved pending review**: deliberately **not** folded into these
recovery artifacts, cherry-picked, or merged. Whether it still applies is a
separate decision.

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

---

## 12. Corrections — 2026-08-08

This notice was drafted on 2026-08-07 and corrected on 2026-08-08 before merge.
The corrections are recorded rather than silently applied, because a recovery
document that quietly rewrites itself is not evidence.

**Correction 1 — `38e0665` was wrongly described as unpublished.**

§5 and §7 originally placed `cam-a19-a20-created-at-schema-parity` @ `38e0665`
in `Local Only` and stated it was "never published." It is on `origin`:

```text
$ git ls-remote --heads origin cam-a19-a20-created-at-schema-parity
38e0665eaaabf15ea050c279d381a8faca8c8323  refs/heads/cam-a19-a20-created-at-schema-parity
```

Corrected to `Published, unmerged`. `LEDGER.md` gained that status because the
original vocabulary could not express it: `PR Open` requires an open PR, and
PR #24 is merged and closed.

A likely cause, offered so the mistake is not repeated: `git branch -vv` shows
this branch with no ahead/behind marker, which means *in sync with its remote* —
easily misread as *has no remote*. `git ls-remote` is the unambiguous check.

**Correction 2 — CAM-A23 is no longer Local Only.**

On 2026-08-08 the branch was pushed and **PR #30** was opened against `main`.
§5 and §6 are updated accordingly. Nothing about the capability changed; only
its publication status did. It remains unmerged.

**Still standing as written:** the contamination ruling (§1–§4), the CAM-A23
designation ruling (§6), the README gap reconciliation (§9), and the refusal to
assign A24 (§10).

**§8 is deliberately left as written.** All three date-time claims have since
been confirmed as real defects by direct schema inspection, so the section's
caution was warranted rather than wrong. Promoting them from `Unverified` to
`Confirmed` is a separate change, and belongs with whatever dev order acts on
them.
