"""
Tests for CAM-A17 Manufacturing Decision Records and traceability inspection.

These tests verify that:
- Decision records can be created and validated
- The decision value is validated
- Assumptions / risk sidecars can be linked (referenced, not mutated)
- The inspector detects traceability sidecars (explicit flags + convention)
- Missing sidecars are handled safely
- Packages are never mutated and the non-execution invariant is preserved
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
CREATE_SCRIPT = SCRIPTS_DIR / "create_manufacturing_decision_record.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_manufacturing_decision_record.py"
INSPECT_SCRIPT = SCRIPTS_DIR / "inspect_strategy_package.py"
CREATE_ASSUMPTIONS = SCRIPTS_DIR / "create_manufacturing_assumptions.py"
CREATE_RISK = SCRIPTS_DIR / "create_risk_assessment.py"


def run_script(script: Path, *args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(script)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def _make_package(parent: Path, name: str = "test_pkg") -> Path:
    package_dir = parent / name
    package_dir.mkdir(parents=True)
    strategy = {
        "strategy_version": "1.0",
        "strategy_id": "test-mdr",
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


def _create_mdr(package, out, decision="approved", extra=()):
    return run_script(
        CREATE_SCRIPT, "--package", str(package),
        "--decision", decision,
        "--prepared-by", "Manufacturing Engineer",
        "--reviewed-by", "Senior Reviewer",
        "--rationale", "Reviewed assumptions and risks.",
        "--out", str(out), *extra,
    )


class TestCreateAndValidate:
    def test_valid_decision_record(self, package, tmp_path):
        out = tmp_path / "d.json"
        code, _, _ = _create_mdr(package, out)
        assert code == 0
        code, stdout, _ = run_script(VALIDATE_SCRIPT, str(out))
        assert code == 0
        assert "PASS" in stdout

    def test_linked_assumptions_file(self, package, tmp_path):
        out = tmp_path / "d.json"
        _create_mdr(package, out, extra=("--assumptions-file", "traceability/test_pkg_assumptions.json"))
        data = json.loads(out.read_text())
        assert data["assumptions_file"] == "traceability/test_pkg_assumptions.json"
        code, _, _ = run_script(VALIDATE_SCRIPT, str(out))
        assert code == 0

    def test_linked_risk_file(self, package, tmp_path):
        out = tmp_path / "d.json"
        _create_mdr(package, out, extra=("--risk-file", "traceability/test_pkg_risk.json"))
        data = json.loads(out.read_text())
        assert data["risk_file"] == "traceability/test_pkg_risk.json"
        code, _, _ = run_script(VALIDATE_SCRIPT, str(out))
        assert code == 0

    def test_authority_block_is_const_true(self, package, tmp_path):
        out = tmp_path / "d.json"
        _create_mdr(package, out)
        data = json.loads(out.read_text())
        assert data["authority"]["does_not_authorize_execution"] is True
        assert data["authority"]["does_not_bypass_human_review"] is True


class TestValidationFailures:
    def _base(self):
        return {
            "record_type": "cam_assist_manufacturing_decision_record",
            "record_version": "1.0.0",
            "package_reference": "test_pkg",
            "prepared_by": "ME",
            "reviewed_by": "SR",
            "decision": "approved",
            "rationale": "ok",
        }

    def test_invalid_decision_value(self, tmp_path):
        data = self._base()
        data["decision"] = "maybe"
        path = tmp_path / "d.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "decision" in stderr

    def test_missing_rationale(self, tmp_path):
        data = self._base()
        del data["rationale"]
        path = tmp_path / "d.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "rationale" in stderr

    def test_partial_authority_block_fails(self, tmp_path):
        """A present authority block must declare all three flags as true."""
        data = self._base()
        data["authority"] = {"is_informational": True}  # missing the other two flags
        path = tmp_path / "d.json"
        path.write_text(json.dumps(data))
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "does_not_authorize_execution" in stderr
        assert "does_not_bypass_human_review" in stderr

    def test_create_rejects_invalid_decision(self, package, tmp_path):
        out = tmp_path / "d.json"
        code, _, stderr = _create_mdr(package, out, decision="maybe")
        # argparse choices rejects before our code runs
        assert code == 2
        assert "maybe" in stderr or "invalid choice" in stderr


class TestTraceabilityInspection:
    def _seed_sidecars(self, package):
        """Create all three sidecars at their conventional locations (default --out)."""
        run_script(
            CREATE_ASSUMPTIONS, "--package", str(package),
            "--assumption", "tooling", "Tool rigidity adequate.",
        )
        run_script(
            CREATE_RISK, "--package", str(package), "--overall-risk", "medium",
            "--risk", "geometry", "warning", "Thin wall may chatter.",
        )
        run_script(
            CREATE_SCRIPT, "--package", str(package),
            "--decision", "approved", "--prepared-by", "ME",
            "--reviewed-by", "SR", "--rationale", "ok",
        )

    def test_inspector_detects_sidecars(self, package):
        self._seed_sidecars(package)
        code, stdout, _ = run_script(INSPECT_SCRIPT, str(package))
        assert code == 0
        assert "Traceability:" in stdout
        assert "assumptions: present" in stdout
        assert "risk assessment: present" in stdout
        assert "decision record: present" in stdout

    def test_missing_sidecars_handled_safely(self, package):
        code, stdout, _ = run_script(INSPECT_SCRIPT, str(package))
        assert code == 0
        assert "Traceability:" in stdout
        assert "not declared" in stdout

    def test_explicit_flag_overrides_convention(self, package, tmp_path):
        out = tmp_path / "explicit_assumptions.json"
        run_script(
            CREATE_ASSUMPTIONS, "--package", str(package),
            "--assumption", "tooling", "Tool rigidity adequate.",
            "--out", str(out),
        )
        code, stdout, _ = run_script(INSPECT_SCRIPT, str(package), "--assumptions", str(out))
        assert code == 0
        assert "assumptions: present" in stdout
        # risk + decision were not created, so they remain absent
        assert "risk assessment: not declared" in stdout

    def test_inspector_json_includes_traceability(self, package):
        self._seed_sidecars(package)
        code, stdout, _ = run_script(INSPECT_SCRIPT, str(package), "--json")
        assert code == 0
        data = json.loads(stdout)
        assert data["traceability"]["assumptions"]["present"] is True
        assert data["traceability"]["decision_record"]["present"] is True

    def test_package_not_mutated(self, package):
        before = {p.name: p.read_bytes() for p in package.iterdir()}
        self._seed_sidecars(package)
        run_script(INSPECT_SCRIPT, str(package))
        after = {p.name: p.read_bytes() for p in package.iterdir()}
        assert before == after

    def test_non_execution_invariant_preserved(self, package):
        self._seed_sidecars(package)
        code, stdout, _ = run_script(INSPECT_SCRIPT, str(package))
        assert code == 0
        assert "No machine execution authority is present." in stdout
