"""
Tests for CAM-A15 Federation Presentation + Preservation.

These tests verify that:
- Inspection renders federation metadata
- Archive round-trip preserves federation fields
- CI invariant verification passes with federation metadata
"""

import json
import pytest
import tempfile
import zipfile
from pathlib import Path
import subprocess
import sys


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

INSPECT_SCRIPT = SCRIPTS_DIR / "inspect_strategy_package.py"
ARCHIVE_SCRIPT = SCRIPTS_DIR / "archive_strategy_package.py"
VALIDATE_ARCHIVE_SCRIPT = SCRIPTS_DIR / "validate_package_archive.py"
STAGE_SCRIPT = SCRIPTS_DIR / "stage_strategy_package.py"
INVARIANT_SCRIPT = SCRIPTS_DIR / "verify_non_execution_invariant.py"


def run_script(script: Path, *args) -> tuple[int, str, str]:
    """Run a script and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, str(script)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def federated_package(tmp_path) -> Path:
    """Create a package with federation metadata."""
    package_dir = tmp_path / "federated_package"
    package_dir.mkdir()

    # Create strategy.json
    strategy = {
        "strategy_version": "1.0",
        "strategy_id": "test-federated",
        "units": "mm",
        "coordinate_frame": {
            "origin": "nut",
            "x_axis": "along_neck",
            "y_axis": "across_fretboard",
            "z_axis": "into_material",
        },
        "provenance": {
            "source_spec_id": "test-spec",
            "cam_assist_version": "0.6.0",
            "created_at": "2026-05-28T00:00:00Z",
            "created_by": "test",
        },
        "operation_intent": {
            "operation_type": "fret_slots",
            "target_feature": "fretboard",
            "cut_intent": "slot",
            "non_execution_declaration": True,
        },
        "material_context": {
            "material_class": "hardwood",
            "species": "ebony",
        },
        "safety_boundary": {
            "non_execution_declaration": True,
            "human_review_required": True,
            "execution_authority_claim": False,
            "max_depth_inches": 0.1,
        },
        "approval_state": "pending",
    }
    (package_dir / "strategy.json").write_text(json.dumps(strategy, indent=2))

    # Create review_packet.md
    (package_dir / "review_packet.md").write_text("# Review Packet\n\nTest review packet.")

    # Create manifest.json with federation metadata
    manifest = {
        "manifest_version": "1.1.0",
        "package_type": "cam_assist_strategy_package",
        "operation_type": "fret_slots",
        "strategy_file": "strategy.json",
        "review_packet_file": "review_packet.md",
        "source_geometry_files": [],
        "created_at": "2026-05-28T00:00:00Z",
        "cam_assist_version": "0.6.0",
        "authority": {
            "non_execution_declaration": True,
            "execution_authority_claim": False,
            "requires_human_review": True,
        },
        "provenance": {
            "source_spec_id": "test-spec",
            "created_by": "test",
            "derivation_notes": "Test federated package",
        },
        "federation": {
            "origin_system": "test-system",
            "authority_domain": "test_authority",
            "review_jurisdiction": "test_review",
            "federated_package_id": "test-system:test:001",
        },
    }
    (package_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return package_dir


class TestInspectionRendersFederation:
    """Tests for federation metadata rendering in inspection."""

    def test_inspect_terminal_shows_federation(self, federated_package):
        """Terminal inspection output should include Federated Identity section."""
        exit_code, stdout, stderr = run_script(INSPECT_SCRIPT, str(federated_package))

        assert exit_code == 0, f"Inspection failed: {stderr}"
        assert "Federated Identity:" in stdout
        assert "origin_system: test-system" in stdout
        assert "authority_domain: test_authority" in stdout
        assert "review_jurisdiction: test_review" in stdout
        assert "federated_package_id: test-system:test:001" in stdout

    def test_inspect_json_includes_federation(self, federated_package):
        """JSON inspection output should include federation object."""
        exit_code, stdout, stderr = run_script(
            INSPECT_SCRIPT, str(federated_package), "--json"
        )

        assert exit_code == 0, f"Inspection failed: {stderr}"

        output = json.loads(stdout)
        assert "federation" in output
        assert output["federation"]["origin_system"] == "test-system"
        assert output["federation"]["authority_domain"] == "test_authority"
        assert output["federation"]["review_jurisdiction"] == "test_review"
        assert output["federation"]["federated_package_id"] == "test-system:test:001"

    def test_inspect_shows_not_declared_when_missing(self, tmp_path):
        """Non-federated packages should show 'not declared'."""
        package_dir = tmp_path / "non_federated"
        package_dir.mkdir()

        # Create minimal valid package without federation
        strategy = {
            "strategy_version": "1.0",
            "strategy_id": "test-non-federated",
            "units": "mm",
            "coordinate_frame": {"origin": "nut", "x_axis": "x", "y_axis": "y", "z_axis": "z"},
            "provenance": {"source_spec_id": "test", "cam_assist_version": "0.5.0", "created_at": "2026-05-28T00:00:00Z"},
            "operation_intent": {"operation_type": "test", "target_feature": "test", "non_execution_declaration": True},
            "material_context": {"material_class": "test"},
            "safety_boundary": {"non_execution_declaration": True, "human_review_required": True, "execution_authority_claim": False},
            "approval_state": "pending",
        }
        (package_dir / "strategy.json").write_text(json.dumps(strategy))
        (package_dir / "review_packet.md").write_text("# Review")

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

        exit_code, stdout, stderr = run_script(INSPECT_SCRIPT, str(package_dir))

        assert exit_code == 0
        assert "not declared" in stdout


class TestArchiveRoundTrip:
    """Tests for federation field preservation in archive round-trip."""

    def test_archive_preserves_federation_fields(self, federated_package, tmp_path):
        """Federation fields should survive archive/extract cycle."""
        archive_path = tmp_path / "test_archive.zip"

        # Archive the package
        exit_code, stdout, stderr = run_script(
            ARCHIVE_SCRIPT, str(federated_package), "--out", str(archive_path)
        )
        assert exit_code == 0, f"Archive failed: {stderr}"
        assert archive_path.exists()

        # Extract the archive
        extract_dir = tmp_path / "extracted"
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_dir)

        # Verify manifest.json was preserved
        extracted_manifest = extract_dir / "manifest.json"
        assert extracted_manifest.exists()

        manifest_data = json.loads(extracted_manifest.read_text())

        # Verify federation fields survived
        assert "federation" in manifest_data
        federation = manifest_data["federation"]
        assert federation["origin_system"] == "test-system"
        assert federation["authority_domain"] == "test_authority"
        assert federation["review_jurisdiction"] == "test_review"
        assert federation["federated_package_id"] == "test-system:test:001"

    def test_ltb_example_archive_round_trip(self, tmp_path):
        """LTB V-Carve example with federation should survive archive round-trip."""
        example_dir = EXAMPLES_DIR / "packages" / "ltb_vcarve_synthetic_example"
        if not example_dir.exists():
            pytest.skip("LTB V-Carve example not found")

        archive_path = tmp_path / "ltb_example.zip"

        # Archive
        exit_code, stdout, stderr = run_script(
            ARCHIVE_SCRIPT, str(example_dir), "--out", str(archive_path)
        )
        assert exit_code == 0, f"Archive failed: {stderr}"

        # Extract
        extract_dir = tmp_path / "extracted"
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_dir)

        # Verify federation preserved
        manifest_data = json.loads((extract_dir / "manifest.json").read_text())
        assert "federation" in manifest_data
        assert manifest_data["federation"]["origin_system"] == "luthiers-toolbox"


class TestStagingPreservation:
    """Tests for federation field preservation through full staging flow."""

    def test_full_staging_flow_preserves_federation(self, federated_package, tmp_path):
        """
        Federation fields should survive full staging flow:
        manifest → archive → validate → stage → staged manifest
        """
        archive_path = tmp_path / "test_archive.zip"
        staging_dir = tmp_path / "staged"

        # Step 1: Archive the package
        exit_code, stdout, stderr = run_script(
            ARCHIVE_SCRIPT, str(federated_package), "--out", str(archive_path)
        )
        assert exit_code == 0, f"Archive failed: {stderr}"
        assert archive_path.exists()

        # Step 2: Validate the archive
        exit_code, stdout, stderr = run_script(
            VALIDATE_ARCHIVE_SCRIPT, str(archive_path)
        )
        assert exit_code == 0, f"Archive validation failed: {stderr}"

        # Step 3: Stage the archive
        exit_code, stdout, stderr = run_script(
            STAGE_SCRIPT, str(archive_path), "--out", str(staging_dir)
        )
        assert exit_code == 0, f"Staging failed: {stderr}"

        # Step 4: Verify staged manifest has federation fields
        staged_manifest = staging_dir / "test_archive" / "manifest.json"
        assert staged_manifest.exists(), "Staged manifest not found"

        manifest_data = json.loads(staged_manifest.read_text())
        assert "federation" in manifest_data, "Federation fields lost during staging"

        federation = manifest_data["federation"]
        assert federation["origin_system"] == "test-system"
        assert federation["authority_domain"] == "test_authority"
        assert federation["review_jurisdiction"] == "test_review"
        assert federation["federated_package_id"] == "test-system:test:001"

    def test_ltb_example_full_staging_flow(self, tmp_path):
        """LTB V-Carve example federation should survive full staging flow."""
        example_dir = EXAMPLES_DIR / "packages" / "ltb_vcarve_synthetic_example"
        if not example_dir.exists():
            pytest.skip("LTB V-Carve example not found")

        archive_path = tmp_path / "ltb_example.zip"
        staging_dir = tmp_path / "staged"

        # Archive → Validate → Stage
        exit_code, _, stderr = run_script(
            ARCHIVE_SCRIPT, str(example_dir), "--out", str(archive_path)
        )
        assert exit_code == 0, f"Archive failed: {stderr}"

        exit_code, _, stderr = run_script(VALIDATE_ARCHIVE_SCRIPT, str(archive_path))
        assert exit_code == 0, f"Validation failed: {stderr}"

        exit_code, _, stderr = run_script(
            STAGE_SCRIPT, str(archive_path), "--out", str(staging_dir)
        )
        assert exit_code == 0, f"Staging failed: {stderr}"

        # Verify federation preserved
        staged_manifest = staging_dir / "ltb_example" / "manifest.json"
        manifest_data = json.loads(staged_manifest.read_text())

        assert "federation" in manifest_data
        assert manifest_data["federation"]["origin_system"] == "luthiers-toolbox"


class TestCIInvariantWithFederation:
    """Tests for CI invariant verification with federation metadata."""

    def test_invariant_passes_with_federation(self, federated_package):
        """Non-execution invariant should still pass when federation is present."""
        if not INVARIANT_SCRIPT.exists():
            pytest.skip("Invariant verification script not found")

        exit_code, stdout, stderr = run_script(
            INVARIANT_SCRIPT, str(federated_package)
        )

        assert exit_code == 0, f"Invariant check failed: {stderr}"

    def test_federation_does_not_grant_execution_authority(self, federated_package):
        """Federation metadata must not bypass execution authority checks."""
        # Modify the manifest to claim execution authority
        manifest_path = federated_package / "manifest.json"
        manifest_data = json.loads(manifest_path.read_text())

        # Federation is present, but execution_authority_claim is true (invalid)
        manifest_data["authority"]["execution_authority_claim"] = True
        manifest_path.write_text(json.dumps(manifest_data))

        # Inspection should fail
        exit_code, stdout, stderr = run_script(INSPECT_SCRIPT, str(federated_package))

        assert exit_code == 1, "Should reject execution_authority_claim=true even with federation"
        # Error appears in terminal output (stdout), not stderr for inspect script
        assert "AUTHORITY VIOLATION" in stdout or "AUTHORITY VIOLATION" in stderr
