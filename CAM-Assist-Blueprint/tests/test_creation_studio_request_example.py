"""
Example-regression tests for CAM-A22 Creation Studio Capability Request.

The committed example is tool-generated, never handwritten. These tests pin it:

- it regenerates BYTE-IDENTICALLY from the creator with the documented command
  (proving it is reproducible and no one hand-edited it)
- it is structurally valid
- its declared references all resolve (`--check-references` clean)
- its key contract invariants hold (record_type, direction, five authority
  flags, both optional refs present, and NO created_at)

The byte-identity check regenerates into a throwaway copy of the examples/ layout
under tmp_path — never touching the committed tree — so the relative references
come out identical to the committed file.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
CREATE_SCRIPT = SCRIPTS_DIR / "create_creation_studio_request.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_creation_studio_request.py"

PACKAGE_NAME = "ltb_vcarve_synthetic_example"
EXAMPLE = REPO_ROOT / "examples" / "creation_studio" / f"{PACKAGE_NAME}_request.json"

# The documented generation command (docs/integration/CAM_CREATION_STUDIO_REQUEST.md
# and the CAM-A22 dev order). Capability order is significant: it is preserved in
# the output, so it must match what produced the committed example.
CAPABILITIES = [
    "feeds_speeds_recommendation",
    "tooling_review",
    "operation_sequence_analysis",
]


def run(script: Path, *args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(script)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def _cap_args() -> list:
    args: list = []
    for c in CAPABILITIES:
        args += ["--capability", c]
    return args


def _stage_examples(tmp_path: Path) -> Path:
    """Replicate just enough of examples/ under tmp_path for the creator to emit a
    byte-identical request: the real package manifest (source of package_reference
    and the declared filenames) plus existence-only stand-ins for the conventional
    traceability bundle and production shop handoff so both optional refs are
    discovered. Returns the staged package directory.
    """
    examples = tmp_path / "examples"
    pkg = examples / "packages" / PACKAGE_NAME
    pkg.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "examples" / "packages" / PACKAGE_NAME / "manifest.json",
        pkg / "manifest.json",
    )
    # Conventional optional references: existence is all the creator checks.
    (examples / "traceability").mkdir()
    (examples / "traceability" / f"{PACKAGE_NAME}_bundle.json").write_text("{}", encoding="utf-8")
    (examples / "production_shop").mkdir()
    (examples / "production_shop" / f"{PACKAGE_NAME}_handoff.json").write_text("{}", encoding="utf-8")
    return pkg


def test_example_regenerates_byte_identical(tmp_path):
    pkg = _stage_examples(tmp_path)
    code, _out, err = run(CREATE_SCRIPT, "--package", pkg, *_cap_args(), "--force")
    assert code == 0, err
    regenerated = tmp_path / "examples" / "creation_studio" / f"{PACKAGE_NAME}_request.json"
    assert regenerated.read_bytes() == EXAMPLE.read_bytes(), (
        "Committed example is stale: regenerate it with\n"
        "  python scripts/create_creation_studio_request.py "
        f"--package examples/packages/{PACKAGE_NAME} "
        + " ".join(f"--capability {c}" for c in CAPABILITIES)
        + " --force"
    )


def test_committed_example_is_structurally_valid():
    code, out, err = run(VALIDATE_SCRIPT, EXAMPLE)
    assert code == 0, err + out


def test_committed_example_references_resolve():
    code, out, _err = run(VALIDATE_SCRIPT, EXAMPLE, "--check-references")
    assert code == 0
    assert "[WARN]" not in out


def test_committed_example_contract_invariants():
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert data["record_type"] == "cam_assist_creation_studio_request"
    assert data["request_direction"] == "cam_assist_to_creation_studio"
    assert data["requested_capabilities"] == CAPABILITIES
    assert data["authority"] == {
        "is_informational": True,
        "does_not_authorize_execution": True,
        "does_not_bypass_human_review": True,
        "does_not_confirm_machine_readiness": True,
        "does_not_require_gcode_generation": True,
    }
    # Both optional references were discovered by convention.
    assert "traceability_bundle_file" in data["contents"]
    assert "production_shop_handoff_file" in data["contents"]
    # The request is deterministic: no wall-clock stamp.
    assert "created_at" not in data
