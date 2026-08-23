"""
CAM-A26 mapped reconciliation core.

Filesystem-free. These tests exercise `reconcile_mapped()` and leave
`reconcile()` as the exact-mode contract covered by test_capability_reconciliation.py.

Pinned here:

- exact matching remains the default calculation and is unchanged
- mapped satisfaction requires an explicit map entry
- exact wins over mapped when identifiers already overlap
- any_of: one declared mapped target is enough
- all declared mapped targets are reported, sorted
- unmapped requests stay unsatisfied; no inference
- raw namespace_divergence survives mapped compatibility
- mapping-array order does not change the result
- neither exact nor mapped satisfaction introduces authority fields
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
SCHEMAS = Path(__file__).resolve().parent.parent / "schemas"
EXAMPLE_PROFILE = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "creation_studio"
    / "capability_profile.json"
)
CANONICAL_MAP = (
    Path(__file__).resolve().parent.parent
    / "contracts"
    / "creation_studio_capability_map.json"
)

sys.path.insert(0, str(SCRIPTS))

from reconcile_creation_studio_capabilities import (  # noqa: E402
    ADVISORY_NOTICE,
    MAPPED_ADVISORY_NOTICE,
    MAPPED_COMPATIBILITY,
    METHOD_EXACT,
    METHOD_MAPPED,
    NAMESPACE_DIVERGENCE,
    Reconciliation,
    format_report,
    reconcile,
    reconcile_mapped,
)
from validate_creation_studio_capability_map import (  # noqa: E402
    build_mapping_index,
    load_capability_map,
)


def shipped_requestable() -> list[str]:
    doc = json.loads((SCHEMAS / "creation_studio_request.schema.json").read_text(encoding="utf-8"))
    return doc["properties"]["requested_capabilities"]["items"]["enum"]


def shipped_declared() -> list[str]:
    doc = json.loads(EXAMPLE_PROFILE.read_text(encoding="utf-8"))
    return [entry["capability_id"] for entry in doc["capabilities"]]


# --- exact mode is untouched -------------------------------------------------


def test_reconcile_signature_remains_two_arguments():
    assert list(inspect.signature(reconcile).parameters) == ["requested", "declared"]


def test_exact_near_miss_is_still_unsatisfied_without_a_map():
    result = reconcile(["feeds_speeds_recommendation"], ["feeds_speeds_authoring"])
    assert result.satisfied == []
    assert result.unsatisfied == ["feeds_speeds_recommendation"]
    assert result.satisfaction_details is None


# --- simple mapped match -----------------------------------------------------


def test_simple_mapped_match():
    result = reconcile_mapped(
        ["simulation_request"],
        ["simulation_support"],
        {"simulation_request": ["simulation_support"]},
    )
    assert result.satisfied == ["simulation_request"]
    assert result.unsatisfied == []
    assert len(result.satisfaction_details) == 1
    detail = result.satisfaction_details[0]
    assert detail.request_capability == "simulation_request"
    assert detail.method == METHOD_MAPPED
    assert detail.matched_capability == "simulation_support"


# --- exact wins --------------------------------------------------------------


def test_exact_match_wins_over_a_mapping():
    result = reconcile_mapped(
        ["simulation_support"],
        ["simulation_support"],
        {"simulation_support": ["something_else"]},
    )
    assert result.satisfied == ["simulation_support"]
    assert result.satisfaction_details[0].method == METHOD_EXACT
    assert result.satisfaction_details[0].matched_capability == "simulation_support"
    assert not result.has_finding(MAPPED_COMPATIBILITY)


# --- any_of and multiple declared targets ------------------------------------


def test_one_of_several_mapped_targets_is_enough():
    result = reconcile_mapped(
        ["gcode_explanation"],
        ["capability_b"],
        {"gcode_explanation": ["capability_a", "capability_b"]},
    )
    assert result.satisfied == ["gcode_explanation"]
    assert [d.matched_capability for d in result.satisfaction_details] == ["capability_b"]


def test_all_declared_mapped_targets_are_reported_sorted():
    result = reconcile_mapped(
        ["gcode_explanation"],
        ["post_processor_education", "gcode_tutorial_generation"],
        {"gcode_explanation": ["post_processor_education", "gcode_tutorial_generation"]},
    )
    assert result.satisfied == ["gcode_explanation"]
    assert [d.matched_capability for d in result.satisfaction_details] == [
        "gcode_tutorial_generation",
        "post_processor_education",
    ]


def test_mapping_index_order_does_not_change_the_result():
    requested = ["gcode_explanation"]
    declared = ["post_processor_education", "gcode_tutorial_generation"]
    a = reconcile_mapped(
        requested,
        declared,
        {"gcode_explanation": ["post_processor_education", "gcode_tutorial_generation"]},
    )
    b = reconcile_mapped(
        requested,
        declared,
        {"gcode_explanation": ["gcode_tutorial_generation", "post_processor_education"]},
    )
    assert a == b
    assert a.as_dict() == b.as_dict()


# --- unsatisfied / unmapped --------------------------------------------------


def test_mapping_without_a_declared_target_stays_unsatisfied():
    result = reconcile_mapped(
        ["simulation_request"],
        ["unrelated_capability"],
        {"simulation_request": ["simulation_support"]},
    )
    assert result.satisfied == []
    assert result.unsatisfied == ["simulation_request"]
    assert result.satisfaction_details == []


def test_unmapped_request_is_not_inferred():
    result = reconcile_mapped(
        ["workholding_review"],
        ["tool_library_editing", "strategy_visualization"],
        {"simulation_request": ["simulation_support"]},
    )
    assert result.satisfied == []
    assert result.unsatisfied == ["workholding_review"]


# --- raw divergence coexists with mapped compatibility -----------------------


def test_raw_namespace_divergence_survives_mapped_satisfaction():
    result = reconcile_mapped(
        ["simulation_request"],
        ["simulation_support"],
        {"simulation_request": ["simulation_support"]},
    )
    assert result.has_finding(NAMESPACE_DIVERGENCE)
    assert result.has_finding(MAPPED_COMPATIBILITY)
    assert result.declared_but_unrequested == ["simulation_support"]


def test_shipped_vocabularies_without_a_map_still_diverge():
    result = reconcile(shipped_requestable(), shipped_declared())
    assert result.satisfied == []
    assert result.has_finding(NAMESPACE_DIVERGENCE)
    assert not result.has_finding(MAPPED_COMPATIBILITY)


def test_shipped_vocabularies_plus_canonical_map_show_both_facts():
    _doc, index, _identity = load_capability_map(CANONICAL_MAP)
    result = reconcile_mapped(shipped_requestable(), shipped_declared(), index)
    assert result.has_finding(NAMESPACE_DIVERGENCE)
    assert result.has_finding(MAPPED_COMPATIBILITY)
    assert set(result.satisfied) == {
        "feeds_speeds_recommendation",
        "gcode_explanation",
        "simulation_request",
    }
    assert set(result.unsatisfied) == {
        "tooling_review",
        "operation_sequence_analysis",
        "cycle_time_estimation",
        "toolpath_development_request",
        "workholding_review",
    }
    # Mapped A23 identifiers were not requested by identifier.
    assert "simulation_support" in result.declared_but_unrequested
    assert "feeds_speeds_authoring" in result.declared_but_unrequested


# --- provenance / versions do not affect matching ----------------------------


def test_map_versions_do_not_participate_in_matching():
    index = {"simulation_request": ["simulation_support"]}
    a = reconcile_mapped(["simulation_request"], ["simulation_support"], index)
    b = reconcile_mapped(["simulation_request"], ["simulation_support"], index)
    assert a.as_dict() == b.as_dict()


# --- authority boundary ------------------------------------------------------


def test_mapped_result_carries_no_authority_fields():
    result = reconcile_mapped(
        ["simulation_request"],
        ["simulation_support"],
        {"simulation_request": ["simulation_support"]},
    )
    forbidden = {
        "approved",
        "authorized",
        "safe",
        "machine_ready",
        "execution_allowed",
        "permission",
        "permitted",
        "allowed",
    }
    assert not forbidden & set(result.as_dict())
    assert not forbidden & set(Reconciliation._fields)
    payload = json.dumps(result.as_dict())
    for word in ("approved", "authorized", "execution_allowed", "machine_ready"):
        assert word not in payload


def test_mapped_report_states_the_advisory_boundary():
    report = format_report(
        reconcile_mapped(
            ["simulation_request"],
            ["simulation_support"],
            {"simulation_request": ["simulation_support"]},
        )
    )
    assert ADVISORY_NOTICE.split("\n")[0] in report
    assert MAPPED_ADVISORY_NOTICE in report
    assert "[MATCH: mapped]" in report
    assert "simulation_request" in report
    assert "simulation_support" in report


def test_human_report_groups_multiple_mapped_targets():
    report = format_report(
        reconcile_mapped(
            ["gcode_explanation"],
            ["gcode_tutorial_generation", "post_processor_education"],
            {"gcode_explanation": ["gcode_tutorial_generation", "post_processor_education"]},
        )
    )
    assert report.index("gcode_tutorial_generation") < report.index("post_processor_education")
    assert "  → gcode_tutorial_generation" in report
    assert "  → post_processor_education" in report


# --- determinism -------------------------------------------------------------


def test_repeated_mapped_reconciliation_is_byte_identical():
    index = build_mapping_index(
        {
            "mappings": [
                {
                    "request_capability": "gcode_explanation",
                    "satisfied_by": ["post_processor_education", "gcode_tutorial_generation"],
                }
            ]
        }
    )
    first = reconcile_mapped(
        ["gcode_explanation", "simulation_request"],
        ["gcode_tutorial_generation", "simulation_support"],
        index,
    )
    second = reconcile_mapped(
        ["simulation_request", "gcode_explanation"],
        ["simulation_support", "gcode_tutorial_generation"],
        index,
    )
    assert json.dumps(first.as_dict()) == json.dumps(second.as_dict())
