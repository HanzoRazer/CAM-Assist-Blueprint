"""
Creator tests for CAM-A23 Creation Studio Capability Profile.

Witnesses:
- deterministic output (same inputs -> byte-identical file; input ORDER is not
  an input, because capabilities are sorted)
- semantic-version handling for the Creation-Studio-owned profile_version
- a sorted, de-duplicated capability list
- name normalization and the display_name rule
- documentation references attached by --capability-doc
- conventional output path (creation_studio/capability_profile.json) and --out
- exit codes: argument errors -> 1, write errors -> 2
- creator output passes the structural validator (the two layers agree)
- the creator mutates nothing outside its output file

The CLI is exercised as a subprocess, matching the other sidecar creators.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
CREATE_SCRIPT = SCRIPTS_DIR / "create_creation_studio_capability_profile.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_creation_studio_capability_profile.py"


def run(script: Path, *args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(script)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def run_create(*args) -> tuple[int, str, str]:
    return run(CREATE_SCRIPT, *args)


def cap_args(*names) -> list:
    args: list = []
    for name in names:
        args += ["--capability", name]
    return args


def profile_path(root: Path) -> Path:
    return root / "creation_studio" / "capability_profile.json"


def read_profile(root: Path) -> dict:
    return json.loads(profile_path(root).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Conventional output and record shape
# ---------------------------------------------------------------------------

def test_creates_at_conventional_path(tmp_path):
    code, out, err = run_create("--root", tmp_path, *cap_args("simulation_support"))
    assert code == 0, err
    assert profile_path(tmp_path).exists()
    assert str(profile_path(tmp_path)) in out


def test_record_shape(tmp_path):
    run_create("--root", tmp_path, *cap_args("simulation_support"))
    data = read_profile(tmp_path)
    assert data["record_type"] == "creation_studio_capability_profile"
    assert data["record_version"] == "1.0.0"
    assert data["profile_version"] == "1.0.0"
    assert data["studio_reference"] == "cam-creation-studio"
    assert data["publication_direction"] == "creation_studio_to_cam_assist"
    assert data["authority"] == {
        "is_informational": True,
        "does_not_authorize_execution": True,
        "does_not_bypass_human_review": True,
        "does_not_confirm_machine_readiness": True,
        "does_not_require_capability_use": True,
    }


def test_no_created_at(tmp_path):
    # Determinism is a hard requirement; a wall-clock stamp would defeat it.
    run_create("--root", tmp_path, *cap_args("simulation_support"))
    assert "created_at" not in read_profile(tmp_path)


def test_explicit_out_path(tmp_path):
    out_path = tmp_path / "nested" / "elsewhere.json"
    code, _out, err = run_create("--out", out_path, *cap_args("simulation_support"))
    assert code == 0, err
    assert out_path.exists()


# ---------------------------------------------------------------------------
# Determinism and sorting
# ---------------------------------------------------------------------------

def test_output_is_deterministic(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    caps = cap_args("simulation_support", "strategy_visualization", "tool_library_editing")
    run_create("--root", a, *caps)
    run_create("--root", b, *caps)
    assert profile_path(a).read_bytes() == profile_path(b).read_bytes()


def test_regeneration_is_byte_identical(tmp_path):
    caps = cap_args("simulation_support", "strategy_visualization")
    run_create("--root", tmp_path, *caps)
    first = profile_path(tmp_path).read_bytes()
    profile_path(tmp_path).unlink()
    run_create("--root", tmp_path, *caps)
    assert profile_path(tmp_path).read_bytes() == first


def test_capability_list_is_sorted(tmp_path):
    run_create(
        "--root", tmp_path,
        *cap_args("tool_library_editing", "feeds_speeds_authoring", "simulation_support"),
    )
    ids = [c["capability_id"] for c in read_profile(tmp_path)["capabilities"]]
    assert ids == sorted(ids)
    assert ids == ["feeds_speeds_authoring", "simulation_support", "tool_library_editing"]


def test_input_order_does_not_affect_output(tmp_path):
    # Unlike CAM-A22's request (where --capability order is preserved and
    # contract-significant), a profile declares a SET: the same capabilities in a
    # different order must produce the same bytes.
    a = tmp_path / "a"
    b = tmp_path / "b"
    run_create("--root", a, *cap_args("strategy_visualization", "simulation_support"))
    run_create("--root", b, *cap_args("simulation_support", "strategy_visualization"))
    assert profile_path(a).read_bytes() == profile_path(b).read_bytes()


def test_duplicate_capabilities_collapse(tmp_path):
    code, _out, err = run_create(
        "--root", tmp_path,
        *cap_args("simulation_support", "simulation_support", "strategy_visualization"),
    )
    assert code == 0, err
    ids = [c["capability_id"] for c in read_profile(tmp_path)["capabilities"]]
    assert ids == ["simulation_support", "strategy_visualization"]


def test_duplicate_via_normalization_collapses(tmp_path):
    # "Simulation Support" and "simulation_support" are the same capability.
    code, _out, err = run_create(
        "--root", tmp_path, *cap_args("simulation_support", "Simulation Support")
    )
    assert code == 0, err
    caps = read_profile(tmp_path)["capabilities"]
    assert [c["capability_id"] for c in caps] == ["simulation_support"]


# ---------------------------------------------------------------------------
# Name normalization and display_name
# ---------------------------------------------------------------------------

def test_identifier_input_emits_no_display_name(tmp_path):
    # A display_name echoing the identifier carries no information.
    run_create("--root", tmp_path, *cap_args("simulation_support"))
    entry = read_profile(tmp_path)["capabilities"][0]
    assert entry == {"capability_id": "simulation_support"}


def test_human_readable_name_is_normalized_and_preserved(tmp_path):
    run_create("--root", tmp_path, *cap_args("Feeds & Speeds Authoring"))
    entry = read_profile(tmp_path)["capabilities"][0]
    assert entry["capability_id"] == "feeds_speeds_authoring"
    assert entry["display_name"] == "Feeds & Speeds Authoring"


def test_normalization_examples(tmp_path):
    cases = {
        "Strategy Visualization": "strategy_visualization",
        "Post-Processor Education": "post_processor_education",
        "  Tool Library Editing  ": "tool_library_editing",
        "machining lesson playback": "machining_lesson_playback",
    }
    for supplied, expected in cases.items():
        root = tmp_path / expected
        code, _out, err = run_create("--root", root, *cap_args(supplied))
        assert code == 0, err
        assert read_profile(root)["capabilities"][0]["capability_id"] == expected


def test_unnormalizable_name_is_refused(tmp_path):
    # Refusing beats silently mangling: published identifiers are meant to be
    # stable forever, so a name that cannot yield a valid one is an error.
    code, _out, err = run_create("--root", tmp_path, *cap_args("!!!"))
    assert code == 1
    assert "capability identifier" in err
    assert not profile_path(tmp_path).exists()


def test_blank_capability_is_refused(tmp_path):
    code, _out, err = run_create("--root", tmp_path, *cap_args("   "))
    assert code == 1
    assert "blank" in err


def test_leading_digit_name_is_refused(tmp_path):
    code, _out, err = run_create("--root", tmp_path, *cap_args("3d Preview"))
    assert code == 1
    assert "capability identifier" in err


# ---------------------------------------------------------------------------
# Documentation references
# ---------------------------------------------------------------------------

def test_capability_doc_is_attached(tmp_path):
    code, _out, err = run_create(
        "--root", tmp_path,
        *cap_args("simulation_support"),
        "--capability-doc", "simulation_support=docs/simulation.md",
    )
    assert code == 0, err
    entry = read_profile(tmp_path)["capabilities"][0]
    assert entry["documentation_reference"] == "docs/simulation.md"


def test_capability_doc_accepts_human_readable_name(tmp_path):
    code, _out, err = run_create(
        "--root", tmp_path,
        *cap_args("Simulation Support"),
        "--capability-doc", "Simulation Support=docs/simulation.md",
    )
    assert code == 0, err
    entry = read_profile(tmp_path)["capabilities"][0]
    assert entry["capability_id"] == "simulation_support"
    assert entry["documentation_reference"] == "docs/simulation.md"


def test_capability_doc_existence_is_not_checked(tmp_path):
    # Existence is the validator's opt-in --check-references concern.
    code, _out, err = run_create(
        "--root", tmp_path,
        *cap_args("simulation_support"),
        "--capability-doc", "simulation_support=docs/does_not_exist.md",
    )
    assert code == 0, err


def test_capability_doc_for_undeclared_capability_is_refused(tmp_path):
    code, _out, err = run_create(
        "--root", tmp_path,
        *cap_args("simulation_support"),
        "--capability-doc", "tool_library_editing=docs/tools.md",
    )
    assert code == 1
    assert "undeclared" in err
    assert not profile_path(tmp_path).exists()


def test_malformed_capability_doc_is_refused(tmp_path):
    code, _out, err = run_create(
        "--root", tmp_path,
        *cap_args("simulation_support"),
        "--capability-doc", "no_equals_sign",
    )
    assert code == 1
    assert "NAME=PATH" in err


def test_absolute_capability_doc_is_refused(tmp_path):
    for bad_ref in ("/etc/passwd", "C:/Windows/x.md"):
        code, _out, err = run_create(
            "--root", tmp_path / "abs",
            *cap_args("simulation_support"),
            "--capability-doc", f"simulation_support={bad_ref}",
        )
        assert code == 1, bad_ref
        assert "relative" in err


def test_conflicting_capability_docs_are_refused(tmp_path):
    code, _out, err = run_create(
        "--root", tmp_path,
        *cap_args("simulation_support"),
        "--capability-doc", "simulation_support=docs/a.md",
        "--capability-doc", "simulation_support=docs/b.md",
    )
    assert code == 1
    assert "twice" in err


# ---------------------------------------------------------------------------
# Versions and studio reference
# ---------------------------------------------------------------------------

def test_profile_version_is_settable(tmp_path):
    code, _out, err = run_create(
        "--root", tmp_path, "--profile-version", "2.5.1", *cap_args("simulation_support")
    )
    assert code == 0, err
    data = read_profile(tmp_path)
    assert data["profile_version"] == "2.5.1"
    # The record FORMAT version is owned by this repository and does not move
    # with the Creation-Studio-owned capability-set version.
    assert data["record_version"] == "1.0.0"


def test_malformed_profile_version_is_refused(tmp_path):
    code, _out, err = run_create(
        "--root", tmp_path, "--profile-version", "2.5", *cap_args("simulation_support")
    )
    assert code == 1
    assert "profile-version" in err
    assert not profile_path(tmp_path).exists()


def test_studio_reference_is_settable(tmp_path):
    code, _out, err = run_create(
        "--root", tmp_path, "--studio-reference", "cam-creation-studio@2.5.1",
        *cap_args("simulation_support"),
    )
    assert code == 0, err
    assert read_profile(tmp_path)["studio_reference"] == "cam-creation-studio@2.5.1"


def test_blank_studio_reference_is_refused(tmp_path):
    code, _out, err = run_create(
        "--root", tmp_path, "--studio-reference", "   ", *cap_args("simulation_support")
    )
    assert code == 1
    assert "studio-reference" in err


# ---------------------------------------------------------------------------
# Argument and write errors
# ---------------------------------------------------------------------------

def test_no_capability_is_refused(tmp_path):
    code, _out, err = run_create("--root", tmp_path)
    assert code == 1
    assert "--capability" in err
    assert not profile_path(tmp_path).exists()


def test_existing_output_without_force_is_refused(tmp_path):
    run_create("--root", tmp_path, *cap_args("simulation_support"))
    before = profile_path(tmp_path).read_bytes()
    code, _out, err = run_create("--root", tmp_path, *cap_args("tool_library_editing"))
    assert code == 1
    assert "--force" in err
    assert profile_path(tmp_path).read_bytes() == before


def test_force_overwrites(tmp_path):
    run_create("--root", tmp_path, *cap_args("simulation_support"))
    code, _out, err = run_create(
        "--root", tmp_path, *cap_args("tool_library_editing"), "--force"
    )
    assert code == 0, err
    ids = [c["capability_id"] for c in read_profile(tmp_path)["capabilities"]]
    assert ids == ["tool_library_editing"]


def test_unwritable_output_returns_2(tmp_path):
    # A file where a directory must go: mkdir fails, and directory-creation
    # shares the write-error class.
    blocker = tmp_path / "creation_studio"
    blocker.write_text("not a directory", encoding="utf-8")
    code, _out, err = run_create("--root", tmp_path, *cap_args("simulation_support"))
    assert code == 2
    assert "Failed to write" in err


def test_quiet_prints_only_path(tmp_path):
    code, out, err = run_create("--root", tmp_path, *cap_args("simulation_support"), "--quiet")
    assert code == 0, err
    assert out.strip() == str(profile_path(tmp_path))


# ---------------------------------------------------------------------------
# Creator and validator agree
# ---------------------------------------------------------------------------

def test_created_profile_passes_validator(tmp_path):
    run_create(
        "--root", tmp_path,
        *cap_args("Feeds & Speeds Authoring", "simulation_support", "tool_library_editing"),
        "--capability-doc", "simulation_support=docs/simulation.md",
    )
    code, _out, err = run(VALIDATE_SCRIPT, profile_path(tmp_path))
    assert code == 0, err


def test_created_profile_passes_schema(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (REPO_ROOT / "schemas" / "creation_studio_capability_profile.schema.json").read_text(
            encoding="utf-8"
        )
    )
    run_create("--root", tmp_path, *cap_args("Feeds & Speeds Authoring", "simulation_support"))
    jsonschema.Draft202012Validator(schema).validate(read_profile(tmp_path))


def test_creator_mutates_nothing_else(tmp_path):
    other = tmp_path / "untouched"
    other.mkdir()
    (other / "file.txt").write_text("original", encoding="utf-8")
    before = {p.relative_to(other).as_posix(): p.read_bytes()
              for p in other.rglob("*") if p.is_file()}
    run_create("--root", tmp_path, *cap_args("simulation_support"))
    after = {p.relative_to(other).as_posix(): p.read_bytes()
             for p in other.rglob("*") if p.is_file()}
    assert before == after
