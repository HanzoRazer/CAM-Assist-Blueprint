#!/usr/bin/env python3
"""
CAM-A25: reconcile a Creation Studio request against a capability profile.

Compares two contracts that already exist:

    CAM-A22 request   requested_capabilities[]        what CAM Assist asks for
    CAM-A23 profile   capabilities[].capability_id    what Creation Studio declares

and reports three sets, by EXACT identifier comparison:

    satisfied                = requested & declared
    unsatisfied              = requested - declared
    declared_but_unrequested = declared - requested

`declared_but_unrequested` is deliberately not called `undeclared`, which would
be confusable with the unsatisfied case -- a capability that WAS requested and is
NOT declared.

WHAT THIS DOES NOT DO
---------------------
No synonym mapping, alias table, ontology translation, semantic inference, or
fuzzy/prefix matching. A25 does not define semantic equivalence between A22
request identifiers and A23 capability identifiers.

Versions are surfaced for traceability, never interpreted. `profile_version` is
owned by CAM-Creation-Studio; inferring compatibility from it here would recreate
the coupling A23's open vocabulary exists to avoid.

AUTHORITY
---------
An unsatisfied capability is a compatibility finding, NOT a prohibition.
A satisfied capability is a declaration match, NOT authorization.

`satisfied` means only that the requested identifier appears in the supplied
profile. It does not mean Creation Studio is installed, reachable, operational,
correctly configured, machine-ready, safe, or able to produce acceptable
machining output. This module grants no execution authority and selects no
capability on anyone's behalf.

This file is reference-only tooling. It reads two records and writes nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path
from typing import NamedTuple

# CAM-A23 fixes this filename. Profile discovery matches the FILE, never merely a
# creation_studio/ directory -- a package's request sidecars live in a directory
# of that name too, and stopping there would resolve to a location holding no
# profile at all.
PROFILE_FILENAME = "capability_profile.json"
REQUEST_SUFFIX = "_request.json"
CREATION_STUDIO_DIR = "creation_studio"

# Exit codes. 2 is an input failure, never a reconciliation result: a missing
# profile must not be reported as "nothing declared".
EXIT_OK = 0
EXIT_UNSATISFIED_STRICT = 1
EXIT_INPUT_ERROR = 2

# Human-report wrap width. The canonical finding message stays a single string in
# the JSON output; only the console rendering is wrapped.
REPORT_WIDTH = 69

# --- finding codes -----------------------------------------------------------

NAMESPACE_DIVERGENCE = "namespace_divergence"

NAMESPACE_DIVERGENCE_MESSAGE = (
    "The request and capability-profile vocabularies are both non-empty "
    "but share no identifiers."
)

SEVERITY_WARNING = "warning"

ADVISORY_NOTICE = (
    "ADVISORY ONLY - identifier matches do not imply execution authority,\n"
    "machine readiness, or downstream availability."
)


class Finding(NamedTuple):
    """A derived diagnosis about the reconciliation as a whole."""

    code: str
    severity: str
    message: str

    def as_dict(self) -> dict:
        return {"code": self.code, "severity": self.severity, "message": self.message}


class Reconciliation(NamedTuple):
    """The complete result. Sets are sorted, so output never depends on input order."""

    satisfied: list[str]
    unsatisfied: list[str]
    declared_but_unrequested: list[str]
    findings: list[Finding]

    @property
    def requested_count(self) -> int:
        return len(self.satisfied) + len(self.unsatisfied)

    @property
    def declared_count(self) -> int:
        return len(self.satisfied) + len(self.declared_but_unrequested)

    def has_finding(self, code: str) -> bool:
        return any(f.code == code for f in self.findings)

    def as_dict(self) -> dict:
        """Ephemeral serialization of the calculation.

        NOT a repository contract, schema, or stored sidecar. It exists so CI can
        consume the same numbers a human reads, and may be reshaped by a later
        capability without a migration.
        """
        return {
            "satisfied": self.satisfied,
            "unsatisfied": self.unsatisfied,
            "declared_but_unrequested": self.declared_but_unrequested,
            "findings": [f.as_dict() for f in self.findings],
        }


# --- input provenance --------------------------------------------------------
#
# Provenance answers a question the reconciliation itself cannot: WHICH request
# and WHICH profile produced this result.
#
# It is deliberately kept OUT of `reconcile()`. The core stays filesystem-free
# and knows nothing about paths or versions, so provenance cannot influence set
# membership by construction rather than merely by test. Versions are carried for
# display only -- comparing them would couple CAM Assist to CAM-Creation-Studio's
# release semantics, which is exactly what A23's open vocabulary avoids.
#
# Paths are POSIX-normalized and NOT absolutized: the same repository layout must
# serialize identically on Windows and Linux, and a machine-specific root would
# defeat that while telling a reviewer nothing useful.


def _posix(path: Path) -> str:
    return path.as_posix()


def _without_missing(fields: dict) -> dict:
    """Drop absent metadata rather than serializing it as null.

    A25 reads only the structural minimum, so a field it never required may be
    absent. Omitting is honest; `null` would assert the record carries an empty
    value.
    """
    return {key: value for key, value in fields.items() if value is not None}


class RequestProvenance(NamedTuple):
    """Identity of the CAM-A22 request actually consumed."""

    path: str
    record_version: str | None = None
    package_reference: str | None = None

    def as_dict(self) -> dict:
        return _without_missing(
            {
                "path": self.path,
                "record_version": self.record_version,
                "package_reference": self.package_reference,
            }
        )


class ProfileProvenance(NamedTuple):
    """Identity of the CAM-A23 profile actually consumed.

    `profile_version` is the Creation-Studio-owned capability-set version;
    `record_version` is the format version owned by this repository. Both are
    surfaced, neither is interpreted.
    """

    path: str
    record_version: str | None = None
    profile_version: str | None = None
    studio_reference: str | None = None

    def as_dict(self) -> dict:
        return _without_missing(
            {
                "path": self.path,
                "record_version": self.record_version,
                "profile_version": self.profile_version,
                "studio_reference": self.studio_reference,
            }
        )


class InputProvenance(NamedTuple):
    request: RequestProvenance
    profile: ProfileProvenance

    def as_dict(self) -> dict:
        return {"request": self.request.as_dict(), "profile": self.profile.as_dict()}


def _optional_str(doc: dict, key: str) -> str | None:
    """Read a metadata field, ignoring anything that is not a string.

    A25 does not re-validate A22/A23; a malformed metadata value is surfaced as
    absent rather than escalated, because it cannot affect the reconciliation.
    """
    value = doc.get(key)
    return value if isinstance(value, str) else None


def extract_request_provenance(doc: dict, path: Path) -> RequestProvenance:
    return RequestProvenance(
        path=_posix(path),
        record_version=_optional_str(doc, "record_version"),
        package_reference=_optional_str(doc, "package_reference"),
    )


def extract_profile_provenance(doc: dict, path: Path) -> ProfileProvenance:
    return ProfileProvenance(
        path=_posix(path),
        record_version=_optional_str(doc, "record_version"),
        profile_version=_optional_str(doc, "profile_version"),
        studio_reference=_optional_str(doc, "studio_reference"),
    )


def serialize_reconciliation(
    result: Reconciliation, provenance: InputProvenance | None = None
) -> dict:
    """Compose the ephemeral JSON payload: provenance first, then the result.

    Still not a repository contract, schema, or stored sidecar -- just a process
    output that now says which inputs produced it.
    """
    payload: dict = {}
    if provenance is not None:
        payload["inputs"] = provenance.as_dict()
    payload.update(result.as_dict())
    return payload


def format_input_traceability(provenance: InputProvenance) -> str:
    """Compact human provenance. Native separators are fine here; only the JSON
    surface must normalize. Absent metadata omits its line entirely."""
    lines = [f"Request: {provenance.request.path}"]
    if provenance.request.package_reference is not None:
        lines.append(f"Package: {provenance.request.package_reference}")
    if provenance.request.record_version is not None:
        lines.append(f"Request record version: {provenance.request.record_version}")

    lines.append("")
    lines.append(f"Profile: {provenance.profile.path}")
    if provenance.profile.studio_reference is not None:
        lines.append(f"Studio: {provenance.profile.studio_reference}")
    if provenance.profile.profile_version is not None:
        lines.append(f"Profile version: {provenance.profile.profile_version}")
    if provenance.profile.record_version is not None:
        lines.append(f"Profile record version: {provenance.profile.record_version}")

    return "\n".join(lines)


def reconcile(requested: list[str], declared: list[str]) -> Reconciliation:
    """Compare two capability vocabularies by exact identifier.

    Pure: no filesystem, no clock, no network. Duplicates within either input are
    collapsed -- both contracts already declare uniqueItems, and a duplicate must
    not inflate a count here.
    """
    requested_set = set(requested)
    declared_set = set(declared)

    satisfied = sorted(requested_set & declared_set)
    unsatisfied = sorted(requested_set - declared_set)
    declared_but_unrequested = sorted(declared_set - requested_set)

    findings: list[Finding] = []

    # Fires only when both vocabularies are non-empty and share nothing. That is a
    # materially different architectural state from "two capabilities are
    # missing", so it must not render as an ordinary unsatisfied count.
    #
    # An empty intersection is NOT sufficient on its own: with an empty request or
    # an empty profile the intersection is trivially empty and says nothing about
    # whether the vocabularies agree.
    if requested_set and declared_set and not satisfied:
        findings.append(
            Finding(
                code=NAMESPACE_DIVERGENCE,
                severity=SEVERITY_WARNING,
                message=NAMESPACE_DIVERGENCE_MESSAGE,
            )
        )

    return Reconciliation(
        satisfied=satisfied,
        unsatisfied=unsatisfied,
        declared_but_unrequested=declared_but_unrequested,
        findings=findings,
    )


def format_report(result: Reconciliation) -> str:
    """Human-readable report. Counts first, then findings, then the boundary."""
    lines = [
        f"Requested:                {result.requested_count}",
        f"Satisfied:                {len(result.satisfied)}",
        f"Unsatisfied:              {len(result.unsatisfied)}",
        f"Declared but unrequested: {len(result.declared_but_unrequested)}",
    ]

    for finding in result.findings:
        lines.append("")
        lines.append(f"[{finding.severity.upper()}] {finding.code}")
        lines.extend(textwrap.wrap(finding.message, width=REPORT_WIDTH))

    lines.append("")
    lines.append(ADVISORY_NOTICE)
    return "\n".join(lines)


# --- input resolution --------------------------------------------------------
#
# Scope distinction, load-bearing throughout this section:
#
#     request  = package-scoped        one per package under review
#     profile  = installation-scoped   one per Creation Studio installation
#     --package = resolution anchor only
#
# Deriving both from one anchor is PATH RESOLUTION. It does not imply package
# ownership of the profile, which remains authoritative at its own location.


class InputError(Exception):
    """An input is missing, unreadable, or not a readable record of its type."""


def conventional_base(package_dir: Path) -> Path:
    """Conventional root for Creation Studio artifacts beside a package.

    Mirrors the helper the CAM-A22 creator writes through, so the reconciler
    reads exactly where the request lands: for examples/packages/<name> the
    sibling roots live under examples/, otherwise beside the package directory.
    """
    parent = package_dir.parent
    if parent.name == "packages" and parent.parent.name == "examples":
        return parent.parent / CREATION_STUDIO_DIR
    return parent / CREATION_STUDIO_DIR


def resolve_request(package_dir: Path, override: Path | None) -> Path:
    """Explicit override, else conventional derivation."""
    if override is not None:
        return override
    return conventional_base(package_dir) / f"{package_dir.name}{REQUEST_SUFFIX}"


def profile_search_paths(package_dir: Path) -> list[Path]:
    """Candidate profile locations, nearest first.

    The conventional base first (in the shipped layout it already holds the
    profile), then package ancestors for the genuine installation-scoped case
    where the profile sits at a workspace root above the package.
    """
    candidates = [conventional_base(package_dir) / PROFILE_FILENAME]
    for ancestor in [package_dir, *package_dir.parents]:
        candidate = ancestor / CREATION_STUDIO_DIR / PROFILE_FILENAME
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def resolve_profile(package_dir: Path, override: Path | None) -> Path:
    """Explicit override, else the first EXISTING capability_profile.json.

    Existence of the profile FILE decides, never existence of a creation_studio/
    directory: a package's request sidecars live in a directory of that name, so
    stopping at the directory would resolve to a location holding no profile.
    """
    if override is not None:
        return override

    searched = profile_search_paths(package_dir)
    for candidate in searched:
        if candidate.is_file():
            return candidate

    listing = "\n".join(f"  {p}" for p in searched)
    raise InputError(
        f"No {PROFILE_FILENAME} found. Searched:\n{listing}\n"
        "Pass --profile to point at an installation-scoped profile explicitly."
    )


def load_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise InputError(f"{label} not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"{label} could not be read: {path} ({exc})") from exc
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(f"{label} is not valid JSON: {path} ({exc})") from exc
    if not isinstance(doc, dict):
        raise InputError(f"{label} must be a JSON object: {path}")
    return doc


def read_requested(path: Path) -> list[str]:
    """Extract requested_capabilities from a CAM-A22 request.

    Structural minimum only. This does not re-implement CAM-A22 validation; it
    requires just enough to read identifiers and otherwise defers to
    validate_creation_studio_request.py.
    """
    doc = load_json(path, "Request")
    values = doc.get("requested_capabilities")
    if not isinstance(values, list):
        raise InputError(f"Request has no 'requested_capabilities' array: {path}")
    if not all(isinstance(v, str) for v in values):
        raise InputError(f"Request 'requested_capabilities' must be strings: {path}")
    return values


def read_declared(path: Path) -> list[str]:
    """Extract capabilities[].capability_id from a CAM-A23 profile."""
    doc = load_json(path, "Capability profile")
    entries = doc.get("capabilities")
    if not isinstance(entries, list):
        raise InputError(f"Profile has no 'capabilities' array: {path}")
    declared: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise InputError(f"Profile capabilities[{index}] must be an object: {path}")
        capability_id = entry.get("capability_id")
        if not isinstance(capability_id, str):
            raise InputError(
                f"Profile capabilities[{index}] has no string 'capability_id': {path}"
            )
        declared.append(capability_id)
    return declared


# --- CLI ---------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile a CAM-A22 Creation Studio request against a CAM-A23 "
            "capability profile (read-only, advisory)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--package",
        type=Path,
        required=True,
        help=(
            "Package directory. Resolution anchor only: the request is "
            "package-scoped and the profile is installation-scoped; this derives "
            "both paths and implies no package ownership of the profile."
        ),
    )
    parser.add_argument(
        "--request",
        type=Path,
        default=None,
        help="Explicit CAM-A22 request path, overriding conventional derivation",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=None,
        help="Explicit CAM-A23 profile path, overriding conventional derivation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Emit the reconciliation as JSON on stdout and nothing else. An "
            "ephemeral serialization of the calculation, not a stored contract."
        ),
    )
    parser.add_argument(
        "--fail-on-unsatisfied",
        action="store_true",
        help=(
            "Exit 1 when 'unsatisfied' is non-empty. Exit-status policy only: it "
            "changes no classification, and namespace_divergence never "
            "independently changes the exit code."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        request_path = resolve_request(args.package, args.request)
        profile_path = resolve_profile(args.package, args.profile)
        requested = read_requested(request_path)
        declared = read_declared(profile_path)
    except InputError as exc:
        # stderr, always: a --json caller must never receive polluted stdout.
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    result = reconcile(requested, declared)

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        # Traceability: which inputs produced this result. Paths only -- versions
        # are surfaced, never interpreted.
        print(f"Request: {request_path}")
        print(f"Profile: {profile_path}")
        print()
        print(format_report(result))

    # Strict mode keys on unsatisfied ALONE. namespace_divergence is diagnostic
    # evidence, not a second gate.
    if args.fail_on_unsatisfied and result.unsatisfied:
        return EXIT_UNSATISFIED_STRICT
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
