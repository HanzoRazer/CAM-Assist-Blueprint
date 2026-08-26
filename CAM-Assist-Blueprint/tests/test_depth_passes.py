"""Tests for the operation-agnostic depth-pass helper."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from _shared.depth_passes import DEPTH_EPSILON, DepthPassError, compute_depth_passes


class TestComputeDepthPasses:
    def test_single_pass_when_final_within_maximum(self):
        assert compute_depth_passes(4, 4) == [4]
        assert compute_depth_passes(3, 4) == [3]

    def test_multiple_even_passes(self):
        assert compute_depth_passes(8, 4) == [4, 8]

    def test_uneven_final_pass_does_not_overcut(self):
        assert compute_depth_passes(9, 4) == [4, 8, 9]

    def test_handoff_example_fifteen_and_six(self):
        assert compute_depth_passes(15, 6) == [6, 12, 15]

    def test_fractional_depths(self):
        assert compute_depth_passes(0.375, 0.125) == [0.125, 0.25, 0.375]

    def test_never_exceeds_final_depth(self):
        passes = compute_depth_passes(9, 4)
        assert all(p <= 9 + DEPTH_EPSILON for p in passes)
        assert passes[-1] == 9

    def test_zero_final_depth_rejected(self):
        with pytest.raises(DepthPassError, match="positive"):
            compute_depth_passes(0, 4)

    def test_negative_final_depth_rejected(self):
        with pytest.raises(DepthPassError, match="positive"):
            compute_depth_passes(-1, 4)

    def test_zero_pass_depth_rejected(self):
        with pytest.raises(DepthPassError, match="positive"):
            compute_depth_passes(4, 0)

    def test_negative_pass_depth_rejected(self):
        with pytest.raises(DepthPassError, match="positive"):
            compute_depth_passes(4, -1)

    def test_boolean_rejected(self):
        with pytest.raises(DepthPassError, match="number"):
            compute_depth_passes(True, 1)

    def test_deterministic(self):
        assert compute_depth_passes(9, 4) == compute_depth_passes(9, 4)
