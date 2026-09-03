"""Review-packet dispatch for pickup_route without changing fret-slot or truss-rod text."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPTS = REPO_ROOT / "scripts"
VALID = REPO_ROOT / "examples" / "valid"
GENERATOR = SCRIPTS / "generate_review_packet.py"


def _generate(strategy_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GENERATOR), str(strategy_path), "--out", str(output_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_pickup_review_contains_cavity_evidence(tmp_path):
    strategy = VALID / "pickup_route_strategy.json"
    output = tmp_path / "review.md"
    result = _generate(strategy, output)
    assert result.returncode == 0, result.stderr
    content = output.read_text(encoding="utf-8")
    assert "Pickup Route Summary" in content
    assert "Fret Slot Summary" not in content
    assert "Truss Rod Channel Summary" not in content
    assert "Cavity Length" in content
    assert "Finishing Depth Strategy" in content
    assert "Tool Compatibility" in content
    assert "does not generate or include a DXF" in content
    assert "does not generate G-code" in content
    assert "advisory only" in content
    assert "does not repeat the roughing pass list" in content


def test_fret_slot_review_still_has_fret_slot_summary(tmp_path):
    output = tmp_path / "review.md"
    result = _generate(VALID / "fret_slot_strategy.json", output)
    assert result.returncode == 0, result.stderr
    content = output.read_text(encoding="utf-8")
    assert "Fret Slot Summary" in content
    assert "Pickup Route Summary" not in content
    assert "Truss Rod Channel Summary" not in content
    assert "Fret Count" in content
    assert "Scale Length" in content
    assert "Fretboard stock must be securely clamped" in content
    assert "Slot too shallow" in content


def test_truss_rod_review_still_has_truss_rod_summary(tmp_path):
    output = tmp_path / "review.md"
    result = _generate(VALID / "truss_rod_channel_strategy.json", output)
    assert result.returncode == 0, result.stderr
    content = output.read_text(encoding="utf-8")
    assert "Truss Rod Channel Summary" in content
    assert "Pickup Route Summary" not in content
    assert "Fret Slot Summary" not in content
    assert "Channel Width" in content
    assert "centerline_cut" in content
    assert "Neck blank must be secured against movement along the channel axis" in content
    assert "Channel too shallow" in content
