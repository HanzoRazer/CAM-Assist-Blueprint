# CAM-Assist-Blueprint — Capability Ledger

Evidence-backed status for every A-series capability. Rebuilt from repository
evidence on 2026-08-07 and live status re-verified on 2026-08-08
(America/Chicago; see `SESSION_RECOVERY_2026-08-07.md`).

**This ledger is derived from the repository, never from conversation.** Any entry
that cannot be substantiated from git history, PRs, `docs/dev_orders/`, `schemas/`,
`scripts/`, `examples/`, or `tests/` is marked `Unverified` rather than asserted.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| **Merged** | Present on authoritative `main` |
| **PR Open** | Published, not merged, with an open PR |
| **Published, unmerged** | Pushed to `origin`, not merged, **no open PR** |
| **Local Only** | Committed or working-tree implementation, never pushed |
| **Specified** | Dev order exists, implementation not verified |
| **Unverified** | Conversation claims it exists; repository evidence not yet established |

`Merged` is not interchangeable with any of the three below it. A capability that
is not on `main` has shipped nothing, however far along it looks.

`Published, unmerged` was added 2026-08-08. The original vocabulary had no term
for work that is pushed but carries no open PR, and that gap produced a real
error: `38e0665` was recorded as `Local Only` and "never published" when it is on
`origin`. Work in this state is the easiest to lose — it is invisible to
`gh pr list` and invisible to anyone reading `main`.

---

## Capability ledger

| ID | Title | Status | PR / Commit | Dev order | README | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| A0 | Repository Foundation | Merged | pre-PR | — | yes | Predates the PR flow |
| A1 | Fret Slot Strategy Contract | Merged | #1 `1dd0dc0` | — | yes | |
| A2 | Strategy Validation | Merged | #2 `ed91f8a` | — | yes | |
| A3 | Review Packet Generator | Merged | #3 `a5ac710` | — | yes | |
| A4 | Strategy Package Manifest | Merged | #4 `bce0cea` | — | yes | |
| A5 | Strategy Package Assembly | Merged | #5 `e97a5d6` | — | yes | |
| A6 | Strategy Package Inspection | Merged | #6 `a1ed5e0` | — | yes | |
| A7 | Strategy Package Index | Merged | #7 `60658bb` | — | yes | |
| A8 | Strategy Package Archive | Merged | #8 `52391e7` | — | yes | |
| A9 | Strategy Package Archive Validator | Merged | #9 `0ea8d83` | — | yes | |
| A10 | Strategy Package Import Staging | Merged | #10 `8b2fae7` | — | yes | |
| A11 | Staged Package Review Queue Index | Merged | #11 `07e6c04` | — | yes | |
| A12 | Review Decision Record | Merged | #12 `86a76d7` | — | yes | |
| A13 | LTB Bridge Infrastructure | Merged | #13 `88778f8` | — | **added 2026-08-07** | README gap closed by recovery |
| A14 | External Package Identity | Merged | #14 `13e7df2` | — | yes | |
| A15 | Federation Presentation + Preservation | Merged | #16 `bd7060d` | — | yes | |
| A16 | Portable Review Annotations | Merged | #17 `95de7b9` | — | yes | |
| A17 | Manufacturing Decision Traceability | Merged | #18 `effdfb0` | — | **added 2026-08-07** | README gap closed by recovery |
| A18 | Revision Lineage | Merged | #19 `0b1af79` | `CAM-A18.md` | **added 2026-08-07** | README gap closed by recovery |
| A19 | Traceability Bundle | Merged | #20 `25708d1` | `CAM-A19.md` | **added 2026-08-07** | Hardened #22 `0380f9b`; cleanup #23 `11e94ca`; parity #24 `4817910` |
| A20 | Production Shop Handoff | Merged | #21 `334f56d` | `CAM-A20.md` | yes | Cleanup #23; parity #24 |
| A21 | Product Identity and Workflow Demo | Merged | #25 `ede5496` | `CAM-A21.md` | **added 2026-08-07** | README gap closed by recovery |
| A22 | CAM-Creation-Studio Capability Request | Merged | #27 `f1c74b4` | `CAM-A22.md` | yes | Example regression #28 `076c6dd` |
| **A23** | **Creation Studio Capability Profile** | **Merged** | PR #30 → `08b3d1b` | `CAM-A23.md` | yes | Landed 2026-08. Ledger row was stale at A25 publication; A23 is on `main`. See collision below |
| A24 | Datetime Blank-Value Hardening | **Merged** | PR #32 `311d6a6` | `CAM-A24.md` | n/a | **Maintenance-class, not a capability** — numbered by explicit authorization 2026-08-10, not by inference. See mapping below |
| **A25** | **Creation Studio Capability Reconciliation** | **Merged** | PR #33 → `cea7782` | `CAM-A25.md` | yes | Merged 2026-08-23. Report-only and advisory: exact identifier matching, `namespace_divergence` finding, request/profile provenance. No persisted artifact. Semantic mapping is CAM-A26 |
| **A26** | **Creation Studio Capability Vocabulary Bridge** | **Merged** | PR #34 → `fc9ab51` | `CAM-A26.md` | yes | Merged 2026-08-23. Explicit A22→A23 mapping contract. Opt-in `--capability-map`. Exact A25 default unchanged |
| A27 | Capability Map Runtime Hardening | **Merged** | PR #35 → `7f20320` | `CAM-A27.md` | n/a | **Maintenance-class, not a capability** — numbered by explicit authorization. Shared map module, controlled errors, blank-identifier rejection. No mapping-policy change. Merged 2026-08-23. |
| **A28** | **Package Coherence Audit** | **Merged** | PR #36 → `65e9f4c` | `CAM-A28.md` | yes | Capability. Read-only identity/reference audit. Advisory by default. Merged 2026-08-24. Declaring-file-relative references only; no project-root fallback. |
| A29 | Traceability Reference Path Canonicalization | **Merged** | PR #37 → `0cfa5e9` | `CAM-A29.md` | compact | **Maintenance-class, not a capability** — numbered by explicit authorization. One declaring-file-relative rule shared by creators, completeness validators, and CAM-A28. Fixture path strings corrected; manufacturing semantics unchanged. Merged 2026-08-25. |
| **A30** | **Truss Rod Channel Strategy Support** | **PR Open** | PR #38 `cursor/cam-a30-truss-rod-channel-strategy-fc97` | `CAM-A30.md` | yes | Capability. First post-fret-slot operation: 2.5D open-path simple strategy. Creator + shared depth-pass helper + dispatched review packet. No G-code. A31 not assigned. Opened 2026-08-25. **Not merged.** |

---

## Supersession and maintenance mapping

Entries that appear in git history but are **not** A-series capabilities.

| Git artifact | Original designation | Correct designation | Ruling |
| --- | --- | --- | --- |
| PR #26 `874fcb0` `cam-a23-created-at-schema-consistency` | CAM-A23 | **Maintenance / governance** | Retro-designated 2026-08-07. Extends the `created_at` `minLength`/`pattern` fix across the remaining schemas. It is maintenance work, **not** a capability, and **no longer occupies the A23 number.** Its commits are not renumbered or moved. |
| PR #23 `11e94ca` `cam-a20-a19-validator-cleanup` | — | Maintenance | Validator cleanup against A19/A20 |
| PR #24 `4817910` `cam-a19-a20-created-at-schema-parity` | — | Maintenance | Schema/validator `created_at` parity |
| PR #22 `0380f9b` `cam-a19-traceability-bundle-hardening` | — | Hardening of A19 | Not a separate capability |
| PR #28 `076c6dd` `cam-a22-example-regression-test` | — | Follow-up to A22 | Additive test + supersession doc |
| `docs/dev_orders/CAM-A22-ALTERNATE-HANDOFF-SUPERSEDED.md` | — | Superseded reference | Historical only; **not** corrective authority over the shipped A22 contract |
| PR #31 `efcbb3d` `cam-a19-a20-created-at-description-followup` | — | Maintenance | Landed the stranded `38e0665`, restated all nine `created_at` descriptions validator-agnostically, and added the `format: date-time` discovery guard |
| **CAM-A24** `CAM-A24.md` | A-series capability | **Maintenance / governance** | Blank-value hardening of the last three date-time fields. Adds no artifact, schema, script, or contract. It occupies an A-number by explicit authorization on 2026-08-10, which `ROADMAP.md` had anticipated: *"they are maintenance work in the same family as PR #26 — not a new capability, and not automatically the next numbered item."* Recorded here so the capability list stays a list of capabilities |
| **CAM-A27** `CAM-A27.md` | A-series capability | **Maintenance / runtime-hardening** | Post-A26 hardening of map loading, import boundary, error classification, mapping-index strictness, blank identifiers, and provenance paths. No mapping-policy change. Occupies an A-number by explicit authorization, the same family as CAM-A24 |
| **CAM-A29** `CAM-A29.md` | A-series capability | **Maintenance / contract-coherence** | Canonicalizes traceability file references to declaring-file-relative portable paths. Occupies an A-number by explicit authorization, the same family as CAM-A24 and CAM-A27. Does not add a product capability. |

### CAM-A23 collision — resolution of record

```text
CAM-A23 = Creation Studio Capability Profile
```

`cam-a23-created-at-schema-consistency` (PR #26) carried the A23 label in its
branch name but shipped no dev order and no README section. `CAM-A23.md` and the
`cam-a23-creation-studio-capability-profile` branch both establish A23 as the
Capability Profile. The dev order and implementation branch win; the maintenance
branch is retro-designated.

Note for readers on `main`: `docs/dev_orders/CAM-A23.md` is present on `main`
(PR #30 → `08b3d1b`). The ruling above stands regardless, because it is a
designation decision.

A reader encountering `cam-a23-created-at-schema-consistency` in git history should
resolve it via this table, not by inferring a capability.

---

## Unmerged branches

These represent work that exists but has shipped nothing. Tracked separately from
the capability ledger on purpose.

**As of 2026-08-10 this table is empty.** Every branch it tracked has landed:

| Branch | Head | Resolved | How |
| --- | --- | --- | --- |
| `cam-a-session-recovery-2026-08-07` | `c7c0b51` | **Merged** | PR #29 → `1673b94` |
| `cam-a23-creation-studio-capability-profile` | `3c3c139` | **Merged** | PR #30 → `08b3d1b`, rebased so its 7 commits landed as `54e6a6d..e61385a` |
| `cam-a19-a20-created-at-schema-parity` | `38e0665` | **Merged by patch** | cherry-picked as `d057be9` in PR #31 → `efcbb3d`. The branch remains on `origin` and is *not* an ancestor of `main`; `git cherry` reports zero unique patches |

The `Published, unmerged` bucket that held `38e0665` for twenty-nine days is now
empty. That entry is why the status exists — the work was pushed on 2026-07-11
but its PR (#24) had already merged and closed, so nothing carried it to `main`
and nothing listed it as outstanding.

At the 2026-08-10 verification, `git cherry origin/main <remote-branch>` found no
remote branch with a unique patch absent from `main`, and `gh pr list --state
open` returned zero. This patch-equivalence check matters: branch topology alone
can report an ahead commit even when an equivalent patch is already on `main`,
which is exactly the state `cam-a19-a20-created-at-schema-parity` is in now.

Viability re-examined and closed 2026-08-13: `38e0665` is **not viable to merge** —
PR #31 superseded its wording for all nine descriptions, and its text carries none
of the clauses now pinned by `tests/test_datetime_description_contract.py`, so
applying it would regress two of the nine fields.

Note for future audits: `gh pr list --state open` is **not** sufficient to find
unmerged work. It returned nothing for `38e0665`, whose PR was closed.
Cross-check `git ls-remote --heads origin` against `main` as well.

---

## Confirmed maintenance findings — closed by CAM-A24

These originated in conversation, were independently confirmed against the
schemas on 2026-08-08, and were fixed by CAM-A24 on 2026-08-10.

| Claim | Location | Status |
| --- | --- | --- |
| annotation `timestamp` accepts blank | `schemas/review_annotations.schema.json` | **Fixed** — CAM-A24 |
| `reviewed_at` accepts blank | `schemas/review_decision_record.schema.json` | **Fixed** — CAM-A24 |
| `approval.timestamp` accepts blank | `schemas/strategy.schema.json` | **Fixed** — CAM-A24 |

All twelve `format: date-time` fields in the repository are now hardened against
blank and whitespace-only values; the `KNOWN_GAP` allowlist in
`tests/test_datetime_description_contract.py` is empty. The allowlist mechanism
remains so the next date-time field added to any schema must be classified
rather than silently accepted.

## Verification snapshot — 2026-08-08

- `main` was `076c6dd`; `pytest --collect-only -q` collected **875** tests.
- PR #30 was open at `3c3c139` (7 commits, 14 files, +3440 / -2); its successful
  CI run collected **1018** tests.
- `cam-a19-a20-created-at-schema-parity` existed on `origin` at full SHA
  `38e0665eaaabf15ea050c279d381a8faca8c8323`; PR #24 was merged and closed, and
  no open PR carried that head.
- PR #29 was open on this branch. Its exact head is intentionally resolved from
  the PR rather than copied into the document it points to.

---

## Maintaining this ledger

Update it in the same PR that changes capability status. A capability moves to
`Merged` only when it is on `main` — not when it is implemented, not when a PR is
opened, and not when a conversation says it is done.
