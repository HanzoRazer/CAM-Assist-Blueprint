# Package Identity Conventions

> **Important**: These are CAM Assist interchange conventions.
> They are not ecosystem mandates.
> Each origin system remains sovereign over its own authority.

## Purpose

CAM Assist provides optional federation metadata fields that enable cross-system package interchange without creating centralized authority.

## Constitutional Principle

```
transporting authority ≠ creating authority
```

CAM Assist is a federal courier, not an emperor. These conventions enable packages to declare their origin and suggest review routing, but do not grant execution authority or override local sovereignty.

## Federation Fields

All federation fields are **optional**. Packages without federation metadata remain valid.

### origin_system

Self-declared identifier of the system that created this package.

- Format: lowercase slug with dots, hyphens, underscores allowed
- Examples: `luthiers-toolbox`, `tap-tone-pi`, `ibg-sandbox`
- Validation: CAM Assist validates format only, not legitimacy

```json
"origin_system": "luthiers-toolbox"
```

### authority_domain

Domain of authority that created the package content.

- Does **not** imply execution authority
- Describes the type of knowledge/capability, not runtime control
- Examples: `runtime_cam`, `acoustic_analysis`, `geometry_generation`

```json
"authority_domain": "runtime_cam"
```

### review_jurisdiction

Suggested review jurisdiction for this package.

- May differ from `authority_domain` to enable cross-system review
- Example: package from `luthiers-toolbox` may request acoustic review from `tap-tone-pi`
- This is a routing hint, not an authority claim

```json
"review_jurisdiction": "manufacturing_review"
```

### federated_package_id

Informational identifier in federated namespace.

- No uniqueness enforcement by CAM Assist
- Format is origin-system-specific
- Purely informational for tracking/reference

```json
"federated_package_id": "luthiers-toolbox:vcarve:example-001"
```

## Example

```json
{
  "federation": {
    "origin_system": "luthiers-toolbox",
    "authority_domain": "runtime_cam",
    "review_jurisdiction": "manufacturing_review",
    "federated_package_id": "luthiers-toolbox:vcarve:example-001"
  }
}
```

## What These Fields Do NOT Do

- Grant execution authority
- Create registry control
- Override local system sovereignty
- Establish mandatory ecosystem standards
- Imply trust relationships

## Backward Compatibility

Existing packages without federation fields remain fully valid. Federation metadata is forward-only — existing packages are not retrofitted.
