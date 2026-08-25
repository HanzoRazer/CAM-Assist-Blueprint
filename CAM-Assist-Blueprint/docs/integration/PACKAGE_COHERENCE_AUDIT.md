# Package Coherence Audit

## Purpose

CAM-A28 reports whether the CAM Assist evidence surrounding one strategy
package agrees about **identity** and **references**.

Package coherence means that CAM Assist evidence artifacts agree about
identity and references. It does not mean the machining strategy is
correct, approved, machine-ready, or authorized for execution.

The result is ephemeral. It is not written back as a sidecar, schema, or
history file.

## Scope

The audit reads one package directory and the conventionally discovered
sidecars associated with it. It reuses existing structural validators. It
does not repair, generate, or approve anything.

## Participating Artifacts

v1 includes:

* package manifest
* strategy
* review packet
* review annotations
* manufacturing assumptions
* risk assessment
* manufacturing decision record
* revision lineage
* traceability bundle
* Production Shop handoff
* Creation Studio request

v1 excludes:

* Creation Studio capability profile (installation-scoped)
* capability map (policy-scoped)
* A12 review-decision records
* A25/A26 reconciliation results (ephemeral)

## Discovery

Conventional discovery lives in `scripts/_shared/package_discovery.py`.
The package inspector and the coherence auditor share those primitives.
The inspector does not run the audit.

Discovery is one expected path per artifact type. It does not scan for
duplicate candidates.

For packages under `examples/packages/<name>`, sidecars are resolved under
the corresponding `examples/<kind>/` directory. Otherwise they are
resolved beside the package parent.

## Structural Validation

Each present participating artifact is validated with its existing
programmatic validator. Review packets have no JSON schema; they are
checked as readable files.

If an artifact is structurally invalid, the audit records
`STRUCTURAL_INVALID` and does not derive identity or reference comparisons
from that artifact.

If the package directory or manifest cannot be established, the CLI exits
2 and emits no JSON document.

## Package Identity

Expected identity is the same rule sidecar creators already use:

```text
manifest.federation.federated_package_id
    when present and a non-blank string
otherwise
    package directory name
```

Each package-scoped sidecar `package_reference` is compared literally
against that expected value. No aliasing or federated-ID translation is
performed.

## Reference Coherence

Declared paths resolve **relative to the declaring file only** through the
shared helper in `scripts/_shared/artifact_references.py`. There is no
project-root fallback. See `docs/integration/ARTIFACT_REFERENCE_PATHS.md`.

* If a declared path does not exist: `MISSING_REFERENCE` (error)
* If it exists but is a different file than conventional discovery:
  `REFERENCE_MISMATCH` (error)
* If an optional artifact is absent and unreferenced: inventory
  `present: false` only — no finding

## Traceability Bundle Semantics

The bundle is a navigational index. The audit compares its declared
contents to the artifacts actually discovered. A disagreement is a
finding. The bundle is not treated as authoritative.

## Production Shop Handoff Semantics

The audit checks that the handoff identifies this package and that its
declared package, strategy, review packet, and bundle references resolve
coherently. It does not infer machine readiness or permission.

## Creation Studio Request Semantics

The audit checks that the request identifies this package and that its
declared contents resolve. It does not perform A25/A26 capability
reconciliation.

## Findings

| Code | Severity | Meaning |
| --- | --- | --- |
| `STRUCTURAL_INVALID` | error | Existing validator rejected the artifact |
| `PACKAGE_REFERENCE_MISMATCH` | error | Sidecar identity ≠ expected identity |
| `MISSING_REFERENCE` | error | Declared path does not resolve |
| `REFERENCE_MISMATCH` | error | Declared path resolves to a different file than discovery |
| `IDENTITY_UNAVAILABLE` | warning | Comparison expected, but no usable `package_reference` |

Optional absence is not an `info` finding.

Duplicate competing candidates are out of v1.

Findings are sorted by severity, artifact, code, path, then slot.

## Severity

```text
error    blocks --fail-on-errors
warning  never fails the process
info     unused for optional absence in v1
```

## Exit Codes

```text
0  audit completed (advisory)
1  audit completed with error findings and --fail-on-errors
2  package/manifest cannot be established
```

`--fail-on-errors` changes only the exit status. JSON is identical.

## JSON Output

`--json` writes one deterministic document to stdout and nothing to
stderr on a completed audit.

```json
{
  "package": {"path": "...", "package_reference": "..."},
  "artifacts": {},
  "findings": [],
  "summary": {"errors": 0, "warnings": 0, "infos": 0}
}
```

Artifact paths are POSIX-normalized relative to the package directory.
`package.path` keeps the input spelling (relative or absolute) after POSIX
normalization and is never rewritten against the process cwd. The document
is not a persisted contract.

The payload must not contain `approved`, `authorized`,
`execution_allowed`, `machine_ready`, `safe_to_run`, or
`permission_granted`.

## CI Usage

```bash
python scripts/audit_package_coherence.py \
  --package examples/packages/ltb_vcarve_synthetic_example \
  --json \
  --fail-on-errors
```

v1 does **not** add this command to repository GitHub Actions.

## Authority Boundary

This audit measures evidence consistency. A coherent package may still
contain a poor strategy, incomplete review, or unsafe setup. An
incoherent package is not prohibited by CAM-A28.

## Committed example classification

Auditing `examples/packages/ltb_vcarve_synthetic_example` is identity-coherent
(`luthiers-toolbox:vcarve:les-paul-custom-2024`). Declared traceability
references resolve declaring-file-relative. CAM-A29 corrected the
decision-record and lineage path strings that previously used
repository-root-style form; that change was a fixture/contract correction,
not a rewrite of the manufacturing decision.

`--json --fail-on-errors` exits `0` for this example. CAM-A28 still reports
a repo-root-style string as `MISSING_REFERENCE` if one is reintroduced.

## Non-Goals

CAM-A28 does not repair artifacts, generate missing sidecars, normalize
identities, perform capability reconciliation, assess machining quality,
authorize execution, persist an audit record, or assign later numbered work.
