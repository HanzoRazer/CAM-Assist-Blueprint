"""
Cross-schema guard: every created_at field rejects empty and whitespace-only.

CAM-A19/A20 closed the created_at schema<->hand-validator drift for the two
execution-adjacent records (production_shop_handoff, traceability_bundle) by
adding `minLength: 1` + `pattern: "\\S"`. This pass extends that invariant to
every OTHER schema that carries a created_at timestamp, so an empty or blank
timestamp is rejected project-wide — not just where a hand validator happened
to also check it.

Scope note: the two execution-adjacent records are intentionally NOT enforced
here. They carry the same constraint, but it is owned (and tested in detail) by
their dedicated suites — test_production_shop_handoff_schema.py and
test_traceability_bundle_schema.py. They are listed in DELEGATED below only so
the discovery guard can confirm no created_at field escapes coverage entirely.

Two layers (per the CAM-A19 Phase 1 pattern):

B (always run, dependency-free): assert each schema DOCUMENT encodes the
    constraint (minLength >= 1 AND pattern "\\S" on the created_at subschema).

C (optional, skipped unless `jsonschema` importable): APPLY the created_at
    subschema and witness behavior on the boundary values.

Validating the created_at *subschema* in isolation (rather than a full record
instance) keeps this guard fixture-free: it locks the field's constraint
without needing a minimal valid instance for each schema.
"""

import json
from pathlib import Path

import pytest


SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"

# (schema filename, JSON path to the created_at subschema) for every schema this
# consistency pass hardens. One entry per created_at field. If a schema gains a
# created_at, add it here (or to DELEGATED) — an unlisted field fails the
# discovery guard below rather than silently escaping the checks.
CREATED_AT_FIELDS = [
    ("manufacturing_assumptions.schema.json", ("properties", "created_at")),
    ("manufacturing_decision_record.schema.json", ("properties", "created_at")),
    ("review_annotations.schema.json", ("properties", "created_at")),
    ("revision_lineage.schema.json", ("properties", "created_at")),
    ("risk_assessment.schema.json", ("properties", "created_at")),
    ("strategy_package_manifest.schema.json", ("properties", "created_at")),
    ("strategy.schema.json", ("properties", "provenance", "properties", "created_at")),
]

# created_at fields whose constraint lives in a dedicated suite, not here.
DELEGATED = {
    ("production_shop_handoff.schema.json", ("properties", "created_at")),
    ("traceability_bundle.schema.json", ("properties", "created_at")),
}

# IDs for readable parametrize output: "<schema-stem>"
_IDS = [f.split(".", 1)[0] for f, _ in CREATED_AT_FIELDS]

# A committed, currently-valid example instance per hardened schema, plus the
# path to its created_at value. Used by the full-document integration tests to
# prove the constraint bites through the real property path (not just on the
# subschema in isolation), which would catch a field-path or composition
# (allOf/$ref) change that isolated subschema validation could miss.
EXAMPLE_INSTANCES = [
    ("manufacturing_assumptions.schema.json",
     "examples/traceability/ltb_vcarve_synthetic_example_assumptions.json", ("created_at",)),
    ("manufacturing_decision_record.schema.json",
     "examples/traceability/ltb_vcarve_synthetic_example_decision_record.json", ("created_at",)),
    ("review_annotations.schema.json",
     "examples/review_annotations/ltb_vcarve_synthetic_example_annotations.json", ("created_at",)),
    ("revision_lineage.schema.json",
     "examples/traceability/ltb_vcarve_synthetic_example_lineage.json", ("created_at",)),
    ("risk_assessment.schema.json",
     "examples/traceability/ltb_vcarve_synthetic_example_risk.json", ("created_at",)),
    ("strategy_package_manifest.schema.json",
     "examples/valid/fret_slot_strategy_manifest.json", ("created_at",)),
    ("strategy.schema.json",
     "examples/valid/fret_slot_strategy.json", ("provenance", "created_at")),
]
_EX_IDS = [f.split(".", 1)[0] for f, _, _ in EXAMPLE_INSTANCES]

# Blank values every created_at must reject. Includes Unicode whitespace
# (NBSP, EM SPACE) to confirm pattern "\\S" agrees with the hand validators'
# str.strip(), which also treats these as whitespace.
BLANK_VALUES = ["", "   ", "\t", "\xa0", " "]

# A non-blank but non-ISO-8601 value. Passes today: the schema constrains
# non-blankness, not timestamp shape (see test_malformed_created_at_passes).
MALFORMED_VALUE = "not-a-date"

_EXAMPLES_DIR = Path(__file__).parent.parent


def _subschema(filename: str, path: tuple) -> dict:
    with open(SCHEMAS_DIR / filename, "r", encoding="utf-8") as f:
        node = json.load(f)
    for key in path:
        node = node[key]
    return node


def test_every_created_at_field_is_accounted_for():
    # Discovery guard: a created_at added to any schema must be enforced here or
    # explicitly delegated — otherwise it fails loudly rather than escaping the
    # empty/whitespace checks.
    found = set()
    for schema_path in SCHEMAS_DIR.glob("*.schema.json"):
        with open(schema_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        def walk(node, path=()):
            if isinstance(node, dict):
                for k, v in node.items():
                    if (
                        k == "created_at"
                        and isinstance(v, dict)
                        and v.get("type") == "string"
                    ):
                        found.add((schema_path.name, path + (k,)))
                    walk(v, path + (k,))

        walk(doc)

    accounted = {(f, p) for f, p in CREATED_AT_FIELDS} | DELEGATED
    assert found == accounted, (
        "created_at fields drifted from the accounted-for set.\n"
        f"  unaccounted (add to CREATED_AT_FIELDS or DELEGATED): {found - accounted}\n"
        f"  stale (remove): {accounted - found}"
    )


# ---------------------------------------------------------------------------
# B — dependency-free contract assertions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename,path", CREATED_AT_FIELDS, ids=_IDS)
def test_created_at_document_rejects_blank(filename, path):
    sub = _subschema(filename, path)
    assert sub.get("type") == "string"
    # minLength >= 1 rejects ""; pattern "\\S" rejects whitespace-only. Together
    # they mirror the hand validators' `not value.strip()` check.
    assert sub.get("minLength", 0) >= 1, f"{filename}: created_at needs minLength >= 1"
    assert sub.get("pattern") == "\\S", f"{filename}: created_at needs pattern \\\\S"


# ---------------------------------------------------------------------------
# C — applied subschema validation (optional)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename,path", CREATED_AT_FIELDS, ids=_IDS)
@pytest.mark.parametrize("blank", BLANK_VALUES, ids=lambda v: repr(v))
def test_applied_created_at_rejects_blank(filename, path, blank):
    jsonschema = pytest.importorskip("jsonschema")
    sub = _subschema(filename, path)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(sub).validate(blank)


@pytest.mark.parametrize("filename,path", CREATED_AT_FIELDS, ids=_IDS)
def test_applied_created_at_allows_valid_timestamp(filename, path):
    jsonschema = pytest.importorskip("jsonschema")
    sub = _subschema(filename, path)
    jsonschema.Draft202012Validator(sub).validate("2026-07-10T00:00:00Z")


@pytest.mark.parametrize("filename,path", CREATED_AT_FIELDS, ids=_IDS)
def test_malformed_created_at_passes(filename, path):
    # Deliberately-unenforced boundary, locked so the limitation stays visible
    # and intentional: `format: date-time` is an annotation, not an assertion,
    # under a plain Draft202012Validator (no FormatChecker registered), so a
    # non-blank but non-ISO-8601 string passes. The schema's real contract is
    # "non-blank string", NOT "well-formed timestamp". If the project ever wants
    # the shape enforced, wire a FormatChecker into the validation path AND the
    # hand validators together — changing only this test would resurface drift.
    jsonschema = pytest.importorskip("jsonschema")
    sub = _subschema(filename, path)
    jsonschema.Draft202012Validator(sub).validate(MALFORMED_VALUE)


# ---------------------------------------------------------------------------
# Full-document integration — the constraint bites through the real path
# ---------------------------------------------------------------------------

def _load_example(rel_path: str) -> dict:
    with open(_EXAMPLES_DIR / rel_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _set_at(doc: dict, path: tuple, value) -> None:
    node = doc
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value


@pytest.mark.parametrize("filename,example,path", EXAMPLE_INSTANCES, ids=_EX_IDS)
def test_example_instance_is_valid_baseline(filename, example, path):
    # Sanity: the committed example validates as-is. If this breaks, the
    # blank-rejection assertion below would be meaningless (it must fail for the
    # created_at reason, not because the fixture drifted).
    jsonschema = pytest.importorskip("jsonschema")
    schema = _subschema(filename, ())  # whole schema document
    jsonschema.Draft202012Validator(schema).validate(_load_example(example))


@pytest.mark.parametrize("filename,example,path", EXAMPLE_INSTANCES, ids=_EX_IDS)
@pytest.mark.parametrize("blank", ["", "   "], ids=lambda v: repr(v))
def test_full_document_rejects_blank_created_at(filename, example, path, blank):
    # End-to-end: mutate created_at to blank on a real, otherwise-valid record
    # and confirm FULL-document validation fails — proving the constraint is
    # reached via the actual property path, not only when the subschema is
    # validated in isolation.
    jsonschema = pytest.importorskip("jsonschema")
    schema = _subschema(filename, ())
    doc = _load_example(example)
    _set_at(doc, path, blank)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(doc)
