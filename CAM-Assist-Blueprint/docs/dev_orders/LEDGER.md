# CAM-Assist-Blueprint — Capability Ledger

Evidence-backed status for every A-series capability. Rebuilt from repository
evidence on 2026-08-07 (see `SESSION_RECOVERY_2026-08-07.md`).

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
| **A23** | **Creation Studio Capability Profile** | **PR Open** | PR #30 `728e62a..3c3c139` (7 commits) | `CAM-A23.md` — *on branch, not on `main`* | on branch only | Pushed and opened 2026-08-08. **Not merged.** See collision below |
| A24+ | — | *unassigned* | — | — | — | **No repository evidence of any kind** |

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

### CAM-A23 collision — resolution of record

```text
CAM-A23 = Creation Studio Capability Profile
```

`cam-a23-created-at-schema-consistency` (PR #26) carried the A23 label in its
branch name but shipped no dev order and no README section. `CAM-A23.md` and the
`cam-a23-creation-studio-capability-profile` branch both establish A23 as the
Capability Profile. The dev order and implementation branch win; the maintenance
branch is retro-designated.

Note for readers on `main`: `docs/dev_orders/CAM-A23.md` is **not present on
`main`** — it lands with the capability's own branch, which is still unmerged
(PR #30). The ruling above stands regardless, because it is a designation
decision, not a statement about which files have merged.

A reader encountering `cam-a23-created-at-schema-consistency` in git history should
resolve it via this table, not by inferring a capability.

---

## Unmerged branches

These represent work that exists but has shipped nothing. Tracked separately from
the capability ledger on purpose.

| Branch | Head | Ahead of `main` | Status | Disposition |
| --- | --- | --- | --- | --- |
| `cam-a23-creation-studio-capability-profile` | `3c3c139` | 7 | PR Open | **PR #30**, opened 2026-08-08. Awaiting review. Preserved untouched by this recovery |
| `cam-a-session-recovery-2026-08-07` | *this branch* | 1 | PR Open | **PR #29**, opened 2026-08-08. These artifacts |
| `cam-a19-a20-created-at-schema-parity` | `38e0665` | 1 | **Published, unmerged** | Post-merge doc fix, committed **and pushed** after PR #24 merged at `3126c9a` and closed. On `origin`; no open PR carries it. **Preserved pending review — deliberately not cherry-picked or folded into recovery artifacts** |

Every other local branch is fully merged into `main`.

**Open PRs: #29 and #30**, both opened 2026-08-08, neither merged. They conflict
with each other on `README.md` — both insert immediately after the CAM-A22
section — so whichever lands second needs a rebase.

Note for future audits: `gh pr list --state open` is **not** sufficient to find
unmerged work. It returns nothing for `38e0665`, whose PR is closed. Cross-check
`git ls-remote --heads origin` against `main` as well.

---

## Unverified claims

Carried from conversation; **not** substantiated by repository evidence. Must be
confirmed against `schemas/` before any dev order references them.

| Claim | Location to verify | Status |
| --- | --- | --- |
| annotation `timestamp` accepts blank | `schemas/review_annotations.schema.json` | Unverified |
| `reviewed_at` accepts blank | `schemas/review_decision_record.schema.json` | Unverified |
| `approval.timestamp` accepts blank | `schemas/strategy.schema.json` | Unverified |

---

## Maintaining this ledger

Update it in the same PR that changes capability status. A capability moves to
`Merged` only when it is on `main` — not when it is implemented, not when a PR is
opened, and not when a conversation says it is done.
