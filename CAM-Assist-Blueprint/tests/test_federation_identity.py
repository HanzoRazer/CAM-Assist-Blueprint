"""
Tests for CAM-A14 External Package Identity (Federation Metadata).

These tests verify that:
- Manifests without federation fields remain valid (backward compatibility)
- Manifests with federation fields are valid
- Invalid origin_system format is rejected
- authority_domain does not imply execution authority
- review_jurisdiction can differ from authority_domain
- federated_package_id is informational only
"""

import json
import pytest
from pathlib import Path
import subprocess
import sys


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

VALIDATOR_SCRIPT = SCRIPTS_DIR / "validate_manifest.py"


def run_validator(input_path: Path) -> tuple[int, str, str]:
    """Run the manifest validator and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, str(VALIDATOR_SCRIPT), str(input_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def minimal_valid_manifest(tmp_path) -> dict:
    """Return a minimal valid manifest with required files created."""
    strategy_file = tmp_path / "strategy.json"
    strategy_file.write_text('{"test": true}')

    review_file = tmp_path / "review.md"
    review_file.write_text("# Review")

    return {
        "manifest_version": "1.0.0",
        "package_type": "cam_assist_strategy_package",
        "operation_type": "fret_slot_strategy",
        "strategy_file": "strategy.json",
        "review_packet_file": "review.md",
        "source_geometry_files": [],
        "created_at": "2026-05-21T12:00:00Z",
        "cam_assist_version": "0.4.0",
        "authority": {
            "non_execution_declaration": True,
            "execution_authority_claim": False,
            "requires_human_review": True,
        },
        "provenance": {
            "source_spec_id": "test-spec",
            "created_by": "test",
            "derivation_notes": "test notes",
        },
    }


class TestBackwardCompatibility:
    """Tests for backward compatibility with non-federated manifests."""

    def test_manifest_without_federation_fields_valid(self, minimal_valid_manifest, tmp_path):
        """Manifest without federation fields should remain valid."""
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0, f"Expected pass without federation fields: {stderr}"

    def test_existing_example_without_federation_valid(self):
        """Existing fret_slot_strategy_example should remain valid without federation."""
        manifest_file = EXAMPLES_DIR / "packages" / "fret_slot_strategy_example" / "manifest.json"
        if not manifest_file.exists():
            pytest.skip("Example manifest not found")

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0, f"Existing example should remain valid: {stderr}"


class TestFederationFieldsValid:
    """Tests for valid federation metadata."""

    def test_manifest_with_all_federation_fields(self, minimal_valid_manifest, tmp_path):
        """Manifest with all federation fields should be valid."""
        minimal_valid_manifest["federation"] = {
            "origin_system": "luthiers-toolbox",
            "authority_domain": "runtime_cam",
            "review_jurisdiction": "manufacturing_review",
            "federated_package_id": "luthiers-toolbox:vcarve:example-001",
        }

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0, f"Expected pass with federation fields: {stderr}"

    def test_manifest_with_partial_federation_fields(self, minimal_valid_manifest, tmp_path):
        """Manifest with partial federation fields should be valid."""
        minimal_valid_manifest["federation"] = {
            "origin_system": "tap-tone-pi",
        }

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0, f"Expected pass with partial federation fields: {stderr}"

    def test_ltb_vcarve_example_with_federation(self):
        """LTB V-Carve example with federation fields should be valid."""
        manifest_file = EXAMPLES_DIR / "packages" / "ltb_vcarve_synthetic_example" / "manifest.json"
        if not manifest_file.exists():
            pytest.skip("LTB V-Carve example not found")

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0, f"LTB V-Carve example should be valid: {stderr}"


class TestOriginSystemFormat:
    """Tests for origin_system format validation."""

    def test_valid_origin_system_simple(self, minimal_valid_manifest, tmp_path):
        """Simple lowercase slug should be valid."""
        minimal_valid_manifest["federation"] = {"origin_system": "luthiers-toolbox"}

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0

    def test_valid_origin_system_with_dots(self, minimal_valid_manifest, tmp_path):
        """Origin system with dots should be valid."""
        minimal_valid_manifest["federation"] = {"origin_system": "com.example.system"}

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0

    def test_valid_origin_system_with_underscores(self, minimal_valid_manifest, tmp_path):
        """Origin system with underscores should be valid."""
        minimal_valid_manifest["federation"] = {"origin_system": "ibg_sandbox"}

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0

    def test_invalid_origin_system_uppercase(self, minimal_valid_manifest, tmp_path):
        """Uppercase origin_system should be rejected."""
        minimal_valid_manifest["federation"] = {"origin_system": "Luthiers-Toolbox"}

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 1, "Uppercase origin_system should be rejected"

    def test_invalid_origin_system_starts_with_number(self, minimal_valid_manifest, tmp_path):
        """Origin system starting with number should be rejected."""
        minimal_valid_manifest["federation"] = {"origin_system": "123system"}

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 1, "Origin system starting with number should be rejected"

    def test_invalid_origin_system_special_chars(self, minimal_valid_manifest, tmp_path):
        """Origin system with special characters should be rejected."""
        minimal_valid_manifest["federation"] = {"origin_system": "system@example"}

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 1, "Origin system with special chars should be rejected"


class TestAuthorityDomainSeparation:
    """Tests verifying authority_domain does not imply execution authority."""

    def test_authority_domain_does_not_grant_execution(self, minimal_valid_manifest, tmp_path):
        """
        authority_domain field does not override non_execution_declaration.

        Even with authority_domain set, execution_authority_claim must remain false.
        """
        minimal_valid_manifest["federation"] = {
            "origin_system": "luthiers-toolbox",
            "authority_domain": "runtime_cam",
        }
        minimal_valid_manifest["authority"]["execution_authority_claim"] = True

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 1, "execution_authority_claim=true must still be rejected"
        assert "EXECUTION AUTHORITY" in stderr


class TestJurisdictionDivergence:
    """Tests for review_jurisdiction differing from authority_domain."""

    def test_review_jurisdiction_can_differ_from_authority_domain(
        self, minimal_valid_manifest, tmp_path
    ):
        """review_jurisdiction may differ from authority_domain for cross-system review."""
        minimal_valid_manifest["federation"] = {
            "origin_system": "luthiers-toolbox",
            "authority_domain": "runtime_cam",
            "review_jurisdiction": "acoustic_review",
        }

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0, f"Divergent jurisdictions should be valid: {stderr}"

    def test_review_jurisdiction_alone_valid(self, minimal_valid_manifest, tmp_path):
        """review_jurisdiction without authority_domain should be valid."""
        minimal_valid_manifest["federation"] = {
            "origin_system": "tap-tone-pi",
            "review_jurisdiction": "acoustic_validation",
        }

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0


class TestFederatedPackageIdInformational:
    """Tests verifying federated_package_id is purely informational."""

    def test_federated_package_id_any_format_valid(self, minimal_valid_manifest, tmp_path):
        """federated_package_id accepts any string format (informational only)."""
        minimal_valid_manifest["federation"] = {
            "origin_system": "luthiers-toolbox",
            "federated_package_id": "any:format:works:here:12345",
        }

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0

    def test_federated_package_id_duplicate_allowed(self, minimal_valid_manifest, tmp_path):
        """
        Duplicate federated_package_id should be allowed (no uniqueness enforcement).

        This test documents that CAM Assist does not enforce uniqueness.
        """
        minimal_valid_manifest["federation"] = {
            "origin_system": "test-system",
            "federated_package_id": "duplicate-id",
        }

        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(minimal_valid_manifest))

        exit_code, stdout, stderr = run_validator(manifest_file)
        assert exit_code == 0, "Duplicate IDs should not be rejected by validator"
