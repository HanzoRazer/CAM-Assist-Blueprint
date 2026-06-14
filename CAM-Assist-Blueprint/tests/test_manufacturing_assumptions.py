"""
Tests for CAM-A17 Manufacturing Assumptions.

These tests verify that:
- Assumptions files can be created and validated
- Required fields are enforced (category, statement)
- The sidecar pattern is followed (no package mutation)
- The informational authority block is present and const-true
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
CREATE_SCRIPT = SCRIPTS_DIR / "create_manufacturing_assumptions.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_manufacturing_assumptions.py"


def run_script(script: Path, *args) -> tuple[int, str, str]:
    """Run a script and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, str(script)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def _make_package(parent: Path, name: str = "test_pkg", federated: bool = False) -> Path:
    """Create a minimal valid strategy package."""
    package_dir = parent / name
    package_dir.mkdir(parents=True)

    strategy = {
        "strategy_version": "1.0",
        "strategy_id": "test-assumptions",
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
    if federated:
        manifest["federation"] = {
            "origin_system": "luthiers-toolbox",
            "federated_package_id": "luthiers-toolbox:vcarve:synthetic-001",
        }
    (package_dir / "manifest.json").write_text(json.dumps(manifest))
    return package_dir


@pytest.fixture
def package(tmp_path) -> Path:
    return _make_package(tmp_path)


class TestCreateAndValidate:
    def test_valid_assumptions_file(self, package, tmp_path):
        out = tmp_path / "a.json"
        code, _, _ = run_script(
            CREATE_SCRIPT, "--package", str(package),
            "--assumption", "tooling", "Tool rigidity adequate.",
            "--out", str(out),
        )
        assert code == 0
        code, stdout, _ = run_script(VALIDATE_SCRIPT, str(out))
        assert code == 0
        assert "PASS" in stdout

    def test_multiple_assumptions(self, package, tmp_path):
        out = tmp_path / "a.json"
        run_script(
            CREATE_SCRIPT, "--package", str(package),
            "--assumption", "tooling", "Tool rigidity adequate.",
            "--assumption", "material", "Cert supplied by customer.",
            "--out", str(out),
        )
        data = json.loads(out.read_text())
        assert len(data["assumptions"]) == 2
        code, _, _ = run_script(VALIDATE_SCRIPT, str(out))
        assert code == 0

    def test_non_federated_package(self, package, tmp_path):
        """A non-federated package resolves package_reference to the directory name."""
        out = tmp_path / "a.json"
        run_script(
            CREATE_SCRIPT, "--package", str(package),
            "--assumption", "tooling", "Tool rigidity adequate.",
            "--out", str(out),
        )
        data = json.loads(out.read_text())
        assert data["package_reference"] == package.name
        code, _, _ = run_script(VALIDATE_SCRIPT, str(out))
        assert code == 0

    def test_federated_package_reference(self, tmp_path):
        package = _make_package(tmp_path, federated=True)
        out = tmp_path / "a.json"
        run_script(
            CREATE_SCRIPT, "--package", str(package),
            "--assumption", "tooling", "Tool rigidity adequate.",
            "--out", str(out),
        )
        data = json.loads(out.read_text())
        assert data["package_reference"] == "luthiers-toolbox:vcarve:synthetic-001"

    def test_authority_block_is_const_true(self, package, tmp_path):
        out = tmp_path / "a.json"
        run_script(
            CREATE_SCRIPT, "--package", str(package),
            "--assumption", "tooling", "Tool rigidity adequate.",
            "--out", str(out),
        )
        data = json.loads(out.read_text())
        assert data["authority"]["is_informational"] is True
        assert data["authority"]["does_not_authorize_execution"] is True
        assert data["authority"]["does_not_bypass_human_review"] is True

    def test_create_requires_at_least_one_assumption(self, package, tmp_path):
        out = tmp_path / "a.json"
        code, _, stderr = run_script(CREATE_SCRIPT, "--package", str(package), "--out", str(out))
        assert code == 1
        assert "at least one" in stderr.lower()


class TestValidationFailures:
    def _base(self, package_name="luthiers-toolbox:vcarve:synthetic-001"):
        return {
            "record_type": "cam_assist_manufacturing_assumptions",
            "record_version": "1.0.0",
            "package_reference": package_name,
            "assumptions": [],
        }

    def test_missing_statement(self, tmp_path):
        data = self._base()
        data["assumptions"] = [{"category": "tooling"}]
        path = tmp_path / "a.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "statement" in stderr

    def test_missing_category(self, tmp_path):
        data = self._base()
        data["assumptions"] = [{"statement": "Something assumed."}]
        path = tmp_path / "a.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "category" in stderr

    def test_invalid_record_type(self, tmp_path):
        data = self._base()
        data["record_type"] = "wrong"
        data["assumptions"] = [{"category": "tooling", "statement": "x"}]
        path = tmp_path / "a.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "record_type" in stderr

    def test_authority_false_fails(self, tmp_path):
        data = self._base()
        data["assumptions"] = [{"category": "tooling", "statement": "x"}]
        data["authority"] = {"is_informational": False}
        path = tmp_path / "a.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "is_informational" in stderr

    def test_missing_file_exit_2(self, tmp_path):
        code, _, _ = run_script(VALIDATE_SCRIPT, str(tmp_path / "nope.json"))
        assert code == 2


class TestNonMutation:
    def test_package_not_mutated(self, package, tmp_path):
        before = {p.name: p.read_bytes() for p in package.iterdir()}
        out = tmp_path / "a.json"
        run_script(
            CREATE_SCRIPT, "--package", str(package),
            "--assumption", "tooling", "Tool rigidity adequate.",
            "--out", str(out),
        )
        after = {p.name: p.read_bytes() for p in package.iterdir()}
        assert before == after
