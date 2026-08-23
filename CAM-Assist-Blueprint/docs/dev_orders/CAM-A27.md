# Dev Order — CAM-A27

## Capability Map Runtime Hardening

## Classification

```text
maintenance-class
not a new mapping capability
no canonical mapping change
```

CAM-A27 occupies an A-number by explicit authorization, the same way CAM-A24
did. It is **not** a product capability. It does not change A26 mapping
policy, reconciliation semantics, or authority.

## Predecessor baseline

```text
Baseline            CAM-Assist-Blueprint main @ fc9ab51
Latest capability   CAM-A26 — Creation Studio Capability Vocabulary Bridge
                    (merged PR #34)
CAM-A27             defined by this dev order, and by nothing preceding it
```

CAM-A26 / PR #34 is on `main`. This work does not stack on an open A26 branch.

## Scope

Harden the A26 runtime boundary so shared map loading is imported through a
stable module, expected failures stay controlled, mapping-index construction
cannot silently drop malformed rows, blank identifiers cannot enter
reconciliation sets, provenance paths are portable, and `declared_count`
cannot mix request and declaration namespaces.

No new mapping semantics.

## Design decisions recorded at implementation time

### Shared module location

There is no existing `scripts/_shared/` convention. CAM-A27 introduces one:

```text
scripts/_shared/creation_studio_capability_map.py
```

`_shared` is a package so both CLI scripts can import it when `scripts/` is
on `sys.path` (the normal `python scripts/<tool>.py` case, and tests that
insert `scripts/`). No public installable package is created.

### CLI scripts do not import one another

```text
reconcile_creation_studio_capabilities.py
        ↓
scripts/_shared/creation_studio_capability_map.py
        ↑
validate_creation_studio_capability_map.py
```

The validator remains a thin CLI adapter and may re-export shared names so
existing in-process tests keep a stable import surface.

### Exception types

Two types, not a hierarchy:

| Type | Meaning |
| --- | --- |
| `CapabilityMapInputError` | Missing or unreadable file, including the authoritative A22 schema |
| `CapabilityMapContractError` | Readable JSON that is not a valid map, or a helper called with data it cannot index |

CLI boundaries catch both. No `RuntimeError` escapes expected failure paths.

### Validator exit codes

```text
0  structurally valid map
1  invalid map content (including unparseable map JSON)
2  missing/unreadable map file, or missing/unreadable/malformed A22 schema
```

The reconciler still treats any unusable map as an input failure (exit 2).

### `build_mapping_index()` is strict

Callers supply a structurally usable mappings list. Non-object rows, missing
or blank sources, non-list targets, and non-string or blank targets raise
`CapabilityMapContractError`. The helper does **not** re-validate the A22
enum or the A23 identifier pattern.

### Blank identifiers at the structural minimum

`read_request` / `read_profile` reject `""` and whitespace-only identifiers.
They still do not enforce the A22 enum or the A23 pattern. Unusual non-blank
strings continue to flow through.

### Provenance paths

All three provenance paths (request, profile, map) use the same normalizer:

* POSIX separators
* `posixpath.normpath` so `./x` and `a/../x` collapse
* never `Path.resolve()` — relative inputs stay relative

### `declared_count` is removed

Repository-wide search found **no callers**. In mapped mode
`len(satisfied) + len(declared_but_unrequested)` mixed A22 and A23
namespaces. Removal is preferred over documenting a trap.
`requested_count` remains: it is `len(satisfied) + len(unsatisfied)` and
stays a count of request identifiers.

### Canonical mappings are frozen

```text
feeds_speeds_recommendation  →  feeds_speeds_authoring
simulation_request           →  simulation_support
gcode_explanation            →  gcode_tutorial_generation
                             →  post_processor_education
```

## Non-goals

No new mappings, no A22/A23 schema changes, no fuzzy matching, no Creation
Studio runtime, no persisted reconciliation, no next product capability.

## Completion criterion

> **Can CAM Assist load and apply the A26 capability bridge reliably across
> supported invocation contexts without changing its mapping policy,
> reconciliation semantics, or authority boundary?**

**Yes.**
