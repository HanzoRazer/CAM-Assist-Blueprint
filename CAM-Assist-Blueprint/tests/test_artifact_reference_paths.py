"""CAM-A29 contract tests for portable artifact reference paths.

Central invariant:

    resolve_declared_reference(output, relative_reference(output, target))
        == normalized target
"""

from __future__ import annotations

import os
import posixpath
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _shared.artifact_references import (  # noqa: E402
    normalize_reference_string,
    relative_reference,
    resolve_declared_reference,
    resolve_from_directory,
)


def _norm(path: Path) -> Path:
    return Path(posixpath.normpath(Path(path).as_posix()))


def test_same_directory_round_trip() -> None:
    declaring = Path("/x/traceability/decision.json")
    target = Path("/x/traceability/risk.json")
    stored = relative_reference(declaring, target)
    assert stored == "risk.json"
    assert "\\" not in stored
    assert resolve_declared_reference(declaring, stored) == _norm(target)


def test_sibling_directory_round_trip() -> None:
    declaring = Path("/x/traceability/bundle.json")
    target = Path("/x/review_annotations/annotations.json")
    stored = relative_reference(declaring, target)
    assert stored == "../review_annotations/annotations.json"
    assert resolve_declared_reference(declaring, stored) == _norm(target)


def test_nested_directory_round_trip() -> None:
    declaring = Path("/x/a/b/c/record.json")
    target = Path("/x/a/other/deep/file.json")
    stored = relative_reference(declaring, target)
    assert stored == "../../other/deep/file.json"
    assert "\\" not in stored
    assert resolve_declared_reference(declaring, stored) == _norm(target)


def test_forward_slash_serialization() -> None:
    declaring = Path("/x/traceability/decision.json")
    target = Path("/x/review_annotations/annotations.json")
    stored = relative_reference(declaring, target)
    assert "/" in stored
    assert "\\" not in stored
    assert normalize_reference_string("foo\\bar\\baz.json") == "foo/bar/baz.json"


def test_relative_reference_is_not_absolute() -> None:
    declaring = Path("/x/traceability/decision.json")
    target = Path("/x/traceability/risk.json")
    stored = relative_reference(declaring, target)
    assert not stored.startswith("/")
    assert not stored.startswith("\\")
    assert not (len(stored) >= 2 and stored[1] == ":")
    assert not Path(stored).is_absolute()


def test_resolution_independent_of_cwd(tmp_path: Path) -> None:
    declaring = tmp_path / "traceability" / "decision.json"
    target = tmp_path / "review_annotations" / "annotations.json"
    declaring.parent.mkdir()
    target.parent.mkdir()
    declaring.write_text("{}\n", encoding="utf-8")
    target.write_text("{}\n", encoding="utf-8")
    stored = relative_reference(declaring, target)
    first = resolve_declared_reference(declaring, stored)

    other = tmp_path / "unrelated" / "cwd"
    other.mkdir(parents=True)
    previous = os.getcwd()
    try:
        os.chdir(other)
        second = resolve_declared_reference(declaring, stored)
        assert first == second
        assert _norm(first) == _norm(target)
        assert first.exists()
    finally:
        os.chdir(previous)


def test_resolution_independent_of_cwd_via_subprocess(tmp_path: Path) -> None:
    declaring = tmp_path / "traceability" / "decision.json"
    target = tmp_path / "risk.json"
    declaring.parent.mkdir()
    declaring.write_text("{}\n", encoding="utf-8")
    target.write_text("{}\n", encoding="utf-8")
    snippet = (
        "import sys\n"
        "from pathlib import Path\n"
        "from _shared.artifact_references import relative_reference, resolve_declared_reference\n"
        "declaring = Path(sys.argv[1])\n"
        "target = Path(sys.argv[2])\n"
        "stored = relative_reference(declaring, target)\n"
        "print(resolve_declared_reference(declaring, stored).as_posix())\n"
    )
    env = os.environ.copy()
    pythonpath = str(SCRIPTS)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = pythonpath if not existing else pythonpath + os.pathsep + existing
    cwd_a = tmp_path / "cwd_a"
    cwd_b = tmp_path / "cwd_b"
    cwd_a.mkdir()
    cwd_b.mkdir()
    cmd = [sys.executable, "-c", snippet, str(declaring), str(target)]
    first = subprocess.run(cmd, cwd=cwd_a, capture_output=True, text=True, env=env, check=True)
    second = subprocess.run(cmd, cwd=cwd_b, capture_output=True, text=True, env=env, check=True)
    assert first.stdout == second.stdout
    assert first.stdout.strip() == _norm(target).as_posix()


def test_repo_root_style_path_does_not_get_a_fallback(tmp_path: Path) -> None:
    declaring = tmp_path / "examples" / "traceability" / "decision.json"
    real_target = tmp_path / "examples" / "traceability" / "risk.json"
    declaring.parent.mkdir(parents=True)
    declaring.write_text("{}\n", encoding="utf-8")
    real_target.write_text("{}\n", encoding="utf-8")
    malformed = "examples/traceability/risk.json"
    resolved = resolve_declared_reference(declaring, malformed)
    assert resolved != _norm(real_target)
    assert resolved == _norm(declaring.parent / malformed)
    assert not resolved.exists()
    assert real_target.exists()


def test_dotdot_sibling_navigation_is_supported() -> None:
    declaring = Path("/package/traceability/bundle.json")
    stored = "../review_annotations/annotations.json"
    resolved = resolve_declared_reference(declaring, stored)
    assert resolved == Path("/package/review_annotations/annotations.json")


def test_resolve_does_not_require_target_existence(tmp_path: Path) -> None:
    declaring = tmp_path / "decision.json"
    declaring.write_text("{}\n", encoding="utf-8")
    resolved = resolve_declared_reference(declaring, "missing.json")
    assert resolved == tmp_path / "missing.json"
    assert not resolved.exists()


def test_resolve_from_directory_matches_declaring_parent() -> None:
    declaring = Path("/x/traceability/bundle.json")
    stored = "risk.json"
    assert resolve_from_directory(declaring.parent, stored) == resolve_declared_reference(
        declaring, stored
    )


def test_creation_validation_symmetry_for_all_shapes() -> None:
    pairs = [
        (Path("/x/traceability/decision.json"), Path("/x/traceability/risk.json")),
        (Path("/x/traceability/bundle.json"), Path("/x/review_annotations/a.json")),
        (Path("/x/a/b/c/record.json"), Path("/x/a/other/deep/file.json")),
        (Path("/workspace/out/handoff.json"), Path("/workspace/pkg/manifest.json")),
    ]
    for declaring, target in pairs:
        stored = relative_reference(declaring, target)
        assert "\\" not in stored
        assert resolve_declared_reference(declaring, stored) == _norm(target)
