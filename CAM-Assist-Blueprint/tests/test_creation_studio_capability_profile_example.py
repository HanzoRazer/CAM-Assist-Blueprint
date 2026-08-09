"""
Example-regression tests for CAM-A23 Creation Studio Capability Profile.

The committed example is tool-generated, never handwritten. These tests pin it:

- it regenerates BYTE-IDENTICALLY from the creator with the documented command
  (proving it is reproducible and no one hand-edited it)
- it is structurally valid
- it is `--check-references` clean
- its key contract invariants hold (record_type, versions, direction, five
  authority flags, sorted capability list, and NO created_at)

Deliberate strictness (not accidental brittleness). CAM-A23 promises byte-identical
regeneration as a verification discipline (see docs/dev_orders/CAM-A23.md), so the
exact serialization is itself part of the contract surface. Consequences that
follow ON PURPOSE:

- the capability list is compared EXACTLY, in sorted order (the creator sorts, so
  order is a property of the artifact rather than of the command line);
- the authority block is compared for EXACT equality because it is a CLOSED
  contract (schema additionalProperties:false; the validator rejects unknown
  flags) — a new flag is a deliberate change that must update this test too;
- `created_at` is forbidden because determinism is a hard requirement.

A failure here means "the creator output changed — regenerate the example and
commit it," NOT "relax the assertion." The byte-identity test localizes its own
failure (formatting drift vs semantic regression) so the right response is obvious.

The byte-identity check regenerates into a throwaway root under tmp_path — never
touching the committed tree. The profile is not package-specific and holds no
package-relative references, so no examples/ layout needs staging.
"""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
CREATE_SCRIPT = SCRIPTS_DIR / "create_creation_studio_capability_profile.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_creation_studio_capability_profile.py"

EXAMPLE = REPO_ROOT / "examples" / "creation_studio" / "capability_profile.json"

# The documented generation command (docs/integration/CREATION_STUDIO_CAPABILITY_PROFILE.md
# and the CAM-A23 dev order). One capability is deliberately supplied as a
# human-readable name to exercise normalization and the display_name rule; the
# rest are supplied as identifiers. Supply ORDER is not significant — the creator
# sorts — but the SET is.
CAPABILITIES = [
    "strategy_visualization",
    "Feeds & Speeds Authoring",
    "tool_library_editing",
    "gcode_tutorial_generation",
    "simulation_support",
    "post_processor_education",
    "machining_lesson_playback",
]

# The sorted identifiers the creator must emit for that set.
EXPECTED_IDS = [
    "feeds_speeds_authoring",
    "gcode_tutorial_generation",
    "machining_lesson_playback",
    "post_processor_education",
    "simulation_support",
    "strategy_visualization",
    "tool_library_editing",
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


def _regen_cmd() -> str:
    return (
        "  python scripts/create_creation_studio_capability_profile.py --root examples "
        + " ".join(f'--capability "{c}"' for c in CAPABILITIES)
        + " --force"
    )


def test_example_regenerates_byte_identical(tmp_path):
    code, _out, err = run(CREATE_SCRIPT, "--root", tmp_path, *_cap_args(), "--force")
    assert code == 0, err
    regenerated = tmp_path / "creation_studio" / "capability_profile.json"
    regen_bytes = regenerated.read_bytes()
    committed_bytes = EXAMPLE.read_bytes()
    if regen_bytes == committed_bytes:
        return

    # Byte-identity failed. Localize it so the fix is obvious rather than a raw
    # bytes-differ. Byte-identity remains the authoritative guarantee in both
    # branches below; this only makes the failure interpretable.
    regen_json = json.loads(regen_bytes)
    committed_json = json.loads(committed_bytes)
    assert regen_json == committed_json, (
        "Committed example DIVERGED SEMANTICALLY from creator output — a real "
        "regression in the creator or a stale committed example. Regenerate:\n"
        + _regen_cmd()
    )
    raise AssertionError(
        "Committed example is byte-stale but SEMANTICALLY EQUAL — the creator's "
        "JSON serialization/formatting changed. Byte-identical regeneration is a "
        "deliberate CAM-A23 guarantee, so regenerate and commit the example:\n"
        + _regen_cmd()
    )


def test_committed_example_is_structurally_valid():
    code, out, err = run(VALIDATE_SCRIPT, EXAMPLE)
    assert code == 0, err + out


def test_committed_example_references_resolve():
    code, out, _err = run(VALIDATE_SCRIPT, EXAMPLE, "--check-references")
    assert code == 0
    # Assert the behavioral signal (a reference that failed to resolve) rather than
    # the "[WARN]" marker wording, so a cosmetic change to the validator's warning
    # prefix does not spuriously fail this test.
    assert "does not resolve" not in out


def test_committed_example_contract_invariants():
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert data["record_type"] == "creation_studio_capability_profile"
    assert data["record_version"] == "1.0.0"
    assert data["profile_version"] == "1.0.0"
    assert data["studio_reference"] == "cam-creation-studio"
    assert data["publication_direction"] == "creation_studio_to_cam_assist"
    # Sorted order is a property of the artifact, not of the command line.
    assert [c["capability_id"] for c in data["capabilities"]] == EXPECTED_IDS
    # Exact equality is intentional: the authority block is a CLOSED contract
    # (schema additionalProperties:false; validator rejects unknown flags). A new
    # or renamed flag is a deliberate change that must update this assertion too.
    assert data["authority"] == {
        "is_informational": True,
        "does_not_authorize_execution": True,
        "does_not_bypass_human_review": True,
        "does_not_confirm_machine_readiness": True,
        "does_not_require_capability_use": True,
    }
    # The profile is deterministic: no wall-clock stamp.
    assert "created_at" not in data


def test_committed_example_display_name_rule():
    # The one capability supplied as a human-readable name keeps it; the ones
    # supplied as identifiers carry no redundant display_name. This pins the
    # documented rule, so a change to normalization surfaces here with its reason
    # attached rather than only as a byte diff.
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    by_id = {c["capability_id"]: c for c in data["capabilities"]}
    assert by_id["feeds_speeds_authoring"]["display_name"] == "Feeds & Speeds Authoring"
    for identifier in EXPECTED_IDS:
        if identifier != "feeds_speeds_authoring":
            assert by_id[identifier] == {"capability_id": identifier}


def test_committed_example_declares_no_approval():
    # A profile records declared support only. No entry may carry an approval,
    # readiness, or authorization signal — the closed entry contract forbids the
    # fields, and this witnesses the committed artifact honours it.
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    for entry in data["capabilities"]:
        assert set(entry) <= {
            "capability_id",
            "display_name",
            "description",
            "documentation_reference",
        }
