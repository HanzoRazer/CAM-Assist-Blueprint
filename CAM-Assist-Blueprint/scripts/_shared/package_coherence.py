"""Read-only package coherence audit.

Import-stable. The CLI adapter in ``scripts/audit_package_coherence.py``
consumes this file. No argument parsing and no printing.

Coherence is evidence consistency, not execution authority.
"""

from __future__ import annotations

import json
import os
import posixpath
from pathlib import Path, PurePosixPath
from typing import Callable, NamedTuple

from _shared.package_discovery import (
    resolve_annotations,
    resolve_bundle,
    resolve_creation_studio_request,
    resolve_handoff,
    resolve_traceability,
)
from validate_creation_studio_request import validate_request_file
from validate_manufacturing_assumptions import validate_assumptions_file
from validate_manufacturing_decision_record import validate_decision_record_file
from validate_manifest import validate_manifest_file
from validate_production_shop_handoff import validate_handoff_file
from validate_review_annotations import validate_annotations_file
from validate_revision_lineage import validate_lineage_file
from validate_risk_assessment import validate_risk_assessment_file
from validate_strategy_package import validate_file as validate_strategy_file
from validate_traceability_bundle import validate_bundle_file

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

CODE_STRUCTURAL_INVALID = "STRUCTURAL_INVALID"
CODE_PACKAGE_REFERENCE_MISMATCH = "PACKAGE_REFERENCE_MISMATCH"
CODE_MISSING_REFERENCE = "MISSING_REFERENCE"
CODE_REFERENCE_MISMATCH = "REFERENCE_MISMATCH"
CODE_IDENTITY_UNAVAILABLE = "IDENTITY_UNAVAILABLE"

ARTIFACT_ORDER = [
    "manifest",
    "strategy",
    "review_packet",
    "annotations",
    "assumptions",
    "risk_assessment",
    "decision_record",
    "revision_lineage",
    "traceability_bundle",
    "production_shop_handoff",
    "creation_studio_request",
]

PACKAGE_SCOPED_IDENTITY = {
    "annotations",
    "assumptions",
    "risk_assessment",
    "decision_record",
    "revision_lineage",
    "traceability_bundle",
    "production_shop_handoff",
    "creation_studio_request",
}

FORBIDDEN_RESULT_KEYS = {
    "approved",
    "authorized",
    "execution_allowed",
    "machine_ready",
    "safe_to_run",
    "permission_granted",
}

_SEVERITY_RANK = {SEVERITY_ERROR: 0, SEVERITY_WARNING: 1, SEVERITY_INFO: 2}

_MANIFEST_REFERENCE_PREFIXES = (
    "Referenced strategy file not found:",
    "Referenced review packet file not found:",
    "Referenced geometry file not found:",
)


class PackageCoherenceInputError(Exception):
    """The package cannot be established as an audit anchor."""


class ArtifactStatus(NamedTuple):
    name: str
    present: bool
    path: str | None
    structural: str | None


class CoherenceFinding(NamedTuple):
    code: str
    severity: str
    artifact: str
    message: str
    expected: str | None = None
    actual: str | None = None
    path: str | None = None
    slot: str | None = None


class PackageCoherenceResult(NamedTuple):
    package_path: str
    package_reference: str | None
    artifacts: dict[str, ArtifactStatus]
    findings: list[CoherenceFinding]

    @property
    def error_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == SEVERITY_ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == SEVERITY_WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for finding in self.findings if finding.severity == SEVERITY_INFO)

    def summary(self) -> dict[str, int]:
        return {
            "errors": self.error_count,
            "warnings": self.warning_count,
            "infos": self.info_count,
        }

    def to_json_dict(self) -> dict:
        artifacts = {
            name: {
                "present": status.present,
                "path": status.path,
                "structural": status.structural,
            }
            for name, status in self.artifacts.items()
        }
        findings = [finding_to_dict(finding) for finding in self.findings]
        payload = {
            "package": {
                "path": self.package_path,
                "package_reference": self.package_reference,
            },
            "artifacts": artifacts,
            "findings": findings,
            "summary": self.summary(),
        }
        _assert_no_authority_fields(payload)
        return payload


def finding_to_dict(finding: CoherenceFinding) -> dict:
    return {
        "code": finding.code,
        "severity": finding.severity,
        "artifact": finding.artifact,
        "expected": finding.expected,
        "actual": finding.actual,
        "path": finding.path,
        "slot": finding.slot,
        "message": finding.message,
    }


def normalize_report_path(path: Path | str, relative_to: Path | None = None) -> str:
    """POSIX-normalize a report path without inventing a new location."""
    raw = path.as_posix() if isinstance(path, Path) else PurePosixPath(path).as_posix()
    if relative_to is not None:
        try:
            rel = os.path.relpath(str(Path(path).resolve()), str(relative_to.resolve()))
            return posixpath.normpath(rel.replace("\\", "/"))
        except OSError:
            pass
    normalized = posixpath.normpath(raw)
    if Path(path).is_absolute():
        try:
            rel = os.path.relpath(str(Path(path)), os.getcwd())
            return posixpath.normpath(rel.replace("\\", "/"))
        except OSError:
            return normalized
    return normalized


def expected_package_identity(package_dir: Path, manifest: dict) -> str:
    """Creator rule: federated_package_id when present and non-blank, else directory name."""
    federation = manifest.get("federation")
    if isinstance(federation, dict):
        federated = federation.get("federated_package_id")
        if isinstance(federated, str) and federated.strip():
            return federated
    return package_dir.name


def extract_package_reference(data: dict) -> str | None:
    value = data.get("package_reference")
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def load_json_object(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _same_file(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def _is_reference_existence_error(error: str) -> bool:
    return any(error.startswith(prefix) for prefix in _MANIFEST_REFERENCE_PREFIXES)


def discover_package_artifacts(package_dir: Path, manifest: dict | None) -> dict[str, Path | None]:
    """One conventional (or manifest-declared) path per participating artifact."""
    paths: dict[str, Path | None] = {name: None for name in ARTIFACT_ORDER}
    manifest_path = package_dir / "manifest.json"
    if manifest_path.is_file():
        paths["manifest"] = manifest_path

    if isinstance(manifest, dict):
        strategy = manifest.get("strategy_file")
        if isinstance(strategy, str) and strategy.strip():
            paths["strategy"] = package_dir / strategy
        review = manifest.get("review_packet_file")
        if isinstance(review, str) and review.strip():
            paths["review_packet"] = package_dir / review

    if paths["strategy"] is None:
        candidate = package_dir / "strategy.json"
        if candidate.is_file():
            paths["strategy"] = candidate
    if paths["review_packet"] is None:
        candidate = package_dir / "review_packet.md"
        if candidate.is_file():
            paths["review_packet"] = candidate

    annotations = resolve_annotations(package_dir)
    if annotations["present"]:
        paths["annotations"] = Path(annotations["path"])

    traceability = resolve_traceability(package_dir)
    for key in ("assumptions", "risk_assessment", "decision_record", "revision_lineage"):
        if traceability[key]["present"]:
            paths[key] = Path(traceability[key]["path"])

    bundle = resolve_bundle(package_dir)
    if bundle["present"]:
        paths["traceability_bundle"] = Path(bundle["path"])

    handoff = resolve_handoff(package_dir)
    if handoff["present"]:
        paths["production_shop_handoff"] = Path(handoff["path"])

    request = resolve_creation_studio_request(package_dir)
    if request["present"]:
        paths["creation_studio_request"] = Path(request["path"])

    return paths


def _validate_review_packet(path: Path) -> tuple[bool, list[str]]:
    if not path.is_file():
        return False, [f"Review packet is not a file: {path}"]
    try:
        path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, [f"Review packet could not be read: {path} ({exc})"]
    return True, []


def validate_artifact(name: str, path: Path):
    """Reuse the dedicated validator. Review packets have no JSON schema."""
    if name == "manifest":
        return validate_manifest_file(path)
    if name == "strategy":
        return validate_strategy_file(path)
    if name == "review_packet":
        valid, errors = _validate_review_packet(path)
        return type("Result", (), {"valid": valid, "errors": errors, "warnings": []})()
    validators: dict[str, Callable] = {
        "annotations": validate_annotations_file,
        "assumptions": validate_assumptions_file,
        "risk_assessment": validate_risk_assessment_file,
        "decision_record": validate_decision_record_file,
        "revision_lineage": validate_lineage_file,
        "traceability_bundle": validate_bundle_file,
        "production_shop_handoff": validate_handoff_file,
        "creation_studio_request": validate_request_file,
    }
    return validators[name](path)


def extract_declared_references(name: str, data: dict) -> list[tuple[str, str, str | None]]:
    """Return (slot, declared_value, target_artifact_or_none)."""
    refs: list[tuple[str, str, str | None]] = []

    def add(slot: str, value: object, target: str | None) -> None:
        if isinstance(value, str) and value.strip():
            refs.append((slot, value, target))

    if name == "manifest":
        add("strategy_file", data.get("strategy_file"), "strategy")
        add("review_packet_file", data.get("review_packet_file"), "review_packet")
        geometry = data.get("source_geometry_files")
        if isinstance(geometry, list):
            for index, item in enumerate(geometry):
                add(f"source_geometry_files[{index}]", item, None)
    elif name == "decision_record":
        add("assumptions_file", data.get("assumptions_file"), "assumptions")
        add("risk_file", data.get("risk_file"), "risk_assessment")
        add("lineage_file", data.get("lineage_file"), "revision_lineage")
    elif name == "revision_lineage":
        revisions = data.get("revisions")
        if isinstance(revisions, list):
            for index, revision in enumerate(revisions):
                if not isinstance(revision, dict):
                    continue
                related = revision.get("related_records")
                if not isinstance(related, dict):
                    continue
                prefix = f"revisions[{index}].related_records"
                add(f"{prefix}.assumptions_file", related.get("assumptions_file"), "assumptions")
                add(f"{prefix}.risk_file", related.get("risk_file"), "risk_assessment")
                add(
                    f"{prefix}.decision_record_file",
                    related.get("decision_record_file"),
                    "decision_record",
                )
    elif name == "traceability_bundle":
        contents = data.get("bundle_contents")
        if isinstance(contents, dict):
            add("bundle_contents.assumptions_file", contents.get("assumptions_file"), "assumptions")
            add("bundle_contents.risk_file", contents.get("risk_file"), "risk_assessment")
            add(
                "bundle_contents.decision_record_file",
                contents.get("decision_record_file"),
                "decision_record",
            )
            add(
                "bundle_contents.annotations_file",
                contents.get("annotations_file"),
                "annotations",
            )
            add("bundle_contents.lineage_file", contents.get("lineage_file"), "revision_lineage")
    elif name == "production_shop_handoff":
        contents = data.get("contents")
        if isinstance(contents, dict):
            add("contents.package_manifest_file", contents.get("package_manifest_file"), "manifest")
            add("contents.strategy_file", contents.get("strategy_file"), "strategy")
            add("contents.review_packet_file", contents.get("review_packet_file"), "review_packet")
            add(
                "contents.traceability_bundle_file",
                contents.get("traceability_bundle_file"),
                "traceability_bundle",
            )
    elif name == "creation_studio_request":
        contents = data.get("contents")
        if isinstance(contents, dict):
            add("contents.package_manifest_file", contents.get("package_manifest_file"), "manifest")
            add("contents.strategy_file", contents.get("strategy_file"), "strategy")
            add("contents.review_packet_file", contents.get("review_packet_file"), "review_packet")
            add(
                "contents.traceability_bundle_file",
                contents.get("traceability_bundle_file"),
                "traceability_bundle",
            )
            add(
                "contents.production_shop_handoff_file",
                contents.get("production_shop_handoff_file"),
                "production_shop_handoff",
            )
    return refs


def sort_findings(findings: list[CoherenceFinding]) -> list[CoherenceFinding]:
    return sorted(
        findings,
        key=lambda finding: (
            _SEVERITY_RANK.get(finding.severity, 9),
            finding.artifact,
            finding.code,
            finding.path or "",
            finding.slot or "",
            finding.message,
        ),
    )


def _assert_no_authority_fields(payload: object) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in FORBIDDEN_RESULT_KEYS:
                raise RuntimeError(f"coherence result must not contain {key!r}")
            _assert_no_authority_fields(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_authority_fields(item)


def compare_package_identity(
    artifact: str,
    declared: str | None,
    expected: str,
    path: str | None,
) -> CoherenceFinding | None:
    if declared is None:
        return CoherenceFinding(
            code=CODE_IDENTITY_UNAVAILABLE,
            severity=SEVERITY_WARNING,
            artifact=artifact,
            message=f"{artifact} does not declare a usable package_reference",
            expected=expected,
            actual=None,
            path=path,
        )
    if declared != expected:
        return CoherenceFinding(
            code=CODE_PACKAGE_REFERENCE_MISMATCH,
            severity=SEVERITY_ERROR,
            artifact=artifact,
            message=(
                f"{artifact} package_reference {declared!r} does not match "
                f"expected {expected!r}"
            ),
            expected=expected,
            actual=declared,
            path=path,
        )
    return None


def compare_reference_target(
    artifact: str,
    slot: str,
    declared: str,
    resolved: Path,
    discovered: Path | None,
    path: str | None,
) -> CoherenceFinding | None:
    if not resolved.exists():
        return CoherenceFinding(
            code=CODE_MISSING_REFERENCE,
            severity=SEVERITY_ERROR,
            artifact=artifact,
            message=f"{artifact} {slot} does not resolve: {declared}",
            expected=declared,
            actual=None,
            path=path,
            slot=slot,
        )
    if discovered is not None and discovered.exists() and not _same_file(resolved, discovered):
        return CoherenceFinding(
            code=CODE_REFERENCE_MISMATCH,
            severity=SEVERITY_ERROR,
            artifact=artifact,
            message=(
                f"{artifact} {slot} resolves to a different artifact than "
                f"conventional discovery"
            ),
            expected=str(discovered),
            actual=declared,
            path=path,
            slot=slot,
        )
    return None


def audit_package_coherence(package_dir: Path) -> PackageCoherenceResult:
    """Audit one package. Raises PackageCoherenceInputError when the anchor fails."""
    if not package_dir.exists():
        raise PackageCoherenceInputError(f"Package directory not found: {package_dir}")
    if not package_dir.is_dir():
        raise PackageCoherenceInputError(f"Path is not a directory: {package_dir}")

    manifest_path = package_dir / "manifest.json"
    if not manifest_path.is_file():
        raise PackageCoherenceInputError(f"manifest.json is missing: {manifest_path}")

    manifest_result = validate_manifest_file(manifest_path)
    manifest = load_json_object(manifest_path)
    if manifest is None:
        raise PackageCoherenceInputError(f"manifest.json is not readable JSON: {manifest_path}")
    if not manifest_result.valid and any(
        not _is_reference_existence_error(error) for error in manifest_result.errors
    ):
        raise PackageCoherenceInputError(
            "Package manifest is not structurally usable: "
            + "; ".join(manifest_result.errors)
        )

    expected = expected_package_identity(package_dir, manifest)
    discovered = discover_package_artifacts(package_dir, manifest)
    findings: list[CoherenceFinding] = []
    statuses: dict[str, ArtifactStatus] = {}
    loaded: dict[str, dict] = {"manifest": manifest}

    for name in ARTIFACT_ORDER:
        path = discovered[name]
        if path is None or not Path(path).exists():
            statuses[name] = ArtifactStatus(name, False, None, None)
            continue
        report = normalize_report_path(path, relative_to=package_dir)
        if name == "manifest" and not manifest_result.valid:
            statuses[name] = ArtifactStatus(name, True, report, "invalid")
            findings.append(
                CoherenceFinding(
                    code=CODE_STRUCTURAL_INVALID,
                    severity=SEVERITY_ERROR,
                    artifact=name,
                    message="manifest failed structural validation",
                    path=report,
                    actual="; ".join(manifest_result.errors),
                )
            )
            continue
        result = validate_artifact(name, Path(path)) if name != "manifest" else manifest_result
        if name == "manifest":
            statuses[name] = ArtifactStatus(
                name, True, report, "valid" if manifest_result.valid else "invalid"
            )
            if not manifest_result.valid:
                findings.append(
                    CoherenceFinding(
                        code=CODE_STRUCTURAL_INVALID,
                        severity=SEVERITY_ERROR,
                        artifact=name,
                        message="manifest failed structural validation",
                        path=report,
                        actual="; ".join(manifest_result.errors),
                    )
                )
            continue
        if not result.valid:
            statuses[name] = ArtifactStatus(name, True, report, "invalid")
            findings.append(
                CoherenceFinding(
                    code=CODE_STRUCTURAL_INVALID,
                    severity=SEVERITY_ERROR,
                    artifact=name,
                    message=f"{name} failed structural validation",
                    path=report,
                    actual="; ".join(result.errors),
                )
            )
            continue
        statuses[name] = ArtifactStatus(name, True, report, "valid")
        data = load_json_object(Path(path))
        if data is not None:
            loaded[name] = data

    for name in ARTIFACT_ORDER:
        status = statuses[name]
        if not status.present or status.structural != "valid":
            continue
        if name not in PACKAGE_SCOPED_IDENTITY:
            continue
        data = loaded.get(name)
        if data is None:
            continue
        finding = compare_package_identity(
            name, extract_package_reference(data), expected, status.path
        )
        if finding is not None:
            findings.append(finding)

    for name in ARTIFACT_ORDER:
        status = statuses[name]
        if not status.present or status.structural != "valid":
            continue
        data = loaded.get(name)
        if data is None:
            continue
        declaring = discovered[name]
        if declaring is None:
            continue
        for slot, declared, target in extract_declared_references(name, data):
            resolved = declaring.parent / declared
            target_path = discovered.get(target) if target is not None else None
            finding = compare_reference_target(
                name, slot, declared, resolved, target_path, status.path
            )
            if finding is not None:
                findings.append(finding)

    ordered = {name: statuses[name] for name in ARTIFACT_ORDER}
    return PackageCoherenceResult(
        package_path=normalize_report_path(package_dir),
        package_reference=expected,
        artifacts=ordered,
        findings=sort_findings(findings),
    )


def format_human_report(result: PackageCoherenceResult) -> str:
    lines = [
        "CAM Assist Package Coherence Audit",
        "==================================",
        "",
        f"Package: {result.package_path}",
        f"Identity: {result.package_reference}",
        "",
        "Artifacts:",
    ]
    width = max(len(name) for name in ARTIFACT_ORDER)
    for name in ARTIFACT_ORDER:
        status = result.artifacts[name]
        if not status.present:
            lines.append(f"  {name:<{width}}  absent")
            continue
        structural = status.structural or "unknown"
        lines.append(f"  {name:<{width}}  present  {structural}")
    lines.append("")
    lines.append("Findings:")
    if not result.findings:
        lines.append("  none")
    else:
        for finding in result.findings:
            location = finding.slot or finding.path or ""
            suffix = f"  {location}" if location else ""
            lines.append(
                f"  [{finding.severity}] {finding.artifact}  {finding.code}{suffix}"
            )
            lines.append(f"      {finding.message}")
    summary = result.summary()
    lines.extend(
        [
            "",
            "Summary:",
            f"  errors: {summary['errors']}",
            f"  warnings: {summary['warnings']}",
            "",
            "This audit reports evidence consistency only.",
            "It does not approve a package, authorize execution, or establish machine readiness.",
        ]
    )
    return "\n".join(lines) + "\n"


def serialize_coherence(result: PackageCoherenceResult) -> str:
    return json.dumps(result.to_json_dict(), indent=2, sort_keys=True) + "\n"
