# Production Shop Handoff

> The handoff is the final step of the end-to-end CAM Assist workflow. For the
> full product context and a command-by-command walkthrough, see
> [docs/product/CAM_ASSIST_WORKFLOW.md](../product/CAM_ASSIST_WORKFLOW.md) and
> [docs/product/WHY_CAM_ASSIST_EXISTS.md](../product/WHY_CAM_ASSIST_EXISTS.md).

## Purpose

A production shop handoff is a portable, **reference-only** sidecar that exports a
reviewed CAM Assist strategy package toward a future Production Shop runtime. It
aggregates references to the package's manifest, strategy, review packet, and —
when available — its traceability bundle into a single outbound artifact, so a
reviewed manufacturing package can be pointed at a downstream shop as one unit.

The handoff is **outbound only** (`CAM Assist → Production Shop`). It lets a
downstream consumer ask *"which reviewed package is being handed to us, and where
are its parts?"* — without CAM Assist reaching into, or depending on, any
Production Shop runtime.

The handoff travels alongside a strategy package without mutating it.

## Authority Model

A production shop handoff is **informational only**.

```text
A Production Shop handoff is informational only.
It does not authorize execution.
It does not confirm machine readiness.
It does not mutate packages.
It does not require Production Shop runtime code.
```

Because the handoff sits at the boundary of execution, it is **execution-adjacent**,
and the non-execution `authority` block is therefore **required** — every one of
its four flags must be `true`:

```json
{
  "authority": {
    "is_informational": true,
    "does_not_authorize_execution": true,
    "does_not_bypass_human_review": true,
    "does_not_confirm_machine_readiness": true
  }
}
```

The fourth flag, `does_not_confirm_machine_readiness`, is specific to the handoff:
exporting a package toward a shop is **not** a claim that the package is ready to
run on a machine. Machine readiness is never inferred, asserted, or implied by the
existence of a handoff.

## File Format

```json
{
  "record_type": "cam_assist_production_shop_handoff",
  "record_version": "1.0.0",
  "package_reference": "luthiers-toolbox:vcarve:les-paul-custom-2024",
  "handoff_direction": "cam_assist_to_production_shop",
  "created_at": "2026-07-09T08:15:41.779627Z",
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

Required: `record_type`, `record_version`, `package_reference`,
`handoff_direction`, `authority`, `contents`. Optional: `created_at`.

- `record_type` must be `cam_assist_production_shop_handoff`.
- `record_version` must be a semantic version (e.g. `1.0.0`).
- `created_at` is an ISO-8601 UTC timestamp recording when the handoff was
  created. It is optional in the contract, but the creator always stamps it for
  auditability. It is metadata only and carries no authority.
- `package_reference` is the package's portable identity — the manifest's
  `federation.federated_package_id` when present, else the package directory name.
- `handoff_direction` must be `cam_assist_to_production_shop`. The handoff is
  outbound only; there is no inbound direction.
- `authority` is required, with all four flags `true` (see [Authority Model](#authority-model)).

`contents` is an object whose keys are drawn from a fixed set of known slots; each
value is a string path **reference**, resolved relative to the handoff file's own
location and forward-slashed for portability (see
`docs/integration/ARTIFACT_REFERENCE_PATHS.md`). The known slots are:

| Slot | References |
| --- | --- |
| `package_manifest_file` | the package `manifest.json` |
| `strategy_file` | the package strategy JSON |
| `review_packet_file` | the human-readable review packet |
| `traceability_bundle_file` | the package's traceability bundle (optional) |

The core three references (`package_manifest_file`, `strategy_file`,
`review_packet_file`) are always emitted by the creator. The
`traceability_bundle_file` slot is optional — included only when explicitly
supplied or conventionally discovered. Unknown slot names are rejected.

The referenced files remain **authoritative**. The handoff references them; it
does not own, copy, cache, or supersede their content.

The record is a **closed contract**: both validation layers (the JSON Schema and
the structural validator) reject any unrecognized top-level field and any
undeclared flag inside `authority`. This keeps the non-execution declaration
airtight — a stray or contradictory flag (for example an execution-granting one)
cannot ride along on an otherwise valid handoff.

## Creating a Handoff

```bash
python scripts/create_production_shop_handoff.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --out examples/production_shop/ltb_vcarve_synthetic_example_handoff.json \
  --force
```

With no `--out`, the handoff is written to its conventional location,
`<package_parent>/production_shop/<package_name>_handoff.json` (for packages under
`examples/packages/<name>`, that root is `examples/production_shop/`).

Every reference is recorded as a path relative to the handoff output file,
forward-slashed. See `docs/integration/ARTIFACT_REFERENCE_PATHS.md`.
The core three content references are always written. The traceability bundle
reference is included when passed explicitly with `--traceability-bundle <path>`
(recorded as-is), or otherwise when a bundle is found at the conventional
`traceability/<package>_bundle.json` location; absent, the slot is simply omitted.

The creator performs no validation beyond discovering its required inputs, and it
does **not** check that referenced files exist — existence is the opt-in
`--check-references` concern of the validator. The source package is never
modified. Use `--force` to overwrite an existing handoff.

## Validating a Handoff

**Structural validity and reference completeness are separate concerns**, and a
`PASS` speaks only to the first unless you opt in to the second:

- **Structural validity** means the handoff record itself conforms to the required
  contract (record type, version, direction, authority block, `contents` shape).
- **Reference completeness** means each declared path in `contents` actually
  resolves on disk.

By default the validator checks structure only and reports a *structurally valid*
handoff. Reference existence is checked only under `--check-references`, and those
findings are advisory (they never change the exit code) unless you additionally
pass `--fail-on-reference-warnings`. A structurally valid handoff is **not** by
itself a statement that its references exist or that the package is ready to run.

Validation has two layers.

### Structural validation (default)

```bash
python scripts/validate_production_shop_handoff.py \
  examples/production_shop/ltb_vcarve_synthetic_example_handoff.json
```

```text
PASS: production shop handoff is structurally valid
```

The structural layer is **filesystem-free**: it opens only the handoff file and
checks `record_type`, `record_version`, a non-empty `package_reference`, the
required `handoff_direction`, the required `authority` block (all four flags
present and `true`), and the `contents` object shape (known slots only, non-empty
string values). A handoff whose references do not exist still passes structurally
— reference existence is a *completeness* concern, not a structural one.

### `--check-references`

```bash
python scripts/validate_production_shop_handoff.py \
  examples/production_shop/ltb_vcarve_synthetic_example_handoff.json \
  --check-references
```

The opt-in `--check-references` layer is a narrow **existence witness**. For each
reference **declared** in `contents`, it resolves the path relative to the handoff
file's own directory (declaring-file-relative; see
`docs/integration/ARTIFACT_REFERENCE_PATHS.md`) and emits a **warning** when the
path does not resolve on disk:

```text
PASS: production shop handoff is structurally valid
  [WARN] strategy_file reference does not resolve: ../packages/.../strategy.json
```

It is existence-only: it never opens, parses, or schema-checks a referenced file;
it performs no `package_reference` cross-check, no Production Shop compatibility or
machine-readiness check, and no absent-slot findings (an omitted reference is
allowed and silent). It mutates nothing.

These warnings are **advisory only**: they never change structural validity and
never change the exit code. A structurally valid handoff with unresolved
references still exits `0`.

### `--fail-on-reference-warnings` (CI enforcement)

For automation that must treat a handoff pointing at missing files as a failure,
add `--fail-on-reference-warnings` alongside `--check-references`:

```bash
python scripts/validate_production_shop_handoff.py \
  examples/production_shop/ltb_vcarve_synthetic_example_handoff.json \
  --check-references --fail-on-reference-warnings
```

This upgrades unresolved-reference findings from warnings to **errors** (exit `1`):

```text
FAIL: production shop handoff validation failed
  [ERR] strategy_file reference does not resolve: ../packages/.../strategy.json
```

It is a strict opt-in and changes nothing else: default behavior is unchanged, no
structural rule is altered, and it has no effect without `--check-references`. The
reference-only doctrine — that a handoff *may* legitimately reference not-yet-present
files — remains the default; this flag exists solely so a pipeline can choose to
enforce completeness at a specific gate.

The behavior matrix:

| Invocation | Structural invalid | Missing references | Exit |
| --- | --- | --- | --- |
| default | — | not checked | `1` if invalid, else `0` |
| `--check-references` | — | warn only | `0` |
| `--check-references --fail-on-reference-warnings` | — | error | `1` |
| any mode | yes | — | `1` (structure dominates) |

Exit codes: `0` structurally valid (and, in strict mode, references resolved),
`1` validation failed, `2` file/read error.

## Inspector Detection

The strategy package inspector reports the handoff under its own section, as
**detection only**:

```text
Production Shop Handoff:
  present
```

or, when no handoff is declared:

```text
Production Shop Handoff:
  not declared
```

```bash
python scripts/inspect_strategy_package.py \
  examples/packages/ltb_vcarve_synthetic_example
```

The inspector is a **discovery surface**, not a validator. It does not open,
parse, validate, or completeness-check the handoff — a handoff with unparseable
contents is still reported as `present`. `present` means only that a handoff file
was found at the resolved path; it is **not** a claim that the handoff is
structurally valid, that its references resolve, or that the package is
machine-ready. Those are three separate questions: use the validator for
structural validity, `--check-references` for reference completeness, and neither
tool ever asserts machine readiness. An explicit path may be supplied with
`--handoff <path>`; otherwise the conventional
`production_shop/<package>_handoff.json` location is used. In `--json` output the
same result appears under a `production_shop_handoff` field:

```json
"production_shop_handoff": {
  "present": true,
  "path": "examples/production_shop/ltb_vcarve_synthetic_example_handoff.json"
}
```

The inspector makes no Production Shop runtime assumptions and introduces no
runtime dependency.

## Non-Execution Doctrine

A production shop handoff never authorizes machine execution, never constitutes
approval, never confirms machine readiness, and never modifies a package. It is a
reference-only, outbound export of an already-reviewed package toward a future
Production Shop runtime. Human review remains required before any downstream CAM
use.

## Production Shop Boundary

The handoff defines a strict, one-directional boundary between CAM Assist and any
downstream Production Shop:

- **Direction is outbound only.** `cam_assist_to_production_shop` is the only
  valid direction. CAM Assist exports; it does not import a shop's state.
- **No runtime dependency.** Creating, validating, or detecting a handoff requires
  no Production Shop runtime code. Nothing in this repository executes, imports, or
  links against a machine controller.
- **No execution authority crosses the boundary.** A handoff carries references
  and identity, never a grant to machine. Execution authority is neither exported
  nor implied.
- **Machine readiness is never asserted.** Producing a handoff says only *"here is
  a reviewed package"* — never *"this package is ready to run."*
- **The package is never mutated.** The handoff is a sidecar; the source package
  and all referenced files remain authoritative and unchanged.

Everything downstream of the boundary — machine execution, post-processing,
readiness confirmation — lives with the operator and the (future) Production Shop
runtime, never with CAM Assist.
