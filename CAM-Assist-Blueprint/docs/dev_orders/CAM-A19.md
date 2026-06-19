# Dev Order CAM-A19 — Traceability Bundle (Completeness Witness)

> Status: **HANDOFF — design-verified, implementation not started.**
> Capability: `CAM-A19 — Traceability Bundle + Completeness Witness`
> Predecessor: CAM-A18 (revision lineage) — merged in PR #19.
> Branch: `cam-a19-traceability-bundle` (create after this handoff is committed).

## Scope

CAM-A18 completed the manufacturing-documentation arc (assumptions → risk → decision →
sign-off → traceability → revision lineage). Those records exist today as **independent
sidecars** with no single artifact that declares "this is the complete traceability story
for this package."

CAM-A19 introduces a **Traceability Bundle**: a single, portable, reference-only artifact
that aggregates the existing informational sidecars so an entire manufacturing review
story can move between systems as one unit, and so a reviewer can ask *"do we possess a
complete traceability story?"*

Current state:

```text
Package
 ├─ Review Decision        (record_review_decision.py)
 ├─ Review Annotations     (create_review_annotations.py)
 ├─ Manufacturing Assumptions
 ├─ Risk Assessment
 ├─ Manufacturing Decision Record
 └─ Revision Lineage       (CAM-A18)
```

CAM-A19 adds:

```text
Traceability Bundle
 ├─ references package
 ├─ references assumptions
 ├─ references risk
 ├─ references decision record (MDR)
 ├─ references annotations
 └─ references lineage
```

The bundle is a **transport + completeness-witness artifact only.**

It is **not**:

```text
an archive (no copying / packing of external files)
workflow automation
approval authority
execution authority
manufacturing release
package mutation
governance enforcement
```

CAM-A19 preserves the non-execution invariant and the one-sidecar-per-type convention.

**Source-of-truth constraint (hard):**

```text
The bundle must not become the source of truth.
The sidecars remain authoritative.
The bundle is a navigational index.
```

The bundle aggregates *references to* the authoritative sidecars; it never duplicates,
caches, or supersedes their content. Any future change that lets the bundle own or carry
record data would invert the dependency direction (`bundle owns records`) and is forbidden
by this order.

---

## Decisions

| Decision | Outcome |
| --- | --- |
| Package mutation | Forbidden |
| Bundle contents | References only (relative path strings) |
| Copy / pack external artifacts | Forbidden (this is not an archive — see CAM-A9 archive for packing) |
| Bundle authority | Informational only (same three const-true flags as A17/A18) |
| Missing sidecars | **Allowed** — reported as completeness *findings*, never structural errors |
| Structural validation | Filesystem-free: shape, types, reference-as-string only |
| Completeness witness | **Opt-in** (`--check-references`); resolves declared refs + reports omissions as warnings |
| Referenced-file existence | A **warning/finding**, never a hard failure |
| Cross-artifact `package_reference` consistency | Checked under `--check-references`; mismatch = warning |
| Bundle ownership of artifacts | None — bundle references, does not own |
| Source of truth | Sidecars remain authoritative; bundle is a navigational index only |
| Approval authority | Not enforced |
| Workflow automation | Forbidden |
| Machine execution | Forbidden |
| Existing packages & A9–A18 sidecars | Remain valid, untouched |

---

## Design Reconciliation (the one judgment call)

The direction described the bundle two ways: a **references-only transport artifact** (the
validator "does not open files") *and* a **completeness witness** that "reports omissions"
and "inspects consistency," with *"missing artifacts are findings, not automatic failures."*

Resolved as a **two-layer validator** so both hold without contradiction:

1. **Structural layer (default, no filesystem access).** Validates `record_type`,
   `record_version` (semver), `package_reference`, and `bundle_contents` shape — every
   declared reference must be a string. Exit `1` on structural error. This preserves the
   pure references-only transport property: a bundle can be validated for *form* with no
   package present.

2. **Completeness-witness layer (opt-in `--check-references [--base <dir>]`).** Resolves
   each declared reference relative to the base directory, reports any that do not resolve
   as **warnings**, and reports which known sidecar slots are **absent** from
   `bundle_contents` as **completeness findings (warnings)**. Optionally reads each
   resolved sidecar's `package_reference` and warns on mismatch with the bundle's. **None
   of these flip `valid` → `invalid`** (honors "missing artifacts are findings, not
   automatic failures"). Exit code stays `0` when only completeness warnings are present.

**Implementer constraint (hard):** the default code path MUST NOT stat or open any file
other than the bundle itself. Filesystem resolution lives strictly behind
`--check-references`. Completeness findings are warnings only — they never set
`result.valid = False`.

---

## Strategic Purpose

```text
A17 answered:  Why was the decision made?
A18 answered:  How did the decision evolve?
A19 answers:   Do we possess a complete traceability story,
               and can we move it between systems as one portable unit?
```

This closes the **portable-documentation arc** before any future read-only Production Shop
integration. The bridge, when it arrives, should consume one coherent traceability unit —
the bundle — not re-discover loose sidecars and implicitly invent a bundle concept
(which would create rework). Direction of that future bridge remains **read-only, outbound,
non-execution** (`CAM-Assist → Bundle → Production Shop`), never inbound authority.

---

## New Artifacts

### Create

```text
schemas/traceability_bundle.schema.json

scripts/create_traceability_bundle.py
scripts/validate_traceability_bundle.py

examples/traceability/traceability_bundle_example.json

docs/traceability/TRACEABILITY_BUNDLES.md

tests/test_traceability_bundle.py
```

### Patch

```text
scripts/inspect_strategy_package.py     # new "Traceability Bundle:" section + --bundle flag
tests/test_inspect_strategy_package.py  # bundle detection coverage
README.md                               # add bundle capability to architecture summary
```

> Note: unlike A18, A19 does **not** patch `manufacturing_decision_record.schema.json` or
> `record_review_decision.py`. The bundle aggregates references *to* the MDR; the MDR does
> not need to reference the bundle. Keep the dependency one-directional.

---

## File-by-File Patch Plan

### CREATE — `schemas/traceability_bundle.schema.json`

Mirror the style of `schemas/revision_lineage.schema.json` (JSON Schema draft-07,
`additionalProperties` permissive at top level to match existing schemas).

```jsonc
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CAM Assist Traceability Bundle",
  "type": "object",
  "required": ["record_type", "record_version", "package_reference", "bundle_contents"],
  "properties": {
    "record_type": { "const": "cam_assist_traceability_bundle" },
    "record_version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" },
    "package_reference": { "type": "string", "minLength": 1 },
    "created_at": { "type": "string", "format": "date-time" },
    "bundle_contents": {
      "type": "object",
      "properties": {
        "assumptions_file":      { "type": "string", "minLength": 1 },
        "risk_file":             { "type": "string", "minLength": 1 },
        "decision_record_file":  { "type": "string", "minLength": 1 },
        "annotations_file":      { "type": "string", "minLength": 1 },
        "lineage_file":          { "type": "string", "minLength": 1 }
      },
      "additionalProperties": false
    },
    "authority": {
      "type": "object",
      "properties": {
        "is_informational":            { "const": true },
        "does_not_authorize_execution":{ "const": true },
        "does_not_bypass_human_review":{ "const": true }
      },
      "required": ["is_informational", "does_not_authorize_execution", "does_not_bypass_human_review"]
    }
  }
}
```

`bundle_contents` is **required but may be empty** (`{}`) — an empty bundle is a valid
(if uninformative) artifact. All five content slots are optional. `additionalProperties:
false` on `bundle_contents` keeps the known-slot set closed so unknown reference kinds are
caught structurally.

---

### CREATE — `scripts/validate_traceability_bundle.py`

Mirror `scripts/validate_revision_lineage.py` exactly: hand-rolled (no `jsonschema`
dependency), `ValidationResult` NamedTuple `(valid, errors, warnings)`, `load_json`,
`validate_authority` helper, exit codes `0` valid / `1` invalid / `2` file error, `--quiet`,
`[PASS]/[FAIL]/[ERR]/[WARN]` output convention.

Module constants:

```python
RECORD_TYPE = "cam_assist_traceability_bundle"
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
AUTHORITY_FLAGS = [
    "is_informational",
    "does_not_authorize_execution",
    "does_not_bypass_human_review",
]
CONTENT_SLOTS = [
    "assumptions_file",
    "risk_file",
    "decision_record_file",
    "annotations_file",
    "lineage_file",
]
```

**Structural layer — `validate_bundle(data) -> ValidationResult` (errors):**

- missing / wrong `record_type` (must equal `RECORD_TYPE`)
- missing / non-semver `record_version`
- missing / empty `package_reference`
- missing `bundle_contents`, or `bundle_contents` not an object → error (return early)
- any key in `bundle_contents` not in `CONTENT_SLOTS` → error (unknown reference kind)
- any present slot whose value is not a non-empty string → error
- empty `bundle_contents` (`{}`) → **warning** (consistent with empty-`revisions` warning)
- `authority` present → all three flags must be `true`, else error (reuse `validate_authority`)

**Completeness layer — `check_references(data, base_dir) -> (warnings)`**, invoked only
when `--check-references` is passed:

- for each slot **present** in `bundle_contents`: resolve `base_dir / value`; if it does not
  exist → `warning` ("declared <slot> reference does not resolve: <path>")
- for each slot **absent** from `bundle_contents`: `warning`
  ("completeness: <slot> not present in bundle") — these are the omission findings
- for each slot present **and** resolvable: best-effort `load_json`; if it parses and carries
  a `package_reference` that differs from the bundle's → `warning`
  ("package_reference mismatch in <slot>: '<x>' != bundle '<y>'"). Parse failures are
  ignored here (validating the referenced file's own structure is that file's validator's job).
- **All outputs are warnings.** `check_references` never appends to `errors` and never sets
  `valid = False`.

CLI:

```python
parser.add_argument("bundle_json", type=Path)
parser.add_argument("--check-references", action="store_true",
                    help="Resolve declared references and report completeness findings (warnings only)")
parser.add_argument("--base", type=Path, default=None,
                    help="Base dir for resolving references (default: the bundle file's directory)")
parser.add_argument("--quiet", "-q", action="store_true")
```

When `--check-references` is set, `base = args.base or path.parent`. Merge the completeness
warnings into the `ValidationResult.warnings` before printing. Exit code is governed by the
structural layer only.

---

### CREATE — `scripts/create_traceability_bundle.py`

Mirror `scripts/create_revision_lineage.py`: `CreateResult` NamedTuple, `utc_now`,
`resolve_package_reference` (manifest `federation.federated_package_id` → dir name),
`--out` / `--force` / `--quiet`, conventional output suffix.

```python
RECORD_TYPE = "cam_assist_traceability_bundle"
RECORD_VERSION = "1.0.0"
OUTPUT_SUFFIX = "_bundle.json"
```

**Behavior — auto-discovery (the useful default):** the creator scans the conventional
sidecar locations for the package and populates `bundle_contents` with the slots it finds,
as **relative path references from the bundle's output directory**. Absent sidecars are
simply omitted (missing is allowed). Reuse the same conventional-location logic the
inspector/creators already use:

| Slot | Conventional source |
| --- | --- |
| `assumptions_file` | `traceability/<pkg>_assumptions.json` |
| `risk_file` | `traceability/<pkg>_risk.json` |
| `decision_record_file` | `traceability/<pkg>_decision_record.json` |
| `lineage_file` | `traceability/<pkg>_lineage.json` |
| `annotations_file` | `review_annotations/<pkg>_annotations.json` |

(For `examples/packages/<name>`, the `traceability/` and `review_annotations/` roots live
under `examples/`, exactly as the existing creators resolve them.)

Output record:

```python
record = {
    "record_type": RECORD_TYPE,
    "record_version": RECORD_VERSION,
    "package_reference": resolve_package_reference(package_dir),
    "created_at": utc_now(),
    "bundle_contents": discovered,   # dict of {slot: relative_path}, omitting absent slots
    "authority": {
        "is_informational": True,
        "does_not_authorize_execution": True,
        "does_not_bypass_human_review": True,
    },
}
```

Add `--empty` to seed `bundle_contents: {}` without scanning (useful for hand-authoring).
`default_output_path` mirrors the lineage creator: `<traceability>/<pkg>_bundle.json`.

---

### CREATE — `examples/traceability/traceability_bundle_example.json`

Generated from the synthetic example package so the references resolve under
`--check-references`. References are relative to the bundle's directory
(`examples/traceability/`).

```json
{
  "record_type": "cam_assist_traceability_bundle",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:example-001",
  "created_at": "2026-06-18T00:00:00Z",
  "bundle_contents": {
    "assumptions_file": "ltb_vcarve_synthetic_example_assumptions.json",
    "risk_file": "ltb_vcarve_synthetic_example_risk.json",
    "decision_record_file": "ltb_vcarve_synthetic_example_decision_record.json",
    "lineage_file": "ltb_vcarve_synthetic_example_lineage.json"
  },
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true
  }
}
```

> Confirm the actual filenames/`package_reference` against the existing example sidecars when
> generating; the example must pass `validate_traceability_bundle.py --check-references`
> with at most expected omission warnings (e.g. `annotations_file` if no annotations example
> exists). Annotations are intentionally omitted above to exercise a completeness warning.

---

### PATCH — `scripts/inspect_strategy_package.py`

The bundle is an **aggregator**, not one of the four leaf sidecars, so it gets its **own
section** rather than a 5th entry in `TRACEABILITY_SPECS`. Model it on the existing
**Federated Identity** block (independent detect + render).

1. Add a conventional resolver + detector near `TRACEABILITY_SPECS` (line ~266):

   ```python
   BUNDLE_SUFFIX = "_bundle.json"

   def resolve_bundle(package_dir: Path, explicit: Path | None = None) -> dict:
       """Detect a traceability bundle: explicit flag first, then conventional path.
       Detection only — does not parse bundle contents (mirrors leaf-sidecar policy)."""
       path = explicit
       if path is None:
           candidate = conventional_traceability_path(package_dir, BUNDLE_SUFFIX)
           if candidate.exists():
               path = candidate
       present = path is not None and Path(path).exists()
       return {"present": present, "path": str(path) if present else None}

   def format_bundle_section(bundle: dict) -> list[str]:
       status = "present" if bundle["present"] else "not declared"
       return ["Traceability Bundle:", f"  {status}"]
   ```

2. Add a `--bundle` CLI flag (mirror `--lineage`, line ~520), with the same not-found guard
   in the flag-validation loop (line ~569) so an explicit-but-missing path returns exit `2`.

3. Thread a `bundle` dict through `format_terminal_output` and `format_json_output`
   (mirror the `traceability` parameter), rendering `format_bundle_section(bundle)` directly
   **after** the Traceability section (line ~429) and adding `"traceability_bundle": bundle`
   to the JSON output.

**Keep detection-only** (`present` / `not declared`) — no parsing of bundle contents in the
inspector, consistent with the four leaf sidecars and avoiding a new failure surface.

---

### PATCH — `README.md`

Add the bundle to the architecture/capability summary alongside the A17/A18 traceability
entries: one line noting `create_traceability_bundle.py` / `validate_traceability_bundle.py`
and the `--check-references` completeness mode. Note it is reference-only and non-execution.

---

## Utilities

### Create a bundle (auto-discovers existing sidecars)

```bash
python scripts/create_traceability_bundle.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --out examples/traceability/traceability_bundle_example.json
```

### Validate structure only (filesystem-free)

```bash
python scripts/validate_traceability_bundle.py \
  examples/traceability/traceability_bundle_example.json
```

### Validate + completeness witness (resolves references)

```bash
python scripts/validate_traceability_bundle.py \
  examples/traceability/traceability_bundle_example.json \
  --check-references
```

### Inspect package (now shows bundle presence)

```bash
python scripts/inspect_strategy_package.py \
  examples/packages/ltb_vcarve_synthetic_example
```

---

## Test Cases

### Bundle — structure (`tests/test_traceability_bundle.py`)

| Test | Expected |
| --- | --- |
| Valid bundle (all slots) | Pass |
| Valid bundle (single slot) | Pass |
| Empty `bundle_contents` (`{}`) | Pass + warning |
| Missing `record_type` | Fail |
| Invalid `record_type` | Fail |
| Bad `record_version` (non-semver) | Fail |
| Missing `package_reference` | Fail |
| Empty `package_reference` | Fail |
| Missing `bundle_contents` | Fail |
| `bundle_contents` not an object | Fail |
| Unknown key in `bundle_contents` | Fail |
| Slot value not a string (numeric) | Fail |
| Slot value empty string | Fail |
| `authority` present, a flag false | Fail |

### Bundle — completeness witness (`--check-references`)

| Test | Expected |
| --- | --- |
| All declared references resolve | Pass, no reference warnings |
| Declared reference does not resolve | **Pass** (valid) + warning |
| Slot absent from `bundle_contents` | **Pass** (valid) + completeness warning |
| Referenced sidecar `package_reference` mismatch | **Pass** (valid) + warning |
| Completeness findings never change exit code (still `0`) | Pass |
| Structural layer does not touch filesystem without the flag | Pass (default path opens only the bundle) |

### Creator

| Test | Expected |
| --- | --- |
| Auto-discovers present sidecars into `bundle_contents` | Pass |
| Omits absent sidecars (no error) | Pass |
| References are relative to bundle output dir | Pass |
| `--empty` seeds `{}` without scanning | Pass |
| Refuses to overwrite without `--force` | Pass |
| Generated bundle passes its own validator | Pass |
| Package directory not mutated by creation | Pass |

### Inspector (`tests/test_inspect_strategy_package.py`)

| Test | Expected |
| --- | --- |
| Bundle detected via `--bundle` | Pass |
| Bundle detected via conventional path | Pass |
| Missing bundle handled safely (`not declared`) | Pass |
| Bundle not parsed deeply (detection only) | Pass |
| Package not mutated by inspection | Pass |
| Non-execution invariant preserved | Pass |

---

## Rollout Order

```text
Phase 1  schema:     traceability_bundle.schema.json
Phase 2  validator:  validate_traceability_bundle.py (structural + --check-references)
Phase 3  creator:    create_traceability_bundle.py (auto-discovery + --empty)
Phase 4  example:    traceability_bundle_example.json (must pass --check-references)
Phase 5  inspector:  --bundle flag + "Traceability Bundle:" section
Phase 6  docs:       TRACEABILITY_BUNDLES.md + README capability line
Phase 7  tests:      new (bundle) + patched (inspector)
Phase 8  regression: pytest + run every existing validator on existing examples
```

---

## Completion Criteria

```text
traceability bundle schema exists
bundle validator exists (structural layer, filesystem-free by default)
completeness-witness layer exists (--check-references, warnings only)
bundle generator exists (auto-discovers sidecars, references relative)
example bundle exists and passes --check-references
inspector detects bundle (own section, detection only)
missing sidecars are findings, never structural failures
bundle references artifacts, never owns or copies them
documentation complete (TRACEABILITY_BUNDLES.md + README)
full test suite passes (new + patched + regression)
non-execution doctrine preserved
package immutability preserved
no inbound authority introduced (reference dependency stays one-directional)
```

---

## Commit Messages

Handoff (this document):

```bash
git commit -m "docs: add CAM-A19 traceability bundle dev order (design-verified handoff)"
```

Implementation:

```bash
git commit -m "feat: add CAM-A19 traceability bundle export"
```

---

## Why CAM-A19 Next

A17 captured *why* each manufacturing decision was made. A18 captured *how* those decisions
evolved. A19 makes the whole story **portable and completeness-checkable** — a single
reference-only artifact that answers *"do we possess a complete traceability story, and can
we move it as one unit?"* It is the right seam to establish **before** any read-only
Production Shop bridge, so the bridge consumes one coherent unit instead of re-discovering
loose sidecars and implicitly reinventing a bundle.

---

## Design Verification Log

| Judgment call | Verdict | Note |
| --- | --- | --- |
| References-only transport vs. completeness witness | Resolved → two-layer validator | Structural layer is filesystem-free (transport validity); completeness layer is opt-in (`--check-references`) and warning-only. See "Design Reconciliation". |
| Missing sidecars: error or finding? | Finding (warning) | Honors "missing artifacts are findings, not automatic failures"; never flips `valid`. |
| Bundle as 5th `TRACEABILITY_SPECS` entry vs. own section | Own section | Bundle is an aggregator, not a leaf sidecar; modeled on the Federated Identity block. |
| Bundle copies/packs artifacts? | No — references only | Packing is CAM-A9 archive territory; bundling here would drift toward archive/governance. |
| MDR/decision back-reference to bundle? | No | Dependency stays one-directional (bundle → artifacts) to avoid inbound coupling. |
| Bundle as source of truth? | No — navigational index | Sidecars stay authoritative; bundle never duplicates/caches/supersedes record content. Owning records would invert the dependency. |
| Creator auto-discovery | Confirmed | Makes the creator useful and matches "aggregate existing sidecars"; absent slots omitted. |

Implementation gated on this handoff. Proceed on branch `cam-a19-traceability-bundle` only
after this handoff is committed.
