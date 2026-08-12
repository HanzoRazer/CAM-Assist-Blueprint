"""
CAM-A25 CLI: input resolution, exit codes, and output-stream discipline.

Runs the script as a subprocess, matching the convention used by the other CLI
suites, so these tests exercise the real entry point rather than an in-process
shortcut.

Two traps are pinned here specifically:

1. Profile discovery must stop on the fixed capability_profile.json FILE, not on
   the first creation_studio/ DIRECTORY. A package's request sidecars live in a
   directory of that name, so a directory-only search resolves to a location
   holding no profile.

2. --json must put JSON and nothing else on stdout. Diagnostics belong on stderr
   or a CI caller receives unparseable output.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "reconcile_creation_studio_capabilities.py"

EXIT_OK = 0
EXIT_UNSATISFIED_STRICT = 1
EXIT_INPUT_ERROR = 2


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
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


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A conventional layout: <root>/packages/pkg with <root>/creation_studio/."""
    package = tmp_path / "packages" / "pkg"
    package.mkdir(parents=True)
    write_request(tmp_path / "packages" / "creation_studio" / "pkg_request.json", ["a", "b"])
    write_profile(tmp_path / "packages" / "creation_studio" / "capability_profile.json", ["b", "c"])
    return package


# --- conventional derivation -------------------------------------------------


def test_single_package_anchor_derives_both_inputs(workspace: Path):
    result = run("--package", str(workspace))
    assert result.returncode == EXIT_OK, result.stderr
    assert "Satisfied:                1" in result.stdout
    assert "Unsatisfied:              1" in result.stdout
    assert "Declared but unrequested: 1" in result.stdout


def test_report_names_the_resolved_inputs(workspace: Path):
    result = run("--package", str(workspace))
    assert "pkg_request.json" in result.stdout
    assert "capability_profile.json" in result.stdout


# --- provenance at the process boundary --------------------------------------


def test_json_provenance_reports_the_derived_paths(workspace: Path):
    payload = json.loads(run("--package", str(workspace), "--json").stdout)
    assert payload["inputs"]["request"]["path"].endswith(
        "packages/creation_studio/pkg_request.json"
    )
    assert payload["inputs"]["profile"]["path"].endswith(
        "packages/creation_studio/capability_profile.json"
    )


def test_json_provenance_paths_are_posix_normalized(workspace: Path):
    payload = json.loads(run("--package", str(workspace), "--json").stdout)
    for record in ("request", "profile"):
        assert "\\" not in payload["inputs"][record]["path"], "native separators leaked into JSON"


def test_json_provenance_surfaces_actual_record_fields(workspace: Path):
    payload = json.loads(run("--package", str(workspace), "--json").stdout)
    assert payload["inputs"]["request"]["record_version"] == "1.0.0"
    assert payload["inputs"]["request"]["package_reference"] == "pkg"
    assert payload["inputs"]["profile"]["profile_version"] == "1.0.0"
    assert payload["inputs"]["profile"]["studio_reference"] == "cam-creation-studio"


def test_json_provenance_reports_an_explicit_request_override(workspace: Path, tmp_path: Path):
    other = write_request(tmp_path / "elsewhere" / "other.json", ["c"])
    payload = json.loads(
        run("--package", str(workspace), "--request", str(other), "--json").stdout
    )
    # The override won, and the profile is still conventionally derived.
    assert payload["inputs"]["request"]["path"].endswith("elsewhere/other.json")
    assert payload["inputs"]["profile"]["path"].endswith("creation_studio/capability_profile.json")


def test_json_provenance_reports_an_explicit_profile_override(workspace: Path, tmp_path: Path):
    other = write_profile(tmp_path / "elsewhere" / "other.json", ["a"])
    payload = json.loads(
        run("--package", str(workspace), "--profile", str(other), "--json").stdout
    )
    assert payload["inputs"]["profile"]["path"].endswith("elsewhere/other.json")
    assert payload["inputs"]["request"]["path"].endswith("creation_studio/pkg_request.json")


def test_json_provenance_reports_both_overrides_simultaneously(workspace: Path, tmp_path: Path):
    req = write_request(tmp_path / "o" / "r.json", ["z"])
    prof = write_profile(tmp_path / "o" / "p.json", ["z"])
    payload = json.loads(
        run(
            "--package", str(workspace),
            "--request", str(req),
            "--profile", str(prof),
            "--json",
        ).stdout
    )
    assert payload["inputs"]["request"]["path"].endswith("o/r.json")
    assert payload["inputs"]["profile"]["path"].endswith("o/p.json")
    assert payload["satisfied"] == ["z"]


def test_human_report_shows_provenance_before_the_counts(workspace: Path):
    stdout = run("--package", str(workspace)).stdout
    assert stdout.index("Request:") < stdout.index("Requested:")
    assert stdout.index("Profile:") < stdout.index("Requested:")
    for label in ("Package:", "Request record version:", "Studio:", "Profile version:"):
        assert label in stdout


def test_provenance_does_not_change_the_reconciliation(tmp_path: Path):
    """Identical capability sets, different record metadata and paths."""
    payloads = []
    for name, version, studio in [("one", "1.0.0", "studio-a"), ("two", "9.9.9", "studio-b")]:
        package = tmp_path / name / "packages" / "pkg"
        package.mkdir(parents=True)
        base = tmp_path / name / "packages" / "creation_studio"
        write_request(base / "pkg_request.json", ["a", "b"])
        write_profile(base / "capability_profile.json", ["b", "c"])

        # Vary profile metadata without touching declared capabilities.
        doc = json.loads((base / "capability_profile.json").read_text(encoding="utf-8"))
        doc["profile_version"] = version
        doc["studio_reference"] = studio
        (base / "capability_profile.json").write_text(json.dumps(doc), encoding="utf-8")

        payloads.append(json.loads(run("--package", str(package), "--json").stdout))

    assert payloads[0]["inputs"] != payloads[1]["inputs"]
    for key in ("satisfied", "unsatisfied", "declared_but_unrequested", "findings"):
        assert payloads[0][key] == payloads[1][key], f"{key} varied with provenance"


def test_repeated_invocations_are_byte_identical(workspace: Path):
    first = run("--package", str(workspace), "--json")
    second = run("--package", str(workspace), "--json")
    assert first.stdout == second.stdout


def test_examples_layout_resolves_without_walking_up(tmp_path: Path):
    # examples/packages/<name> puts sibling roots under examples/, matching the
    # helper the CAM-A22 creator writes through.
    package = tmp_path / "examples" / "packages" / "demo"
    package.mkdir(parents=True)
    write_request(tmp_path / "examples" / "creation_studio" / "demo_request.json", ["x"])
    write_profile(tmp_path / "examples" / "creation_studio" / "capability_profile.json", ["x"])

    result = run("--package", str(package))
    assert result.returncode == EXIT_OK, result.stderr
    assert "Satisfied:                1" in result.stdout


def test_profile_is_found_at_a_workspace_root_above_the_package(tmp_path: Path):
    # The genuine installation-scoped case: profile above the package, not beside it.
    package = tmp_path / "deep" / "nested" / "packages" / "pkg"
    package.mkdir(parents=True)
    write_request(
        tmp_path / "deep" / "nested" / "packages" / "creation_studio" / "pkg_request.json", ["a"]
    )
    write_profile(tmp_path / "creation_studio" / "capability_profile.json", ["a"])

    result = run("--package", str(package))
    assert result.returncode == EXIT_OK, result.stderr
    assert "Satisfied:                1" in result.stdout


def test_profile_search_requires_the_file_not_merely_the_directory(tmp_path: Path):
    """THE TRAP: a creation_studio/ holding only requests must not stop the search.

    Nearest creation_studio/ has a request but no profile; the real profile is
    two levels up. A directory-only search resolves to the nearer directory and
    fails, so reaching the true profile proves the search matches the FILE.
    """
    package = tmp_path / "workspace" / "packages" / "pkg"
    package.mkdir(parents=True)
    decoy = tmp_path / "workspace" / "packages" / "creation_studio"
    write_request(decoy / "pkg_request.json", ["a"])
    assert decoy.is_dir() and not (decoy / "capability_profile.json").exists()

    write_profile(tmp_path / "creation_studio" / "capability_profile.json", ["a"])

    result = run("--package", str(package))
    assert result.returncode == EXIT_OK, result.stderr
    assert "Satisfied:                1" in result.stdout


def test_nearest_profile_wins_when_several_exist(tmp_path: Path):
    package = tmp_path / "workspace" / "packages" / "pkg"
    package.mkdir(parents=True)
    write_request(
        tmp_path / "workspace" / "packages" / "creation_studio" / "pkg_request.json", ["near"]
    )
    write_profile(
        tmp_path / "workspace" / "packages" / "creation_studio" / "capability_profile.json",
        ["near"],
    )
    write_profile(tmp_path / "creation_studio" / "capability_profile.json", ["far"])

    result = run("--package", str(package), "--json")
    payload = json.loads(result.stdout)
    assert payload["satisfied"] == ["near"]


# --- overrides and precedence ------------------------------------------------


def test_explicit_request_overrides_derivation(workspace: Path, tmp_path: Path):
    other = write_request(tmp_path / "elsewhere" / "other.json", ["c"])
    result = run("--package", str(workspace), "--request", str(other), "--json")
    assert result.returncode == EXIT_OK, result.stderr
    payload = json.loads(result.stdout)
    assert payload["satisfied"] == ["c"]  # from the override, not pkg_request.json


def test_explicit_profile_overrides_derivation(workspace: Path, tmp_path: Path):
    other = write_profile(tmp_path / "elsewhere" / "other.json", ["a", "b"])
    result = run("--package", str(workspace), "--profile", str(other), "--json")
    assert result.returncode == EXIT_OK, result.stderr
    payload = json.loads(result.stdout)
    assert payload["satisfied"] == ["a", "b"]
    assert payload["unsatisfied"] == []


def test_overriding_one_input_does_not_disable_derivation_of_the_other(
    workspace: Path, tmp_path: Path
):
    # Precedence is per input, independently.
    other = write_profile(tmp_path / "elsewhere" / "other.json", ["a"])
    result = run("--package", str(workspace), "--profile", str(other), "--json")
    assert result.returncode == EXIT_OK, result.stderr
    payload = json.loads(result.stdout)
    # 'a' and 'b' came from the DERIVED request; only the profile was overridden.
    assert payload["satisfied"] == ["a"]
    assert payload["unsatisfied"] == ["b"]


# --- exit code 2: input failures ---------------------------------------------


def test_derived_request_missing_exits_2(tmp_path: Path):
    package = tmp_path / "packages" / "pkg"
    package.mkdir(parents=True)
    write_profile(tmp_path / "packages" / "creation_studio" / "capability_profile.json", ["a"])

    result = run("--package", str(package))
    assert result.returncode == EXIT_INPUT_ERROR
    assert "ERROR" in result.stderr


def test_derived_profile_missing_exits_2(tmp_path: Path):
    package = tmp_path / "packages" / "pkg"
    package.mkdir(parents=True)
    write_request(tmp_path / "packages" / "creation_studio" / "pkg_request.json", ["a"])

    result = run("--package", str(package))
    assert result.returncode == EXIT_INPUT_ERROR
    # A missing profile is an input failure, never "nothing declared".
    assert "capability_profile.json" in result.stderr
    assert "Declared but unrequested" not in result.stdout


def test_explicit_request_missing_exits_2(workspace: Path, tmp_path: Path):
    result = run("--package", str(workspace), "--request", str(tmp_path / "nope.json"))
    assert result.returncode == EXIT_INPUT_ERROR
    assert "ERROR" in result.stderr


def test_explicit_profile_missing_exits_2(workspace: Path, tmp_path: Path):
    result = run("--package", str(workspace), "--profile", str(tmp_path / "nope.json"))
    assert result.returncode == EXIT_INPUT_ERROR
    assert "ERROR" in result.stderr


@pytest.mark.parametrize(
    "content,why",
    [
        ("{ not json", "unparseable"),
        ("[]", "not an object"),
        ('{"record_type": "x"}', "no requested_capabilities"),
        ('{"requested_capabilities": "a"}', "not an array"),
        ('{"requested_capabilities": [1, 2]}', "not strings"),
    ],
    ids=["unparseable", "not-object", "missing-field", "not-array", "not-strings"],
)
def test_malformed_request_exits_2(workspace: Path, tmp_path: Path, content: str, why: str):
    bad = tmp_path / "bad_request.json"
    bad.write_text(content, encoding="utf-8")
    result = run("--package", str(workspace), "--request", str(bad))
    assert result.returncode == EXIT_INPUT_ERROR, why
    assert "ERROR" in result.stderr


@pytest.mark.parametrize(
    "content,why",
    [
        ("{ not json", "unparseable"),
        ('{"record_type": "x"}', "no capabilities"),
        ('{"capabilities": "a"}', "not an array"),
        ('{"capabilities": ["a"]}', "entries not objects"),
        ('{"capabilities": [{"name": "a"}]}', "no capability_id"),
        ('{"capabilities": [{"capability_id": 7}]}', "capability_id not a string"),
    ],
    ids=["unparseable", "missing-field", "not-array", "not-objects", "no-id", "id-not-string"],
)
def test_malformed_profile_exits_2(workspace: Path, tmp_path: Path, content: str, why: str):
    bad = tmp_path / "bad_profile.json"
    bad.write_text(content, encoding="utf-8")
    result = run("--package", str(workspace), "--profile", str(bad))
    assert result.returncode == EXIT_INPUT_ERROR, why
    assert "ERROR" in result.stderr


# --- exit code policy --------------------------------------------------------


def test_valid_reconciliation_exits_0_even_with_unsatisfied(workspace: Path):
    # Advisory by default: a gap is information, not a gate.
    result = run("--package", str(workspace))
    assert result.returncode == EXIT_OK
    assert "Unsatisfied:              1" in result.stdout


def test_strict_mode_exits_1_when_unsatisfied(workspace: Path):
    result = run("--package", str(workspace), "--fail-on-unsatisfied")
    assert result.returncode == EXIT_UNSATISFIED_STRICT


def test_strict_mode_exits_0_when_all_satisfied(tmp_path: Path):
    package = tmp_path / "packages" / "pkg"
    package.mkdir(parents=True)
    write_request(tmp_path / "packages" / "creation_studio" / "pkg_request.json", ["a"])
    write_profile(tmp_path / "packages" / "creation_studio" / "capability_profile.json", ["a", "z"])

    result = run("--package", str(package), "--fail-on-unsatisfied")
    assert result.returncode == EXIT_OK  # declared_but_unrequested does not fail


def test_namespace_divergence_alone_never_changes_the_exit_code(tmp_path: Path):
    """Divergence is diagnostic evidence, not a second gate.

    Disjoint vocabularies produce the finding AND a non-empty unsatisfied set, so
    the distinction is only observable by checking that the default run still
    exits 0 while the finding is present.
    """
    package = tmp_path / "packages" / "pkg"
    package.mkdir(parents=True)
    write_request(tmp_path / "packages" / "creation_studio" / "pkg_request.json", ["a"])
    write_profile(tmp_path / "packages" / "creation_studio" / "capability_profile.json", ["z"])

    default = run("--package", str(package), "--json")
    assert default.returncode == EXIT_OK
    assert json.loads(default.stdout)["findings"][0]["code"] == "namespace_divergence"

    # Under strict mode the failure is attributable to unsatisfied, not the finding.
    strict = run("--package", str(package), "--fail-on-unsatisfied", "--json")
    assert strict.returncode == EXIT_UNSATISFIED_STRICT
    assert json.loads(strict.stdout)["unsatisfied"] == ["a"]


def test_strict_mode_does_not_change_the_reported_classification(workspace: Path):
    # Exit-status policy only: the payload must be identical either way.
    plain = run("--package", str(workspace), "--json")
    strict = run("--package", str(workspace), "--fail-on-unsatisfied", "--json")
    assert json.loads(plain.stdout) == json.loads(strict.stdout)


# --- stream discipline -------------------------------------------------------


def test_json_mode_emits_only_json_on_stdout(workspace: Path):
    result = run("--package", str(workspace), "--json")
    assert result.returncode == EXIT_OK
    payload = json.loads(result.stdout)  # would raise on any extra output
    assert set(payload) == {
        "inputs",
        "satisfied",
        "unsatisfied",
        "declared_but_unrequested",
        "findings",
    }
    # No human-report furniture leaked onto stdout. "Request:" and "Profile:" are
    # the human provenance labels; the JSON surface carries the same evidence as
    # structured fields instead.
    for fragment in ("Request:", "Profile:", "ADVISORY", "Requested:", "Studio:"):
        assert fragment not in result.stdout


def test_json_mode_keeps_input_errors_off_stdout(workspace: Path, tmp_path: Path):
    result = run("--package", str(workspace), "--profile", str(tmp_path / "nope.json"), "--json")
    assert result.returncode == EXIT_INPUT_ERROR
    assert result.stdout.strip() == ""  # a CI caller gets nothing to misparse
    assert "ERROR" in result.stderr


def test_json_mode_stays_clean_when_a_finding_is_present(tmp_path: Path):
    package = tmp_path / "packages" / "pkg"
    package.mkdir(parents=True)
    write_request(tmp_path / "packages" / "creation_studio" / "pkg_request.json", ["a"])
    write_profile(tmp_path / "packages" / "creation_studio" / "capability_profile.json", ["z"])

    result = run("--package", str(package), "--json")
    payload = json.loads(result.stdout)
    assert payload["findings"][0]["severity"] == "warning"
    assert "WARNING" not in result.stdout  # the human bracket form must not leak


# --- surface ------------------------------------------------------------------


def test_package_is_required(tmp_path: Path):
    result = run("--json")
    assert result.returncode != EXIT_OK
    assert "--package" in result.stderr


def test_help_states_the_advisory_boundary():
    result = run("--help")
    assert result.returncode == EXIT_OK
    # argparse re-wraps help text, so compare on collapsed whitespace rather
    # than depending on where the terminal width happens to break a line.
    collapsed = " ".join(result.stdout.split()).lower()
    assert "resolution anchor only" in collapsed
    assert "not authorization" in collapsed
    assert "no package ownership of the profile" in collapsed
    assert "never independently changes the exit code" in collapsed
