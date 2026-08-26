"""Truss rod channel manufacturing-strategy model.

Computes a reviewable strategy for a straight, constant-width, flat-bottom
channel. This module does not print, does not generate G-code, and does not
claim execution authority.
"""

from __future__ import annotations

import math
import re
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
SEQUENCE_CENTERLINE = "single_centerline_cut"
SEQUENCE_CLEARING = WIDTH_STRATEGY_CLEARING
DEFAULT_TOOL_TYPE = "end_mill"
DEFAULT_TOOL_DESCRIPTION = "End mill sized to the channel width"
STRATEGY_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
CROSS_OPERATION_SCHEDULING = "not_specified"
GEOMETRY_GENERATED = False

PHASE_INTENT_CENTERLINE = (
    "Cut the straight truss rod channel along the supplied centerline "
    "to final depth. Tool diameter equals channel width, so a single "
    "centerline cut describes the width strategy. No cutter-offset "
    "toolpath is generated."
)
PHASE_INTENT_CLEARING = (
    "Cut the straight truss rod channel to final depth. Tool diameter "
    "is smaller than channel width, so width clearing is required. "
    "This is a manufacturing-strategy statement; no cutter-center "
    "offsets or machine motion are generated."
)
DEPTH_PARAMETER_NOTES = (
    "Depth-pass sequence is advisory manufacturing strategy, "
    "not machine motion. No feeds or speeds are derived from material."
)
SETUP_WORKHOLDING = (
    "Neck blank must be secured against movement along the channel "
    "axis. This is an advisory manufacturing assumption, not a "
    "fixture program or work-offset assignment."
)
SETUP_PLACEMENT_AUTHORITY = (
    "Channel coordinates are design intent relative to the strategy "
    "coordinate frame. They are not fixture zero, a work offset, or machine home."
)

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
    if "z" in value:
        raise TrussRodChannelError(
            f"{name} must be an XY point; depth is channel.depth, not a Z coordinate"
        )
    x = _as_number(f"{name}.x", value["x"])
    y = _as_number(f"{name}.y", value["y"])
    return {"x": json_number(x), "y": json_number(y)}


def channel_length(start: dict[str, float], end: dict[str, float]) -> float:
    dx = float(end["x"]) - float(start["x"])
    dy = float(end["y"]) - float(start["y"])
    return math.sqrt(dx * dx + dy * dy)


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
        width_clearing_required = False
    else:
        width_strategy = WIDTH_STRATEGY_CLEARING
        width_clearing_required = True
    return {
        "status": "compatible",
        "recommendation": "recommended",
        "tool_diameter": json_number(tool_diameter),
        "channel_width": json_number(channel_width),
        "width_strategy": width_strategy,
        "width_clearing_required": width_clearing_required,
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


def _same_number(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        return False
    return json_number(float(left)) == json_number(float(right))


def _same_pass_list(left: object, right: object) -> bool:
    if not isinstance(left, list) or not isinstance(right, list):
        return False
    if len(left) != len(right):
        return False
    return all(_same_number(first, second) for first, second in zip(left, right))


def _same_point(left: object, right: object) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    if "z" in left or "z" in right:
        return False
    return _same_number(left.get("x"), right.get("x")) and _same_number(
        left.get("y"), right.get("y")
    )


def _width_plan(tool_fit: dict[str, Any]) -> tuple[str, str]:
    if tool_fit["width_strategy"] == WIDTH_STRATEGY_CENTERLINE:
        return SEQUENCE_CENTERLINE, PHASE_INTENT_CENTERLINE
    return SEQUENCE_CLEARING, PHASE_INTENT_CLEARING


def _present(mapping: dict[str, Any], key: str) -> bool:
    return key in mapping and mapping.get(key) is not None


def resolve_blank_thickness(request: dict[str, Any], units: str) -> float:
    """Require blank thickness; accept blank_thickness_inches as an inches-only alias."""
    has_canonical = _present(request, "blank_thickness")
    has_inch_alias = _present(request, "blank_thickness_inches")
    if has_inch_alias and units != "inches":
        raise TrussRodChannelError(
            "blank_thickness_inches is only valid when units are inches; use blank_thickness"
        )
    if has_canonical and has_inch_alias:
        canonical = _positive("blank_thickness", request.get("blank_thickness"))
        alias = _positive("blank_thickness_inches", request.get("blank_thickness_inches"))
        if not _same_number(canonical, alias):
            raise TrussRodChannelError(
                "blank_thickness and blank_thickness_inches must agree"
            )
        return canonical
    if has_canonical:
        return _positive("blank_thickness", request.get("blank_thickness"))
    if has_inch_alias:
        return _positive("blank_thickness", request.get("blank_thickness_inches"))
    raise TrussRodChannelError(
        "blank_thickness is required "
        "(blank_thickness_inches is accepted as an alias when units are inches)"
    )


def resolve_tool_type(tool: dict[str, Any]) -> str:
    if not _present(tool, "tool_type"):
        return DEFAULT_TOOL_TYPE
    return _non_blank_string("tool.tool_type", tool.get("tool_type"))


def resolve_tool_description(tool: dict[str, Any]) -> str:
    if not _present(tool, "description"):
        return DEFAULT_TOOL_DESCRIPTION
    return _non_blank_string("tool.description", tool.get("description"))


def compute_residual_material(blank_thickness: float, final_depth: float) -> float:
    residual_material = blank_thickness - final_depth
    if residual_material <= DEPTH_EPSILON:
        raise TrussRodChannelError(
            "residual_material must be greater than zero "
            "(blank_thickness must exceed channel depth)"
        )
    return residual_material


def build_review_requirements(
    *,
    channel: dict[str, Any],
    tool_fit: dict[str, Any],
    depth_strategy: dict[str, Any],
    residual_material: float,
    blank_thickness: float,
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
        "width_clearing_required": tool_fit["width_clearing_required"],
        "blank_thickness": json_number(blank_thickness),
        "residual_material": json_number(residual_material),
        "pass_count": depth_strategy["pass_count"],
        "passes": depth_strategy["passes"],
    }
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
    if STRATEGY_ID_PATTERN.fullmatch(strategy_id) is None:
        raise TrussRodChannelError(
            "strategy_id must contain only lowercase ASCII letters, digits, and hyphens"
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
    blank_thickness = resolve_blank_thickness(request, units)
    residual_material = compute_residual_material(
        blank_thickness, float(channel["depth"])
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

    sequence, phase_intent = _width_plan(tool_fit)

    review_requirements = build_review_requirements(
        channel=channel,
        tool_fit=tool_fit,
        depth_strategy=depth_strategy,
        residual_material=residual_material,
        blank_thickness=blank_thickness,
        access_direction=access_direction,
        unresolved=unresolved,
    )

    setup_assumptions: dict[str, Any] = {
        "workholding": SETUP_WORKHOLDING,
        "cross_operation_scheduling": CROSS_OPERATION_SCHEDULING,
        "placement_authority": SETUP_PLACEMENT_AUTHORITY,
    }
    if access_direction is not None:
        setup_assumptions["access_direction"] = access_direction

    tool_type = resolve_tool_type(tool)
    tool_description = resolve_tool_description(tool)
    width_strategy = tool_fit["width_strategy"]

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
                "width_clearing_required": tool_fit["width_clearing_required"],
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
            "generated": GEOMETRY_GENERATED,
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
                "notes": DEPTH_PARAMETER_NOTES,
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
    errors.extend(_validate_identity(intent, data.get("strategy_id")))

    channel = data.get("channel")
    if not isinstance(channel, dict):
        errors.append("channel object is required for truss_rod_channel")
        return errors
    try:
        expected = validate_channel_geometry(channel)
    except TrussRodChannelError as exc:
        errors.append(str(exc))
        return errors
    errors.extend(_validate_channel_fields(channel, expected))

    tool = (data.get("operation") or {}).get("tool") or {}
    try:
        tool_type = _non_blank_string("operation.tool.tool_type", tool.get("tool_type"))
        tool_fit = validate_tool_fit(
            _positive("operation.tool.diameter", tool.get("diameter")),
            float(expected["width"]),
        )
    except TrussRodChannelError as exc:
        errors.append(str(exc))
        return errors
    errors.extend(_validate_tool_contract(data, tool_fit, tool_type, expected))

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
    errors.extend(_validate_depth_contract(data, expected, depth_strategy, recomputed))
    errors.extend(_validate_phase_contract(data, tool_fit, tool_type, recomputed))
    errors.extend(_validate_evidence_contract(data, expected, tool_fit, recomputed))
    errors.extend(_validate_geometry_contract(data.get("geometry") or {}))
    errors.extend(_validate_setup_contract(data.get("setup_assumptions") or {}))
    return errors


def _validate_identity(intent: dict[str, Any], strategy_id: object) -> list[str]:
    errors: list[str] = []
    if intent.get("geometry_type") != GEOMETRY_TYPE:
        errors.append("operation_intent.geometry_type must be '2.5D'")
    if intent.get("strategy_complexity") != STRATEGY_COMPLEXITY:
        errors.append("operation_intent.strategy_complexity must be 'simple'")
    if intent.get("cut_intent") != CUT_INTENT:
        errors.append("operation_intent.cut_intent must be 'channel'")
    if not isinstance(strategy_id, str) or STRATEGY_ID_PATTERN.fullmatch(strategy_id) is None:
        errors.append(
            "strategy_id must contain only lowercase ASCII letters, digits, and hyphens"
        )
    return errors


def _validate_channel_fields(channel: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if channel.get("bottom_profile") != "flat":
        errors.append("channel.bottom_profile must be 'flat'")
    if channel.get("path_kind") != "open_centerline":
        errors.append("channel.path_kind must be 'open_centerline'")
    if not _same_number(channel.get("width"), expected["width"]):
        errors.append("channel.width is inconsistent with validated geometry")
    if not _same_number(channel.get("depth"), expected["depth"]):
        errors.append("channel.depth is inconsistent with validated geometry")
    if not _same_number(channel.get("length"), expected["length"]):
        errors.append("channel.length must match the centerline length")
    if not _same_point(channel.get("start"), expected["start"]):
        errors.append("channel.start must be an XY point matching validated geometry")
    if not _same_point(channel.get("end"), expected["end"]):
        errors.append("channel.end must be an XY point matching validated geometry")
    return errors


def _validate_tool_contract(
    data: dict[str, Any],
    tool_fit: dict[str, Any],
    tool_type: str,
    expected: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    compatibility = data.get("tool_compatibility") or {}
    if compatibility.get("width_strategy") != tool_fit["width_strategy"]:
        errors.append("tool_compatibility.width_strategy is inconsistent with tool fit")
    if compatibility.get("width_clearing_required") != tool_fit["width_clearing_required"]:
        errors.append(
            "tool_compatibility.width_clearing_required is inconsistent with tool fit"
        )
    if not _same_number(compatibility.get("tool_diameter"), tool_fit["tool_diameter"]):
        errors.append("tool_compatibility.tool_diameter is inconsistent with operation.tool")
    if not _same_number(compatibility.get("channel_width"), expected["width"]):
        errors.append("tool_compatibility.channel_width is inconsistent with channel.width")

    operation = data.get("operation") or {}
    if operation.get("type") != OPERATION_CUT_TYPE:
        errors.append("operation.type must be 'channel_cut'")
    sequence, _intent = _width_plan(tool_fit)
    if operation.get("sequence") != sequence:
        errors.append("operation.sequence is inconsistent with tool fit")

    parameters = operation.get("parameters") or {}
    if not _same_number(parameters.get("depth"), expected["depth"]):
        errors.append("operation.parameters.depth must equal channel.depth")
    if not _same_number(parameters.get("width"), expected["width"]):
        errors.append("operation.parameters.width must equal channel.width")
    if parameters.get("notes") != DEPTH_PARAMETER_NOTES:
        errors.append("operation.parameters.notes must remain the advisory depth-pass statement")

    tool = operation.get("tool") or {}
    if tool.get("tool_type") != tool_type:
        errors.append("operation.tool.tool_type is inconsistent")
    description = tool.get("description")
    if description is not None and (not isinstance(description, str) or not description.strip()):
        errors.append("operation.tool.description must be a non-blank string when present")
    return errors


def _validate_depth_contract(
    data: dict[str, Any],
    expected: dict[str, Any],
    depth_strategy: dict[str, Any],
    recomputed: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if not _same_pass_list(depth_strategy.get("passes"), recomputed["passes"]):
        errors.append("depth_strategy.passes must match the shared depth-pass helper")
    if not _same_number(depth_strategy.get("final_depth"), expected["depth"]):
        errors.append("depth_strategy.final_depth must equal channel.depth")
    if depth_strategy.get("pass_count") != recomputed["pass_count"]:
        errors.append("depth_strategy.pass_count must match the shared depth-pass helper")
    for value in depth_strategy.get("passes") or []:
        try:
            if float(value) - float(expected["depth"]) > DEPTH_EPSILON:
                errors.append("depth_strategy passes must not exceed final channel depth")
                break
        except (TypeError, ValueError):
            errors.append("depth_strategy.passes must contain numbers")
            break
    parameters = (data.get("operation") or {}).get("parameters") or {}
    if not _same_number(parameters.get("depth_per_pass"), depth_strategy.get("maximum_pass_depth")):
        errors.append(
            "operation.parameters.depth_per_pass must equal depth_strategy.maximum_pass_depth"
        )
    safety = data.get("safety_boundary") or {}
    if not _same_number(safety.get("max_depth_inches"), expected["depth"]):
        errors.append("safety_boundary.max_depth_inches must equal channel.depth")
    return errors


def _validate_phase_contract(
    data: dict[str, Any],
    tool_fit: dict[str, Any],
    tool_type: str,
    recomputed: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    phases = data.get("strategy_phases")
    if not isinstance(phases, list) or len(phases) != 1:
        errors.append("strategy_phases must contain exactly one channel_cut phase")
        return errors
    phase = phases[0]
    if not isinstance(phase, dict):
        errors.append("strategy_phases[0] must be an object")
        return errors
    if phase.get("phase_id") != "channel_cut":
        errors.append("strategy phase must be channel_cut")
    if phase.get("order") != 1:
        errors.append("channel_cut phase order must be 1")
    _sequence, expected_intent = _width_plan(tool_fit)
    if phase.get("intent") != expected_intent:
        errors.append("strategy_phases[0].intent is inconsistent with tool fit")
    recommended = phase.get("recommended_tool") or {}
    if recommended.get("tool_type") != tool_type:
        errors.append("recommended_tool.tool_type must match operation.tool.tool_type")
    if recommended.get("width_strategy") != tool_fit["width_strategy"]:
        errors.append("recommended_tool.width_strategy is inconsistent with tool fit")
    if recommended.get("width_clearing_required") != tool_fit["width_clearing_required"]:
        errors.append("recommended_tool.width_clearing_required is inconsistent with tool fit")
    if not _same_number(recommended.get("diameter"), tool_fit["tool_diameter"]):
        errors.append("recommended_tool.diameter must match operation.tool.diameter")
    phase_depth = phase.get("depth_strategy") or {}
    if not _same_pass_list(phase_depth.get("passes"), recomputed["passes"]):
        errors.append("strategy_phases[0].depth_strategy.passes must match depth_strategy")
    return errors


def _validate_evidence_contract(
    data: dict[str, Any],
    expected: dict[str, Any],
    tool_fit: dict[str, Any],
    recomputed: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    evidence = ((data.get("review_requirements") or {}).get("evidence") or {})
    if not _present(evidence, "blank_thickness"):
        errors.append("blank_thickness is required")
        return errors
    try:
        blank_thickness = _positive(
            "review_requirements.evidence.blank_thickness",
            evidence.get("blank_thickness"),
        )
        expected_residual = compute_residual_material(
            blank_thickness, float(expected["depth"])
        )
    except TrussRodChannelError as exc:
        errors.append(str(exc))
        return errors

    if not _present(evidence, "residual_material"):
        errors.append("residual_material is required")
        return errors
    try:
        residual_material = _as_number(
            "review_requirements.evidence.residual_material",
            evidence.get("residual_material"),
        )
    except TrussRodChannelError as exc:
        errors.append(str(exc))
        return errors
    if residual_material <= DEPTH_EPSILON:
        errors.append("residual_material must be greater than zero")
    if json_number(residual_material) != json_number(expected_residual):
        errors.append(
            "residual_material must equal blank_thickness minus channel depth"
        )
    if not _same_number(evidence.get("channel_width"), expected["width"]):
        errors.append("review evidence channel_width must equal channel.width")
    if not _same_number(evidence.get("channel_depth"), expected["depth"]):
        errors.append("review evidence channel_depth must equal channel.depth")
    if not _same_number(evidence.get("tool_diameter"), tool_fit["tool_diameter"]):
        errors.append("review evidence tool_diameter must match operation.tool.diameter")
    if evidence.get("width_strategy") != tool_fit["width_strategy"]:
        errors.append("review evidence width_strategy is inconsistent with tool fit")
    if evidence.get("width_clearing_required") != tool_fit["width_clearing_required"]:
        errors.append("review evidence width_clearing_required is inconsistent with tool fit")
    if not _same_pass_list(evidence.get("passes"), recomputed["passes"]):
        errors.append("review evidence passes must match depth_strategy.passes")
    return errors


def _validate_geometry_contract(geometry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if geometry.get("dxf_file") != DXF_FILENAME:
        errors.append("geometry.dxf_file must be 'geometry.dxf'")
    if geometry.get("primary_layer") != PRIMARY_LAYER:
        errors.append("geometry.primary_layer must be 'TRUSS_ROD_CHANNEL'")
    if geometry.get("generated") is not False:
        errors.append(
            "geometry.generated must be false; dxf_file is a contract filename, not a packaged file"
        )
    return errors


def _validate_setup_contract(setup: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(setup.get("workholding"), str) or not setup["workholding"].strip():
        errors.append("setup_assumptions.workholding is required")
    if setup.get("cross_operation_scheduling") != CROSS_OPERATION_SCHEDULING:
        errors.append("setup_assumptions.cross_operation_scheduling must be 'not_specified'")
    if not isinstance(setup.get("placement_authority"), str) or not setup["placement_authority"].strip():
        errors.append("setup_assumptions.placement_authority is required")
    return errors
