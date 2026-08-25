# Artifact Reference Paths

## Purpose

CAM Assist artifacts point at one another with portable relative path strings.
This document is the single contract for how those strings are stored and
resolved. It is maintenance of existing traceability mechanics, not a new
product capability.

## Canonical Rule

Every relative artifact reference is interpreted **relative to the file that
declares the reference**:

```text
resolve_declared_reference(declaring_file, value)
    = normalize(declaring_file.parent / value)
```

Writers store:

```text
relative_reference(output_file, target_file)
```

which is the path from `output_file.parent` to `target_file`.

## Declaring File

The declaring file is the JSON artifact that contains the reference field.
Examples: a manufacturing decision record, a revision lineage, a traceability
bundle, a Production Shop handoff, or a Creation Studio request.

Resolution uses that file's directory. It does not use the process working
directory and it does not use the repository root unless that happens to be
the declaring file's parent.

## Relative References

Stored values are portable relative paths.

Same directory:

```json
{ "risk_file": "ltb_vcarve_synthetic_example_risk.json" }
```

Sibling directory:

```json
{ "annotations_file": "../review_annotations/ltb_vcarve_synthetic_example_annotations.json" }
```

## Forward-Slash Serialization

Serialized JSON references use `/`, not platform-native separators. A Windows
writer must still emit `../review_annotations/file.json`, never
`..\\review_annotations\\file.json`.

## Examples

A decision record at
`examples/traceability/ltb_vcarve_synthetic_example_decision_record.json`
referencing sidecars in the same directory stores:

```json
{
  "assumptions_file": "ltb_vcarve_synthetic_example_assumptions.json",
  "risk_file": "ltb_vcarve_synthetic_example_risk.json"
}
```

CLI arguments may still be written in whatever spelling locates the target
file (`--assumptions-file examples/traceability/...json`). The stored JSON
is rewritten to the canonical relative form. The raw CLI string is not
preserved.

## Cross-Directory References

Portable packages require `..` when the target lives in a sibling directory.
`..` is supported and expected. CAM-A29 does not introduce a path-security
sandbox or package-root escape policy.

## Resolution

Creators, completeness validators, and the CAM-A28 package coherence audit
share `scripts/_shared/artifact_references.py`.

Default completeness resolution is declaring-file-relative. The traceability
bundle validator's `--base` flag is an **explicit operator override** of the
resolution directory. It is not a silent repository-root fallback and is not
removed.

## Creation/Validation Symmetry

```text
resolve_declared_reference(
    output_file,
    relative_reference(output_file, target_file)
)
== normalized target_file
```

If a creator emits a reference, the matching completeness check must recover
the same target through the shared resolver.

## Portability

Committed references must remain valid when a package and its surrounding
sidecars move together. They must not encode a checkout-specific absolute
path or assume a particular repository-root working directory.

## Working-Directory Independence

Reference resolution does not call `os.getcwd()`. Given the same declaring
file path, resolution is identical regardless of where the validator or
auditor process was launched. CLI writers may interpret *input* relative
paths against process CWD (that is how the shell located the file); they then
store a declaring-file-relative string.

## Forbidden Patterns

Do not store:

```text
C:\Users\...
/home/user/...
examples/traceability/foo.json   (inside a file already under examples/traceability/)
```

Do not implement:

```text
try declaring-file-relative
else try repository root
```

A malformed reference must remain invalid.

## Legacy Example Correction

CAM-A28 classified committed decision-record and lineage references that used
repository-root-style strings as example debt. CAM-A29 corrected those path
strings only. The manufacturing decision, rationale, risks, assumptions,
authority flags, and package identity were not rewritten. Changing a
malformed relative path in a committed example is a fixture/contract
correction, not historical revisionism of the decision those artifacts record.

## Non-Goals

This contract does not authorize:

* a second resolution fallback
* repository-root-relative stored references
* absolute committed paths
* automatic bulk migration of historical records
* reference URI schemes
* path-security sandboxing
* package identity changes
* schema redesign
* A12 review-decision rewrite
* manifest `strategy_file` / `review_packet_file` rewrite
* CAM-A25/A26 reconciliation changes

Manifest core-file paths already resolve relative to the manifest. They were
inventoried and left unchanged. A12 `record_review_decision.py` still stores
CLI link strings as given; that writer is out of CAM-A29 scope.
