"""
CAM-A27 shared capability-map module.

Filesystem-light tests of the import-stable module. No CLI argument parsing
and no executable side effects. The module must be importable when scripts/
is on sys.path, independently of either CLI adapter.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
CANONICAL_MAP = REPO_ROOT / "contracts" / "creation_studio_capability_map.json"

sys.path.insert(0, str(SCRIPTS))

from _shared.creation_studio_capability_map import (  # noqa: E402
    A22_SCHEMA_RELATIVE,
    CapabilityMapContractError,
    CapabilityMapInputError,
    build_mapping_index,
    default_a22_schema_path,
    get_project_root,
    load_a22_request_enum,
    load_capability_map,
    load_capability_map_document,
    locate_project_root,
    normalize_provenance_path,
    validate_capability_map_document,
)
import _shared.creation_studio_capability_map as shared_module  # noqa: E402


CANONICAL_INDEX = {
    "feeds_speeds_recommendation": ["feeds_speeds_authoring"],
    "gcode_explanation": ["gcode_tutorial_generation", "post_processor_education"],
    "simulation_request": ["simulation_support"],
}


def test_importing_the_shared_module_has_no_cli_side_effects(capsys):
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert callable(load_capability_map)
    assert callable(build_mapping_index)
    assert not hasattr(shared_module, "A22_SCHEMA")
    assert not hasattr(shared_module, "REPO_ROOT")
    assert callable(default_a22_schema_path)
    assert callable(get_project_root)


def test_scripts_do_not_import_one_another():
    validator = (SCRIPTS / "validate_creation_studio_capability_map.py").read_text(
        encoding="utf-8"
    )
    reconciler = (SCRIPTS / "reconcile_creation_studio_capabilities.py").read_text(
        encoding="utf-8"
    )
    assert "from validate_creation_studio_capability_map import" not in reconciler
    assert "import validate_creation_studio_capability_map" not in reconciler
    assert "from reconcile_creation_studio_capabilities import" not in validator
    assert "import reconcile_creation_studio_capabilities" not in validator
    assert "from _shared.creation_studio_capability_map import" in validator
    assert "from _shared.creation_studio_capability_map import" in reconciler


def test_canonical_map_index_is_deterministic():
    doc, index, identity = load_capability_map(CANONICAL_MAP)
    assert index == CANONICAL_INDEX
    assert identity.record_version == "1.0.0"
    assert identity.map_version == "1.0.0"
    again = build_mapping_index(doc)
    assert again == CANONICAL_INDEX
    assert json.dumps(index, sort_keys=True) == json.dumps(CANONICAL_INDEX, sort_keys=True)


def test_canonical_mapping_rows_are_unchanged():
    doc = json.loads(CANONICAL_MAP.read_text(encoding="utf-8"))
    rows = {
        entry["request_capability"]: entry["satisfied_by"]
        for entry in doc["mappings"]
    }
    assert rows == {
        "feeds_speeds_recommendation": ["feeds_speeds_authoring"],
        "gcode_explanation": ["gcode_tutorial_generation", "post_processor_education"],
        "simulation_request": ["simulation_support"],
    }


def test_normalize_provenance_path_collapses_equivalent_relative_spellings():
    assert normalize_provenance_path("./contracts/creation_studio_capability_map.json") == (
        "contracts/creation_studio_capability_map.json"
    )
    assert normalize_provenance_path(
        "contracts/../contracts/creation_studio_capability_map.json"
    ) == "contracts/creation_studio_capability_map.json"
    assert normalize_provenance_path(
        Path("contracts") / ".." / "contracts" / "creation_studio_capability_map.json"
    ) == "contracts/creation_studio_capability_map.json"


def test_normalize_provenance_path_does_not_absolutize_a_relative_input():
    raw = "contracts/creation_studio_capability_map.json"
    normalized = normalize_provenance_path(raw)
    assert not Path(normalized).is_absolute()
    assert "\\" not in normalized


def test_missing_schema_is_typed_input_error(tmp_path: Path):
    with pytest.raises(CapabilityMapInputError):
        load_a22_request_enum(tmp_path / "absent.json")


def test_build_mapping_index_does_not_silently_skip(tmp_path: Path):
    with pytest.raises(CapabilityMapContractError):
        build_mapping_index({"mappings": [{"request_capability": "   ", "satisfied_by": ["x"]}]})


def test_load_capability_map_document_missing_file(tmp_path: Path):
    with pytest.raises(CapabilityMapInputError, match="not found"):
        load_capability_map_document(tmp_path / "nope.json")


def test_validate_document_accepts_a_supplied_enum(tmp_path: Path):
    # Supplying the enum avoids touching the on-disk schema.
    result = validate_capability_map_document(
        {
            "record_type": "cam_assist_creation_studio_capability_map",
            "record_version": "1.0.0",
            "map_version": "1.0.0",
            "mappings": [],
            "authority": {
                "is_informational": True,
                "does_not_authorize_execution": True,
                "does_not_bypass_human_review": True,
                "does_not_confirm_machine_readiness": True,
                "does_not_grant_permission": True,
            },
        },
        a22_enum=["simulation_request"],
    )
    assert result.valid


def test_a22_schema_default_resolves_to_on_disk_request_schema() -> None:
    """Default A22 path must be the schema next to this project's scripts/."""
    expected = (REPO_ROOT / A22_SCHEMA_RELATIVE).resolve()
    assert expected.is_file()
    resolved = default_a22_schema_path().resolve()
    assert resolved == expected
    assert resolved.parent.name == "schemas"
    assert resolved.parent.parent == REPO_ROOT
    assert get_project_root() == REPO_ROOT


def test_locate_project_root_is_cam_assist_not_git_monorepo() -> None:
    """Discovery must stop at the project that owns schemas/, not the git root."""
    project = locate_project_root()
    assert project == REPO_ROOT
    assert (project / "scripts").is_dir()
    assert (project / A22_SCHEMA_RELATIVE).is_file()
    # This checkout may sit inside a larger git tree. The directory above
    # CAM-Assist-Blueprint is not the project root even if it is the git root.
    parent = project.parent
    assert not (parent / A22_SCHEMA_RELATIVE).is_file()
    from_tests = locate_project_root(Path(__file__))
    assert from_tests == REPO_ROOT


def test_load_a22_request_enum_default_reads_on_disk_schema() -> None:
    """Calling the loader with no path must read the real A22 request enum."""
    on_disk = json.loads((REPO_ROOT / A22_SCHEMA_RELATIVE).read_text(encoding="utf-8"))
    expected = on_disk["properties"]["requested_capabilities"]["items"]["enum"]
    assert load_a22_request_enum() == expected
    assert "feeds_speeds_recommendation" in expected
    assert "simulation_request" in expected


def test_fixed_parent_hop_count_is_layout_sensitive() -> None:
    """Three hops land on this project today; one more hop leaves schemas/ behind."""
    shared_file = REPO_ROOT / "scripts" / "_shared" / "creation_studio_capability_map.py"
    three_hops = shared_file.resolve().parent.parent.parent
    four_hops = shared_file.resolve().parent.parent.parent.parent
    assert three_hops == REPO_ROOT
    assert (three_hops / A22_SCHEMA_RELATIVE).is_file()
    assert four_hops != REPO_ROOT
    assert not (four_hops / A22_SCHEMA_RELATIVE).is_file()
    assert locate_project_root(shared_file) == three_hops


def test_locate_project_root_raises_when_schema_absent(tmp_path: Path) -> None:
    with pytest.raises(CapabilityMapInputError, match="A22 request schema not found"):
        locate_project_root(tmp_path)


def test_import_succeeds_when_on_disk_schema_is_absent(tmp_path: Path) -> None:
    """Partial checkout / isolated tooling must be able to import the module."""
    dest = tmp_path / "creation_studio_capability_map.py"
    dest.write_text(
        (SCRIPTS / "_shared" / "creation_studio_capability_map.py").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("isolated_capability_map", dest)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.load_a22_request_enum)
    with pytest.raises(module.CapabilityMapInputError, match="A22 request schema"):
        module.default_a22_schema_path()
    with pytest.raises(module.CapabilityMapInputError, match="A22 request schema"):
        module.load_a22_request_enum()
