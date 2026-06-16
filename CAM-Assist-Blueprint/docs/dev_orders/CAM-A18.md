# Dev Order CAM-A18 — Revision Lineage for Traceability Records

> Status: **HANDOFF — design-verified, implementation not started.**
> Capability: `CAM-A18 — Revision Lineage for Traceability Records`
> Predecessor: CAM-A17 (manufacturing decision traceability) — merged in PR #18.

## Scope

Add the one capability named in the CAM-A17 direction but not built: **revision lineage**.
Capture how a package's manufacturing reasoning evolved across revisions as an immutable
sidecar — which revision supersedes which, what changed, and (optionally) which
assumptions / risk / decision sidecars belong to each revision.

```text
Strategy
→ Assumptions
→ Risk Review
→ Decision
→ Sign-Off
→ Traceability
→ Revision Lineage   ← CAM-A18
```

CAM-A18 is **sidecar / metadata only** and preserves the non-execution invariant.

It does **not** introduce: machine execution, runtime orchestration, CAM generation,
post processors, workflow / approval automation, package mutation, or governance expansion.

---

## Decisions

| Decision | Outcome |
| --- | --- |
| Package mutation | Forbidden |
| Lineage records | Sidecar artifacts |
| Lineage model | Single sidecar per package holding a supersession graph (one or more chains) |
| Lineage granularity | Package-scoped narrative chain (NOT artifact version control) — see below |
| Supersession | Informational pointer (`supersedes`), not enforced |
| Lineage integrity | Validated structurally (dup / dangling / self / cycle / root) — not authority |
| Forked lineage (multiple roots) | Allowed, emits warning |
| Approval authority | Not enforced |
| Workflow automation | Forbidden |
| Machine execution | Forbidden |
| Existing packages & A17 sidecars | Remain valid, untouched |

---

## Lineage Granularity & Scope (design-verified)

**Resolved question:** does lineage track *the package* or *individual traceability artifacts*?

**Verdict: package-scoped narrative chain.**

A17 stores exactly one assumptions sidecar, one risk sidecar, and one MDR per package, and
their `record_version` is the *format* version (e.g. `1.0.0`), **not** a content-revision
counter. Artifact-scoped lineage would collide with that one-sidecar-per-type convention and
would imply retaining historical artifact files — i.e. version control, which is one step from
governance enforcement and trips the "no governance expansion" boundary.

Therefore:

- A **revision** is a human-declared checkpoint in the package's manufacturing reasoning — not
  a version bump of a single artifact.
- Assumptions, risk assessments, and MDRs may evolve at **different rates**. That differential
  evolution is captured by (1) the per-revision `summary` (human text describing what changed)
  and (2) optional `related_records` pointers to the artifact files associated with that revision.
  `related_records` is **load-bearing**, not decoration: it is the mechanism that reconciles a
  single package-scoped chain with artifacts that change at different cadences.
- A18 is **not** artifact version control. It does not retain or reconstruct historical versions
  of assumption / risk / MDR sidecars. `related_records` points at *associated* files; it does
  not guarantee a file's historical state is preserved.

**Implementer constraint (hard):** do **not** add per-artifact version counters, content hashes,
or historical-retention logic to the lineage schema. Keep `record_version` as the format version
only, exactly as A17 uses it. Retaining historical artifact versions, if ever needed, is a
separate future order and must avoid governance expansion.

---

## New Artifacts

### Create

```text
schemas/revision_lineage.schema.json

scripts/create_revision_lineage.py
scripts/validate_revision_lineage.py

examples/traceability/revision_lineage_example.json

docs/traceability/REVISION_LINEAGE.md

tests/test_revision_lineage.py
```

### Patch

```text
schemas/manufacturing_decision_record.schema.json   # optional lineage_file property
scripts/inspect_strategy_package.py                 # 4th traceability spec + --lineage flag
scripts/record_review_decision.py                   # optional --lineage-file linkage
tests/test_inspect_strategy_package.py              # lineage detection coverage
tests/test_record_review_decision.py                # --lineage-file linkage coverage
README.md
```

---

## Artifact Definition — Revision Lineage

Purpose:

```text
Capture how a package's manufacturing reasoning evolved across revisions,
as an immutable supersession graph (one or more chains).
```

Record type: `cam_assist_revision_lineage` (mirrors the A17 `cam_assist_*` const convention).

### Schema (`schemas/revision_lineage.schema.json`)

Top-level required: `record_type`, `record_version`, `package_reference`, `revisions`.
Optional: `created_at` (date-time), `authority` (same three const-true flags as A17).

Each entry in `revisions[]`:

| Field | Required | Notes |
| --- | --- | --- |
| `revision_id` | yes | Human label, unique within the file (e.g. `"rev-1"`, `"A"`) |
| `summary` | yes | What changed in this revision |
| `supersedes` | no | `revision_id` of the prior revision this replaces; absent = root |
| `revised_by` | no | Informational identifier, no trust validation |
| `related_records` | no | Object with optional `assumptions_file` / `risk_file` / `decision_record_file` string refs (referenced, never mutated) |

Example (`examples/traceability/revision_lineage_example.json`):

```json
{
  "record_type": "cam_assist_revision_lineage",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
  "created_at": "2026-06-15T00:00:00Z",
  "revisions": [
    {
      "revision_id": "rev-1",
      "summary": "Initial manufacturing strategy review.",
      "revised_by": "Manufacturing Engineer"
    },
    {
      "revision_id": "rev-2",
      "supersedes": "rev-1",
      "summary": "Reduced depth of cut after thin-wall chatter risk flagged.",
      "revised_by": "Senior Reviewer",
      "related_records": {
        "risk_file": "examples/traceability/risk_assessment_example.json"
      }
    }
  ],
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true
  }
}
```

---

## Validator (`scripts/validate_revision_lineage.py`)

Mirror `validate_manufacturing_assumptions.py` exactly: hand-rolled (no `jsonschema`
dependency), `ValidationResult` NamedTuple, `validate_authority` helper, exit codes
`0` valid / `1` invalid / `2` file error, `--quiet`.

**Field checks (errors):** wrong / missing `record_type`, bad / missing `record_version`
semver, missing `package_reference`, missing / non-array `revisions`, each revision missing
`revision_id` or `summary` (must be non-empty strings).

**Lineage integrity checks (the A18-specific value):**

- Duplicate `revision_id` → **error**
- `supersedes` referencing an unknown `revision_id` → **error** (dangling pointer)
- A revision superseding itself → **error**
- A cycle in the `supersedes` chain → **error**
- Zero roots (every revision supersedes something — implies a cycle / broken chain) → **error**
- More than one root → **warning** (forked lineage permitted but flagged)
- Empty `revisions` array → **warning** (consistent with the empty-assumptions warning)
- `authority` present → all three flags must be `true`, else error

---

## Creator (`scripts/create_revision_lineage.py`)

Mirror `create_manufacturing_assumptions.py`. Seed a valid single-root lineage from a package:

```bash
python scripts/create_revision_lineage.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --out examples/traceability/revision_lineage_example.json \
  --revised-by "Manufacturing Engineer" \
  --summary "Initial manufacturing strategy review."
```

Resolves `package_reference` the same way A17 creators do, stamps `created_at`, seeds one root
revision (`rev-1`), includes the authority block.

---

## Inspector Enhancements (`scripts/inspect_strategy_package.py`)

1. Append to `TRACEABILITY_SPECS`:

   ```python
   ("revision_lineage", "revision lineage", "_lineage.json"),
   ```

   The existing `conventional_traceability_path` / `resolve_traceability` /
   `format_traceability_section` machinery then handles it with zero structural change.

2. Add a `--lineage` CLI flag (mirrors `--assumptions` / `--risk` / `--decision-record`),
   thread it through the not-found guard loop and the
   `resolve_traceability(... revision_lineage=args.lineage)` call.

Output (present):

```text
Traceability:
  assumptions: present
  risk assessment: present
  decision record: present
  revision lineage: present
```

The absent path is unchanged (`not declared` when no sidecars at all). **Keep it
present / not-declared only** — no parsing of lineage content in the inspector, to stay
consistent with the other three and avoid a new failure surface.

---

## Review Decision Integration (`scripts/record_review_decision.py`)

Add optional `--lineage-file` (mirrors `--assumptions-file` / `--risk-file`). When provided,
store as `record["lineage_file"]` — **referenced, never mutated**. Patch
`manufacturing_decision_record.schema.json` to permit the optional `lineage_file` property
(alongside existing `assumptions_file` / `risk_file`).

---

## Test Cases

### Revision Lineage (`tests/test_revision_lineage.py`)

| Test | Expected |
| --- | --- |
| Valid root-only lineage | Pass |
| Valid multi-revision chain | Pass |
| Missing `revision_id` | Fail |
| Missing `summary` | Fail |
| Duplicate `revision_id` | Fail |
| `supersedes` → unknown id | Fail |
| Revision supersedes itself | Fail |
| Cyclic chain (A→B→A) | Fail |
| Two roots (forked) | Pass + warning |
| Invalid `record_type` | Fail |
| Bad `record_version` | Fail |
| `authority` flag false | Fail |
| Empty `revisions` | Pass + warning |

### Traceability / Inspector

| Test | Expected |
| --- | --- |
| Inspector detects lineage via `--lineage` | Pass |
| Inspector detects lineage via conventional path | Pass |
| Missing lineage handled safely (`not declared`) | Pass |
| Package not mutated by inspection | Pass |
| Non-execution invariant preserved | Pass |

### Decision Linkage

| Test | Expected |
| --- | --- |
| Decision record with `--lineage-file` | Pass, `lineage_file` present |
| Lineage sidecar not mutated by linkage | Pass |

---

## Rollout Order

```text
Phase 1  schema: revision_lineage.schema.json
Phase 2  validator: validate_revision_lineage.py
Phase 3  creator: create_revision_lineage.py
Phase 4  example sidecar
Phase 5  inspector patch (+ --lineage flag)
Phase 6  review-decision linkage patch (+ decision schema lineage_file)
Phase 7  documentation
Phase 8  testing (new + patched)
```

---

## Completion Criteria

```text
revision lineage records supported
lineage integrity validated (duplicate / dangling / self / cycle / root)
forked lineage flagged, not blocked
lineage scoped to the package (narrative chain, not artifact version control)
inspector visibility added (4th traceability spec)
decision-record lineage linkage added (referenced, not mutated)
package immutability preserved
non-execution invariant preserved
full test suite passes
```

---

## Commit Message (implementation)

```bash
git commit -m "feat: add CAM-A18 revision lineage for traceability records"
```

---

## Why CAM-A18 Next

CAM-A17 captured **why** each manufacturing decision was made. CAM-A18 captures **how those
decisions evolved** — the supersession chain across revisions. It closes the last unbuilt item
from the A17 scope list (assumptions ✓, risk ✓, sign-offs ✓, revision lineage ←) and completes
the manufacturing-grade documentation arc *before* any future read-only Production Shop bridge
work.

---

## Design Verification Log

| Judgment call | Verdict | Note |
| --- | --- | --- |
| Single lineage sidecar per package | Confirmed | Fits A17 one-sidecar pattern; simplifies cycle detection |
| Forked lineage = warning (not error) | Confirmed | Keeps the system informational; a hard error drifts toward workflow enforcement |
| Package vs artifact granularity | Resolved → package-scoped | Artifact-scoped lineage implies version control / governance expansion (forbidden). `related_records` reconciles differential artifact evolution within a single chain. See "Lineage Granularity & Scope". |

Implementation gated on this handoff. Proceed on branch `cam-a18-revision-lineage` (this branch)
only after the handoff is committed.
