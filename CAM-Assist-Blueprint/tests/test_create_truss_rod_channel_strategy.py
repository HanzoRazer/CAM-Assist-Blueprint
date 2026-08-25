"""Process-boundary tests for the truss-rod-channel strategy creator CLI."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "scripts" / "create_truss_rod_channel_strategy.py"
EXAMPLE_INPUT = REPO_ROOT / "examples" / "operations" / "truss_rod_channel_example.json"


def run_creator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


class TestCreatorCli:
    def test_valid_input_writes_strategy(self, tmp_path):
        output = tmp_path / "strategy.json"
        result = run_creator(str(EXAMPLE_INPUT), "--out", str(output))
        assert result.returncode == 0, result.stderr
        assert "PASS" in result.stdout
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["operation_intent"]["operation_type"] == "truss_rod_channel"
        assert data["operation_intent"]["geometry_type"] == "2.5D"

    def test_quiet_prints_only_path(self, tmp_path):
        output = tmp_path / "strategy.json"
        result = run_creator(str(EXAMPLE_INPUT), "--out", str(output), "--quiet")
        assert result.returncode == 0
        assert result.stdout.strip() == str(output)

    def test_refuses_overwrite_without_force(self, tmp_path):
        output = tmp_path / "strategy.json"
        output.write_text("existing\n", encoding="utf-8")
        result = run_creator(str(EXAMPLE_INPUT), "--out", str(output))
        assert result.returncode == 1
        assert "already exists" in result.stderr

    def test_force_overwrites(self, tmp_path):
        output = tmp_path / "strategy.json"
        output.write_text("existing\n", encoding="utf-8")
        result = run_creator(str(EXAMPLE_INPUT), "--out", str(output), "--force")
        assert result.returncode == 0
        json.loads(output.read_text(encoding="utf-8"))

    def test_zero_width_exits_1(self, tmp_path):
        request = json.loads(EXAMPLE_INPUT.read_text(encoding="utf-8"))
        request["channel"]["width"] = 0
        input_path = tmp_path / "bad.json"
        input_path.write_text(json.dumps(request), encoding="utf-8")
        result = run_creator(str(input_path), "--out", str(tmp_path / "out.json"))
        assert result.returncode == 1
        assert "width" in result.stderr

    def test_oversized_tool_exits_1(self, tmp_path):
        request = json.loads(EXAMPLE_INPUT.read_text(encoding="utf-8"))
        request["tool"]["diameter"] = 0.5
        input_path = tmp_path / "bad.json"
        input_path.write_text(json.dumps(request), encoding="utf-8")
        result = run_creator(str(input_path), "--out", str(tmp_path / "out.json"))
        assert result.returncode == 1
        assert "exceeds" in result.stderr

    def test_missing_file_exits_2(self, tmp_path):
        result = run_creator(str(tmp_path / "missing.json"), "--out", str(tmp_path / "out.json"))
        assert result.returncode == 2

    def test_malformed_json_exits_2(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        result = run_creator(str(bad), "--out", str(tmp_path / "out.json"))
        assert result.returncode == 2

    def test_identical_inputs_byte_identical_output(self, tmp_path):
        first = tmp_path / "a.json"
        second = tmp_path / "b.json"
        run_creator(str(EXAMPLE_INPUT), "--out", str(first))
        run_creator(str(EXAMPLE_INPUT), "--out", str(second))
        assert first.read_bytes() == second.read_bytes()
