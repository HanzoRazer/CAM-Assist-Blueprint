"""Truss rod channel manufacturing-strategy model.

Computes a reviewable strategy for a straight, constant-width, flat-bottom
channel. This module does not print, does not generate G-code, and does not
claim execution authority.
"""

from __future__ import annotations

import math
from typing import Any

from .depth_passes import DEPTH_EPSILON, DepthPassError, compute_depth_passes, json_number

OPERATION_TYPE = "truss_rod_channel"
GEOMETRY_TYPE = "2.5D"
STRATEGY_COMPLEXITY = "simple"
CUT_INTENT = "channel"
OPERATION_CUT_TYPE = "channel_cut"
PRIMARY_LAYER = "TRUSS_ROD_CHANNEL"
REFERENCE_LAYERS = ["NECK_CENTERLINE", "NECK_OUTLINE"]
DXF_FILENAME = "geometry.dxf"
TARGET_FEATURE = "neck"

WIDTH_STRATEGY_CENTERLINE = "centerline_cut"
WIDTH_STRATEGY_CLEARING = "width_clearing_required"

FORBIDDEN_AUTHORITY_TOKENS = (
    "approved",
    "machine_ready",
    "safe_to_execute",
    "execution_authorized",
    "permission_granted",
    "approved_for_cutting",
    "safe_to_run",
)


class TrussRodChannelError(ValueError):
    """Invalid truss-rod-channel strategy input."""


def _as_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrussRodChannelError(f"{name} must be a number")
    return float(value)


def _positive(name: str, value: object) -> float:
    number = _as_number(name, value)
    if number <= 0:
        raise TrussRodChannelError(f"{name} must be positive")
    return number


def _point(name: str, value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        raise TrussRodChannelError(f"{name} must be an object with x and y")
    if "x" not in value or "y" not in value:
        raise TrussRodChannelError(f"{name} must include x and y")
    x = _as_number(f"{name}.x", value["x"])
    y = _as_number(f"{name}.y", value["y"])
    point: dict[str, float] = {"x": json_number(x), "y": json_number(y)}
    if "z" in value:
        point["z"] = json_number(_as_number(f"{name}.z", value["z"]))
    return point


def channel_length(start: dict[str, float], end: dict[str, float]) -> float:
    dx = float(end["x"]) - float(start["x"])
    dy = float(end["y"]) - float(start["y"])
    dz = float(end.get("z", 0)) - float(start.get("z", 0))
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def validate_channel_geometry(channel: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(channel, dict):
        raise TrussRodChannelError("channel must be an object")
    start = _point("channel.start", channel.get("start"))
    end = _point("channel.end", channel.get("end"))
    width = _positive("channel.width", channel.get("width"))
    depth = _positive("channel.depth", channel.get("depth"))
    length = channel_length(start, end)
    if length <= DEPTH_EPSILON:
        raise TrussRodChannelError("channel centerline length must be greater than zero")
    return {
        "start": start,
        "end": end,
        "width": json_number(width),
        "depth": json_number(depth),
        "length": json_number(length),
        "bottom_profile": "flat",
        "path_kind": "open_centerline",
    }


def validate_tool_fit(tool_diameter: float, channel_width: float) -> dict[str, Any]:
    if tool_diameter > channel_width + DEPTH_EPSILON:
        raise TrussRodChannelError(
            "tool diameter exceeds channel width; oversized tools cannot be recommended"
        )
    if abs(tool_diameter - channel_width) <= DEPTH_EPSILON:
        width_strategy = WIDTH_STRATEGY_CENTERLINE
    else:
        width_strategy = WIDTH_STRATEGY_CLEARING
    return {
        "status": "compatible",
        "recommendation": "recommended",
        "tool_diameter": json_number(tool_diameter),
        "channel_width": json_number(channel_width),
        "width_strategy": width_strategy,
    }


def build_depth_strategy(final_depth: float, maximum_pass_depth: float) -> dict[str, Any]:
    try:
        passes = compute_depth_passes(final_depth, maximum_pass_depth)
    except DepthPassError as exc:
        raise TrussRodChannelError(str(exc)) from exc
    last = float(passes[-1])
    if last - float(final_depth) > DEPTH_EPSILON:
        raise TrussRodChannelError("depth-pass calculation exceeded final_depth")
    if abs(last - float(final_depth)) > DEPTH_EPSILON:
        raise TrussRodChannelError("depth-pass calculation did not reach final_depth")
    return {
        "final_depth": json_number(final_depth),
        "maximum_pass_depth": json_number(maximum_pass_depth),
        "pass_count": len(passes),
        "passes": passes,
    }


def _non_blank_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TrussRodChannelError(f"{name} must be a non-blank string")
    return value


def _optional_positive(name: str, value: object | None) -> float | None:
    if value is None:
        return None
    return _positive(name, value)


def build_review_requirements(
    *,
    channel: dict[str, Any],
    tool_fit: dict[str, Any],
    depth_strategy: dict[str, Any],
    residual_material: float | None,
    access_direction: str | None,
    unresolved: list[str],
) -> dict[str, Any]:
    items = [
        "Channel start and end match the intended neck centerline location.",
        "Channel width matches the intended truss rod and any explicit routing allowance.",
        "Channel depth matches the intended rod and does not overcut the blank.",
        "Residual material beneath the channel is adequate for the neck blank.",
        "Recommended tool diameter fits the channel width.",
        "Depth-pass sequence reaches final depth without overcutting.",
        "Access direction and workholding are understood by the operator.",
        "This package is advisory only and does not authorize machine execution.",
    ]
    evidence = {
        "channel_width": channel["width"],
        "channel_depth": channel["depth"],
        "channel_length": channel["length"],
        "start": channel["start"],
        "end": channel["end"],
        "tool_diameter": tool_fit["tool_diameter"],
        "tool_compatibility": tool_fit["status"],
        "width_strategy": tool_fit["width_strategy"],
        "pass_count": depth_strategy["pass_count"],
        "passes": depth_strategy["passes"],
    }
    if residual_material is not None:
        evidence["residual_material"] = json_number(residual_material)
    if access_direction is not None:
        evidence["access_direction"] = access_direction
    return {
        "items": items,
        "evidence": evidence,
        "unresolved_assumptions": list(unresolved),
    }


def build_channel_strategy(request: dict[str, Any], cam_assist_version: str) -> dict[str, Any]:
    """Build a complete A2 strategy document from a truss-rod-channel request."""
    if not isinstance(request, dict):
        raise TrussRodChannelError("request must be a JSON object")

    operation_type = request.get("operation_type")
    if operation_type != OPERATION_TYPE:
        raise TrussRodChannelError(
            f"operation_type must be '{OPERATION_TYPE}'"
        )

    strategy_id = _non_blank_string("strategy_id", request.get("strategy_id"))
    if not all(c.isalnum() or c == "-" for c in strategy_id) or strategy_id != strategy_id.lower():
        raise TrussRodChannelError(
            "strategy_id must contain only lowercase alphanumeric characters and hyphens"
        )

    units = request.get("units", "inches")
    if units not in ("inches", "mm"):
        raise TrussRodChannelError("units must be 'inches' or 'mm'")

    coordinate_frame = request.get("coordinate_frame")
    if not isinstance(coordinate_frame, dict):
        raise TrussRodChannelError("coordinate_frame must be an object")
    for field in ("origin", "x_axis", "y_axis"):
        if field not in coordinate_frame:
            raise TrussRodChannelError(f"coordinate_frame.{field} is required")

    material_context = request.get("material_context")
    if not isinstance(material_context, dict) or "material_class" not in material_context:
        raise TrussRodChannelError("material_context.material_class is required")

    channel = validate_channel_geometry(request.get("channel") or {})

    tool = request.get("tool")
    if not isinstance(tool, dict):
        raise TrussRodChannelError("tool must be an object")
    tool_diameter = _positive("tool.diameter", tool.get("diameter"))
    tool_fit = validate_tool_fit(tool_diameter, float(channel["width"]))

    maximum_pass_depth = _positive("maximum_pass_depth", request.get("maximum_pass_depth"))
    depth_strategy = build_depth_strategy(float(channel["depth"]), maximum_pass_depth)

    unresolved: list[str] = []
    blank_thickness = _optional_positive(
        "blank_thickness", request.get("blank_thickness")
    )
    residual_material: float | None
    if blank_thickness is None:
        residual_material = None
        unresolved.append(
            "residual_material_beneath_channel: blank_thickness not supplied"
        )
    else:
        residual_material = blank_thickness - float(channel["depth"])
        if residual_material <= DEPTH_EPSILON:
            raise TrussRodChannelError(
                "blank_thickness must exceed channel depth so residual material is positive"
            )

    access_direction = request.get("access_direction")
    if access_direction is not None:
        access_direction = _non_blank_string("access_direction", access_direction)

    provenance_in = request.get("provenance") or {}
    if not isinstance(provenance_in, dict):
        raise TrussRodChannelError("provenance must be an object")
    created_at = provenance_in.get("created_at")
    if not isinstance(created_at, str) or not created_at.strip():
        raise TrussRodChannelError(
            "provenance.created_at is required so strategy serialization is deterministic"
        )

    source_spec_id = provenance_in.get("source_spec_id")
    created_by = provenance_in.get("created_by", "cam-assist-blueprint")

    width_strategy = tool_fit["width_strategy"]
    if width_strategy == WIDTH_STRATEGY_CENTERLINE:
        sequence = "single_centerline_cut"
        phase_intent = (
            "Cut the straight truss rod channel along the supplied centerline "
            "to final depth. Tool diameter equals channel width, so a single "
            "centerline cut describes the width strategy. No cutter-offset "
            "toolpath is generated."
        )
    else:
        sequence = "width_clearing_required"
        phase_intent = (
            "Cut the straight truss rod channel to final depth. Tool diameter "
            "is smaller than channel width, so width clearing is required. "
            "This is a manufacturing-strategy statement; no cutter-center "
            "offsets or machine motion are generated."
        )

    review_requirements = build_review_requirements(
        channel=channel,
        tool_fit=tool_fit,
        depth_strategy=depth_strategy,
        residual_material=residual_material,
        access_direction=access_direction,
        unresolved=unresolved,
    )

    setup_assumptions: dict[str, Any] = {
        "workholding": (
            "Neck blank must be secured against movement along the channel "
            "axis. This is an advisory manufacturing assumption, not a "
            "fixture program or work-offset assignment."
        ),
        "cross_operation_scheduling": "not_specified",
        "placement_authority": (
            "Channel coordinates are design intent relative to the strategy "
            "coordinate frame. They are not fixture zero, a work offset, or machine home."
        ),
    }
    if access_direction is not None:
        setup_assumptions["access_direction"] = access_direction

    tool_type = tool.get("tool_type", "end_mill")
    if not isinstance(tool_type, str) or not tool_type.strip():
        raise TrussRodChannelError("tool.tool_type must be a non-blank string when present")
    tool_description = tool.get("description", "End mill sized to the channel width")

    strategy_phases = [
        {
            "phase_id": "channel_cut",
            "order": 1,
            "intent": phase_intent,
            "recommended_tool": {
                "status": "recommended",
                "compatibility": "compatible",
                "reference_type": "dimension_spec",
                "tool_type": tool_type,
                "diameter": json_number(tool_diameter),
                "description": tool_description,
                "width_strategy": width_strategy,
            },
            "depth_strategy": depth_strategy,
        }
    ]

    strategy = {
        "strategy_version": "1.2",
        "strategy_id": strategy_id,
        "units": units,
        "coordinate_frame": coordinate_frame,
        "provenance": {
            "source_spec_id": source_spec_id,
            "cam_assist_version": cam_assist_version,
            "created_at": created_at,
            "created_by": created_by,
        },
        "operation_intent": {
            "operation_type": OPERATION_TYPE,
            "target_feature": request.get("target_feature", TARGET_FEATURE),
            "cut_intent": CUT_INTENT,
            "geometry_type": GEOMETRY_TYPE,
            "strategy_complexity": STRATEGY_COMPLEXITY,
            "non_execution_declaration": True,
        },
        "material_context": material_context,
        "safety_boundary": {
            "non_execution_declaration": True,
            "human_review_required": True,
            "max_depth_inches": json_number(float(channel["depth"])),
            "tool_diameter_inches": json_number(tool_diameter),
            "execution_authority_claim": False,
        },
        "geometry": {
            "dxf_file": DXF_FILENAME,
            "primary_layer": PRIMARY_LAYER,
            "reference_layers": list(REFERENCE_LAYERS),
        },
        "operation": {
            "type": OPERATION_CUT_TYPE,
            "tool": {
                "reference_type": "dimension_spec",
                "tool_type": tool_type,
                "diameter": json_number(tool_diameter),
                "description": tool_description,
            },
            "parameters": {
                "depth": json_number(float(channel["depth"])),
                "width": json_number(float(channel["width"])),
                "depth_per_pass": json_number(maximum_pass_depth),
                "notes": (
                    "Depth-pass sequence is advisory manufacturing strategy, "
                    "not machine motion. No feeds or speeds are derived from material."
                ),
            },
            "sequence": sequence,
        },
        "channel": channel,
        "depth_strategy": depth_strategy,
        "strategy_phases": strategy_phases,
        "tool_compatibility": tool_fit,
        "setup_assumptions": setup_assumptions,
        "review_requirements": review_requirements,
        "warnings": [],
        "approval_state": "pending",
    }

    if source_spec_id is None:
        del strategy["provenance"]["source_spec_id"]

    _assert_no_forbidden_authority(strategy)
    return strategy


def _walk_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(_walk_strings(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_walk_strings(item))
    return found


def _assert_no_forbidden_authority(strategy: dict[str, Any]) -> None:
    blob = " ".join(_walk_strings(strategy)).lower()
    for token in FORBIDDEN_AUTHORITY_TOKENS:
        if token.replace("_", " ") in blob or token in blob:
            raise TrussRodChannelError(
                f"strategy must not assert machine authority token '{token}'"
            )


def validate_truss_rod_channel_strategy_data(data: dict[str, Any]) -> list[str]:
    """Semantic checks for an already-assembled truss-rod-channel strategy."""
    errors: list[str] = []
    intent = data.get("operation_intent") or {}
    if intent.get("operation_type") != OPERATION_TYPE:
        return errors
    if intent.get("geometry_type") != GEOMETRY_TYPE:
        errors.append("operation_intent.geometry_type must be '2.5D'")
    if intent.get("strategy_complexity") != STRATEGY_COMPLEXITY:
        errors.append("operation_intent.strategy_complexity must be 'simple'")
    if intent.get("cut_intent") != CUT_INTENT:
        errors.append("operation_intent.cut_intent must be 'channel'")

    channel = data.get("channel")
    if not isinstance(channel, dict):
        errors.append("channel object is required for truss_rod_channel")
        return errors
    try:
        expected = validate_channel_geometry(channel)
    except TrussRodChannelError as exc:
        errors.append(str(exc))
        return errors

    tool = (data.get("operation") or {}).get("tool") or {}
    diameter = tool.get("diameter")
    try:
        tool_fit = validate_tool_fit(_positive("operation.tool.diameter", diameter), float(expected["width"]))
    except TrussRodChannelError as exc:
        errors.append(str(exc))
        return errors

    depth_strategy = data.get("depth_strategy")
    if not isinstance(depth_strategy, dict):
        errors.append("depth_strategy is required for truss_rod_channel")
        return errors
    try:
        recomputed = build_depth_strategy(
            float(expected["depth"]),
            _positive("depth_strategy.maximum_pass_depth", depth_strategy.get("maximum_pass_depth")),
        )
    except TrussRodChannelError as exc:
        errors.append(str(exc))
        return errors
    if depth_strategy.get("passes") != recomputed["passes"]:
        errors.append("depth_strategy.passes must match the shared depth-pass helper")
    if any(float(p) - float(expected["depth"]) > DEPTH_EPSILON for p in depth_strategy.get("passes") or []):
        errors.append("depth_strategy passes must not exceed final channel depth")

    phases = data.get("strategy_phases")
    if not isinstance(phases, list) or not phases:
        errors.append("strategy_phases must contain the channel_cut phase")
    elif phases[0].get("phase_id") != "channel_cut":
        errors.append("first strategy phase must be channel_cut")

    compatibility = data.get("tool_compatibility") or {}
    if compatibility.get("width_strategy") != tool_fit["width_strategy"]:
        errors.append("tool_compatibility.width_strategy is inconsistent with tool fit")

    return errors
