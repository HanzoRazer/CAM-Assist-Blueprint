"""
Tests for CAM-A17 Risk Assessment.

These tests verify that:
- Risk assessment files can be created and validated
- overall_risk level and per-risk severity are validated
- Required per-risk fields are enforced
- The informational authority block is present and const-true
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
CREATE_SCRIPT = SCRIPTS_DIR / "create_risk_assessment.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_risk_assessment.py"


def run_script(script: Path, *args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(script)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def _make_package(parent: Path, name: str = "test_pkg") -> Path:
    package_dir = parent / name
    package_dir.mkdir(parents=True)
    strategy = {
        "strategy_version": "1.0",
        "strategy_id": "test-risk",
        "units": "mm",
        "coordinate_frame": {"origin": "nut", "x_axis": "x", "y_axis": "y", "z_axis": "z"},
        "provenance": {"source_spec_id": "test", "cam_assist_version": "0.6.0", "created_at": "2026-06-14T00:00:00Z"},
        "operation_intent": {"operation_type": "test", "target_feature": "test", "non_execution_declaration": True},
        "material_context": {"material_class": "test"},
        "safety_boundary": {"non_execution_declaration": True, "human_review_required": True, "execution_authority_claim": False},
        "approval_state": "pending",
    }
    (package_dir / "strategy.json").write_text(json.dumps(strategy))
    (package_dir / "review_packet.md").write_text("# Review Packet\n\nTest content.\n" * 50)
    manifest = {
        "manifest_version": "1.0.0",
        "package_type": "cam_assist_strategy_package",
        "operation_type": "test",
        "strategy_file": "strategy.json",
        "review_packet_file": "review_packet.md",
        "created_at": "2026-06-14T00:00:00Z",
        "authority": {
            "non_execution_declaration": True,
            "execution_authority_claim": False,
            "requires_human_review": True,
        },
    }
    (package_dir / "manifest.json").write_text(json.dumps(manifest))
    return package_dir


@pytest.fixture
def package(tmp_path) -> Path:
    return _make_package(tmp_path)


class TestCreateAndValidate:
    def test_valid_risk_file(self, package, tmp_path):
        out = tmp_path / "r.json"
        code, _, _ = run_script(
            CREATE_SCRIPT, "--package", str(package), "--overall-risk", "medium",
            "--risk", "geometry", "warning", "Thin wall may chatter.",
            "--out", str(out),
        )
        assert code == 0
        code, stdout, _ = run_script(VALIDATE_SCRIPT, str(out))
        assert code == 0
        assert "PASS" in stdout

    def test_multiple_risks(self, package, tmp_path):
        out = tmp_path / "r.json"
        run_script(
            CREATE_SCRIPT, "--package", str(package), "--overall-risk", "high",
            "--risk", "geometry", "warning", "Thin wall may chatter.",
            "--risk", "tooling", "info", "Reduce feed for softwood.",
            "--out", str(out),
        )
        data = json.loads(out.read_text())
        assert len(data["risks"]) == 2
        assert data["overall_risk"] == "high"
        code, _, _ = run_script(VALIDATE_SCRIPT, str(out))
        assert code == 0

    def test_authority_block_is_const_true(self, package, tmp_path):
        out = tmp_path / "r.json"
        run_script(
            CREATE_SCRIPT, "--package", str(package), "--overall-risk", "low",
            "--risk", "geometry", "info", "Minor.",
            "--out", str(out),
        )
        data = json.loads(out.read_text())
        assert data["authority"]["does_not_authorize_execution"] is True

    def test_create_rejects_invalid_overall_risk(self, package, tmp_path):
        out = tmp_path / "r.json"
        code, _, stderr = run_script(
            CREATE_SCRIPT, "--package", str(package), "--overall-risk", "extreme",
            "--risk", "geometry", "info", "Minor.", "--out", str(out),
        )
        # argparse choices rejects this before our code runs
        assert code == 2
        assert "extreme" in stderr or "invalid choice" in stderr


class TestValidationFailures:
    def _base(self):
        return {
            "record_type": "cam_assist_risk_assessment",
            "record_version": "1.0.0",
            "package_reference": "test_pkg",
            "overall_risk": "medium",
            "risks": [{"category": "geometry", "severity": "warning", "description": "x"}],
        }

    def test_invalid_risk_level(self, tmp_path):
        data = self._base()
        data["overall_risk"] = "extreme"
        path = tmp_path / "r.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "overall_risk" in stderr

    def test_missing_risk_description(self, tmp_path):
        data = self._base()
        data["risks"] = [{"category": "geometry", "severity": "warning"}]
        path = tmp_path / "r.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "description" in stderr

    def test_invalid_severity(self, tmp_path):
        data = self._base()
        data["risks"] = [{"category": "geometry", "severity": "catastrophic", "description": "x"}]
        path = tmp_path / "r.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "severity" in stderr

    def test_missing_overall_risk(self, tmp_path):
        data = self._base()
        del data["overall_risk"]
        path = tmp_path / "r.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "overall_risk" in stderr

    def test_partial_authority_block_fails(self, tmp_path):
        """A present authority block must declare all three flags as true."""
        data = self._base()
        data["authority"] = {"is_informational": True}  # missing the other two flags
        path = tmp_path / "r.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "does_not_authorize_execution" in stderr
        assert "does_not_bypass_human_review" in stderr


class TestNonMutation:
    def test_package_not_mutated(self, package, tmp_path):
        before = {p.name: p.read_bytes() for p in package.iterdir()}
        out = tmp_path / "r.json"
        run_script(
            CREATE_SCRIPT, "--package", str(package), "--overall-risk", "medium",
            "--risk", "geometry", "warning", "Thin wall may chatter.",
            "--out", str(out),
        )
        after = {p.name: p.read_bytes() for p in package.iterdir()}
        assert before == after
