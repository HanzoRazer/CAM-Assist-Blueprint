# Dev Order — CAM-A24

## Datetime Blank-Value Hardening (Maintenance-Class)

## Scope

Close the last three date-time fields in this repository that accept blank and
whitespace-only values, bringing them to the guarantee every `created_at` field
has carried since CAM-A19/A20.

```text
review_annotations       annotations[].timestamp
review_decision_record   reviewed_at
strategy                 approval.timestamp
```

### Classification

This is **maintenance and governance work in the same family as PR #26**, not a
new capability. It adds no artifact, no schema, no script, and no contract. It
occupies the A24 number by explicit authorization on 2026-08-10 rather than by
being capability work; `LEDGER.md` records that so the distinction survives.

`ROADMAP.md` anticipated exactly this: *"If confirmed, they are maintenance work
in the same family as PR #26 — not a new capability, and not automatically the
next numbered item."* The claims were confirmed; the numbering is a deliberate
choice, not an inference.

## Core Objective

> Does every date-time field in this repository now reject empty and
> whitespace-only strings, with the schema and hand-validator layers in
> agreement, and with the guard that discovers them left intact?

## Why these three escaped

`test_created_at_schema_consistency.py` guards fields **named** `created_at`. Its
discovery guard keys on that literal name, so a date-time field called
`timestamp` or `reviewed_at` fell outside coverage **by construction, not by
decision.** Nobody chose to exempt them; the measurement could not see them.

PR #31 fixed the measurement — `test_datetime_description_contract.py` discovers
by `format: date-time` — and recorded the three as an explicit `KNOWN_GAP`
allowlist, documented in each schema's own `description`. CAM-A24 empties that
allowlist.

## Required change

For each of the three fields:

| Layer | Change |
| --- | --- |
| Schema keywords | add `minLength: 1` and `pattern: "\\S"` |
| Schema description | swap the gap-disclosure sentence for the hardened contract sentence |
| `KNOWN_GAP` allowlist | remove the entry |

These are **one atomic change**. `test_datetime_description_contract.py` fails if
the keywords are added while the allowlist entry remains, and fails if the entry
is removed while the keywords are missing. Half-done is not a passing state in
either direction. The description swap is pinned verbatim, so it cannot be
forgotten either.

### Hand-validator parity

CAM-A19/A20 established that a schema guard without a matching hand-validator
guard is drift, not a fix. Coverage of these three is uneven:

| Field | Hand validator | Action |
| --- | --- | --- |
| `annotations[].timestamp` | `validate_review_annotations.py` — checks presence only | **add a non-blank check** |
| `reviewed_at` | none exists | nothing to keep in lockstep; recorded here |
| `approval.timestamp` | `validate_strategy_package.py` — does not inspect `approval` | nothing to keep in lockstep; recorded here |

Only the first has a hand validator that actually reaches the field, so only the
first can drift. The other two are noted so a future reader does not read their
absence as an oversight.

## Compatibility

A record carrying a blank timestamp becomes invalid where it was previously
accepted. Assessed against the repository:

```text
examples/review_annotations/..._annotations.json   3 timestamps, all non-blank
examples/review_decisions/..._decision.json        reviewed_at non-blank
strategy approval.timestamp                        no example populates it
```

`record_review_decision.py` stamps `reviewed_at` from `datetime.now(timezone.utc)`,
which cannot be blank. No creator emits a blank value for any of the three, so no
example, sample, or fixture needs regenerating.

`samples/fret-slot-strategy/approval.json` has a top-level `timestamp: null`, but
that file is a **different artifact** with its own `approval_version` shape — it
is not validated against `strategy.schema.json`'s `approval` block and is out of
scope here.

## Boundary Invariants

Validation strictness only. No new artifact, no execution authority, no change to
what any record *means* — only to which values are structurally legal. `format:
date-time` remains an annotation; this hardens non-blankness, never ISO-8601
shape. The description wording stays validator-agnostic, as PR #31 established.

## Rollout (phased)

1. Dev order (this file).
2. Schemas + `KNOWN_GAP` emptied, in one commit (the guard requires it).
3. Hand-validator parity for `annotations[].timestamp` + tests.
4. Ledger and roadmap status.

## Completion Criteria

All three fields carry `minLength` + `pattern`; `KNOWN_GAP` is empty; every
date-time field is `HARDENED`; the review annotations validator rejects a blank
annotation timestamp; the discovery guard still reports twelve fields; full suite
passes; no example or sample regenerated.
