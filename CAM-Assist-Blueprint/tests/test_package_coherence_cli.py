"""CAM-A28 CLI process-boundary tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from package_coherence_fixtures import assumptions, make_package, write_json, write_sidecar_set

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "audit_package_coherence.py"


def run_audit(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_clean_package_exits_0(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "luthiers-toolbox:vcarve:test-001")
    result = run_audit("--package", str(package))
    assert result.returncode == 0, result.stderr
    assert "Package Coherence Audit" in result.stdout
    assert "does not approve a package" in result.stdout


def test_errors_are_advisory_by_default(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_json(
        tmp_path / "traceability" / f"{package.name}_assumptions.json",
        assumptions("other"),
    )
    result = run_audit("--package", str(package))
    assert result.returncode == 0, result.stderr
    assert "PACKAGE_REFERENCE_MISMATCH" in result.stdout


def test_fail_on_errors_exits_1(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_json(
        tmp_path / "traceability" / f"{package.name}_assumptions.json",
        assumptions("other"),
    )
    result = run_audit("--package", str(package), "--fail-on-errors")
    assert result.returncode == 1
    assert "PACKAGE_REFERENCE_MISMATCH" in result.stdout


def test_warnings_do_not_fail_strict_mode(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    result = run_audit("--package", str(package), "--fail-on-errors")
    assert result.returncode == 0, result.stderr


def test_json_is_stdout_pure_and_identical_in_strict_mode(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_json(
        tmp_path / "traceability" / f"{package.name}_assumptions.json",
        assumptions("other"),
    )
    default = run_audit("--package", str(package), "--json")
    strict = run_audit("--package", str(package), "--json", "--fail-on-errors")
    assert default.returncode == 0
    assert strict.returncode == 1
    assert default.stderr == ""
    assert strict.stderr == ""
    assert default.stdout == strict.stdout
    payload = json.loads(default.stdout)
    assert payload["summary"]["errors"] >= 1
    assert not Path(payload["artifacts"]["manifest"]["path"]).is_absolute()
    assert "\\" not in payload["artifacts"]["manifest"]["path"]


def test_json_is_byte_identical_across_discovery_order(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "luthiers-toolbox:vcarve:test-001")
    first = run_audit("--package", str(package), "--json")
    second = run_audit("--package", str(package), "--json")
    assert first.stdout == second.stdout


def test_missing_package_exits_2_without_json(tmp_path: Path) -> None:
    result = run_audit("--package", str(tmp_path / "absent"), "--json")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback (most recent call last)" not in result.stderr
    assert "not found" in result.stderr


def test_invalid_manifest_exits_2(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "manifest.json").write_text("{}\n", encoding="utf-8")
    result = run_audit("--package", str(package), "--json")
    assert result.returncode == 2
    assert result.stdout == ""


def test_audit_does_not_mutate_artifacts(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    write_sidecar_set(package, "luthiers-toolbox:vcarve:test-001")
    files = [path for path in tmp_path.rglob("*") if path.is_file()]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    result = run_audit("--package", str(package), "--json")
    assert result.returncode == 0, result.stderr
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    assert before == after


def test_cli_does_not_import_inspector() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "inspect_strategy_package" not in text
    inspector = (REPO_ROOT / "scripts" / "inspect_strategy_package.py").read_text(
        encoding="utf-8"
    )
    assert "package_coherence" not in inspector
    assert "audit_package_coherence" not in inspector
    assert "from _shared.package_discovery import" in inspector
