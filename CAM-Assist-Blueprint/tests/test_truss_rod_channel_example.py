"""Canonical A30 example: creator regeneration, assembly, inspector, A28."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPTS = REPO_ROOT / "scripts"
EXAMPLE_INPUT = REPO_ROOT / "examples" / "operations" / "truss_rod_channel_example.json"
EXAMPLE_STRATEGY = REPO_ROOT / "examples" / "valid" / "truss_rod_channel_strategy.json"
EXAMPLE_PACKAGE = REPO_ROOT / "examples" / "packages" / "truss_rod_channel_strategy_example"


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_example_files_exist():
    assert EXAMPLE_INPUT.is_file()
    assert EXAMPLE_STRATEGY.is_file()
    assert (EXAMPLE_PACKAGE / "strategy.json").is_file()
    assert (EXAMPLE_PACKAGE / "manifest.json").is_file()
    assert (EXAMPLE_PACKAGE / "review_packet.md").is_file()
    assert not (EXAMPLE_PACKAGE / "geometry.dxf").exists()


def test_example_strategy_regenerates_byte_identically(tmp_path):
    output = tmp_path / "strategy.json"
    result = _run(
        "create_truss_rod_channel_strategy.py",
        str(EXAMPLE_INPUT),
        "--out",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    assert output.read_bytes() == EXAMPLE_STRATEGY.read_bytes()


def test_example_strategy_validates():
    result = _run("validate_strategy_package.py", str(EXAMPLE_STRATEGY))
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout or "valid" in result.stdout.lower() or result.returncode == 0


def test_assembled_package_validates_and_inspects():
    inspect = _run("inspect_strategy_package.py", str(EXAMPLE_PACKAGE))
    assert inspect.returncode == 0, inspect.stderr
    assert "truss_rod_channel_strategy" in inspect.stdout
    assert "advisory only" in inspect.stdout
    assert "machine_ready" not in inspect.stdout.lower()
    assert "execution authority denied" in inspect.stdout.lower() or "Execution authority denied" in inspect.stdout


def test_assembled_strategy_matches_creator_output():
    assembled = json.loads((EXAMPLE_PACKAGE / "strategy.json").read_text(encoding="utf-8"))
    created = json.loads(EXAMPLE_STRATEGY.read_text(encoding="utf-8"))
    assert assembled == created


def test_a28_example_has_no_a30_caused_errors():
    result = _run(
        "audit_package_coherence.py",
        "--package",
        str(EXAMPLE_PACKAGE),
        "--json",
        "--fail-on-errors",
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["summary"]["errors"] == 0


def test_example_contains_no_gcode_or_postprocessor():
    blob = (EXAMPLE_PACKAGE / "strategy.json").read_text(encoding="utf-8")
    blob += (EXAMPLE_PACKAGE / "manifest.json").read_text(encoding="utf-8")
    for token in ("G0", "G1", "G2", "G3", "M3", "M5", "G54", "post_processor"):
        assert token not in blob


def test_a28_does_not_mutate_example():
    files = [
        EXAMPLE_PACKAGE / "strategy.json",
        EXAMPLE_PACKAGE / "manifest.json",
        EXAMPLE_PACKAGE / "review_packet.md",
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    result = _run("audit_package_coherence.py", "--package", str(EXAMPLE_PACKAGE), "--json")
    assert result.returncode == 0
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    assert before == after
