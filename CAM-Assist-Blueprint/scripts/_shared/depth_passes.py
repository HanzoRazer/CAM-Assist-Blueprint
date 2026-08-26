"""Operation-agnostic depth-pass calculation.

CAM Assist uses this helper to describe how a requested final depth should be
approached. The result is a manufacturing-strategy sequence, not machine motion.

The helper knows only two numbers: final depth and maximum pass depth. It does
not know operations, tools, materials, or controllers.
"""

from __future__ import annotations

from typing import Union

Number = Union[int, float]

DEPTH_EPSILON = 1e-9


class DepthPassError(ValueError):
    """Invalid depth-pass inputs."""


def _reject_non_number(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DepthPassError(f"{name} must be a number")


def json_number(value: float) -> Number:
    """Emit a stable JSON number: ints when integral, otherwise 12-decimal float."""
    quantized = round(float(value), 12)
    rounded = round(quantized)
    if abs(quantized - rounded) <= DEPTH_EPSILON:
        return int(rounded)
    return quantized


def compute_depth_passes(
    final_depth: Number,
    maximum_pass_depth: Number,
) -> list[Number]:
    """Return cumulative depths that reach, but never exceed, final_depth.

    Examples:
        final_depth=9, maximum_pass_depth=4 -> [4, 8, 9]
        final_depth=15, maximum_pass_depth=6 -> [6, 12, 15]
        final_depth=4, maximum_pass_depth=4 -> [4]
        final_depth=3, maximum_pass_depth=4 -> [3]
    """
    _reject_non_number("final_depth", final_depth)
    _reject_non_number("maximum_pass_depth", maximum_pass_depth)

    if final_depth <= 0:
        raise DepthPassError("final_depth must be positive")
    if maximum_pass_depth <= 0:
        raise DepthPassError("maximum_pass_depth must be positive")

    passes: list[Number] = []
    remaining = float(final_depth)
    while remaining > DEPTH_EPSILON:
        step = min(float(maximum_pass_depth), remaining)
        remaining -= step
        if remaining <= DEPTH_EPSILON:
            passes.append(json_number(float(final_depth)))
            break
        current = float(final_depth) - remaining
        passes.append(json_number(current))
    return passes
