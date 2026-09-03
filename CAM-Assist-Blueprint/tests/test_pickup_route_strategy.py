"""CAM-A31 pickup-route strategy model and validation."""

from copy import deepcopy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from _shared.depth_passes import compute_depth_passes
from _shared.pickup_route import (
    OPERATION_TYPE,
    PickupRouteError,
    aabbs_touch_or_overlap,
    aabb_from_center,
    build_pickup_route_strategy,
    validate_cavity_geometry,
)
from validate_strategy_package import validate_strategy_package
from version import CAM_ASSIST_VERSION


def valid_request(**overrides):
    request = {
        "operation_type": "pickup_route",
        "strategy_id": "pickup-route-test",
        "units": "inches",
        "coordinate_frame": {
            "origin": "body_center",
            "x_axis": "along_body",
            "y_axis": "across_body",
        },
        "cavity": {
            "reference_point": {"x": 0.0, "y": 0.0},
            "length": 3.0,
            "width": 1.5,
            "corner_radius": 0.125,
            "final_depth": 0.75,
            "mounting_tabs": [],
        },
        "roughing": {
            "tool_diameter": 0.25,
            "maximum_pass_depth": 0.25,
            "finish_allowance": 0.02,
            "tool_type": "end_mill",
        },
        "finishing": {
            "tool_diameter": 0.25,
            "tool_type": "end_mill",
        },
        "material_context": {"material_class": "hardwood"},
        "provenance": {"created_at": "2026-08-30T00:00:00Z"},
    }
    request.update(overrides)
    return request


def touching_tab():
    return {
        "x": 1.5,
        "y": 0.0,
        "length": 0.5,
        "width": 0.375,
        "corner_radius": 0.0625,
    }


class TestCavityGeometry:
    def test_valid_centered_cavity(self):
        cavity = validate_cavity_geometry(valid_request()["cavity"])
        assert cavity["bottom_profile"] == "flat"
        assert cavity["reference_point"] == {"x": 0, "y": 0}
        assert cavity["envelope"] == {"xmin": -1.5, "xmax": 1.5, "ymin": -0.75, "ymax": 0.75}

    def test_zero_length_rejected(self):
        with pytest.raises(PickupRouteError, match="length"):
            validate_cavity_geometry({**valid_request()["cavity"], "length": 0})

    def test_zero_width_rejected(self):
        with pytest.raises(PickupRouteError, match="width"):
            validate_cavity_geometry({**valid_request()["cavity"], "width": 0})

    def test_zero_depth_rejected(self):
        with pytest.raises(PickupRouteError, match="final_depth"):
            validate_cavity_geometry({**valid_request()["cavity"], "final_depth": 0})

    def test_negative_corner_radius_rejected(self):
        with pytest.raises(PickupRouteError, match="corner_radius"):
            validate_cavity_geometry({**valid_request()["cavity"], "corner_radius": -0.01})

    def test_corner_radius_larger_than_half_min_side_rejected(self):
        with pytest.raises(PickupRouteError, match="half"):
            validate_cavity_geometry({**valid_request()["cavity"], "corner_radius": 0.8})

    def test_z_on_reference_point_rejected(self):
        with pytest.raises(PickupRouteError, match="XY"):
            validate_cavity_geometry({
                **valid_request()["cavity"],
                "reference_point": {"x": 0, "y": 0, "z": 0},
            })

    def test_zero_tabs_accepted(self):
        cavity = validate_cavity_geometry(valid_request()["cavity"])
        assert cavity["mounting_tabs"] == []

    def test_touching_tab_accepted(self):
        request_cavity = valid_request()["cavity"]
        request_cavity["mounting_tabs"] = [touching_tab()]
        cavity = validate_cavity_geometry(request_cavity)
        assert len(cavity["mounting_tabs"]) == 1

    def test_many_tabs_accepted(self):
        request_cavity = valid_request()["cavity"]
        request_cavity["mounting_tabs"] = [
            touching_tab(),
            {"x": -1.5, "y": 0.0, "length": 0.5, "width": 0.375, "corner_radius": 0.0625},
        ]
        cavity = validate_cavity_geometry(request_cavity)
        assert len(cavity["mounting_tabs"]) == 2

    def test_floating_tab_rejected(self):
        request_cavity = valid_request()["cavity"]
        request_cavity["mounting_tabs"] = [
            {"x": 4.0, "y": 4.0, "length": 0.4, "width": 0.4, "corner_radius": 0.05}
        ]
        with pytest.raises(PickupRouteError, match="intersect or touch"):
            validate_cavity_geometry(request_cavity)

    def test_tab_edge_touch_is_contact(self):
        cavity = aabb_from_center(0, 0, 3.0, 1.5)
        tab = aabb_from_center(1.75, 0, 0.5, 0.375)
        assert aabbs_touch_or_overlap(cavity, tab)

    def test_invalid_tab_radius_rejected(self):
        request_cavity = valid_request()["cavity"]
        request_cavity["mounting_tabs"] = [
            {"x": 1.5, "y": 0.0, "length": 0.5, "width": 0.375, "corner_radius": 0.4}
        ]
        with pytest.raises(PickupRouteError, match="half"):
            validate_cavity_geometry(request_cavity)


class TestCornerFitInvariant:
    def test_positive_allowance_finishing_governs_corner(self):
        request = valid_request()
        request["roughing"]["tool_diameter"] = 0.375
        request["roughing"]["finish_allowance"] = 0.02
        request["finishing"]["tool_diameter"] = 0.25
        strategy = build_pickup_route_strategy(request, CAM_ASSIST_VERSION)
        assert strategy["tool_compatibility"]["roughing"]["claims_final_walls"] is False
        assert strategy["tool_compatibility"]["finishing"]["claims_final_walls"] is True
        assert strategy["tool_compatibility"]["roughing"]["corner_fit_applicable"] is False
        assert strategy["tool_compatibility"]["finishing"]["corner_fit_applicable"] is True

    def test_positive_allowance_rejects_incompatible_finishing_cutter(self):
        request = valid_request()
        request["finishing"]["tool_diameter"] = 0.375
        with pytest.raises(PickupRouteError, match="corner radius"):
            build_pickup_route_strategy(request, CAM_ASSIST_VERSION)

    def test_zero_allowance_requires_both_cutters_to_fit_positive_corner(self):
        request = valid_request()
        request["roughing"]["finish_allowance"] = 0
        request["roughing"]["tool_diameter"] = 0.375
        request["finishing"]["tool_diameter"] = 0.25
        with pytest.raises(PickupRouteError, match="corner radius"):
            build_pickup_route_strategy(request, CAM_ASSIST_VERSION)

    def test_zero_allowance_accepts_both_compatible_cutters(self):
        request = valid_request()
        request["roughing"]["finish_allowance"] = 0
        strategy = build_pickup_route_strategy(request, CAM_ASSIST_VERSION)
        assert strategy["tool_compatibility"]["roughing"]["claims_final_walls"] is True
        assert strategy["tool_compatibility"]["finishing"]["claims_final_walls"] is True
        assert strategy["tool_compatibility"]["roughing"]["corner_fit_applicable"] is True
        assert strategy["tool_compatibility"]["finishing"]["corner_fit_applicable"] is True

    def test_zero_corner_radius_is_tool_limited_sharp(self):
        request = valid_request()
        request["cavity"]["corner_radius"] = 0
        request["roughing"]["finish_allowance"] = 0
        strategy = build_pickup_route_strategy(request, CAM_ASSIST_VERSION)
        assert strategy["cavity"]["corner_radius"] == 0
        assert strategy["tool_compatibility"]["tool_limited_sharp"] is True
        evidence = strategy["review_requirements"]["evidence"]
        assert evidence["tool_limited_sharp"] is True
        assert evidence["finishing_tool_radius"] == 0.125
        assert "tool_limited_sharp_note" in evidence

    def test_negative_finish_allowance_rejected(self):
        request = valid_request()
        request["roughing"]["finish_allowance"] = -0.01
        with pytest.raises(PickupRouteError, match="finish_allowance"):
            build_pickup_route_strategy(request, CAM_ASSIST_VERSION)

    def test_oversized_roughing_tool_rejected(self):
        request = valid_request()
        request["roughing"]["tool_diameter"] = 2.0
        with pytest.raises(PickupRouteError, match="exceeds"):
            build_pickup_route_strategy(request, CAM_ASSIST_VERSION)

    def test_oversized_finishing_tool_rejected(self):
        request = valid_request()
        request["finishing"]["tool_diameter"] = 2.0
        with pytest.raises(PickupRouteError, match="exceeds"):
            build_pickup_route_strategy(request, CAM_ASSIST_VERSION)

    def test_missing_finishing_cutter_rejected(self):
        request = valid_request()
        del request["finishing"]
        with pytest.raises(PickupRouteError, match="finishing"):
            build_pickup_route_strategy(request, CAM_ASSIST_VERSION)


class TestStrategyBuild:
    def test_valid_strategy_identity(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        intent = strategy["operation_intent"]
        assert intent["operation_type"] == OPERATION_TYPE
        assert intent["geometry_type"] == "2.5D"
        assert intent["strategy_complexity"] == "compound"
        assert intent["cut_intent"] == "pocket"
        assert intent["target_feature"] == "body"
        assert intent["non_execution_declaration"] is True
        assert strategy["safety_boundary"]["execution_authority_claim"] is False
        assert strategy["approval_state"] == "pending"

    def test_depth_passes_reuse_shared_helper(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        expected = compute_depth_passes(0.75, 0.25)
        assert strategy["depth_strategy"]["passes"] == expected
        assert expected == [0.25, 0.5, 0.75]

    def test_uneven_integer_passes(self):
        request = valid_request()
        request["cavity"]["final_depth"] = 15
        request["roughing"]["maximum_pass_depth"] = 6
        strategy = build_pickup_route_strategy(request, CAM_ASSIST_VERSION)
        assert strategy["depth_strategy"]["passes"] == [6, 12, 15]
        assert compute_depth_passes(15, 6) == [6, 12, 15]

    def test_finishing_depth_strategy_is_final_depth_only(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        finish_depth = strategy["strategy_phases"][1]["depth_strategy"]
        assert finish_depth == {"final_depth": 0.75}
        assert "passes" not in finish_depth
        assert "maximum_pass_depth" not in finish_depth

    def test_exactly_two_phases(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        assert [phase["phase_id"] for phase in strategy["strategy_phases"]] == ["rough", "finish"]
        assert [phase["order"] for phase in strategy["strategy_phases"]] == [1, 2]

    def test_omitted_blank_thickness_does_not_fail(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        evidence = strategy["review_requirements"]["evidence"]
        assert "blank_thickness" not in evidence
        assert "residual_material" not in evidence
        assert strategy["review_requirements"]["unresolved_assumptions"] == []

    def test_supplied_blank_thickness_surfaces_residual(self):
        strategy = build_pickup_route_strategy(
            valid_request(blank_thickness=1.25), CAM_ASSIST_VERSION
        )
        evidence = strategy["review_requirements"]["evidence"]
        assert evidence["blank_thickness"] == 1.25
        assert evidence["residual_material"] == 0.5

    def test_blank_thinner_than_cavity_rejected(self):
        with pytest.raises(PickupRouteError, match="blank_thickness"):
            build_pickup_route_strategy(valid_request(blank_thickness=0.5), CAM_ASSIST_VERSION)

    def test_no_feeds_or_speeds(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        params = strategy["operation"]["parameters"]
        assert "feed_rate_ipm" not in params
        assert "spindle_rpm" not in params
        serialized = json.dumps(strategy)
        assert "feed_rate" not in serialized
        assert "spindle_rpm" not in serialized

    def test_no_machining_commands(self):
        serialized = json.dumps(build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION))
        for token in ("G0", "G1", "G2", "G3", "M3", "M5", "G54", "controller", "post_processor"):
            assert token not in serialized

    def test_no_machine_authority_language(self):
        serialized = json.dumps(build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)).lower()
        for token in (
            "machine_ready",
            "safe_to_execute",
            "execution_authorized",
            "permission_granted",
            "approved_for_cutting",
        ):
            assert token not in serialized

    def test_determinism(self):
        first = json.dumps(build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION), indent=2)
        second = json.dumps(build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION), indent=2)
        assert first == second

    def test_generic_validator_accepts_result(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        result = validate_strategy_package(strategy)
        assert result.valid, result.errors

    def test_generic_validator_rejects_oversized_tool_in_output(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        strategy["operation"]["tool"]["diameter"] = 2.0
        result = validate_strategy_package(strategy)
        assert not result.valid
        assert any("exceeds" in error for error in result.errors)

    def test_extra_strategy_phase_rejected(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        strategy["strategy_phases"].append({"phase_id": "cleanup", "order": 3})
        result = validate_strategy_package(strategy)
        assert not result.valid
        assert any("exactly two" in error for error in result.errors)

    def test_finishing_pass_list_rejected(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        strategy["strategy_phases"][1]["depth_strategy"] = {
            "final_depth": 0.75,
            "passes": [0.75],
        }
        result = validate_strategy_package(strategy)
        assert not result.valid
        assert any("only final_depth" in error for error in result.errors)

    def test_wrong_phase_order_rejected(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        strategy["strategy_phases"][1]["order"] = 3
        result = validate_strategy_package(strategy)
        assert not result.valid
        assert any("order" in error for error in result.errors)

    def test_geometry_filename_is_contract_not_generated_file(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        assert strategy["geometry"]["dxf_file"] == "geometry.dxf"
        assert strategy["geometry"]["generated"] is False
        assert strategy["geometry"]["primary_layer"] == "PICKUP_ROUTE"
        result = validate_strategy_package(strategy)
        assert result.valid, result.errors

    def test_missing_geometry_generated_flag_rejected(self):
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        del strategy["geometry"]["generated"]
        result = validate_strategy_package(strategy)
        assert not result.valid
        assert any("generated" in error for error in result.errors)

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

    def test_wrong_operation_type_rejected(self):
        with pytest.raises(PickupRouteError, match="pickup_route"):
            build_pickup_route_strategy(valid_request(operation_type="fret_slots"), CAM_ASSIST_VERSION)

    def test_unicode_strategy_id_rejected(self):
        with pytest.raises(PickupRouteError, match="strategy_id"):
            build_pickup_route_strategy(valid_request(strategy_id="pickup-ß"), CAM_ASSIST_VERSION)

    def test_operation_tool_is_finishing_cutter(self):
        request = valid_request()
        request["finishing"]["tool_diameter"] = 0.125
        strategy = build_pickup_route_strategy(request, CAM_ASSIST_VERSION)
        assert strategy["operation"]["tool"]["diameter"] == 0.125
        assert strategy["safety_boundary"]["tool_diameter_inches"] == 0.125


def _load_schema(name: str) -> dict:
    path = Path(__file__).parent.parent / "schemas" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _operation_request(**overrides):
    request = {
        "operation_type": "pickup_route",
        "geometry_type": "2.5D",
        "strategy_complexity": "compound",
        "instrument_spec": {"instrument_type": "guitar"},
        "parameters": {
            "depth_inches": 0.75,
            "width_inches": 1.5,
            "length_inches": 3.0,
            "corner_radius_inches": 0.125,
            "finish_allowance_inches": 0.02,
            "reference_point": {"x": 0.0, "y": 0.0},
        },
    }
    request.update(overrides)
    return request


class TestSchemaParity:
    def test_operation_schema_does_not_require_blank_thickness(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = _load_schema("operation.schema.json")
        jsonschema.Draft202012Validator(schema).validate(_operation_request())

    def test_operation_schema_requires_cavity_dimensions(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = _load_schema("operation.schema.json")
        missing = _operation_request()
        del missing["parameters"]["length_inches"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(missing)

    def test_strategy_schema_does_not_require_blank_thickness(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = _load_schema("strategy.schema.json")
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        jsonschema.Draft202012Validator(schema).validate(strategy)
        assert "blank_thickness" not in strategy["review_requirements"]["evidence"]

    def test_strategy_schema_requires_generated_false(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = _load_schema("strategy.schema.json")
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        jsonschema.Draft202012Validator(schema).validate(strategy)
        strategy["geometry"]["generated"] = True
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(strategy)

    def test_strategy_schema_rejects_finishing_pass_list(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = _load_schema("strategy.schema.json")
        strategy = build_pickup_route_strategy(valid_request(), CAM_ASSIST_VERSION)
        strategy["strategy_phases"][1]["depth_strategy"] = {
            "final_depth": 0.75,
            "passes": [0.75],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(strategy)

    def test_operation_schema_rejects_z_on_reference_point(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = _load_schema("operation.schema.json")
        request = _operation_request()
        request["parameters"]["reference_point"]["z"] = 0
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(request)

    def test_fret_slot_and_truss_rod_unaffected(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = _load_schema("strategy.schema.json")
        fret = Path(__file__).parent.parent / "examples" / "valid" / "fret_slot_strategy.json"
        truss = Path(__file__).parent.parent / "examples" / "valid" / "truss_rod_channel_strategy.json"
        jsonschema.Draft202012Validator(schema).validate(json.loads(fret.read_text(encoding="utf-8")))
        jsonschema.Draft202012Validator(schema).validate(json.loads(truss.read_text(encoding="utf-8")))


class TestGeometryContractHandshake:
    EXAMPLE_STRATEGY = Path(__file__).parent.parent / "examples" / "valid" / "pickup_route_strategy.json"
    EXAMPLE_PACKAGE = (
        Path(__file__).parent.parent
        / "examples"
        / "packages"
        / "pickup_route_strategy_example"
    )

    def _example_strategy(self) -> dict:
        return json.loads(self.EXAMPLE_STRATEGY.read_text(encoding="utf-8"))

    def test_committed_example_satisfies_schema_validator_and_package(self):
        jsonschema = pytest.importorskip("jsonschema")
        strategy = self._example_strategy()
        geometry = strategy["geometry"]
        assert geometry["dxf_file"] == "geometry.dxf"
        assert geometry["generated"] is False
        jsonschema.Draft202012Validator(_load_schema("strategy.schema.json")).validate(strategy)
        result = validate_strategy_package(strategy)
        assert result.valid, result.errors
        manifest = json.loads((self.EXAMPLE_PACKAGE / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["source_geometry_files"] == []
        assert not (self.EXAMPLE_PACKAGE / "geometry.dxf").exists()
        assert strategy["safety_boundary"]["execution_authority_claim"] is False
        assert strategy["operation_intent"]["non_execution_declaration"] is True

    def test_generated_true_fails_schema_and_python(self):
        jsonschema = pytest.importorskip("jsonschema")
        strategy = self._example_strategy()
        strategy["geometry"]["generated"] = True
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(_load_schema("strategy.schema.json")).validate(strategy)
        result = validate_strategy_package(strategy)
        assert not result.valid
        assert any("generated" in error for error in result.errors)

    def test_wrong_dxf_filename_fails_schema_and_python(self):
        jsonschema = pytest.importorskip("jsonschema")
        strategy = self._example_strategy()
        strategy["geometry"]["dxf_file"] = "cavity.dxf"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(_load_schema("strategy.schema.json")).validate(strategy)
        result = validate_strategy_package(strategy)
        assert not result.valid
        assert any("dxf_file" in error for error in result.errors)
