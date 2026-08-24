# Dev Order — CAM-A28

## Package Coherence Audit

## Classification

```text
capability
advisory
read-only
not execution authority
```

CAM-A28 is a **capability**, not maintenance. It adds a new read-only audit
that compares identities and references across the evidence surrounding one
strategy package. `LEDGER.md` records it in the capability table.

## Predecessor baseline

```text
Baseline            CAM-Assist-Blueprint main @ 7f20320
Latest capability   CAM-A26 — Creation Studio Capability Vocabulary Bridge
                    (merged PR #34)
Latest maintenance  CAM-A27 — Capability Map Runtime Hardening
                    (merged PR #35 → 7f20320)
CAM-A28             defined by this dev order, and by nothing preceding it
```

CAM-A27 is on `main`. This work does not stack on an open A27 branch.

## Scope

Add a report-only Package Coherence Audit. Given one strategy package
directory, CAM Assist must answer whether the discoverable CAM Assist
artifacts tell a mutually consistent story about identity and references.

Authorized work:

1. Discover the v1 participating artifacts for one package.
2. Reuse existing structural validators; do not reimplement schema rules.
3. Compare package identity using the creator rule already in this tree.
4. Compare declared references against declaring-file-relative resolution
   and against conventionally discovered artifacts.
5. Distinguish structural invalidity, missing referenced evidence, identity
   mismatch, and reference mismatch.
6. Emit deterministic human and JSON reports.
7. Support `--fail-on-errors` as an opt-in CI policy.
8. Extract conventional discovery into `_shared` so the inspector and the
   auditor share one source of truth.
9. Document the audit, including an honest classification of the committed
   example ecosystem.
10. Update README, ledger, and roadmap. Correct the stale A27 ledger row to
    **Merged**.

Out of scope:

* modifying audited artifacts or rewriting fixtures to obtain a green example;
* generating missing sidecars;
* approving a package;
* machining-correctness, machine readiness, or execution authority;
* capability reconciliation (CAM-A25 / CAM-A26);
* capability profile or capability map participation;
* A12 review-decision records;
* directory scanning for duplicate candidates;
* a repository-wide CI gate on the committed example;
* assigning CAM-A29.

## Core objective

> Can CAM Assist determine whether the evidence surrounding a package is
> internally coherent without becoming a new source of truth or execution
> authority?

## Design decisions recorded at authorization time

### Report-only

No `package_coherence.json`, coherence sidecar, coherence schema, or
coherence history. The result is ephemeral derived state.

### Package directory is the only CLI anchor

```text
python scripts/audit_package_coherence.py \
  --package examples/packages/ltb_vcarve_synthetic_example
```

No artifact-override flags in v1.

### Expected package identity

The same rule the sidecar creators already use:

```text
manifest.federation.federated_package_id
    when present and a non-blank string
otherwise
    package directory name
```

Compare each package-scoped sidecar `package_reference` against that
expected identity. Literal comparison only. The manifest is not
`identity_not_declared` when it already carries the federation identity.

### Declared paths resolve relative to the declaring file only

No project-root fallback. Existing decision-record and lineage links that
use repo-root-style paths are audit findings if they fail to resolve, not
reasons to weaken the resolver.

### Participating artifacts (v1)

```text
in   manifest
     strategy
     review packet
     review annotations
     manufacturing assumptions
     risk assessment
     manufacturing decision record
     revision lineage
     traceability bundle
     Production Shop handoff
     Creation Studio request

out  capability profile          (installation-scoped)
     capability map              (policy-scoped)
     A12 review-decision records
     A25/A26 reconciliation      (ephemeral)
```

### Optional absence is inventory only

`present: false` on the artifact. No `info` finding. An explicit reference
to an absent artifact is `MISSING_REFERENCE` (error).

### Duplicate detection is deferred

v1 does not scan for competing candidates. Conventional discovery yields
one expected path per type.

### Structural validity precedes interpretation

`STRUCTURAL_INVALID` is recorded separately. Identity and reference
comparisons are not derived from malformed content.

### Validator reuse

Call existing `validate_*_file` / equivalent programmatic entrypoints.
Do not spawn validator CLIs. Do not import executable scripts from
executable scripts.

### Shared discovery

```text
inspect_strategy_package.py
        ↓
scripts/_shared/package_discovery.py
        ↑
scripts/_shared/package_coherence.py
```

Inspector behavior is preserved. The inspector does not run the audit.

### Creation Studio request

Identity and declared-reference coherence only. No capability
reconciliation.

### Production Shop handoff

Identity and declared-reference coherence only. No machine-readiness
inference.

### Traceability bundle

Navigational index. Conflicts with conventional discovery are reported.
The bundle is not treated as authoritative.

### Severity

```text
error    STRUCTURAL_INVALID
         PACKAGE_REFERENCE_MISMATCH
         MISSING_REFERENCE
         REFERENCE_MISMATCH

warning  IDENTITY_UNAVAILABLE
         (only where comparison would normally be expected)

info     not used for optional absence in v1
```

Directory-scan duplicate warnings are not part of v1.

### Exit policy

```text
valid audit, no error findings         → 0
valid audit, errors, default           → 0
valid audit, errors, --fail-on-errors  → 1
input/audit infrastructure failure     → 2
```

Invalid or missing package / manifest is exit 2. Warnings never cause
exit 1. `--fail-on-errors` changes only the exit status; JSON is identical.

### JSON

Deterministic, stdout-pure, ephemeral. Paths are POSIX-normalized and not
absolutized. No approval, authorization, machine-readiness, or
permission fields.

### Phase 8 is a classification gate

The committed example may produce error findings because decision-record
and lineage links use repo-root-style paths. Document that honestly. Do
not rewrite fixtures or weaken the resolver without a separate decision.

### CI

v1 does not add a strict example-audit step to GitHub Actions.

### Governance

When A28 updates the ledger, also record A27 as **Merged** (PR #35,
`7f20320`). A28 publication status is truthful: `Local Only` until a PR
exists, then `PR Open`.

CAM-A29 remains unassigned.

## Interfaces

```text
scripts/audit_package_coherence.py
  --package <dir>       required
  --json                optional
  --fail-on-errors      optional
```

Existing schemas, sidecars, validator semantics, and inspector output
remain unchanged except for the inspector importing shared discovery.

## Authority boundary

Package coherence means that CAM Assist evidence artifacts agree about
identity and references. It does not mean the machining strategy is
correct, approved, machine-ready, or authorized for execution.

## Non-goals

No repair, generation, identity normalization, fixture rewriting,
A25/A26 reconciliation, A29 assignment, persisted audit records,
dashboards, or downstream-repository changes.

## Completion criterion

> **Can CAM Assist determine whether the evidence surrounding a package is
> internally coherent without becoming a new source of truth or execution
> authority?**

**Yes.**
