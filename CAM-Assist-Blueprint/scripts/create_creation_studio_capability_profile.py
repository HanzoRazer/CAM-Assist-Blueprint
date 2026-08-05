#!/usr/bin/env python3
"""
Creation Studio Capability Profile Creator

Creates a read-only, informational capability profile declaring what the separate
CAM-Creation-Studio product is capable of AUTHORING. The profile is published
BY Creation Studio and consumed by CAM Assist for informational display, request
compatibility checking, and documentation only.

A profile is NOT package-specific: there is one per Creation Studio
installation/version, discovered at creation_studio/capability_profile.json.

The profile is descriptive and advisory: it does not authorize execution, does
not request execution, does not bypass human review, does not confirm machine
readiness, does not validate machining, does not approve strategies, and never
requires CAM Assist to use a declared capability. No capability implies approval.
It never mutates a strategy package or any other repository artifact.

The profile carries NO created_at timestamp: the artifact is deterministic so
that regenerating it (delete -> recreate) yields byte-identical output.
Auditability of when a profile was published belongs to the surrounding workflow
(git, filesystem), not the artifact body.

Determinism rules:
    - capabilities are sorted by capability_id (input order is NOT significant)
    - duplicate capabilities collapse to one entry
    - only supplied, informative fields are emitted

Capability names:
    --capability accepts either a stable identifier (recorded as-is) or a
    human-readable name, which is normalized mechanically: lowercased, with each
    run of non-alphanumeric characters folded to a single underscore
    ("Feeds & Speeds Authoring" -> "feeds_speeds_authoring"). When the supplied
    name differs from its normalized identifier, the original is preserved as
    display_name -- it carried information the identifier does not. When the
    caller already supplied the identifier, no redundant display_name is emitted.
    Normalization is mechanical, not clever: a caller who needs an exact
    identifier should pass that identifier.

Usage:
    python scripts/create_creation_studio_capability_profile.py \
        --capability strategy_visualization --capability "Feeds & Speeds Authoring"
    python scripts/create_creation_studio_capability_profile.py --root examples \
        --capability simulation_support \
        --capability-doc simulation_support=docs/simulation.md --force

Exit codes:
    0 — Capability profile created successfully
    1 — Argument error (no/invalid capability, malformed version, blank
        studio reference, malformed --capability-doc, doc for an undeclared
        capability, absolute documentation reference, or output exists
        without --force)
    2 — File/write error (directory creation or write failed)
"""

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import NamedTuple


RECORD_TYPE = "creation_studio_capability_profile"
RECORD_VERSION = "1.0.0"
PUBLICATION_DIRECTION = "creation_studio_to_cam_assist"

DEFAULT_PROFILE_VERSION = "1.0.0"
DEFAULT_STUDIO_REFERENCE = "cam-creation-studio"

# Conventional discovery location. A profile is per-installation, not
# per-package, so the filename is fixed rather than package-derived.
PROFILE_DIR = "creation_studio"
PROFILE_FILENAME = "capability_profile.json"

VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
CAPABILITY_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

AUTHORITY = {
    "is_informational": True,
    "does_not_authorize_execution": True,
    "does_not_bypass_human_review": True,
    "does_not_confirm_machine_readiness": True,
    "does_not_require_capability_use": True,
}


class CreateResult(NamedTuple):
    success: bool
    output_path: Path | None
    error: str | None
    exit_code: int = 0


class CapabilityError(Exception):
    """Raised when a supplied capability name or documentation reference is unusable."""


def normalize_capability_names(names: list[str]) -> list[tuple[str, str]]:
    """Normalize supplied capability names to (identifier, original) pairs.

    Mechanical normalization: lowercase, then fold each run of non-alphanumeric
    characters to a single underscore and trim leading/trailing underscores.
    Order is preserved here; sorting happens in discover_capabilities().

    Raises CapabilityError when a name is blank or cannot normalize to a valid
    stable identifier — a silently mangled identifier would be worse than a
    refusal, since published identifiers are meant never to change.
    """
    pairs: list[tuple[str, str]] = []
    for name in names:
        original = name.strip()
        if not original:
            raise CapabilityError("--capability must not be blank")
        identifier = re.sub(r"[^a-z0-9]+", "_", original.lower()).strip("_")
        if not CAPABILITY_ID_PATTERN.fullmatch(identifier):
            raise CapabilityError(
                f"cannot derive a valid capability identifier from '{original}' "
                "(identifiers must match ^[a-z][a-z0-9_]*$)"
            )
        pairs.append((identifier, original))
    return pairs


def is_absolute_reference(value: str) -> bool:
    """True if a documentation reference is an absolute (non-portable) path.

    References resolve relative to the profile file's own location; an absolute
    path escapes that base entirely, so it is rejected rather than recorded.
    """
    v = value.strip()
    if PurePosixPath(v).is_absolute() or PureWindowsPath(v).is_absolute():
        return True
    if v.startswith(("/", "\\")):
        return True
    if len(v) >= 2 and v[1] == ":" and v[0].isalpha():
        return True
    return False


def parse_capability_docs(entries: list[str]) -> dict[str, str]:
    """Parse --capability-doc NAME=PATH entries into {identifier: reference}.

    NAME is normalized exactly like --capability, so a documentation flag may use
    either the identifier or the same human-readable name. The path is recorded
    as-is (existence is the validator's opt-in --check-references concern) but
    must be relative, for the same portability reason the schema enforces.
    """
    docs: dict[str, str] = {}
    for entry in entries:
        name, separator, reference = entry.partition("=")
        if not separator:
            raise CapabilityError(
                f"--capability-doc must be NAME=PATH: '{entry}'"
            )
        reference = reference.strip()
        if not reference:
            raise CapabilityError(f"--capability-doc path must not be blank: '{entry}'")
        if is_absolute_reference(reference):
            raise CapabilityError(
                f"--capability-doc path must be relative "
                f"(absolute paths are not portable): '{reference}'"
            )
        identifier, _original = normalize_capability_names([name])[0]
        if identifier in docs and docs[identifier] != reference:
            raise CapabilityError(
                f"--capability-doc given twice for '{identifier}' with different paths"
            )
        docs[identifier] = reference
    return docs


def discover_capabilities(names: list[str], docs: dict[str, str]) -> list[dict]:
    """Build the deterministic, sorted capability list.

    Capabilities are sorted by capability_id and de-duplicated, so the emitted
    profile depends on the SET of declared capabilities rather than the order they
    were supplied. display_name is emitted only when the supplied name carried
    information the identifier does not; documentation_reference only when one was
    attached. Discovery records DECLARED support only — it never asks whether a
    capability is supported, appropriate, or approved.
    """
    pairs = normalize_capability_names(names)

    unknown = sorted(set(docs) - {identifier for identifier, _ in pairs})
    if unknown:
        raise CapabilityError(
            "--capability-doc references undeclared capabilities: "
            + ", ".join(unknown)
        )

    by_id: dict[str, dict] = {}
    for identifier, original in pairs:
        entry: dict = {"capability_id": identifier}
        if original != identifier:
            entry["display_name"] = original
        if identifier in docs:
            entry["documentation_reference"] = docs[identifier]
        # A repeated capability keeps its first-supplied form; the entries are
        # identical in every field that matters unless the caller supplied two
        # different display forms, in which case first-wins is deterministic.
        by_id.setdefault(identifier, entry)

    return [by_id[identifier] for identifier in sorted(by_id)]


def resolve_profile_path(root: Path) -> Path:
    """Conventional profile location: <root>/creation_studio/capability_profile.json.

    A profile is per Creation Studio installation/version, not per package, so the
    filename is fixed. The same convention is what the inspector detects.
    """
    return root / PROFILE_DIR / PROFILE_FILENAME


def create_profile(
    capabilities: list[str],
    root: Path | None = None,
    output_path: Path | None = None,
    profile_version: str = DEFAULT_PROFILE_VERSION,
    studio_reference: str = DEFAULT_STUDIO_REFERENCE,
    capability_docs: list[str] | None = None,
    force: bool = False,
) -> CreateResult:
    if not capabilities:
        return CreateResult(
            False, None,
            "At least one --capability is required", 1,
        )

    if not VERSION_PATTERN.fullmatch(profile_version):
        return CreateResult(
            False, None,
            f"Invalid --profile-version: '{profile_version}'. "
            "Must be semantic version (e.g., '1.0.0')", 1,
        )

    if not studio_reference.strip():
        return CreateResult(False, None, "--studio-reference must not be blank", 1)

    try:
        docs = parse_capability_docs(capability_docs or [])
        entries = discover_capabilities(capabilities, docs)
    except CapabilityError as e:
        return CreateResult(False, None, str(e), 1)

    if output_path is None:
        output_path = resolve_profile_path(root if root is not None else Path("."))

    if output_path.exists() and not force:
        return CreateResult(
            False, None,
            f"Output file already exists: {output_path} (use --force to overwrite)", 1,
        )

    record = {
        "record_type": RECORD_TYPE,
        "record_version": RECORD_VERSION,
        "profile_version": profile_version,
        "studio_reference": studio_reference,
        "publication_direction": PUBLICATION_DIRECTION,
        "capabilities": entries,
        "authority": dict(AUTHORITY),
    }

    # Directory creation and the write share the file/write-error class (exit 2).
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
            f.write("\n")
    except OSError as e:
        return CreateResult(False, None, f"Failed to write capability profile: {e}", 2)

    return CreateResult(True, output_path, None, 0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create Creation Studio capability profile (read-only capability contract)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--capability", action="append", default=[], dest="capabilities", metavar="NAME",
        help=(
            "Declared authoring capability (repeatable). Accepts a stable identifier "
            "or a human-readable name, which is normalized to an identifier"
        ),
    )
    parser.add_argument(
        "--capability-doc", action="append", default=[], dest="capability_docs",
        metavar="NAME=PATH",
        help=(
            "Attach a relative documentation reference to a declared capability "
            "(repeatable). Existence is not checked here"
        ),
    )
    parser.add_argument(
        "--root", type=Path, default=None,
        help=f"Root under which to write {PROFILE_DIR}/{PROFILE_FILENAME} (default: .)",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help=f"Explicit output path (default: <root>/{PROFILE_DIR}/{PROFILE_FILENAME})",
    )
    parser.add_argument(
        "--profile-version", type=str, default=DEFAULT_PROFILE_VERSION, dest="profile_version",
        help=(
            "Semantic version of the published capability set, owned by Creation "
            f"Studio and independent of the CAM Assist version (default: {DEFAULT_PROFILE_VERSION})"
        ),
    )
    parser.add_argument(
        "--studio-reference", type=str, default=DEFAULT_STUDIO_REFERENCE, dest="studio_reference",
        help=(
            "Identifier of the Creation Studio installation/version this profile "
            f"describes (default: {DEFAULT_STUDIO_REFERENCE})"
        ),
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing profile file")
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only output the path on success"
    )

    args = parser.parse_args()

    result = create_profile(
        capabilities=args.capabilities,
        root=args.root,
        output_path=args.out,
        profile_version=args.profile_version,
        studio_reference=args.studio_reference,
        capability_docs=args.capability_docs,
        force=args.force,
    )

    if result.success:
        if args.quiet:
            print(str(result.output_path))
        else:
            print(f"Creation studio capability profile created: {result.output_path}")
            print()
            print("Note: A capability profile is a read-only, informational declaration of")
            print("what CAM-Creation-Studio can author. It does not authorize execution,")
            print("bypass human review, confirm machine readiness, approve any strategy, or")
            print("require CAM Assist to use a declared capability.")
        return 0
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
