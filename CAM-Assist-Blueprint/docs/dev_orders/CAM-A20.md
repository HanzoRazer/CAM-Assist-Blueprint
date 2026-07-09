# Dev Order CAM-A20 — Read-Only Production Shop Handoff

> Status: **HANDOFF — design-verified, implementation not started.**
> Capability: `CAM-A20 — Read-Only Production Shop Handoff`
> Predecessor: CAM-A19 (traceability bundle) — merged in PR #20.
> Branch: `cam-a20-production-shop-handoff` (create after this handoff is committed).

## Scope

Create the **first read-only handoff seam** from CAM-Assist-Blueprint toward the future
Production Shop runtime. CAM-A20 exports a reviewed CAM Assist package plus its traceability
bundle into a **non-execution handoff manifest** — a single reference-only artifact that says
"here is a reviewed package and its complete traceability story, ready for a human to carry to
Production Shop."

```text
A17 → why a decision was made
A18 → how decisions evolved
A19 → do we possess a complete traceability story?
A20 → can that reviewed story be handed off safely, without creating execution authority?
```

CAM-A20 is **reference-only metadata**. It does **not** add: machine execution, G-code
generation, runtime orchestration, approval automation, package mutation, or Production Shop
ingestion. The Production Shop does not exist as a runtime dependency here; A20 only defines the
outbound seam.

Direction is strictly **CAM Assist → Production Shop, read-only, outbound, non-execution**. No
inbound authority is ever introduced.

---

## Decisions

| Decision | Outcome |
| --- | --- |
| Direction | CAM Assist → Production Shop (outbound only) |
| Mode | Read-only export |
| Execution authority | Forbidden |
| Package mutation | Forbidden |
| Handoff ownership | References only — never copies/packs package or bundle content |
| Authority block | **Required** (execution-adjacent artifact); four flags, all const-true |
| Traceability bundle | Required *if available* — creator includes when present; not validator-enforced |
| `contents` | Required object; known slots only; string values; no individual slot required |
| `handoff_direction` | Required; must equal `cam_assist_to_production_shop` |
| Completeness witness | Opt-in `--check-references`; existence-only; no content parsing |
| Production Shop dependency | None |
| Runtime integration | Deferred |
| CI | Must remain green |
| Existing packages & A9–A19 artifacts | Remain valid, untouched |

---

## Design-Verified Resolutions

These four were resolved before implementation (carrying the A19 lessons forward):

1. **Conventional name wins over the draft's shorthand.** The artifact is
   `<package_parent>/production_shop/<package_name>_handoff.json`. For the synthetic example
   that is `examples/production_shop/ltb_vcarve_synthetic_example_handoff.json` — **not** the
   shorter `ltb_vcarve_synthetic_handoff.json`. The inspector detects via this convention, so
   the executing convention governs the name (A19 Phase 5 precedent).

2. **Authority is required.** Unlike the informational sidecars (A17–A19, where `authority`
   was optional), the handoff is execution-adjacent, so the non-execution declaration is
   **mandatory**. All four flags must be present and `true`:
   `is_informational`, `does_not_authorize_execution`, `does_not_bypass_human_review`,
   `does_not_confirm_machine_readiness`. The fourth flag is A20-specific: a handoff explicitly
   does **not** assert the package is machine-ready.

3. **`contents` is a required object; individual slots are optional.** Validator enforces:
   `contents` present and an object, known slots only, non-empty string values — but does not
   require any specific slot. The *creator* always populates `package_manifest_file`,
   `strategy_file`, and `review_packet_file`, and includes `traceability_bundle_file` when
   available.

4. **Creator bundle resolution = flag + conventional fallback.** `--traceability-bundle` if
   given, else the conventional `<pkg>_bundle.json`, else the slot is omitted ("required if
   available"). References are stored relative to the handoff file's directory, forward-slashed.

**Settled invariants for `--check-references`:** resolves declared references relative to the
handoff file's own directory; **existence-only**; never opens/parses the package, bundle, or
sidecar contents; **no** `package_reference` cross-check; **no** absent-slot findings. Warnings
only — never change validity or exit code.

---

## New Artifacts

### Create

```text
schemas/production_shop_handoff.schema.json

scripts/create_production_shop_handoff.py
scripts/validate_production_shop_handoff.py

examples/production_shop/ltb_vcarve_synthetic_example_handoff.json

docs/integration/PRODUCTION_SHOP_HANDOFF.md

tests/test_production_shop_handoff.py
```

### Patch

```text
scripts/inspect_strategy_package.py   # new "Production Shop Handoff:" section + --handoff flag
README.md                             # capability entry
```

> One-directional dependency: the handoff references the package + bundle; nothing references
> the handoff. No back-references, no inbound authority.

---

## Handoff Shape

Record type: `cam_assist_production_shop_handoff`.

```json
{
  "record_type": "cam_assist_production_shop_handoff",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
  "handoff_direction": "cam_assist_to_production_shop",
  "created_at": "2026-06-21T00:00:00Z",
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true,
    "does_not_confirm_machine_readiness": true
  },
  "contents": {
    "package_manifest_file": "../packages/ltb_vcarve_synthetic_example/manifest.json",
    "strategy_file": "../packages/ltb_vcarve_synthetic_example/strategy.json",
    "review_packet_file": "../packages/ltb_vcarve_synthetic_example/review_packet.md",
    "traceability_bundle_file": "../traceability/ltb_vcarve_synthetic_example_bundle.json"
  }
}
```

Top-level required: `record_type`, `record_version`, `package_reference`, `handoff_direction`,
`authority`, `contents`. Optional: `created_at`.

Known `contents` slots (closed set): `package_manifest_file`, `strategy_file`,
`review_packet_file`, `traceability_bundle_file`.

---

## Schema (`schemas/production_shop_handoff.schema.json`)

Mirror `schemas/traceability_bundle.schema.json` style (JSON Schema 2020-12, rich
descriptions). Differences from the bundle schema:

- `handoff_direction`: `const: "cam_assist_to_production_shop"`, required.
- `authority`: **required** (not optional), with four required const-true flags including
  `does_not_confirm_machine_readiness`.
- `contents`: required object, `additionalProperties: false`, the four known string slots
  (each `minLength: 1`), no `minProperties` (no individual slot required).

---

## Validator (`scripts/validate_production_shop_handoff.py`)

Mirror `validate_traceability_bundle.py`: hand-rolled, `ValidationResult` NamedTuple,
`load_json`, `validate_authority`, exit codes `0`/`1`/`2`, `--quiet`,
`[PASS]/[FAIL]/[ERR]/[WARN]`.

**Structural checks (errors):**

- missing / wrong `record_type` (must equal `cam_assist_production_shop_handoff`)
- missing / non-semver `record_version`
- missing / empty `package_reference`
- missing `handoff_direction`, or `handoff_direction != "cam_assist_to_production_shop"`
- **missing `authority`** (required) → error; when present, all four flags must be `true`
- missing `contents`, or `contents` not an object → error
- unknown key in `contents` → error; any present slot whose value is not a non-empty string → error
- empty `contents` (`{}`) → **warning** (consistent with empty-bundle warning)

**Completeness witness — `check_reference_existence(data, base_dir)`**, opt-in via
`--check-references` (default `base = handoff file's directory`):

- for each **declared** slot: resolve `base_dir / value`; if it does not exist → **warning**
- existence-only — never opens/parses any referenced file
- warnings only; run only on a structurally valid handoff; never change validity/exit code

Authority validator uses a four-flag list:
`is_informational`, `does_not_authorize_execution`, `does_not_bypass_human_review`,
`does_not_confirm_machine_readiness`.

---

## Creator (`scripts/create_production_shop_handoff.py`)

Mirror `create_traceability_bundle.py`: `CreateResult`, `utc_now`, `resolve_package_reference`,
`--out` / `--force` / `--quiet`, default output
`<package_parent>/production_shop/<package>_handoff.json`.

Behavior:

- Read the package `manifest.json` for `strategy_file` / `review_packet_file`; reference the
  manifest, strategy, and review packet (relative to the handoff output dir, forward-slashed).
  Always include these three slots.
- `traceability_bundle_file`: `--traceability-bundle <path>` if given, else conventional
  `<traceability>/<pkg>_bundle.json`, else omit.
- Stamp `created_at`, `handoff_direction`, the required four-flag authority block.
- Never mutate the source package.

```bash
python scripts/create_production_shop_handoff.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --traceability-bundle examples/traceability/ltb_vcarve_synthetic_example_bundle.json \
  --out examples/production_shop/ltb_vcarve_synthetic_example_handoff.json
```

---

## Inspector Patch (`scripts/inspect_strategy_package.py`)

Mirror the CAM-A19 bundle section exactly (own block, detection only):

- `HANDOFF_SUFFIX = "_handoff.json"`; a `conventional_handoff_path()` that resolves under
  `production_shop/` (the bundle helper uses `traceability/`, so a small dedicated resolver is
  needed).
- `resolve_handoff(package_dir, explicit)` → `{"present": bool, "path": str | None}` —
  detection only, never opens the file.
- `format_handoff_section()` → `Production Shop Handoff:` / `present` | `not declared`.
- `--handoff` flag (with the not-found guard → exit 2); thread through terminal + JSON output;
  add `production_shop_handoff` to JSON. Render after the Traceability Bundle section.

Detection only — an unparseable handoff still reports `present`.

---

## Test Cases (`tests/test_production_shop_handoff.py` + dedicated phase files)

| Test | Expected |
| --- | --- |
| Valid handoff validates | Pass |
| Invalid `record_type` rejected | Fail |
| Wrong `handoff_direction` rejected | Fail |
| Missing `package_reference` rejected | Fail |
| Missing `authority` rejected (required) | Fail |
| Authority flag false / fourth flag missing rejected | Fail |
| Unknown content slot rejected | Fail |
| Non-string / empty content slot rejected | Fail |
| Empty `contents` → pass + warning | Pass |
| `--check-references`: missing referenced file → warn only, exit 0 | Pass |
| Warnings do not change validity | Pass |
| `--check-references` does not parse referenced contents | Pass |
| Creator emits a valid handoff (always 3 core slots) | Pass |
| Creator includes bundle via flag and via conventional fallback | Pass |
| Creator omits bundle slot when none available | Pass |
| Creator does not mutate package | Pass |
| References relative to handoff dir, forward-slashed | Pass |
| Inspector detects handoff conventionally + via `--handoff` | Pass |
| Inspector reports `not declared` when absent | Pass |
| Inspector does not parse handoff (unparseable still `present`) | Pass |
| Schema (B contract assertions + C jsonschema applied, importorskip) | Pass |
| Non-execution invariant unchanged | Pass |

Schema tests follow the A19 Phase 1 pattern: dependency-free contract assertions always run;
`jsonschema`-applied tests guarded by `pytest.importorskip("jsonschema")`. `jsonschema` is not
added as a project dependency.

---

## Rollout Order

```text
Phase 1  schema + schema/contract tests (B + C)
Phase 2  structural validator + tests
Phase 3  creator (flag + conventional fallback) + tests
Phase 4  example handoff generated by the tool
Phase 5  --check-references (existence-only) + tests
Phase 6  inspector patch (--handoff, presence-only) + tests
Phase 7  docs (PRODUCTION_SHOP_HANDOFF.md + README)
Phase 8  full regression; commit; PR
```

Each phase is witnessed by tests before its commit (A19 discipline).

---

## Completion Criteria

```text
production shop handoff schema exists
creator exists (3 core slots always; bundle via flag/fallback)
structural validator exists (authority required; direction const; known slots)
completeness witness exists (--check-references, existence-only, warnings only)
example handoff exists (tool-generated, conventional name)
inspector detects handoff (own section, detection only)
full test suite passes; CI green
no package mutation
no execution authority; authority block mandatory and const-true
no Production Shop runtime dependency
non-execution invariant preserved
```

---

## Commit Messages

Handoff (this document):

```bash
git commit -m "docs: add CAM-A20 production shop handoff dev order (design-verified handoff)"
```

Implementation:

```bash
git commit -m "feat: add CAM-A20 read-only production shop handoff"
```

---

## Design Verification Log

| Judgment call | Verdict | Note |
| --- | --- | --- |
| Conventional name vs draft shorthand | Convention wins | `<pkg>_handoff.json` under `production_shop/`; inspector detects via convention (A19 Phase 5 precedent). |
| Authority optional vs required | Required | Execution-adjacent artifact; non-execution declaration must be mandatory; four flags const-true. |
| Fourth authority flag | Added | `does_not_confirm_machine_readiness` — a handoff does not assert machine readiness. |
| Individual content slots required? | No | `contents` required object; known-slots-only; slots optional. Creator populates the three core slots. |
| Bundle inclusion | Flag + conventional fallback | Mirrors A19 auto-discovery; omitted if unavailable. |
| `--check-references` depth | Existence-only | No content parsing, no package_reference cross-check, no absent-slot findings (simpler than the merged bundle validator, per dev-order scope). |
| Handoff as source of truth | No | References only; package + bundle remain authoritative; one-directional dependency. |

Implementation gated on this handoff. Proceed on branch `cam-a20-production-shop-handoff` only
after this handoff is committed.
