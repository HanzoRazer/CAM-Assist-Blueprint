"""
Tests for CAM-A16 Federated Review Annotations.

These tests verify that:
- Annotation files can be created and validated
- Annotations follow the sidecar pattern (no package mutation)
- Authority constraints are enforced
- Annotations integrate with inspection and review decisions
"""

import json
import pytest
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

CREATE_SCRIPT = SCRIPTS_DIR / "create_review_annotations.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_review_annotations.py"
INSPECT_SCRIPT = SCRIPTS_DIR / "inspect_strategy_package.py"
RECORD_SCRIPT = SCRIPTS_DIR / "record_review_decision.py"


def run_script(script: Path, *args) -> tuple[int, str, str]:
    """Run a script and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, str(script)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def valid_package(tmp_path) -> Path:
    """Create a minimal valid package for annotation tests."""
    package_dir = tmp_path / "test_package"
    package_dir.mkdir()

    strategy = {
        "strategy_version": "1.0",
        "strategy_id": "test-annotation",
        "units": "mm",
        "coordinate_frame": {"origin": "nut", "x_axis": "x", "y_axis": "y", "z_axis": "z"},
        "provenance": {"source_spec_id": "test", "cam_assist_version": "0.5.0", "created_at": "2026-05-28T00:00:00Z"},
        "operation_intent": {"operation_type": "test", "target_feature": "test", "non_execution_declaration": True},
        "material_context": {"material_class": "test"},
        "safety_boundary": {"non_execution_declaration": True, "human_review_required": True, "execution_authority_claim": False},
        "approval_state": "pending",
    }
    (package_dir / "strategy.json").write_text(json.dumps(strategy))
    (package_dir / "review_packet.md").write_text("# Review Packet\n\nTest content for review.\n" * 50)

    manifest = {
        "manifest_version": "1.0.0",
        "package_type": "cam_assist_strategy_package",
        "operation_type": "test",
        "strategy_file": "strategy.json",
        "review_packet_file": "review_packet.md",
        "created_at": "2026-05-28T00:00:00Z",
        "authority": {
            "non_execution_declaration": True,
            "execution_authority_claim": False,
            "requires_human_review": True,
        },
    }
    (package_dir / "manifest.json").write_text(json.dumps(manifest))

    return package_dir


@pytest.fixture
def federated_package(tmp_path) -> Path:
    """Create a package with federation metadata."""
    package_dir = tmp_path / "federated_package"
    package_dir.mkdir()

    strategy = {
        "strategy_version": "1.0",
        "strategy_id": "test-federated",
        "units": "mm",
        "coordinate_frame": {"origin": "nut", "x_axis": "x", "y_axis": "y", "z_axis": "z"},
        "provenance": {"source_spec_id": "test", "cam_assist_version": "0.5.0", "created_at": "2026-05-28T00:00:00Z"},
        "operation_intent": {"operation_type": "test", "target_feature": "test", "non_execution_declaration": True},
        "material_context": {"material_class": "test"},
        "safety_boundary": {"non_execution_declaration": True, "human_review_required": True, "execution_authority_claim": False},
        "approval_state": "pending",
    }
    (package_dir / "strategy.json").write_text(json.dumps(strategy))
    (package_dir / "review_packet.md").write_text("# Review Packet\n\nTest content for review.\n" * 50)

    manifest = {
        "manifest_version": "1.1.0",
        "package_type": "cam_assist_strategy_package",
        "operation_type": "test",
        "strategy_file": "strategy.json",
        "review_packet_file": "review_packet.md",
        "created_at": "2026-05-28T00:00:00Z",
        "authority": {
            "non_execution_declaration": True,
            "execution_authority_claim": False,
            "requires_human_review": True,
        },
        "federation": {
            "origin_system": "luthiers-toolbox",
            "authority_domain": "vcarve_review",
            "review_jurisdiction": "manufacturing_review",
            "federated_package_id": "luthiers-toolbox:vcarve:test-001",
        },
    }
    (package_dir / "manifest.json").write_text(json.dumps(manifest))

    return package_dir


class TestAnnotationCreation:
    """Tests for creating review annotations."""

    def test_create_basic_annotation(self, valid_package, tmp_path):
        """Should create a valid annotation file."""
        out_path = tmp_path / "annotations.json"

        exit_code, stdout, stderr = run_script(
            CREATE_SCRIPT,
            "--package", str(valid_package),
            "--reviewer", "test-reviewer",
            "--severity", "info",
            "--category", "test",
            "--message", "Test annotation message",
            "--out", str(out_path),
        )

        assert exit_code == 0, f"Creation failed: {stderr}"
        assert out_path.exists()

        data = json.loads(out_path.read_text())
        assert data["record_type"] == "cam_assist_review_annotations"
        assert data["record_version"] == "1.0.0"
        assert data["package_reference"] == valid_package.name
        assert len(data["annotations"]) == 1
        assert data["annotations"][0]["severity"] == "info"
        assert data["annotations"][0]["message"] == "Test annotation message"
        assert data["authority"]["annotations_are_informational"] is True

    def test_create_annotation_with_federated_package(self, federated_package, tmp_path):
        """Should use federated_package_id as package_reference."""
        out_path = tmp_path / "annotations.json"

        exit_code, stdout, stderr = run_script(
            CREATE_SCRIPT,
            "--package", str(federated_package),
            "--reviewer", "test-reviewer",
            "--severity", "warning",
            "--category", "tooling",
            "--message", "Federated test",
            "--out", str(out_path),
        )

        assert exit_code == 0, f"Creation failed: {stderr}"

        data = json.loads(out_path.read_text())
        assert data["package_reference"] == "luthiers-toolbox:vcarve:test-001"

    def test_create_annotation_with_optional_fields(self, valid_package, tmp_path):
        """Should include optional fields when provided."""
        out_path = tmp_path / "annotations.json"

        exit_code, stdout, stderr = run_script(
            CREATE_SCRIPT,
            "--package", str(valid_package),
            "--reviewer", "test-reviewer",
            "--severity", "concern",
            "--category", "safety",
            "--message", "Safety concern",
            "--jurisdiction", "safety_review",
            "--recommended-action", "Verify depth limit",
            "--out", str(out_path),
        )

        assert exit_code == 0
        data = json.loads(out_path.read_text())

        ann = data["annotations"][0]
        assert ann["jurisdiction"] == "safety_review"
        assert ann["recommended_action"] == "Verify depth limit"

    def test_create_annotation_appends_to_existing(self, valid_package, tmp_path):
        """Should append to existing annotations file."""
        out_path = tmp_path / "annotations.json"

        # Create first annotation
        run_script(
            CREATE_SCRIPT,
            "--package", str(valid_package),
            "--reviewer", "reviewer-1",
            "--severity", "info",
            "--category", "first",
            "--message", "First annotation",
            "--out", str(out_path),
        )

        # Create second annotation
        exit_code, stdout, stderr = run_script(
            CREATE_SCRIPT,
            "--package", str(valid_package),
            "--reviewer", "reviewer-2",
            "--severity", "warning",
            "--category", "second",
            "--message", "Second annotation",
            "--out", str(out_path),
        )

        assert exit_code == 0
        data = json.loads(out_path.read_text())
        assert len(data["annotations"]) == 2
        assert data["annotations"][0]["category"] == "first"
        assert data["annotations"][1]["category"] == "second"

    def test_create_annotation_unique_ids(self, valid_package, tmp_path):
        """Each annotation should have a unique ID."""
        out_path = tmp_path / "annotations.json"

        for i in range(3):
            run_script(
                CREATE_SCRIPT,
                "--package", str(valid_package),
                "--reviewer", "test",
                "--severity", "info",
                "--category", "test",
                "--message", f"Annotation {i}",
                "--out", str(out_path),
            )

        data = json.loads(out_path.read_text())
        ids = [ann["annotation_id"] for ann in data["annotations"]]
        assert len(ids) == len(set(ids)), "Annotation IDs should be unique"

    def test_invalid_severity_rejected(self, valid_package, tmp_path):
        """Should reject invalid severity levels."""
        out_path = tmp_path / "annotations.json"

        exit_code, stdout, stderr = run_script(
            CREATE_SCRIPT,
            "--package", str(valid_package),
            "--reviewer", "test",
            "--severity", "critical",  # invalid
            "--category", "test",
            "--message", "Test",
            "--out", str(out_path),
        )

        assert exit_code != 0


class TestAnnotationValidation:
    """Tests for validating annotation files."""

    def test_validate_example_annotations(self):
        """Should validate the example annotations file."""
        example_path = EXAMPLES_DIR / "review_annotations" / "ltb_vcarve_synthetic_example_annotations.json"
        if not example_path.exists():
            pytest.skip("Example annotations not found")

        exit_code, stdout, stderr = run_script(VALIDATE_SCRIPT, str(example_path))
        assert exit_code == 0, f"Validation failed: {stderr}"

    def test_validate_missing_required_field(self, tmp_path):
        """Should reject annotations missing required fields."""
        invalid = {
            "record_type": "cam_assist_review_annotations",
            "record_version": "1.0.0",
            "package_reference": "test",
            "annotations": [
                {
                    "annotation_id": "ann-1234",
                    # missing reviewer, timestamp, severity, category, message
                }
            ],
        }
        path = tmp_path / "invalid.json"
        path.write_text(json.dumps(invalid))

        exit_code, stdout, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert exit_code == 1

    def test_validate_invalid_severity(self, tmp_path):
        """Should reject invalid severity values."""
        invalid = {
            "record_type": "cam_assist_review_annotations",
            "record_version": "1.0.0",
            "package_reference": "test",
            "annotations": [
                {
                    "annotation_id": "ann-1234",
                    "reviewer": "test",
                    "timestamp": "2026-05-28T00:00:00Z",
                    "severity": "extreme",  # invalid
                    "category": "test",
                    "message": "test",
                }
            ],
        }
        path = tmp_path / "invalid.json"
        path.write_text(json.dumps(invalid))

        exit_code, stdout, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert exit_code == 1

    def test_validate_invalid_annotation_id_format(self, tmp_path):
        """Should reject invalid annotation_id format."""
        invalid = {
            "record_type": "cam_assist_review_annotations",
            "record_version": "1.0.0",
            "package_reference": "test",
            "annotations": [
                {
                    "annotation_id": "bad-format",  # should be ann-<uuid>
                    "reviewer": "test",
                    "timestamp": "2026-05-28T00:00:00Z",
                    "severity": "info",
                    "category": "test",
                    "message": "test",
                }
            ],
        }
        path = tmp_path / "invalid.json"
        path.write_text(json.dumps(invalid))

        exit_code, stdout, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert exit_code == 1

    def test_validate_missing_record_type(self, tmp_path):
        """Should reject annotations missing record_type."""
        invalid = {
            "record_version": "1.0.0",
            "package_reference": "test",
            "annotations": [],
        }
        path = tmp_path / "invalid.json"
        path.write_text(json.dumps(invalid))

        exit_code, stdout, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert exit_code == 1

    def test_validate_missing_record_version(self, tmp_path):
        """Should reject annotations missing record_version."""
        invalid = {
            "record_type": "cam_assist_review_annotations",
            "package_reference": "test",
            "annotations": [],
        }
        path = tmp_path / "invalid.json"
        path.write_text(json.dumps(invalid))

        exit_code, stdout, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert exit_code == 1

    def test_validate_authority_constraints(self, tmp_path):
        """Should reject annotations with incorrect authority values."""
        invalid = {
            "record_type": "cam_assist_review_annotations",
            "record_version": "1.0.0",
            "package_reference": "test",
            "annotations": [],
            "authority": {
                "annotations_are_informational": False,  # must be true
            },
        }
        path = tmp_path / "invalid.json"
        path.write_text(json.dumps(invalid))

        exit_code, stdout, stderr = run_script(VALIDATE_SCRIPT, str(path))
        assert exit_code == 1


class TestAnnotationInspection:
    """Tests for displaying annotations during package inspection."""

    def test_inspect_with_annotations_terminal(self, valid_package, tmp_path):
        """Should display annotations in terminal output."""
        ann_path = tmp_path / "annotations.json"
        run_script(
            CREATE_SCRIPT,
            "--package", str(valid_package),
            "--reviewer", "test-reviewer",
            "--severity", "warning",
            "--category", "tooling",
            "--message", "Test warning message",
            "--out", str(ann_path),
        )

        exit_code, stdout, stderr = run_script(
            INSPECT_SCRIPT,
            str(valid_package),
            "--annotations", str(ann_path),
        )

        assert exit_code == 0
        assert "Review Annotations:" in stdout
        assert "total: 1" in stdout
        assert "warnings: 1" in stdout
        assert "[WARNING]" in stdout
        assert "Test warning message" in stdout

    def test_inspect_with_annotations_json(self, valid_package, tmp_path):
        """Should include annotations in JSON output."""
        ann_path = tmp_path / "annotations.json"
        run_script(
            CREATE_SCRIPT,
            "--package", str(valid_package),
            "--reviewer", "test-reviewer",
            "--severity", "concern",
            "--category", "safety",
            "--message", "Safety concern",
            "--out", str(ann_path),
        )

        exit_code, stdout, stderr = run_script(
            INSPECT_SCRIPT,
            str(valid_package),
            "--annotations", str(ann_path),
            "--json",
        )

        assert exit_code == 0
        output = json.loads(stdout)
        assert "annotations" in output
        assert len(output["annotations"]) == 1
        assert output["annotations"][0]["severity"] == "concern"


    def test_inspect_conventional_path_fallback(self, tmp_path):
        """Should auto-load annotations from conventional path."""
        # Create package structure
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()
        package_dir = packages_dir / "test_pkg"
        package_dir.mkdir()

        strategy = {
            "strategy_version": "1.0",
            "strategy_id": "test",
            "units": "mm",
            "coordinate_frame": {"origin": "nut", "x_axis": "x", "y_axis": "y", "z_axis": "z"},
            "provenance": {"source_spec_id": "test", "cam_assist_version": "0.5.0", "created_at": "2026-05-28T00:00:00Z"},
            "operation_intent": {"operation_type": "test", "target_feature": "test", "non_execution_declaration": True},
            "material_context": {"material_class": "test"},
            "safety_boundary": {"non_execution_declaration": True, "human_review_required": True, "execution_authority_claim": False},
            "approval_state": "pending",
        }
        (package_dir / "strategy.json").write_text(json.dumps(strategy))
        (package_dir / "review_packet.md").write_text("# Review\n\n" + "content " * 200)
        manifest = {
            "manifest_version": "1.0.0",
            "package_type": "cam_assist_strategy_package",
            "operation_type": "test",
            "strategy_file": "strategy.json",
            "review_packet_file": "review_packet.md",
            "created_at": "2026-05-28T00:00:00Z",
            "authority": {"non_execution_declaration": True, "execution_authority_claim": False, "requires_human_review": True},
        }
        (package_dir / "manifest.json").write_text(json.dumps(manifest))

        # Create annotation at conventional path
        ann_dir = packages_dir / "review_annotations"
        ann_dir.mkdir()
        ann_path = ann_dir / "test_pkg_annotations.json"
        run_script(
            CREATE_SCRIPT,
            "--package", str(package_dir),
            "--reviewer", "test",
            "--severity", "info",
            "--category", "test",
            "--message", "Conventional path test",
            "--out", str(ann_path),
        )

        # Inspect without --annotations flag
        exit_code, stdout, stderr = run_script(INSPECT_SCRIPT, str(package_dir))

        assert exit_code == 0
        assert "Review Annotations:" in stdout
        assert "total: 1" in stdout
        assert "Conventional path test" in stdout


class TestReviewDecisionIntegration:
    """Tests for annotation integration with review decisions."""

    def test_record_decision_with_annotation_file(self, valid_package, tmp_path):
        """Should include annotation_files in decision record."""
        ann_path = tmp_path / "annotations.json"
        run_script(
            CREATE_SCRIPT,
            "--package", str(valid_package),
            "--reviewer", "test-reviewer",
            "--severity", "info",
            "--category", "test",
            "--message", "Reviewed",
            "--out", str(ann_path),
        )

        decision_path = tmp_path / "decision.json"
        exit_code, stdout, stderr = run_script(
            RECORD_SCRIPT,
            str(valid_package),
            "--decision", "approve_for_downstream_cam",
            "--reviewer", "Human Reviewer",
            "--annotation-file", str(ann_path),
            "--out", str(decision_path),
        )

        assert exit_code == 0, f"Record failed: {stderr}"
        data = json.loads(decision_path.read_text())
        assert "annotation_files" in data
        assert str(ann_path) in data["annotation_files"]

    def test_record_decision_with_multiple_annotation_files(self, valid_package, tmp_path):
        """Should support multiple annotation files."""
        ann1 = tmp_path / "ann1.json"
        ann2 = tmp_path / "ann2.json"

        for path, cat in [(ann1, "acoustic"), (ann2, "safety")]:
            run_script(
                CREATE_SCRIPT,
                "--package", str(valid_package),
                "--reviewer", "test",
                "--severity", "info",
                "--category", cat,
                "--message", f"{cat} review",
                "--out", str(path),
            )

        decision_path = tmp_path / "decision.json"
        exit_code, stdout, stderr = run_script(
            RECORD_SCRIPT,
            str(valid_package),
            "--decision", "approve_for_downstream_cam",
            "--reviewer", "Human Reviewer",
            "--annotation-file", str(ann1),
            "--annotation-file", str(ann2),
            "--out", str(decision_path),
        )

        assert exit_code == 0
        data = json.loads(decision_path.read_text())
        assert len(data["annotation_files"]) == 2


class TestSidecarPattern:
    """Tests verifying annotations follow the sidecar pattern."""

    def test_annotations_do_not_modify_package(self, valid_package, tmp_path):
        """Creating annotations should not modify package contents."""
        # Record original state
        manifest_before = (valid_package / "manifest.json").read_text()
        strategy_before = (valid_package / "strategy.json").read_text()
        review_before = (valid_package / "review_packet.md").read_text()

        # Create annotations
        ann_path = tmp_path / "annotations.json"
        run_script(
            CREATE_SCRIPT,
            "--package", str(valid_package),
            "--reviewer", "test",
            "--severity", "warning",
            "--category", "test",
            "--message", "Test",
            "--out", str(ann_path),
        )

        # Verify package unchanged
        assert (valid_package / "manifest.json").read_text() == manifest_before
        assert (valid_package / "strategy.json").read_text() == strategy_before
        assert (valid_package / "review_packet.md").read_text() == review_before

    def test_annotations_stored_outside_package(self, valid_package, tmp_path):
        """Default path should be outside package directory."""
        # Use default output path behavior
        exit_code, stdout, stderr = run_script(
            CREATE_SCRIPT,
            "--package", str(valid_package),
            "--reviewer", "test",
            "--severity", "info",
            "--category", "test",
            "--message", "Test",
        )

        assert exit_code == 0

        # Verify no new files in package
        package_files = list(valid_package.iterdir())
        file_names = [f.name for f in package_files]
        assert "annotations.json" not in file_names
        for f in package_files:
            assert "annotation" not in f.name.lower()
