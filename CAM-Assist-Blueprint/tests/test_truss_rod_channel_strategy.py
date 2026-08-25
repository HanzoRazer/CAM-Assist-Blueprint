"""CAM-A30 truss-rod-channel strategy model and validation."""

from copy import deepcopy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from _shared.depth_passes import compute_depth_passes
from _shared.truss_rod_channel import (
    OPERATION_TYPE,
    TrussRodChannelError,
    build_channel_strategy,
    validate_channel_geometry,
    validate_tool_fit,
)
from validate_strategy_package import validate_strategy_package
from version import CAM_ASSIST_VERSION


def valid_request(**overrides):
    request = {
        "operation_type": "truss_rod_channel",
        "strategy_id": "truss-rod-channel-test",
        "units": "inches",
        "coordinate_frame": {
            "origin": "nut_centerline",
            "x_axis": "along_neck_toward_bridge",
            "y_axis": "across_neck",
        },
        "channel": {
            "start": {"x": 0.0, "y": 0.0},
            "end": {"x": 10.0, "y": 0.0},
            "width": 0.25,
            "depth": 0.375,
        },
        "tool": {"diameter": 0.25, "tool_type": "end_mill"},
        "maximum_pass_depth": 0.125,
        "material_context": {"material_class": "hardwood"},
        "provenance": {"created_at": "2026-08-25T00:00:00Z"},
    }
    request.update(overrides)
    return request


class TestChannelGeometry:
    def test_valid_straight_channel(self):
        channel = validate_channel_geometry(valid_request()["channel"])
        assert channel["length"] == 10
        assert channel["bottom_profile"] == "flat"
        assert channel["path_kind"] == "open_centerline"

    def test_zero_width_rejected(self):
        with pytest.raises(TrussRodChannelError, match="width"):
            validate_channel_geometry({**valid_request()["channel"], "width": 0})

    def test_negative_width_rejected(self):
        with pytest.raises(TrussRodChannelError, match="width"):
            validate_channel_geometry({**valid_request()["channel"], "width": -0.1})

    def test_zero_depth_rejected(self):
        with pytest.raises(TrussRodChannelError, match="depth"):
            validate_channel_geometry({**valid_request()["channel"], "depth": 0})

    def test_negative_depth_rejected(self):
        with pytest.raises(TrussRodChannelError, match="depth"):
            validate_channel_geometry({**valid_request()["channel"], "depth": -1})

    def test_zero_length_centerline_rejected(self):
        with pytest.raises(TrussRodChannelError, match="length"):
            validate_channel_geometry({
                "start": {"x": 1, "y": 1},
                "end": {"x": 1, "y": 1},
                "width": 0.25,
                "depth": 0.3,
            })


class TestToolFit:
    def test_equal_diameter_is_centerline_cut(self):
        fit = validate_tool_fit(0.25, 0.25)
        assert fit["status"] == "compatible"
        assert fit["recommendation"] == "recommended"
        assert fit["width_strategy"] == "centerline_cut"

    def test_smaller_tool_requires_width_clearing(self):
        fit = validate_tool_fit(0.125, 0.25)
        assert fit["width_strategy"] == "width_clearing_required"
        assert fit["recommendation"] == "recommended"

    def test_oversized_tool_hard_fails(self):
        with pytest.raises(TrussRodChannelError, match="exceeds"):
            validate_tool_fit(0.375, 0.25)


class TestStrategyBuild:
    def test_valid_strategy_identity(self):
        strategy = build_channel_strategy(valid_request(), CAM_ASSIST_VERSION)
        intent = strategy["operation_intent"]
        assert intent["operation_type"] == OPERATION_TYPE
        assert intent["geometry_type"] == "2.5D"
        assert intent["strategy_complexity"] == "simple"
        assert intent["cut_intent"] == "channel"
        assert intent["non_execution_declaration"] is True
        assert strategy["safety_boundary"]["execution_authority_claim"] is False
        assert strategy["approval_state"] == "pending"

    def test_depth_passes_reuse_shared_helper(self):
        strategy = build_channel_strategy(valid_request(), CAM_ASSIST_VERSION)
        expected = compute_depth_passes(0.375, 0.125)
        assert strategy["depth_strategy"]["passes"] == expected
        assert strategy["depth_strategy"]["pass_count"] == len(expected)
        assert expected == [0.125, 0.25, 0.375]

    def test_uneven_integer_passes(self):
        request = valid_request()
        request["channel"]["depth"] = 9
        request["maximum_pass_depth"] = 4
        strategy = build_channel_strategy(request, CAM_ASSIST_VERSION)
        assert strategy["depth_strategy"]["passes"] == [4, 8, 9]
        assert compute_depth_passes(9, 4) == [4, 8, 9]

    def test_single_depth_pass(self):
        request = valid_request()
        request["channel"]["depth"] = 0.1
        request["maximum_pass_depth"] = 0.125
        strategy = build_channel_strategy(request, CAM_ASSIST_VERSION)
        assert strategy["depth_strategy"]["passes"] == [0.1]
        assert strategy["depth_strategy"]["pass_count"] == 1

    def test_blank_thickness_residual(self):
        request = valid_request(blank_thickness=0.8)
        strategy = build_channel_strategy(request, CAM_ASSIST_VERSION)
        assert strategy["review_requirements"]["evidence"]["residual_material"] == 0.425
        assert strategy["review_requirements"]["unresolved_assumptions"] == []

    def test_missing_blank_thickness_is_unresolved_assumption(self):
        strategy = build_channel_strategy(valid_request(), CAM_ASSIST_VERSION)
        assert strategy["review_requirements"]["unresolved_assumptions"] == [
            "residual_material_beneath_channel: blank_thickness not supplied"
        ]

    def test_blank_thinner_than_channel_rejected(self):
        with pytest.raises(TrussRodChannelError, match="blank_thickness"):
            build_channel_strategy(valid_request(blank_thickness=0.1), CAM_ASSIST_VERSION)

    def test_no_feeds_or_speeds(self):
        strategy = build_channel_strategy(valid_request(), CAM_ASSIST_VERSION)
        params = strategy["operation"]["parameters"]
        assert "feed_rate_ipm" not in params
        assert "spindle_rpm" not in params
        serialized = json.dumps(strategy)
        assert "feed_rate" not in serialized
        assert "spindle_rpm" not in serialized

    def test_no_machining_commands(self):
        serialized = json.dumps(build_channel_strategy(valid_request(), CAM_ASSIST_VERSION))
        for token in ("G0", "G1", "G2", "G3", "M3", "M5", "G54", "controller", "post_processor"):
            assert token not in serialized

    def test_no_machine_authority_language(self):
        serialized = json.dumps(build_channel_strategy(valid_request(), CAM_ASSIST_VERSION)).lower()
        for token in (
            "machine_ready",
            "safe_to_execute",
            "execution_authorized",
            "permission_granted",
            "approved_for_cutting",
        ):
            assert token not in serialized

    def test_determinism(self):
        first = json.dumps(build_channel_strategy(valid_request(), CAM_ASSIST_VERSION), indent=2)
        second = json.dumps(build_channel_strategy(valid_request(), CAM_ASSIST_VERSION), indent=2)
        assert first == second

    def test_input_order_independence(self):
        a = valid_request()
        b = valid_request()
        b["channel"] = {
            "depth": 0.375,
            "end": {"y": 0.0, "x": 10.0},
            "width": 0.25,
            "start": {"y": 0.0, "x": 0.0},
        }
        strategy_a = build_channel_strategy(a, CAM_ASSIST_VERSION)
        strategy_b = build_channel_strategy(b, CAM_ASSIST_VERSION)
        assert strategy_a["channel"] == strategy_b["channel"]
        assert strategy_a["depth_strategy"] == strategy_b["depth_strategy"]

    def test_generic_validator_accepts_result(self):
        strategy = build_channel_strategy(valid_request(blank_thickness=0.8), CAM_ASSIST_VERSION)
        result = validate_strategy_package(strategy)
        assert result.valid, result.errors

    def test_generic_validator_rejects_oversized_tool_in_output(self):
        strategy = build_channel_strategy(valid_request(), CAM_ASSIST_VERSION)
        strategy["operation"]["tool"]["diameter"] = 0.5
        result = validate_strategy_package(strategy)
        assert not result.valid
        assert any("exceeds" in error for error in result.errors)

    def test_fret_slot_minimal_package_unchanged(self):
        package = {
            "strategy_version": "1.2",
            "strategy_id": "test-package",
            "units": "inches",
            "coordinate_frame": {
                "origin": "nut_centerline",
                "x_axis": "along_neck",
                "y_axis": "across_fretboard",
            },
            "provenance": {
                "cam_assist_version": "0.3.0",
                "created_at": "2026-05-21T12:00:00Z",
            },
            "operation_intent": {
                "operation_type": "fret_slots",
                "target_feature": "fretboard",
                "cut_intent": "slot",
                "non_execution_declaration": True,
            },
            "material_context": {"material_class": "hardwood"},
            "safety_boundary": {
                "non_execution_declaration": True,
                "human_review_required": True,
            },
            "geometry": {"dxf_file": "geometry.dxf", "primary_layer": "FRET_SLOTS"},
            "operation": {
                "type": "slot_cut",
                "tool": {"tool_type": "slot_cutter"},
                "parameters": {"depth": 0.060},
            },
            "approval_state": "pending",
        }
        result = validate_strategy_package(deepcopy(package))
        assert result.valid, result.errors

    def test_missing_operation_type_still_rejected(self):
        package = {
            "strategy_version": "1.2",
            "strategy_id": "test-package",
            "units": "inches",
            "coordinate_frame": {"origin": "nut", "x_axis": "along", "y_axis": "across"},
            "provenance": {"cam_assist_version": "0.3.0", "created_at": "2026-05-21T12:00:00Z"},
            "operation_intent": {
                "target_feature": "fretboard",
                "cut_intent": "slot",
                "non_execution_declaration": True,
            },
            "material_context": {"material_class": "hardwood"},
            "safety_boundary": {
                "non_execution_declaration": True,
                "human_review_required": True,
            },
            "geometry": {"dxf_file": "geometry.dxf", "primary_layer": "FRET_SLOTS"},
            "operation": {
                "type": "slot_cut",
                "tool": {"tool_type": "slot_cutter"},
                "parameters": {"depth": 0.060},
            },
            "approval_state": "pending",
        }
        result = validate_strategy_package(package)
        assert not result.valid
        assert any("operation_type" in error for error in result.errors)

    def test_single_phase_is_channel_cut(self):
        strategy = build_channel_strategy(valid_request(), CAM_ASSIST_VERSION)
        assert len(strategy["strategy_phases"]) == 1
        assert strategy["strategy_phases"][0]["phase_id"] == "channel_cut"
        assert strategy["strategy_phases"][0]["order"] == 1

    def test_wrong_operation_type_rejected(self):
        with pytest.raises(TrussRodChannelError, match="truss_rod_channel"):
            build_channel_strategy(valid_request(operation_type="fret_slots"), CAM_ASSIST_VERSION)
