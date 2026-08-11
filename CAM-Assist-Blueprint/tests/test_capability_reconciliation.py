"""
CAM-A25 reconciler core: exact set comparison and the namespace_divergence finding.

Filesystem-free. These tests exercise `reconcile()` directly, so a failure here
means the calculation is wrong and not that a path, CLI flag, or fixture moved.
CLI behaviour (derivation, overrides, exit codes) is covered separately.

Two authority invariants from docs/dev_orders/CAM-A25.md are asserted here rather
than left to prose, because they are the whole reason this capability is safe:

    An unsatisfied capability is a compatibility finding, not a prohibition.
    A satisfied capability is a declaration match, not authorization.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from reconcile_creation_studio_capabilities import (  # noqa: E402
    ADVISORY_NOTICE,
    NAMESPACE_DIVERGENCE,
    SEVERITY_WARNING,
    Reconciliation,
    format_report,
    reconcile,
)

# The two shipped vocabularies, read from the schemas rather than retyped, so a
# contract change surfaces here instead of quietly diverging from a copy.
SCHEMAS = Path(__file__).resolve().parent.parent / "schemas"


def shipped_requestable() -> list[str]:
    doc = json.loads((SCHEMAS / "creation_studio_request.schema.json").read_text(encoding="utf-8"))
    return doc["properties"]["requested_capabilities"]["items"]["enum"]


def shipped_declared() -> list[str]:
    example = (
        Path(__file__).resolve().parent.parent
        / "examples"
        / "creation_studio"
        / "capability_profile.json"
    )
    doc = json.loads(example.read_text(encoding="utf-8"))
    return [c["capability_id"] for c in doc["capabilities"]]


# --- the calculation ---------------------------------------------------------


def test_partition_is_exact():
    result = reconcile(["a", "b", "c"], ["b", "c", "d"])
    assert result.satisfied == ["b", "c"]
    assert result.unsatisfied == ["a"]
    assert result.declared_but_unrequested == ["d"]


def test_every_requested_capability_lands_in_exactly_one_set():
    requested = ["a", "b", "c", "d"]
    result = reconcile(requested, ["c", "d", "e"])
    # No requested identifier may be dropped or double-counted.
    assert sorted(result.satisfied + result.unsatisfied) == sorted(requested)
    assert not set(result.satisfied) & set(result.unsatisfied)


def test_every_declared_capability_lands_in_exactly_one_set():
    declared = ["c", "d", "e"]
    result = reconcile(["a", "b", "c", "d"], declared)
    assert sorted(result.satisfied + result.declared_but_unrequested) == sorted(declared)
    assert not set(result.satisfied) & set(result.declared_but_unrequested)


@pytest.mark.parametrize(
    "requested,declared",
    [
        (["b", "a", "c"], ["c", "b"]),
        (["c", "b", "a"], ["b", "c"]),
        (["a", "c", "b"], ["b", "c"]),
    ],
    ids=["order-1", "order-2", "order-3"],
)
def test_output_is_deterministic_regardless_of_input_order(requested, declared):
    # Determinism is a contract property: CI diffing two runs must not see churn
    # caused by the order identifiers happened to appear in a file.
    assert reconcile(requested, declared) == reconcile(sorted(requested), sorted(declared))


def test_sets_are_sorted():
    result = reconcile(["z", "m", "a"], ["z", "q", "b"])
    for group in (result.satisfied, result.unsatisfied, result.declared_but_unrequested):
        assert group == sorted(group)


def test_duplicates_are_collapsed_not_counted_twice():
    # Both schemas declare uniqueItems, but a duplicate must not inflate a count
    # if one ever reaches this layer.
    result = reconcile(["a", "a", "b"], ["b", "b"])
    assert result.satisfied == ["b"]
    assert result.unsatisfied == ["a"]
    assert result.requested_count == 2


def test_no_semantic_inference_between_near_miss_identifiers():
    # The exact trap A25 must not fall into: these are related concepts with
    # different identifiers. Matching them would require an alias table, which
    # this capability explicitly does not define.
    result = reconcile(["feeds_speeds_recommendation"], ["feeds_speeds_authoring"])
    assert result.satisfied == []
    assert result.unsatisfied == ["feeds_speeds_recommendation"]
    assert result.declared_but_unrequested == ["feeds_speeds_authoring"]


def test_matching_is_case_sensitive():
    # Identifiers are pattern-constrained to lowercase by CAM-A23; case-insensitive
    # matching would be a form of the inference A25 forbids.
    result = reconcile(["Simulation_Support"], ["simulation_support"])
    assert result.satisfied == []


# --- namespace_divergence ----------------------------------------------------


def test_namespace_divergence_fires_when_both_populated_and_disjoint():
    result = reconcile(["a", "b"], ["c", "d"])
    assert result.has_finding(NAMESPACE_DIVERGENCE)
    finding = result.findings[0]
    assert finding.severity == SEVERITY_WARNING
    assert "share no identifiers" in finding.message


@pytest.mark.parametrize(
    "requested,declared,why",
    [
        (["a"], ["a"], "full overlap"),
        (["a", "b"], ["b", "c"], "partial overlap"),
        ([], ["a", "b"], "empty request - intersection trivially empty"),
        (["a", "b"], [], "empty profile - intersection trivially empty"),
        ([], [], "both empty"),
    ],
    ids=["full-overlap", "partial-overlap", "empty-request", "empty-profile", "both-empty"],
)
def test_namespace_divergence_does_not_fire_otherwise(requested, declared, why):
    # An empty intersection is NOT sufficient. With either side empty the
    # intersection is trivially empty and says nothing about whether the
    # vocabularies agree, so reporting divergence would be a false diagnosis.
    result = reconcile(requested, declared)
    assert not result.has_finding(NAMESPACE_DIVERGENCE), why


def test_divergence_is_the_only_finding_code_emitted():
    # findings is a list so later diagnoses can be added; today exactly one code
    # exists, and an unexpected second would mean something invented a diagnosis.
    for requested, declared in [(["a"], ["b"]), (["a"], ["a"]), ([], []), (["a"], [])]:
        for finding in reconcile(requested, declared).findings:
            assert finding.code == NAMESPACE_DIVERGENCE


# --- authority invariants ----------------------------------------------------


def test_unsatisfied_is_a_finding_not_a_prohibition():
    """Invariant: an unsatisfied capability must not read as a denial.

    The result carries no field expressing permission, blocking, approval or
    prohibition -- there is nothing a caller could mistake for a decision.
    """
    result = reconcile(["a", "b"], [])
    assert result.unsatisfied == ["a", "b"]

    forbidden = {
        "approved", "authorized", "permitted", "allowed", "blocked", "denied",
        "prohibited", "rejected", "execute", "execution", "machine_ready",
    }
    assert not forbidden & set(result.as_dict())
    assert not forbidden & set(Reconciliation._fields)


def test_satisfied_is_a_declaration_match_not_authorization():
    """Invariant: a full match must not read as approval.

    Total success and total failure differ only in which sets are populated;
    neither produces an authority claim, and the advisory notice is present
    either way.
    """
    matched = reconcile(["a"], ["a"])
    assert matched.satisfied == ["a"]
    assert matched.findings == []

    assert set(matched.as_dict()) == set(reconcile(["a"], ["b"]).as_dict())
    assert ADVISORY_NOTICE in format_report(matched)


def test_report_always_states_the_evidence_boundary():
    for requested, declared in [(["a"], ["a"]), (["a"], ["b"]), ([], []), (["a"], [])]:
        report = format_report(reconcile(requested, declared))
        assert "ADVISORY ONLY" in report
        assert "do not imply execution authority" in report


# --- serialization -----------------------------------------------------------


def test_json_shape_is_stable_and_complete():
    payload = reconcile(["a", "b"], ["b", "c"]).as_dict()
    assert set(payload) == {
        "satisfied",
        "unsatisfied",
        "declared_but_unrequested",
        "findings",
    }
    assert payload["satisfied"] == ["b"]
    assert json.loads(json.dumps(payload)) == payload  # round-trips


def test_findings_serialize_as_code_severity_message():
    payload = reconcile(["a"], ["b"]).as_dict()
    assert payload["findings"] == [
        {
            "code": NAMESPACE_DIVERGENCE,
            "severity": SEVERITY_WARNING,
            "message": (
                "The request and capability-profile vocabularies are both "
                "non-empty but share no identifiers."
            ),
        }
    ]


def test_report_renders_the_divergence_finding_as_specified():
    # Pins the exact console rendering from docs/dev_orders/CAM-A25.md, including
    # the wrap. The canonical message stays one string in JSON; only the human
    # report wraps it.
    report = format_report(reconcile(["a"], ["b"]))
    assert "[WARNING] namespace_divergence" in report
    assert "The request and capability-profile vocabularies are both non-empty" in report
    assert "but share no identifiers." in report


def test_report_counts_match_the_sets():
    result = reconcile(["a", "b", "c"], ["c", "d"])
    report = format_report(result)
    assert "Requested:                3" in report
    assert "Satisfied:                1" in report
    assert "Unsatisfied:              2" in report
    assert "Declared but unrequested: 1" in report


# --- the shipped contracts ---------------------------------------------------


def test_shipped_vocabularies_are_disjoint_and_diagnosed():
    """Pins the finding that motivated namespace_divergence.

    A22's enum is closed and CAM-Assist-owned; A23's vocabulary is open and
    Creation-Studio-owned. As shipped they share nothing, so the reconciler's
    honest answer today is "nothing matches, and here is why".

    If this ever fails, the vocabularies have converged -- which is good news, and
    means the forward-looking note in CAM-A25.md deserves revisiting rather than
    this test being deleted.
    """
    requested, declared = shipped_requestable(), shipped_declared()
    assert requested and declared

    result = reconcile(requested, declared)
    assert result.satisfied == []
    assert result.unsatisfied == sorted(requested)
    assert result.declared_but_unrequested == sorted(declared)
    assert result.has_finding(NAMESPACE_DIVERGENCE)
