"""
CAM-A26 CLI: --capability-map is opt-in; exact mode is unchanged.

Process-boundary tests. The script is invoked as a subprocess so these pin
the real entry point: missing/invalid maps exit 2 with empty --json stdout,
strict mode keys on final unsatisfied only, and omitting the flag leaves the
CAM-A25 payload shape intact.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "reconcile_creation_studio_capabilities.py"
CANONICAL_MAP = REPO_ROOT / "contracts" / "creation_studio_capability_map.json"
EXAMPLE_PACKAGE = REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example"

EXIT_OK = 0
EXIT_UNSATISFIED_STRICT = 1
EXIT_INPUT_ERROR = 2


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def write_request(path: Path, capabilities: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "record_type": "cam_assist_creation_studio_request",
                "record_version": "1.0.0",
                "package_reference": "pkg",
                "request_direction": "cam_assist_to_creation_studio",
                "requested_capabilities": capabilities,
                "contents": {},
                "authority": {},
            }
        ),
        encoding="utf-8",
    )
    return path


def write_profile(path: Path, capability_ids: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "record_type": "creation_studio_capability_profile",
                "record_version": "1.0.0",
                "profile_version": "1.0.0",
                "studio_reference": "cam-creation-studio",
                "publication_direction": "creation_studio_to_cam_assist",
                "capabilities": [{"capability_id": c} for c in capability_ids],
                "authority": {},
            }
        ),
        encoding="utf-8",
    )
    return path


def write_map(
    path: Path,
    mappings: list[dict],
    record_version: str = "1.0.0",
    map_version: str = "1.0.0",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "record_type": "cam_assist_creation_studio_capability_map",
                "record_version": record_version,
                "map_version": map_version,
                "mappings": mappings,
                "authority": {
                    "is_informational": True,
                    "does_not_authorize_execution": True,
                    "does_not_bypass_human_review": True,
                    "does_not_confirm_machine_readiness": True,
                    "does_not_grant_permission": True,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    package = tmp_path / "packages" / "pkg"
    package.mkdir(parents=True)
    write_request(
        tmp_path / "packages" / "creation_studio" / "pkg_request.json",
        ["simulation_request", "workholding_review"],
    )
    write_profile(
        tmp_path / "packages" / "creation_studio" / "capability_profile.json",
        ["simulation_support", "tool_library_editing"],
    )
    return package


# --- exact mode regression ---------------------------------------------------


def test_omitting_the_map_keeps_exact_a25_json_shape(workspace: Path):
    result = run("--package", str(workspace), "--json")
    assert result.returncode == EXIT_OK, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload) == {
        "inputs",
        "satisfied",
        "unsatisfied",
        "declared_but_unrequested",
        "findings",
    }
    assert "capability_map" not in payload["inputs"]
    assert "satisfaction_details" not in payload
    assert payload["satisfied"] == []
    assert payload["unsatisfied"] == ["simulation_request", "workholding_review"]
    assert payload["findings"][0]["code"] == "namespace_divergence"


def test_example_package_without_map_matches_a25_strict_failure():
    result = run("--package", str(EXAMPLE_PACKAGE), "--json", "--fail-on-unsatisfied")
    assert result.returncode == EXIT_UNSATISFIED_STRICT
    payload = json.loads(result.stdout)
    assert payload["satisfied"] == []
    assert "satisfaction_details" not in payload
    assert payload["findings"][0]["code"] == "namespace_divergence"


# --- mapped mode -------------------------------------------------------------


def test_capability_map_satisfies_an_explicit_row(workspace: Path, tmp_path: Path):
    mapping = write_map(
        tmp_path / "map.json",
        [
            {
                "request_capability": "simulation_request",
                "satisfied_by": ["simulation_support"],
                "rationale": "Explicit simulation correspondence.",
            }
        ],
    )
    result = run("--package", str(workspace), "--capability-map", str(mapping), "--json")
    assert result.returncode == EXIT_OK, result.stderr
    payload = json.loads(result.stdout)
    assert payload["satisfied"] == ["simulation_request"]
    assert payload["unsatisfied"] == ["workholding_review"]
    assert payload["inputs"]["capability_map"]["map_version"] == "1.0.0"
    assert payload["inputs"]["capability_map"]["record_version"] == "1.0.0"
    assert payload["inputs"]["capability_map"]["path"].endswith("map.json")
    methods = {d["request_capability"]: d["method"] for d in payload["satisfaction_details"]}
    assert methods["simulation_request"] == "mapped"
    codes = [f["code"] for f in payload["findings"]]
    assert "namespace_divergence" in codes
    assert "mapped_compatibility" in codes


def test_human_report_distinguishes_mapped_matches(workspace: Path, tmp_path: Path):
    mapping = write_map(
        tmp_path / "map.json",
        [
            {
                "request_capability": "simulation_request",
                "satisfied_by": ["simulation_support"],
                "rationale": "Explicit simulation correspondence.",
            }
        ],
    )
    result = run("--package", str(workspace), "--capability-map", str(mapping))
    assert result.returncode == EXIT_OK, result.stderr
    assert "[MATCH: mapped]" in result.stdout
    assert "simulation_request" in result.stdout
    assert "simulation_support" in result.stdout
    assert "Capability map:" in result.stdout
    assert "Map version:" in result.stdout
    assert "explicit compatibility declarations" in result.stdout


def test_map_versions_do_not_change_matching(workspace: Path, tmp_path: Path):
    mappings = [
        {
            "request_capability": "simulation_request",
            "satisfied_by": ["simulation_support"],
            "rationale": "Explicit simulation correspondence.",
        }
    ]
    a = write_map(tmp_path / "a.json", mappings, record_version="1.0.0", map_version="1.0.0")
    b = write_map(tmp_path / "b.json", mappings, record_version="9.9.9", map_version="3.2.1")
    first = json.loads(
        run("--package", str(workspace), "--capability-map", str(a), "--json").stdout
    )
    second = json.loads(
        run("--package", str(workspace), "--capability-map", str(b), "--json").stdout
    )
    for key in ("satisfied", "unsatisfied", "declared_but_unrequested", "satisfaction_details"):
        assert first[key] == second[key]
    assert first["inputs"]["capability_map"]["map_version"] != second["inputs"]["capability_map"]["map_version"]


def test_strict_mode_exits_0_when_mappings_resolve_every_request(tmp_path: Path):
    package = tmp_path / "packages" / "pkg"
    package.mkdir(parents=True)
    write_request(
        tmp_path / "packages" / "creation_studio" / "pkg_request.json",
        ["simulation_request"],
    )
    write_profile(
        tmp_path / "packages" / "creation_studio" / "capability_profile.json",
        ["simulation_support"],
    )
    mapping = write_map(
        tmp_path / "map.json",
        [
            {
                "request_capability": "simulation_request",
                "satisfied_by": ["simulation_support"],
                "rationale": "Explicit simulation correspondence.",
            }
        ],
    )
    result = run(
        "--package",
        str(package),
        "--capability-map",
        str(mapping),
        "--fail-on-unsatisfied",
        "--json",
    )
    assert result.returncode == EXIT_OK, result.stderr
    assert json.loads(result.stdout)["unsatisfied"] == []


def test_strict_mode_exits_1_when_any_request_remains_unresolved(workspace: Path, tmp_path: Path):
    mapping = write_map(
        tmp_path / "map.json",
        [
            {
                "request_capability": "simulation_request",
                "satisfied_by": ["simulation_support"],
                "rationale": "Explicit simulation correspondence.",
            }
        ],
    )
    result = run(
        "--package",
        str(workspace),
        "--capability-map",
        str(mapping),
        "--fail-on-unsatisfied",
        "--json",
    )
    assert result.returncode == EXIT_UNSATISFIED_STRICT
    assert json.loads(result.stdout)["unsatisfied"] == ["workholding_review"]


def test_canonical_map_on_shipped_example_preserves_raw_divergence():
    result = run(
        "--package",
        str(EXAMPLE_PACKAGE),
        "--capability-map",
        str(CANONICAL_MAP),
        "--json",
    )
    assert result.returncode == EXIT_OK, result.stderr
    payload = json.loads(result.stdout)
    assert payload["satisfied"] == ["feeds_speeds_recommendation"]
    assert payload["unsatisfied"] == ["operation_sequence_analysis", "tooling_review"]
    codes = [f["code"] for f in payload["findings"]]
    assert "namespace_divergence" in codes
    assert "mapped_compatibility" in codes
    assert payload["inputs"]["capability_map"]["path"].endswith(
        "contracts/creation_studio_capability_map.json"
    )


def test_repeated_mapped_cli_is_byte_identical(workspace: Path, tmp_path: Path):
    mapping = write_map(
        tmp_path / "map.json",
        [
            {
                "request_capability": "simulation_request",
                "satisfied_by": ["simulation_support"],
                "rationale": "Explicit simulation correspondence.",
            }
        ],
    )
    first = run("--package", str(workspace), "--capability-map", str(mapping), "--json")
    second = run("--package", str(workspace), "--capability-map", str(mapping), "--json")
    assert first.stdout == second.stdout


# --- malformed map -----------------------------------------------------------


def test_missing_map_exits_2_with_empty_json_stdout(workspace: Path, tmp_path: Path):
    result = run(
        "--package",
        str(workspace),
        "--capability-map",
        str(tmp_path / "nope.json"),
        "--json",
    )
    assert result.returncode == EXIT_INPUT_ERROR
    assert result.stdout.strip() == ""
    assert "ERROR" in result.stderr


def test_structurally_invalid_map_exits_2_with_empty_json_stdout(
    workspace: Path, tmp_path: Path
):
    bad = tmp_path / "bad.json"
    bad.write_text('{"record_type": "nope"}', encoding="utf-8")
    result = run("--package", str(workspace), "--capability-map", str(bad), "--json")
    assert result.returncode == EXIT_INPUT_ERROR
    assert result.stdout.strip() == ""
    assert "ERROR" in result.stderr


def test_unknown_source_in_map_exits_2(workspace: Path, tmp_path: Path):
    mapping = write_map(
        tmp_path / "map.json",
        [
            {
                "request_capability": "unknown_request_capability",
                "satisfied_by": ["simulation_support"],
                "rationale": "This source is not an A22 identifier.",
            }
        ],
    )
    result = run("--package", str(workspace), "--capability-map", str(mapping), "--json")
    assert result.returncode == EXIT_INPUT_ERROR
    assert result.stdout.strip() == ""
    assert "unknown_request_capability" in result.stderr


# --- help / authority --------------------------------------------------------


def test_help_documents_the_opt_in_map():
    result = run("--help")
    assert result.returncode == EXIT_OK
    collapsed = " ".join(result.stdout.split()).lower()
    assert "--capability-map" in result.stdout
    assert "exact identifier comparison only" in collapsed
    assert "not authorization" in collapsed


def test_mapped_json_carries_no_authority_equivalents(workspace: Path, tmp_path: Path):
    mapping = write_map(
        tmp_path / "map.json",
        [
            {
                "request_capability": "simulation_request",
                "satisfied_by": ["simulation_support"],
                "rationale": "Explicit simulation correspondence.",
            }
        ],
    )
    payload = json.loads(
        run("--package", str(workspace), "--capability-map", str(mapping), "--json").stdout
    )
    blob = json.dumps(payload)
    for word in (
        "approved",
        "authorized",
        "safe",
        "machine_ready",
        "execution_allowed",
        "permission",
    ):
        assert word not in blob
