"""
Cross-schema guard: every date-time field documents what is actually enforced.

`test_created_at_schema_consistency.py` guards the *keywords* on fields literally
named `created_at`. Two gaps remained, and this module closes both:

1. Its discovery guard keys on the literal key name `created_at`, so a date-time
   field with any other name (`timestamp`, `reviewed_at`) falls outside coverage
   by construction — not by decision. This module discovers by
   `format: date-time` instead, so no date-time field can escape classification.

2. Nothing pinned the *description* text. The wording drifted before: two schemas
   kept validator-internals commentary ("matching the hand validator's .strip()
   check ... no FormatChecker") long after the other seven had moved to a
   contract-style description. Wording that documents a specific harness goes
   stale the moment the harness changes.

The wording these tests pin is deliberately **validator-agnostic**. These schemas
are published contracts; consumers outside this repository may run a validator
with format assertion enabled, in which case `format: date-time` *is* enforced.
A description asserting that the shape is never checked would be wrong for those
consumers. It therefore states what this schema requires (non-blankness) and
defers the shape question to the consuming validator's configuration.

Every date-time field must be in exactly one of two buckets:

    HARDENED   minLength >= 1 AND pattern "\\S" — blank values rejected
    KNOWN_GAP  neither guard present — blank values accepted

`KNOWN_GAP` is an explicit allowlist, not a silent tolerance. Each entry
discloses the gap in its own `description`, so a consumer reading the schema
learns the limitation from the artifact rather than from a dev order. Fixing a
gap means moving it to HARDENED here and adding the guards — the test fails
until both happen, in either direction.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

# Date-time fields WITHOUT blank-rejection guards. Every entry is a real defect
# awaiting its own change; see docs/dev_orders/LEDGER.md. Shrinking this list is
# the goal. Growing it requires a deliberate edit here, which is the point.
KNOWN_GAP = {
    ("review_annotations.schema.json", "properties/annotations/items/properties/timestamp"),
    ("review_decision_record.schema.json", "properties/reviewed_at"),
    ("strategy.schema.json", "properties/approval/properties/timestamp"),
}

# Sentence every hardened field's description must carry verbatim. Pinning the
# exact string is what stops the wording drifting apart again.
HARDENED_CONTRACT = (
    "This schema enforces non-blankness only (minLength + pattern reject empty "
    "and whitespace-only); whether the format: date-time annotation is asserted "
    "depends on the consuming validator's configuration, so the ISO-8601 shape "
    "may go unchecked."
)

# Sentence every known-gap field's description must carry verbatim.
GAP_DISCLOSURE = (
    "Known gap: no minLength/pattern guard here, so empty and whitespace-only "
    "values are accepted, unlike the created_at fields in these schemas; whether "
    "the format: date-time annotation is asserted depends on the consuming "
    "validator's configuration."
)

# Wording that documents the validation harness rather than the contract. It
# went stale once already; it must not come back.
FORBIDDEN_FRAGMENTS = ("FormatChecker", ".strip()", "hand validator")


def _discover() -> list[tuple[str, str, dict]]:
    """Every subschema with format: date-time, as (filename, json path, node)."""
    found: list[tuple[str, str, dict]] = []
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))

        def walk(node: object, trail: list[str]) -> None:
            if isinstance(node, dict):
                if node.get("format") == "date-time":
                    found.append((path.name, "/".join(trail), node))
                for key, value in node.items():
                    walk(value, trail + [key])
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, trail + [str(index)])

        walk(doc, [])
    return found


DATETIME_FIELDS = _discover()


def _is_hardened(node: dict) -> bool:
    return node.get("minLength", 0) >= 1 and node.get("pattern") == "\\S"


def _ids() -> list[str]:
    return [f"{name}::{path}" for name, path, _ in DATETIME_FIELDS]


def test_discovery_found_the_schemas():
    # Guards against the walker silently returning nothing (wrong directory,
    # renamed glob) and every assertion below vacuously passing.
    assert len(DATETIME_FIELDS) >= 12, (
        f"expected at least 12 date-time fields, found {len(DATETIME_FIELDS)} — "
        "discovery is probably broken, not the schemas"
    )


@pytest.mark.parametrize("name,path,node", DATETIME_FIELDS, ids=_ids())
def test_every_datetime_field_is_classified(name, path, node):
    listed = (name, path) in KNOWN_GAP
    hardened = _is_hardened(node)
    assert hardened != listed, (
        f"{name} :: {path} is unclassified.\n"
        f"  minLength={node.get('minLength')!r} pattern={node.get('pattern')!r}\n"
        "  Either add minLength >= 1 and pattern \"\\\\S\", or add it to "
        "KNOWN_GAP with a description disclosing the gap."
    )


@pytest.mark.parametrize("name,path,node", DATETIME_FIELDS, ids=_ids())
def test_every_datetime_field_has_a_description(name, path, node):
    # strategy.schema.json's approval.timestamp shipped with no description at
    # all, which is how it stayed invisible.
    assert node.get("description", "").strip(), f"{name} :: {path} has no description"


@pytest.mark.parametrize("name,path,node", DATETIME_FIELDS, ids=_ids())
def test_description_states_the_enforced_contract(name, path, node):
    expected = GAP_DISCLOSURE if (name, path) in KNOWN_GAP else HARDENED_CONTRACT
    assert expected in node["description"], (
        f"{name} :: {path} description does not carry the required contract "
        f"sentence verbatim.\n  expected: {expected}\n  actual:   {node['description']}"
    )


@pytest.mark.parametrize("name,path,node", DATETIME_FIELDS, ids=_ids())
def test_description_does_not_document_the_harness(name, path, node):
    for fragment in FORBIDDEN_FRAGMENTS:
        assert fragment not in node["description"], (
            f"{name} :: {path} description mentions {fragment!r}. Descriptions "
            "state the schema's contract, not the validator that happens to "
            "check it — harness commentary goes stale when the harness changes."
        )


def test_known_gap_entries_all_exist():
    # A fixed gap must be removed from KNOWN_GAP, and a renamed field must not
    # leave a stale entry behind silently excusing something else.
    discovered = {(name, path) for name, path, _ in DATETIME_FIELDS}
    stale = KNOWN_GAP - discovered
    assert not stale, (
        f"KNOWN_GAP lists fields that no longer exist: {sorted(stale)}. "
        "Remove them — a stale entry cannot be distinguished from a real one."
    )


def test_created_at_fields_are_all_hardened():
    # The A19/A20 rule, restated on the discovery-by-format axis: whatever else
    # is unhardened, nothing named created_at may be.
    unhardened = [
        f"{name} :: {path}"
        for name, path, node in DATETIME_FIELDS
        if path.endswith("created_at") and not _is_hardened(node)
    ]
    assert not unhardened, f"created_at fields missing blank guards: {unhardened}"
