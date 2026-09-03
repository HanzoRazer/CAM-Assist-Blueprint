"""Pickup-route manufacturing-strategy model.

Computes a reviewable two-phase strategy for a flat-bottom, constant-depth
pickup cavity. This module does not print, does not generate G-code, and does
not claim execution authority.
"""

from __future__ import annotations

import re
from typing import Any

from .depth_passes import DEPTH_EPSILON, DepthPassError, compute_depth_passes, json_number

OPERATION_TYPE = "pickup_route"
GEOMETRY_TYPE = "2.5D"
STRATEGY_COMPLEXITY = "compound"
CUT_INTENT = "pocket"
OPERATION_CUT_TYPE = "pocket_cut"
PRIMARY_LAYER = "PICKUP_ROUTE"
REFERENCE_LAYERS = ["BODY_OUTLINE"]
DXF_FILENAME = "geometry.dxf"
TARGET_FEATURE = "body"
SEQUENCE_ROUGH_THEN_FINISH = "rough_then_finish"
DEFAULT_TOOL_TYPE = "end_mill"
DEFAULT_ROUGHING_DESCRIPTION = "End mill for cavity roughing"
DEFAULT_FINISHING_DESCRIPTION = "End mill for cavity finishing"
STRATEGY_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
CROSS_OPERATION_SCHEDULING = "not_specified"
GEOMETRY_GENERATED = False
BOTTOM_PROFILE = "flat"
PHASE_ROUGH = "rough"
PHASE_FINISH = "finish"

PHASE_INTENT_ROUGH_STOCK = (
    "Rough the pickup cavity to final depth while leaving the declared "
    "finish allowance as wall stock. This is a manufacturing-strategy "
    "statement; no cutter-center offsets or machine motion are generated."
)
PHASE_INTENT_ROUGH_FINAL = (
    "Rough the pickup cavity to final depth. Finish allowance is zero, "
    "so this phase also claims final wall geometry. This is a "
    "manufacturing-strategy statement; no cutter-center offsets or "
    "machine motion are generated."
)
PHASE_INTENT_FINISH = (
    "Finish the pickup cavity walls at the already-established final "
    "depth. Roughing owns the plunge and depth progression. This is a "
    "manufacturing-strategy statement; no cutter-center offsets or "
    "machine motion are generated."
)
DEPTH_PARAMETER_NOTES = (
    "Depth-pass sequence is advisory manufacturing strategy, "
    "not machine motion. No feeds or speeds are derived from material."
)
SETUP_WORKHOLDING = (
    "Body blank must be secured against movement during cavity routing. "
    "This is an advisory manufacturing assumption, not a fixture program "
    "or work-offset assignment."
)
SETUP_PLACEMENT_AUTHORITY = (
    "Cavity coordinates are design intent relative to the strategy "
    "coordinate frame. They are not fixture zero, a work offset, or machine home."
)
TOOL_LIMITED_SHARP_NOTE = (
    "Design corner radius is 0. The cavity is tool-limited sharp: the "
    "finishing tool radius is the smallest inside corner the recommended "
    "finishing cutter can leave. Design radius 0 is preserved and is not "
    "rewritten."
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


class PickupRouteError(ValueError):
    """Invalid pickup-route strategy input."""


def _as_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PickupRouteError(f"{name} must be a number")
    return float(value)


def _positive(name: str, value: object) -> float:
    number = _as_number(name, value)
    if number <= 0:
        raise PickupRouteError(f"{name} must be positive")
    return number


def _non_negative(name: str, value: object) -> float:
    number = _as_number(name, value)
    if number < 0:
        raise PickupRouteError(f"{name} must be greater than or equal to zero")
    return number


def _point(name: str, value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        raise PickupRouteError(f"{name} must be an object with x and y")
    if "x" not in value or "y" not in value:
        raise PickupRouteError(f"{name} must include x and y")
    if "z" in value:
        raise PickupRouteError(
            f"{name} must be an XY point; depth is cavity.final_depth, not a Z coordinate"
        )
    x = _as_number(f"{name}.x", value["x"])
    y = _as_number(f"{name}.y", value["y"])
    return {"x": json_number(x), "y": json_number(y)}


def _non_blank_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PickupRouteError(f"{name} must be a non-blank string")
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


def _present(mapping: dict[str, Any], key: str) -> bool:
    return key in mapping and mapping.get(key) is not None


def _is_zero(value: float) -> bool:
    return abs(float(value)) <= DEPTH_EPSILON


def aabb_from_center(
    x: float, y: float, length: float, width: float
) -> tuple[float, float, float, float]:
    """Return (xmin, xmax, ymin, ymax) for an axis-aligned rectangle about (x, y)."""
    half_length = float(length) / 2.0
    half_width = float(width) / 2.0
    return (
        float(x) - half_length,
        float(x) + half_length,
        float(y) - half_width,
        float(y) + half_width,
    )


def aabbs_touch_or_overlap(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> bool:
    """Inclusive AABB contact: touching edges count as intersecting."""
    ax0, ax1, ay0, ay1 = left
    bx0, bx1, by0, by1 = right
    separated = (
        ax1 < bx0 - DEPTH_EPSILON
        or bx1 < ax0 - DEPTH_EPSILON
        or ay1 < by0 - DEPTH_EPSILON
        or by1 < ay0 - DEPTH_EPSILON
    )
    return not separated


def envelope_dict(bounds: tuple[float, float, float, float]) -> dict[str, Any]:
    xmin, xmax, ymin, ymax = bounds
    return {
        "xmin": json_number(xmin),
        "xmax": json_number(xmax),
        "ymin": json_number(ymin),
        "ymax": json_number(ymax),
    }


def validate_corner_radius(name: str, radius: float, length: float, width: float) -> float:
    if radius < 0:
        raise PickupRouteError(f"{name} must be greater than or equal to zero")
    limit = min(float(length), float(width)) / 2.0
    if radius - limit > DEPTH_EPSILON:
        raise PickupRouteError(
            f"{name} must not exceed half of the smaller of length and width"
        )
    return radius


def validate_mounting_tab(tab: object, index: int, cavity_bounds: tuple[float, float, float, float]) -> dict[str, Any]:
    name = f"cavity.mounting_tabs[{index}]"
    if not isinstance(tab, dict):
        raise PickupRouteError(f"{name} must be an object")
    if "x" not in tab or "y" not in tab:
        raise PickupRouteError(f"{name} must include x and y")
    if "z" in tab:
        raise PickupRouteError(
            f"{name} must be an XY center; depth is cavity.final_depth, not a Z coordinate"
        )
    x = _as_number(f"{name}.x", tab["x"])
    y = _as_number(f"{name}.y", tab["y"])
    length = _positive(f"{name}.length", tab.get("length"))
    width = _positive(f"{name}.width", tab.get("width"))
    corner_radius = _non_negative(f"{name}.corner_radius", tab.get("corner_radius"))
    validate_corner_radius(f"{name}.corner_radius", corner_radius, length, width)
    tab_bounds = aabb_from_center(x, y, length, width)
    if not aabbs_touch_or_overlap(tab_bounds, cavity_bounds):
        raise PickupRouteError(
            f"{name} must intersect or touch the main cavity envelope"
        )
    return {
        "x": json_number(x),
        "y": json_number(y),
        "length": json_number(length),
        "width": json_number(width),
        "corner_radius": json_number(corner_radius),
        "envelope": envelope_dict(tab_bounds),
    }


def validate_cavity_geometry(cavity: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(cavity, dict):
        raise PickupRouteError("cavity must be an object")
    reference_point = _point("cavity.reference_point", cavity.get("reference_point"))
    length = _positive("cavity.length", cavity.get("length"))
    width = _positive("cavity.width", cavity.get("width"))
    corner_radius = _non_negative("cavity.corner_radius", cavity.get("corner_radius"))
    validate_corner_radius("cavity.corner_radius", corner_radius, length, width)
    final_depth = _positive("cavity.final_depth", cavity.get("final_depth"))

    bounds = aabb_from_center(
        float(reference_point["x"]),
        float(reference_point["y"]),
        length,
        width,
    )
    tabs_in = cavity.get("mounting_tabs")
    if tabs_in is None:
        tabs_in = []
    if not isinstance(tabs_in, list):
        raise PickupRouteError("cavity.mounting_tabs must be an array")
    tabs = [
        validate_mounting_tab(tab, index, bounds)
        for index, tab in enumerate(tabs_in)
    ]

    return {
        "reference_point": reference_point,
        "length": json_number(length),
        "width": json_number(width),
        "corner_radius": json_number(corner_radius),
        "final_depth": json_number(final_depth),
        "mounting_tabs": tabs,
        "bottom_profile": BOTTOM_PROFILE,
        "envelope": envelope_dict(bounds),
    }


def validate_envelope_fit(tool_diameter: float, length: float, width: float, name: str) -> None:
    if tool_diameter - length > DEPTH_EPSILON:
        raise PickupRouteError(
            f"{name} exceeds cavity length; oversized tools cannot be recommended"
        )
    if tool_diameter - width > DEPTH_EPSILON:
        raise PickupRouteError(
            f"{name} exceeds cavity width; oversized tools cannot be recommended"
        )


def claims_final_walls(phase_id: str, finish_allowance: float) -> bool:
    if phase_id == PHASE_FINISH:
        return True
    return _is_zero(finish_allowance)


def validate_corner_fit(
    *,
    tool_diameter: float,
    corner_radius: float,
    claims_walls: bool,
    name: str,
) -> dict[str, Any]:
    tool_radius = float(tool_diameter) / 2.0
    if _is_zero(corner_radius):
        return {
            "applicable": False,
            "compatible": True,
            "tool_limited_sharp": True,
            "tool_radius": json_number(tool_radius),
        }
    if not claims_walls:
        return {
            "applicable": False,
            "compatible": True,
            "tool_limited_sharp": False,
            "tool_radius": json_number(tool_radius),
        }
    if tool_radius - float(corner_radius) > DEPTH_EPSILON:
        raise PickupRouteError(
            f"{name} radius exceeds the requested positive corner radius; "
            "incompatible tools cannot be recommended"
        )
    return {
        "applicable": True,
        "compatible": True,
        "tool_limited_sharp": False,
        "tool_radius": json_number(tool_radius),
    }


def build_tool_fit(
    *,
    roughing_diameter: float,
    finishing_diameter: float,
    length: float,
    width: float,
    corner_radius: float,
    finish_allowance: float,
) -> dict[str, Any]:
    validate_envelope_fit(roughing_diameter, length, width, "roughing.tool_diameter")
    validate_envelope_fit(finishing_diameter, length, width, "finishing.tool_diameter")
    rough_claims = claims_final_walls(PHASE_ROUGH, finish_allowance)
    finish_claims = claims_final_walls(PHASE_FINISH, finish_allowance)
    rough_corner = validate_corner_fit(
        tool_diameter=roughing_diameter,
        corner_radius=corner_radius,
        claims_walls=rough_claims,
        name="roughing tool",
    )
    finish_corner = validate_corner_fit(
        tool_diameter=finishing_diameter,
        corner_radius=corner_radius,
        claims_walls=finish_claims,
        name="finishing tool",
    )
    tool_limited_sharp = _is_zero(corner_radius)
    return {
        "status": "compatible",
        "recommendation": "recommended",
        "finish_allowance": json_number(finish_allowance),
        "corner_radius": json_number(corner_radius),
        "tool_limited_sharp": tool_limited_sharp,
        "roughing": {
            "tool_diameter": json_number(roughing_diameter),
            "tool_radius": rough_corner["tool_radius"],
            "envelope_fit": True,
            "corner_fit_applicable": rough_corner["applicable"],
            "corner_fit": rough_corner["compatible"],
            "claims_final_walls": rough_claims,
        },
        "finishing": {
            "tool_diameter": json_number(finishing_diameter),
            "tool_radius": finish_corner["tool_radius"],
            "envelope_fit": True,
            "corner_fit_applicable": finish_corner["applicable"],
            "corner_fit": finish_corner["compatible"],
            "claims_final_walls": finish_claims,
        },
    }


def build_depth_strategy(final_depth: float, maximum_pass_depth: float) -> dict[str, Any]:
    try:
        passes = compute_depth_passes(final_depth, maximum_pass_depth)
    except DepthPassError as exc:
        raise PickupRouteError(str(exc)) from exc
    last = float(passes[-1])
    if last - float(final_depth) > DEPTH_EPSILON:
        raise PickupRouteError("depth-pass calculation exceeded final_depth")
    if abs(last - float(final_depth)) > DEPTH_EPSILON:
        raise PickupRouteError("depth-pass calculation did not reach final_depth")
    return {
        "final_depth": json_number(final_depth),
        "maximum_pass_depth": json_number(maximum_pass_depth),
        "pass_count": len(passes),
        "passes": passes,
    }


def build_finishing_depth_strategy(final_depth: float) -> dict[str, Any]:
    return {"final_depth": json_number(final_depth)}


def resolve_optional_blank_thickness(request: dict[str, Any], units: str) -> float | None:
    """Accept optional blank_thickness; blank_thickness_inches is an inches-only alias."""
    has_canonical = _present(request, "blank_thickness")
    has_inch_alias = _present(request, "blank_thickness_inches")
    if has_inch_alias and units != "inches":
        raise PickupRouteError(
            "blank_thickness_inches is only valid when units are inches; use blank_thickness"
        )
    if has_canonical and has_inch_alias:
        canonical = _positive("blank_thickness", request.get("blank_thickness"))
        alias = _positive("blank_thickness_inches", request.get("blank_thickness_inches"))
        if not _same_number(canonical, alias):
            raise PickupRouteError(
                "blank_thickness and blank_thickness_inches must agree"
            )
        return canonical
    if has_canonical:
        return _positive("blank_thickness", request.get("blank_thickness"))
    if has_inch_alias:
        return _positive("blank_thickness", request.get("blank_thickness_inches"))
    return None


def compute_residual_material(blank_thickness: float, final_depth: float) -> float:
    residual_material = blank_thickness - final_depth
    if residual_material <= DEPTH_EPSILON:
        raise PickupRouteError(
            "blank_thickness must be greater than final_depth"
        )
    return residual_material


def resolve_tool_type(tool: dict[str, Any], name: str) -> str:
    if not _present(tool, "tool_type"):
        return DEFAULT_TOOL_TYPE
    return _non_blank_string(f"{name}.tool_type", tool.get("tool_type"))


def resolve_tool_description(tool: dict[str, Any], name: str, default: str) -> str:
    if not _present(tool, "description"):
        return default
    return _non_blank_string(f"{name}.description", tool.get("description"))


def _phase_tool(
    *,
    tool_type: str,
    diameter: float,
    description: str,
    claims_walls: bool,
    corner: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "recommended",
        "compatibility": "compatible",
        "reference_type": "dimension_spec",
        "tool_type": tool_type,
        "diameter": json_number(diameter),
        "description": description,
        "claims_final_walls": claims_walls,
        "corner_fit_applicable": corner["corner_fit_applicable"],
        "corner_fit": corner["corner_fit"],
    }


def build_review_requirements(
    *,
    cavity: dict[str, Any],
    tool_fit: dict[str, Any],
    depth_strategy: dict[str, Any],
    finish_allowance: float,
    residual_material: float | None,
    blank_thickness: float | None,
    unresolved: list[str],
) -> dict[str, Any]:
    items = [
        "Cavity center, length, and width match the intended pickup location.",
        "Corner radius matches the intended cavity corners, including tool-limited-sharp when radius is 0.",
        "Final depth matches the intended cavity and does not overcut the blank.",
        "Mounting tabs, when present, contact the main cavity envelope.",
        "Roughing and finishing cutters both fit the cavity envelope.",
        "Cutters that claim final wall geometry satisfy a positive corner-radius constraint.",
        "Finish allowance is wall stock only and is understood by the operator.",
        "Depth-pass sequence reaches final depth without overcutting.",
        "This package is advisory only and does not authorize machine execution.",
    ]
    evidence: dict[str, Any] = {
        "cavity_center": cavity["reference_point"],
        "cavity_length": cavity["length"],
        "cavity_width": cavity["width"],
        "corner_radius": cavity["corner_radius"],
        "final_depth": cavity["final_depth"],
        "mounting_tab_count": len(cavity["mounting_tabs"]),
        "mounting_tabs": cavity["mounting_tabs"],
        "roughing_tool_diameter": tool_fit["roughing"]["tool_diameter"],
        "finishing_tool_diameter": tool_fit["finishing"]["tool_diameter"],
        "finishing_tool_radius": tool_fit["finishing"]["tool_radius"],
        "finish_allowance": json_number(finish_allowance),
        "roughing_claims_final_walls": tool_fit["roughing"]["claims_final_walls"],
        "tool_limited_sharp": tool_fit["tool_limited_sharp"],
        "tool_compatibility": tool_fit["status"],
        "pass_count": depth_strategy["pass_count"],
        "passes": depth_strategy["passes"],
    }
    if tool_fit["tool_limited_sharp"]:
        evidence["tool_limited_sharp_note"] = TOOL_LIMITED_SHARP_NOTE
    if blank_thickness is not None:
        evidence["blank_thickness"] = json_number(blank_thickness)
    if residual_material is not None:
        evidence["residual_material"] = json_number(residual_material)
    return {
        "items": items,
        "evidence": evidence,
        "unresolved_assumptions": list(unresolved),
    }


def build_pickup_route_strategy(request: dict[str, Any], cam_assist_version: str) -> dict[str, Any]:
    """Build a complete A2 strategy document from a pickup-route request."""
    if not isinstance(request, dict):
        raise PickupRouteError("request must be a JSON object")

    operation_type = request.get("operation_type")
    if operation_type != OPERATION_TYPE:
        raise PickupRouteError(f"operation_type must be '{OPERATION_TYPE}'")

    strategy_id = _non_blank_string("strategy_id", request.get("strategy_id"))
    if STRATEGY_ID_PATTERN.fullmatch(strategy_id) is None:
        raise PickupRouteError(
            "strategy_id must contain only lowercase ASCII letters, digits, and hyphens"
        )

    units = request.get("units", "inches")
    if units not in ("inches", "mm"):
        raise PickupRouteError("units must be 'inches' or 'mm'")

    coordinate_frame = request.get("coordinate_frame")
    if not isinstance(coordinate_frame, dict):
        raise PickupRouteError("coordinate_frame must be an object")
    for field in ("origin", "x_axis", "y_axis"):
        if field not in coordinate_frame:
            raise PickupRouteError(f"coordinate_frame.{field} is required")

    material_context = request.get("material_context")
    if not isinstance(material_context, dict) or "material_class" not in material_context:
        raise PickupRouteError("material_context.material_class is required")

    cavity = validate_cavity_geometry(request.get("cavity") or {})

    roughing = request.get("roughing")
    if not isinstance(roughing, dict):
        raise PickupRouteError("roughing must be an object")
    finishing = request.get("finishing")
    if not isinstance(finishing, dict):
        raise PickupRouteError("finishing must be an object")

    roughing_diameter = _positive("roughing.tool_diameter", roughing.get("tool_diameter"))
    finishing_diameter = _positive("finishing.tool_diameter", finishing.get("tool_diameter"))
    maximum_pass_depth = _positive(
        "roughing.maximum_pass_depth", roughing.get("maximum_pass_depth")
    )
    finish_allowance = _non_negative(
        "roughing.finish_allowance", roughing.get("finish_allowance")
    )

    tool_fit = build_tool_fit(
        roughing_diameter=roughing_diameter,
        finishing_diameter=finishing_diameter,
        length=float(cavity["length"]),
        width=float(cavity["width"]),
        corner_radius=float(cavity["corner_radius"]),
        finish_allowance=finish_allowance,
    )
    depth_strategy = build_depth_strategy(float(cavity["final_depth"]), maximum_pass_depth)
    finishing_depth_strategy = build_finishing_depth_strategy(float(cavity["final_depth"]))

    unresolved: list[str] = []
    blank_thickness = resolve_optional_blank_thickness(request, units)
    residual_material = None
    if blank_thickness is not None:
        residual_material = compute_residual_material(
            blank_thickness, float(cavity["final_depth"])
        )

    provenance_in = request.get("provenance") or {}
    if not isinstance(provenance_in, dict):
        raise PickupRouteError("provenance must be an object")
    created_at = provenance_in.get("created_at")
    if not isinstance(created_at, str) or not created_at.strip():
        raise PickupRouteError(
            "provenance.created_at is required so strategy serialization is deterministic"
        )

    source_spec_id = provenance_in.get("source_spec_id")
    created_by = provenance_in.get("created_by", "cam-assist-blueprint")

    review_requirements = build_review_requirements(
        cavity=cavity,
        tool_fit=tool_fit,
        depth_strategy=depth_strategy,
        finish_allowance=finish_allowance,
        residual_material=residual_material,
        blank_thickness=blank_thickness,
        unresolved=unresolved,
    )

    setup_assumptions: dict[str, Any] = {
        "workholding": SETUP_WORKHOLDING,
        "cross_operation_scheduling": CROSS_OPERATION_SCHEDULING,
        "placement_authority": SETUP_PLACEMENT_AUTHORITY,
    }

    roughing_type = resolve_tool_type(roughing, "roughing")
    finishing_type = resolve_tool_type(finishing, "finishing")
    roughing_description = resolve_tool_description(
        roughing, "roughing", DEFAULT_ROUGHING_DESCRIPTION
    )
    finishing_description = resolve_tool_description(
        finishing, "finishing", DEFAULT_FINISHING_DESCRIPTION
    )
    rough_claims = tool_fit["roughing"]["claims_final_walls"]
    rough_intent = PHASE_INTENT_ROUGH_FINAL if rough_claims else PHASE_INTENT_ROUGH_STOCK

    strategy_phases = [
        {
            "phase_id": PHASE_ROUGH,
            "order": 1,
            "intent": rough_intent,
            "recommended_tool": _phase_tool(
                tool_type=roughing_type,
                diameter=roughing_diameter,
                description=roughing_description,
                claims_walls=rough_claims,
                corner=tool_fit["roughing"],
            ),
            "depth_strategy": depth_strategy,
        },
        {
            "phase_id": PHASE_FINISH,
            "order": 2,
            "intent": PHASE_INTENT_FINISH,
            "recommended_tool": _phase_tool(
                tool_type=finishing_type,
                diameter=finishing_diameter,
                description=finishing_description,
                claims_walls=True,
                corner=tool_fit["finishing"],
            ),
            "depth_strategy": finishing_depth_strategy,
        },
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
            "max_depth_inches": json_number(float(cavity["final_depth"])),
            "tool_diameter_inches": json_number(finishing_diameter),
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
                "tool_type": finishing_type,
                "diameter": json_number(finishing_diameter),
                "description": finishing_description,
            },
            "parameters": {
                "length": json_number(float(cavity["length"])),
                "width": json_number(float(cavity["width"])),
                "depth": json_number(float(cavity["final_depth"])),
                "corner_radius": json_number(float(cavity["corner_radius"])),
                "finish_allowance": json_number(finish_allowance),
                "depth_per_pass": json_number(maximum_pass_depth),
                "notes": DEPTH_PARAMETER_NOTES,
            },
            "sequence": SEQUENCE_ROUGH_THEN_FINISH,
        },
        "cavity": cavity,
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
            raise PickupRouteError(
                f"strategy must not assert machine authority token '{token}'"
            )


def validate_pickup_route_strategy_data(data: dict[str, Any]) -> list[str]:
    """Semantic checks for an already-assembled pickup-route strategy."""
    errors: list[str] = []
    intent = data.get("operation_intent") or {}
    if intent.get("operation_type") != OPERATION_TYPE:
        return errors
    errors.extend(_validate_identity(intent, data.get("strategy_id")))

    cavity = data.get("cavity")
    if not isinstance(cavity, dict):
        errors.append("cavity object is required for pickup_route")
        return errors
    try:
        expected = validate_cavity_geometry(cavity)
    except PickupRouteError as exc:
        errors.append(str(exc))
        return errors
    errors.extend(_validate_cavity_fields(cavity, expected))

    try:
        roughing_diameter, finishing_diameter, finish_allowance, maximum_pass_depth = (
            _extract_tooling(data)
        )
        tool_fit = build_tool_fit(
            roughing_diameter=roughing_diameter,
            finishing_diameter=finishing_diameter,
            length=float(expected["length"]),
            width=float(expected["width"]),
            corner_radius=float(expected["corner_radius"]),
            finish_allowance=finish_allowance,
        )
        finishing_type = _non_blank_string(
            "operation.tool.tool_type",
            ((data.get("operation") or {}).get("tool") or {}).get("tool_type"),
        )
        roughing_type = _non_blank_string(
            "strategy_phases[0].recommended_tool.tool_type",
            (((data.get("strategy_phases") or [{}])[0] or {}).get("recommended_tool") or {}).get(
                "tool_type"
            ),
        )
    except PickupRouteError as exc:
        errors.append(str(exc))
        return errors
    except (IndexError, TypeError):
        errors.append("strategy_phases must contain rough and finish phases")
        return errors

    errors.extend(
        _validate_tool_contract(data, tool_fit, finishing_type, expected, finish_allowance)
    )

    depth_strategy = data.get("depth_strategy")
    if not isinstance(depth_strategy, dict):
        errors.append("depth_strategy is required for pickup_route")
        return errors
    try:
        recomputed = build_depth_strategy(float(expected["final_depth"]), maximum_pass_depth)
    except PickupRouteError as exc:
        errors.append(str(exc))
        return errors
    errors.extend(_validate_depth_contract(data, expected, depth_strategy, recomputed))
    errors.extend(
        _validate_phase_contract(
            data, tool_fit, roughing_type, finishing_type, recomputed, expected
        )
    )
    errors.extend(_validate_evidence_contract(data, expected, tool_fit, recomputed))
    errors.extend(_validate_geometry_contract(data.get("geometry") or {}))
    errors.extend(_validate_setup_contract(data.get("setup_assumptions") or {}))
    return errors


def _extract_tooling(data: dict[str, Any]) -> tuple[float, float, float, float]:
    phases = data.get("strategy_phases")
    if not isinstance(phases, list) or len(phases) != 2:
        raise PickupRouteError("strategy_phases must contain exactly two phases")
    rough_tool = (phases[0] or {}).get("recommended_tool") or {}
    finish_tool = ((data.get("operation") or {}).get("tool") or {})
    parameters = (data.get("operation") or {}).get("parameters") or {}
    depth_strategy = data.get("depth_strategy") or {}
    roughing_diameter = _positive(
        "strategy_phases[0].recommended_tool.diameter", rough_tool.get("diameter")
    )
    finishing_diameter = _positive("operation.tool.diameter", finish_tool.get("diameter"))
    finish_allowance = _non_negative(
        "operation.parameters.finish_allowance", parameters.get("finish_allowance")
    )
    maximum_pass_depth = _positive(
        "depth_strategy.maximum_pass_depth", depth_strategy.get("maximum_pass_depth")
    )
    return roughing_diameter, finishing_diameter, finish_allowance, maximum_pass_depth


def _validate_identity(intent: dict[str, Any], strategy_id: object) -> list[str]:
    errors: list[str] = []
    if intent.get("geometry_type") != GEOMETRY_TYPE:
        errors.append("operation_intent.geometry_type must be '2.5D'")
    if intent.get("strategy_complexity") != STRATEGY_COMPLEXITY:
        errors.append("operation_intent.strategy_complexity must be 'compound'")
    if intent.get("cut_intent") != CUT_INTENT:
        errors.append("operation_intent.cut_intent must be 'pocket'")
    if not isinstance(strategy_id, str) or STRATEGY_ID_PATTERN.fullmatch(strategy_id) is None:
        errors.append(
            "strategy_id must contain only lowercase ASCII letters, digits, and hyphens"
        )
    return errors


def _validate_cavity_fields(cavity: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if cavity.get("bottom_profile") != BOTTOM_PROFILE:
        errors.append("cavity.bottom_profile must be 'flat'")
    if not _same_number(cavity.get("length"), expected["length"]):
        errors.append("cavity.length is inconsistent with validated geometry")
    if not _same_number(cavity.get("width"), expected["width"]):
        errors.append("cavity.width is inconsistent with validated geometry")
    if not _same_number(cavity.get("corner_radius"), expected["corner_radius"]):
        errors.append("cavity.corner_radius is inconsistent with validated geometry")
    if not _same_number(cavity.get("final_depth"), expected["final_depth"]):
        errors.append("cavity.final_depth is inconsistent with validated geometry")
    if not _same_point(cavity.get("reference_point"), expected["reference_point"]):
        errors.append("cavity.reference_point must be the cavity-center XY point")
    if not isinstance(cavity.get("mounting_tabs"), list):
        errors.append("cavity.mounting_tabs must be an array")
    elif len(cavity["mounting_tabs"]) != len(expected["mounting_tabs"]):
        errors.append("cavity.mounting_tabs is inconsistent with validated geometry")
    return errors


def _validate_tool_contract(
    data: dict[str, Any],
    tool_fit: dict[str, Any],
    finishing_type: str,
    expected: dict[str, Any],
    finish_allowance: float,
) -> list[str]:
    errors: list[str] = []
    compatibility = data.get("tool_compatibility") or {}
    if compatibility.get("status") != tool_fit["status"]:
        errors.append("tool_compatibility.status is inconsistent with tool fit")
    if compatibility.get("tool_limited_sharp") != tool_fit["tool_limited_sharp"]:
        errors.append("tool_compatibility.tool_limited_sharp is inconsistent with corner radius")
    if not _same_number(compatibility.get("finish_allowance"), tool_fit["finish_allowance"]):
        errors.append("tool_compatibility.finish_allowance is inconsistent")
    if not _same_number(compatibility.get("corner_radius"), expected["corner_radius"]):
        errors.append("tool_compatibility.corner_radius is inconsistent with cavity.corner_radius")

    for phase_name in ("roughing", "finishing"):
        actual = compatibility.get(phase_name) or {}
        expected_phase = tool_fit[phase_name]
        if actual.get("claims_final_walls") != expected_phase["claims_final_walls"]:
            errors.append(
                f"tool_compatibility.{phase_name}.claims_final_walls is inconsistent"
            )
        if actual.get("corner_fit_applicable") != expected_phase["corner_fit_applicable"]:
            errors.append(
                f"tool_compatibility.{phase_name}.corner_fit_applicable is inconsistent"
            )
        if not _same_number(actual.get("tool_diameter"), expected_phase["tool_diameter"]):
            errors.append(
                f"tool_compatibility.{phase_name}.tool_diameter is inconsistent"
            )

    operation = data.get("operation") or {}
    if operation.get("type") != OPERATION_CUT_TYPE:
        errors.append("operation.type must be 'pocket_cut'")
    if operation.get("sequence") != SEQUENCE_ROUGH_THEN_FINISH:
        errors.append("operation.sequence must be 'rough_then_finish'")

    parameters = operation.get("parameters") or {}
    if not _same_number(parameters.get("depth"), expected["final_depth"]):
        errors.append("operation.parameters.depth must equal cavity.final_depth")
    if not _same_number(parameters.get("length"), expected["length"]):
        errors.append("operation.parameters.length must equal cavity.length")
    if not _same_number(parameters.get("width"), expected["width"]):
        errors.append("operation.parameters.width must equal cavity.width")
    if not _same_number(parameters.get("corner_radius"), expected["corner_radius"]):
        errors.append("operation.parameters.corner_radius must equal cavity.corner_radius")
    if not _same_number(parameters.get("finish_allowance"), finish_allowance):
        errors.append("operation.parameters.finish_allowance is inconsistent")
    if parameters.get("notes") != DEPTH_PARAMETER_NOTES:
        errors.append("operation.parameters.notes must remain the advisory depth-pass statement")

    tool = operation.get("tool") or {}
    if tool.get("tool_type") != finishing_type:
        errors.append("operation.tool.tool_type is inconsistent")
    if not _same_number(tool.get("diameter"), tool_fit["finishing"]["tool_diameter"]):
        errors.append("operation.tool.diameter must equal the finishing tool diameter")
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
    if not _same_number(depth_strategy.get("final_depth"), expected["final_depth"]):
        errors.append("depth_strategy.final_depth must equal cavity.final_depth")
    if depth_strategy.get("pass_count") != recomputed["pass_count"]:
        errors.append("depth_strategy.pass_count must match the shared depth-pass helper")
    for value in depth_strategy.get("passes") or []:
        try:
            if float(value) - float(expected["final_depth"]) > DEPTH_EPSILON:
                errors.append("depth_strategy passes must not exceed final cavity depth")
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
    if not _same_number(safety.get("max_depth_inches"), expected["final_depth"]):
        errors.append("safety_boundary.max_depth_inches must equal cavity.final_depth")
    return errors


def _validate_phase_contract(
    data: dict[str, Any],
    tool_fit: dict[str, Any],
    roughing_type: str,
    finishing_type: str,
    recomputed: dict[str, Any],
    expected: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    phases = data.get("strategy_phases")
    if not isinstance(phases, list) or len(phases) != 2:
        errors.append("strategy_phases must contain exactly two phases: rough then finish")
        return errors

    rough, finish = phases[0], phases[1]
    if not isinstance(rough, dict) or not isinstance(finish, dict):
        errors.append("strategy_phases entries must be objects")
        return errors

    if rough.get("phase_id") != PHASE_ROUGH:
        errors.append("strategy_phases[0].phase_id must be 'rough'")
    if rough.get("order") != 1:
        errors.append("rough phase order must be 1")
    expected_rough_intent = (
        PHASE_INTENT_ROUGH_FINAL
        if tool_fit["roughing"]["claims_final_walls"]
        else PHASE_INTENT_ROUGH_STOCK
    )
    if rough.get("intent") != expected_rough_intent:
        errors.append("strategy_phases[0].intent is inconsistent with finish allowance")
    rough_tool = rough.get("recommended_tool") or {}
    if rough_tool.get("tool_type") != roughing_type:
        errors.append("rough recommended_tool.tool_type is inconsistent")
    if not _same_number(rough_tool.get("diameter"), tool_fit["roughing"]["tool_diameter"]):
        errors.append("rough recommended_tool.diameter must match the roughing cutter")
    if rough_tool.get("claims_final_walls") != tool_fit["roughing"]["claims_final_walls"]:
        errors.append("rough recommended_tool.claims_final_walls is inconsistent")
    rough_depth = rough.get("depth_strategy") or {}
    if not _same_pass_list(rough_depth.get("passes"), recomputed["passes"]):
        errors.append("strategy_phases[0].depth_strategy.passes must match depth_strategy")

    if finish.get("phase_id") != PHASE_FINISH:
        errors.append("strategy_phases[1].phase_id must be 'finish'")
    if finish.get("order") != 2:
        errors.append("finish phase order must be 2")
    if finish.get("intent") != PHASE_INTENT_FINISH:
        errors.append("strategy_phases[1].intent is inconsistent")
    finish_tool = finish.get("recommended_tool") or {}
    if finish_tool.get("tool_type") != finishing_type:
        errors.append("finish recommended_tool.tool_type must match operation.tool.tool_type")
    if not _same_number(finish_tool.get("diameter"), tool_fit["finishing"]["tool_diameter"]):
        errors.append("finish recommended_tool.diameter must match operation.tool.diameter")
    if finish_tool.get("claims_final_walls") is not True:
        errors.append("finish recommended_tool.claims_final_walls must be true")

    finish_depth = finish.get("depth_strategy")
    if not isinstance(finish_depth, dict):
        errors.append("strategy_phases[1].depth_strategy is required")
    else:
        extra = set(finish_depth.keys()) - {"final_depth"}
        if extra:
            errors.append(
                "finishing depth_strategy must contain only final_depth"
            )
        if not _same_number(finish_depth.get("final_depth"), expected["final_depth"]):
            errors.append(
                "finishing depth_strategy.final_depth must equal cavity.final_depth"
            )
    return errors


def _validate_evidence_contract(
    data: dict[str, Any],
    expected: dict[str, Any],
    tool_fit: dict[str, Any],
    recomputed: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    evidence = ((data.get("review_requirements") or {}).get("evidence") or {})
    if not _same_number(evidence.get("cavity_length"), expected["length"]):
        errors.append("review evidence cavity_length must equal cavity.length")
    if not _same_number(evidence.get("cavity_width"), expected["width"]):
        errors.append("review evidence cavity_width must equal cavity.width")
    if not _same_number(evidence.get("corner_radius"), expected["corner_radius"]):
        errors.append("review evidence corner_radius must equal cavity.corner_radius")
    if not _same_number(evidence.get("final_depth"), expected["final_depth"]):
        errors.append("review evidence final_depth must equal cavity.final_depth")
    if not _same_point(evidence.get("cavity_center"), expected["reference_point"]):
        errors.append("review evidence cavity_center must equal cavity.reference_point")
    if not _same_number(evidence.get("roughing_tool_diameter"), tool_fit["roughing"]["tool_diameter"]):
        errors.append("review evidence roughing_tool_diameter is inconsistent")
    if not _same_number(evidence.get("finishing_tool_diameter"), tool_fit["finishing"]["tool_diameter"]):
        errors.append("review evidence finishing_tool_diameter is inconsistent")
    if not _same_number(evidence.get("finishing_tool_radius"), tool_fit["finishing"]["tool_radius"]):
        errors.append("review evidence finishing_tool_radius is inconsistent")
    if not _same_number(evidence.get("finish_allowance"), tool_fit["finish_allowance"]):
        errors.append("review evidence finish_allowance is inconsistent")
    if evidence.get("tool_limited_sharp") != tool_fit["tool_limited_sharp"]:
        errors.append("review evidence tool_limited_sharp is inconsistent")
    if evidence.get("roughing_claims_final_walls") != tool_fit["roughing"]["claims_final_walls"]:
        errors.append("review evidence roughing_claims_final_walls is inconsistent")
    if not _same_pass_list(evidence.get("passes"), recomputed["passes"]):
        errors.append("review evidence passes must match depth_strategy.passes")

    has_blank = _present(evidence, "blank_thickness")
    has_residual = _present(evidence, "residual_material")
    if has_blank or has_residual:
        if not has_blank or not has_residual:
            errors.append(
                "blank_thickness and residual_material must both be present when residual is surfaced"
            )
            return errors
        try:
            blank_thickness = _positive(
                "review_requirements.evidence.blank_thickness",
                evidence.get("blank_thickness"),
            )
            expected_residual = compute_residual_material(
                blank_thickness, float(expected["final_depth"])
            )
            residual_material = _as_number(
                "review_requirements.evidence.residual_material",
                evidence.get("residual_material"),
            )
        except PickupRouteError as exc:
            errors.append(str(exc))
            return errors
        if json_number(residual_material) != json_number(expected_residual):
            errors.append(
                "residual_material must equal blank_thickness minus final_depth"
            )
    return errors


def _validate_geometry_contract(geometry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if geometry.get("dxf_file") != DXF_FILENAME:
        errors.append("geometry.dxf_file must be 'geometry.dxf'")
    if geometry.get("primary_layer") != PRIMARY_LAYER:
        errors.append("geometry.primary_layer must be 'PICKUP_ROUTE'")
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
