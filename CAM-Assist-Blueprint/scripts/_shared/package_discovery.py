"""Conventional CAM Assist sidecar discovery.

Import-stable. CLI adapters consume this module; they must not import one
another. No argument parsing and no printing.

Discovery is one conventional candidate per artifact type. It does not
broad-scan. Explicit override paths, when supplied, win over convention.
"""

from __future__ import annotations

from pathlib import Path

TRACEABILITY_SPECS = [
    ("assumptions", "assumptions", "_assumptions.json"),
    ("risk_assessment", "risk assessment", "_risk.json"),
    ("decision_record", "decision record", "_decision_record.json"),
    ("revision_lineage", "revision lineage", "_lineage.json"),
]
BUNDLE_SUFFIX = "_bundle.json"
HANDOFF_SUFFIX = "_handoff.json"
REQUEST_SUFFIX = "_request.json"
ANNOTATIONS_SUFFIX = "_annotations.json"
CAPABILITY_PROFILE_FILENAME = "capability_profile.json"


def is_examples_package(package_dir: Path) -> bool:
    """True when package_dir is examples/packages/<name>."""
    parent = package_dir.parent
    return parent.name == "packages" and parent.parent.name == "examples"


def conventional_base(package_dir: Path, directory_name: str) -> Path:
    """Parent-adjacent directory, or examples/<directory_name> for example packages."""
    parent = package_dir.parent
    if is_examples_package(package_dir):
        return parent.parent / directory_name
    return parent / directory_name


def conventional_traceability_path(package_dir: Path, suffix: str) -> Path:
    """Conventional sidecar location: <parent>/traceability/<package><suffix>.

    For examples/packages/<name>, look under examples/traceability/ instead.
    """
    return conventional_base(package_dir, "traceability") / f"{package_dir.name}{suffix}"


def conventional_handoff_path(package_dir: Path) -> Path:
    """Conventional handoff location: <parent>/production_shop/<package>_handoff.json.

    For examples/packages/<name>, look under examples/production_shop/ instead.
    """
    return conventional_base(package_dir, "production_shop") / (
        f"{package_dir.name}{HANDOFF_SUFFIX}"
    )


def conventional_request_path(package_dir: Path) -> Path:
    """Conventional request location: <parent>/creation_studio/<package>_request.json.

    For examples/packages/<name>, look under examples/creation_studio/ instead.
    """
    return conventional_base(package_dir, "creation_studio") / (
        f"{package_dir.name}{REQUEST_SUFFIX}"
    )


def conventional_annotations_path(package_dir: Path) -> Path:
    """Conventional annotations: <parent>/review_annotations/<package>_annotations.json.

    For examples/packages/<name>, look under examples/review_annotations/ instead.
    """
    return conventional_base(package_dir, "review_annotations") / (
        f"{package_dir.name}{ANNOTATIONS_SUFFIX}"
    )


def conventional_capability_profile_path(package_dir: Path) -> Path:
    """Conventional profile location: <parent>/creation_studio/capability_profile.json.

    For examples/packages/<name>, look under examples/creation_studio/ instead.
    """
    return conventional_base(package_dir, "creation_studio") / CAPABILITY_PROFILE_FILENAME


def _detect(explicit: Path | None, conventional: Path) -> dict:
    """Explicit flag first, then conventional path. Detection only."""
    path = explicit
    if path is None:
        if conventional.exists():
            path = conventional
    present = path is not None and Path(path).exists()
    return {"present": present, "path": str(path) if present else None}


def resolve_traceability(
    package_dir: Path,
    assumptions: Path | None = None,
    risk: Path | None = None,
    decision_record: Path | None = None,
    revision_lineage: Path | None = None,
) -> dict:
    """Resolve traceability sidecars: explicit flag first, then conventional fallback.

    Does not broad-scan. Returns {key: {"present": bool, "path": str | None}}.
    """
    explicit = {
        "assumptions": assumptions,
        "risk_assessment": risk,
        "decision_record": decision_record,
        "revision_lineage": revision_lineage,
    }
    out: dict = {}
    for key, _label, suffix in TRACEABILITY_SPECS:
        path = explicit.get(key)
        if path is None:
            candidate = conventional_traceability_path(package_dir, suffix)
            if candidate.exists():
                path = candidate
        present = path is not None and Path(path).exists()
        out[key] = {"present": present, "path": str(path) if present else None}
    return out


def resolve_bundle(package_dir: Path, explicit: Path | None = None) -> dict:
    """Detect a traceability bundle: explicit flag first, then conventional path.

    Detection only — does not parse, validate, resolve, or completeness-check the
    bundle's contents. Returns {"present": bool, "path": str | None}.
    """
    return _detect(explicit, conventional_traceability_path(package_dir, BUNDLE_SUFFIX))


def resolve_handoff(package_dir: Path, explicit: Path | None = None) -> dict:
    """Detect a production shop handoff: explicit flag first, then conventional path.

    Detection only — never opens, parses, validates, resolves references, or
    completeness-checks the handoff, and makes no Production Shop runtime
    assumptions. An existing-but-unparseable handoff still counts as present.
    Returns {"present": bool, "path": str | None}.
    """
    return _detect(explicit, conventional_handoff_path(package_dir))


def resolve_creation_studio_request(package_dir: Path, explicit: Path | None = None) -> dict:
    """Detect a creation studio request: explicit flag first, then conventional path.

    Detection only — never opens, parses, validates, resolves references, infers
    supported capabilities, or completeness-checks the request. An
    existing-but-unparseable request still counts as present.
    Returns {"present": bool, "path": str | None}.
    """
    return _detect(explicit, conventional_request_path(package_dir))


def resolve_annotations(package_dir: Path, explicit: Path | None = None) -> dict:
    """Detect review annotations: explicit flag first, then conventional path.

    Detection only. Returns {"present": bool, "path": str | None}.
    """
    return _detect(explicit, conventional_annotations_path(package_dir))


def resolve_capability_profile(package_dir: Path, explicit: Path | None = None) -> dict:
    """Detect a capability profile: explicit flag first, then conventional path.

    Detection only — never opens, parses, validates, resolves references, or reads
    which capabilities are declared. An existing-but-unparseable profile still
    counts as present. Presence says a Creation Studio profile was published
    alongside this package's tree; it says nothing about what Creation Studio can
    do for THIS package, and confers no authority of any kind.
    Returns {"present": bool, "path": str | None}.
    """
    return _detect(explicit, conventional_capability_profile_path(package_dir))
