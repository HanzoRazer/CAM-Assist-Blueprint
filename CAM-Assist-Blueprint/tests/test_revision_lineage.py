"""
Tests for CAM-A18 Revision Lineage.

These tests verify that:
- Lineage files can be created and validated
- Required fields are enforced (revision_id, summary)
- Lineage integrity is enforced (unique ids, no dangling/self/cyclic supersession, a root)
- Forked lineage (multiple roots) is a warning, not a failure
- The sidecar pattern is followed (no package mutation)
- The informational authority block is present and const-true
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
CREATE_SCRIPT = SCRIPTS_DIR / "create_revision_lineage.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_revision_lineage.py"


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
        "strategy_id": "test-lineage",
        "units": "mm",
        "coordinate_frame": {"origin": "nut", "x_axis": "x", "y_axis": "y", "z_axis": "z"},
        "provenance": {"source_spec_id": "test", "cam_assist_version": "0.6.0", "created_at": "2026-06-15T00:00:00Z"},
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
        "created_at": "2026-06-15T00:00:00Z",
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


def _base(package_name="luthiers-toolbox:vcarve:synthetic-001"):
    return {
        "record_type": "cam_assist_revision_lineage",
        "record_version": "1.0.0",
        "package_reference": package_name,
        "revisions": [],
    }


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "lineage.json"
    path.write_text(json.dumps(data))
    return path


class TestCreateAndValidate:
    def test_valid_root_only_lineage(self, package, tmp_path):
        out = tmp_path / "l.json"
        code, _, _ = run_script(
            CREATE_SCRIPT, "--package", str(package),
            "--summary", "Initial review.",
            "--out", str(out),
        )
        assert code == 0
        code, stdout, _ = run_script(VALIDATE_SCRIPT, str(out))
        assert code == 0
        assert "PASS" in stdout

    def test_created_lineage_has_single_root(self, package, tmp_path):
        out = tmp_path / "l.json"
        run_script(CREATE_SCRIPT, "--package", str(package), "--out", str(out))
        data = json.loads(out.read_text())
        assert len(data["revisions"]) == 1
        assert "supersedes" not in data["revisions"][0]

    def test_valid_multi_revision_chain(self, tmp_path):
        data = _base()
        data["revisions"] = [
            {"revision_id": "rev-1", "summary": "Initial."},
            {"revision_id": "rev-2", "supersedes": "rev-1", "summary": "Reduced depth of cut."},
            {"revision_id": "rev-3", "supersedes": "rev-2", "summary": "Updated fixturing."},
        ]
        path = _write(tmp_path, data)
        code, stdout, _ = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 0
        assert "PASS" in stdout

    def test_non_federated_package_reference(self, package, tmp_path):
        out = tmp_path / "l.json"
        run_script(CREATE_SCRIPT, "--package", str(package), "--out", str(out))
        data = json.loads(out.read_text())
        assert data["package_reference"] == package.name

    def test_federated_package_reference(self, tmp_path):
        package = _make_package(tmp_path, federated=True)
        out = tmp_path / "l.json"
        run_script(CREATE_SCRIPT, "--package", str(package), "--out", str(out))
        data = json.loads(out.read_text())
        assert data["package_reference"] == "luthiers-toolbox:vcarve:synthetic-001"

    def test_revised_by_recorded(self, package, tmp_path):
        out = tmp_path / "l.json"
        run_script(
            CREATE_SCRIPT, "--package", str(package),
            "--revised-by", "Manufacturing Engineer", "--out", str(out),
        )
        data = json.loads(out.read_text())
        assert data["revisions"][0]["revised_by"] == "Manufacturing Engineer"

    def test_authority_block_is_const_true(self, package, tmp_path):
        out = tmp_path / "l.json"
        run_script(CREATE_SCRIPT, "--package", str(package), "--out", str(out))
        data = json.loads(out.read_text())
        assert data["authority"]["is_informational"] is True
        assert data["authority"]["does_not_authorize_execution"] is True
        assert data["authority"]["does_not_bypass_human_review"] is True


class TestFieldValidationFailures:
    def test_missing_revision_id(self, tmp_path):
        data = _base()
        data["revisions"] = [{"summary": "Something changed."}]
        path = _write(tmp_path, data)
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "revision_id" in stderr

    def test_missing_summary(self, tmp_path):
        data = _base()
        data["revisions"] = [{"revision_id": "rev-1"}]
        path = _write(tmp_path, data)
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "summary" in stderr

    def test_invalid_record_type(self, tmp_path):
        data = _base()
        data["record_type"] = "wrong"
        data["revisions"] = [{"revision_id": "rev-1", "summary": "x"}]
        path = _write(tmp_path, data)
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "record_type" in stderr

    def test_bad_record_version(self, tmp_path):
        data = _base()
        data["record_version"] = "1.0"
        data["revisions"] = [{"revision_id": "rev-1", "summary": "x"}]
        path = _write(tmp_path, data)
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "record_version" in stderr

    def test_missing_revisions(self, tmp_path):
        data = _base()
        del data["revisions"]
        path = _write(tmp_path, data)
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "revisions" in stderr

    def test_authority_false_fails(self, tmp_path):
        data = _base()
        data["revisions"] = [{"revision_id": "rev-1", "summary": "x"}]
        data["authority"] = {"is_informational": False}
        path = _write(tmp_path, data)
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "is_informational" in stderr

    def test_missing_file_exit_2(self, tmp_path):
        code, _, _ = run_script(VALIDATE_SCRIPT, str(tmp_path / "nope.json"))
        assert code == 2


class TestLineageIntegrity:
    def test_duplicate_revision_id_fails(self, tmp_path):
        data = _base()
        data["revisions"] = [
            {"revision_id": "rev-1", "summary": "First."},
            {"revision_id": "rev-1", "summary": "Duplicate id."},
        ]
        path = _write(tmp_path, data)
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "duplicate" in stderr.lower()

    def test_dangling_supersedes_fails(self, tmp_path):
        data = _base()
        data["revisions"] = [
            {"revision_id": "rev-1", "summary": "First."},
            {"revision_id": "rev-2", "supersedes": "rev-99", "summary": "Points nowhere."},
        ]
        path = _write(tmp_path, data)
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "unknown" in stderr.lower()

    def test_self_supersession_fails(self, tmp_path):
        data = _base()
        data["revisions"] = [{"revision_id": "rev-1", "supersedes": "rev-1", "summary": "Self."}]
        path = _write(tmp_path, data)
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "itself" in stderr.lower()

    def test_cycle_fails(self, tmp_path):
        data = _base()
        data["revisions"] = [
            {"revision_id": "rev-1", "supersedes": "rev-2", "summary": "A."},
            {"revision_id": "rev-2", "supersedes": "rev-1", "summary": "B."},
        ]
        path = _write(tmp_path, data)
        code, _, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 1
        assert "cycle" in stderr.lower()

    def test_forked_lineage_passes_with_warning(self, tmp_path):
        """Two roots (no supersedes) is permitted but flagged as a warning."""
        data = _base()
        data["revisions"] = [
            {"revision_id": "rev-1", "summary": "Root A."},
            {"revision_id": "rev-2", "summary": "Root B."},
        ]
        path = _write(tmp_path, data)
        code, stdout, _ = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 0
        assert "WARN" in stdout
        assert "fork" in stdout.lower()

    def test_empty_revisions_passes_with_warning(self, tmp_path):
        data = _base()
        data["revisions"] = []
        path = _write(tmp_path, data)
        code, stdout, _ = run_script(VALIDATE_SCRIPT, str(path))
        assert code == 0
        assert "WARN" in stdout


class TestNonMutation:
    def test_package_not_mutated(self, package, tmp_path):
        before = {p.name: p.read_bytes() for p in package.iterdir()}
        out = tmp_path / "l.json"
        run_script(CREATE_SCRIPT, "--package", str(package), "--out", str(out))
        after = {p.name: p.read_bytes() for p in package.iterdir()}
        assert before == after
