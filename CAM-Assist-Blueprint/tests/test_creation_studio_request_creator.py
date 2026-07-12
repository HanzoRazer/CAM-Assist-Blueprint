"""
Phase 4 tests for CAM-A22 Creation Studio Capability Request — creator.

Witnesses (mapping to the dev-order test matrix):
- creator emits a valid request; generated request passes the structural validator
- the non-execution authority block (five const-true flags) is always emitted
- request_direction and requested_capabilities are always emitted
- the core three content references are always emitted
- federation id used when present, else the directory name
- multiple --capability flags supported; duplicates de-duplicated; order preserved
- at least one --capability required; unknown capability rejected (exit 1)
- conventional traceability bundle and production shop handoff discovered
- explicit bundle/handoff paths override conventional discovery
- missing optional references omitted
- request_context emitted only when a context flag is supplied
- references relative to the request file, forward-slashed
- default output convention correct
- overwrite blocked without --force
- source package not mutated
- NO created_at is emitted (deterministic artifact)
- output is deterministic: regeneration is byte-identical

The creator is reference-only: it never resolves or stats the referenced core
files, and an explicit bundle/handoff path is recorded as-is without an existence
check.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
CREATE_SCRIPT = SCRIPTS_DIR / "create_creation_studio_request.py"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_creation_studio_request.py"

CORE_SLOTS = {"package_manifest_file", "strategy_file", "review_packet_file"}


def run_script(script: Path, *args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(script)] + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def make_package(
    root: Path,
    name: str = "pkg",
    federated_id: str | None = None,
    strategy_file: str = "strategy.json",
    review_packet_file: str = "review_packet.md",
) -> Path:
    """Create a package dir with a manifest and the files it declares."""
    pkg = root / name
    pkg.mkdir(parents=True)
    manifest: dict = {
        "manifest_version": "1.1.0",
        "package_type": "cam_assist_strategy_package",
        "strategy_file": strategy_file,
        "review_packet_file": review_packet_file,
    }
    if federated_id is not None:
        manifest["federation"] = {"federated_package_id": federated_id}
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (pkg / strategy_file).write_text("{}", encoding="utf-8")
    (pkg / review_packet_file).write_text("# review\n", encoding="utf-8")
    return pkg


def write_conventional_bundle(root: Path, pkg_name: str) -> Path:
    d = root / "traceability"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{pkg_name}_bundle.json"
    path.write_text("{}", encoding="utf-8")
    return path


def write_conventional_handoff(root: Path, pkg_name: str) -> Path:
    d = root / "production_shop"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{pkg_name}_handoff.json"
    path.write_text("{}", encoding="utf-8")
    return path


def snapshot(d: Path) -> dict:
    return {
        p.relative_to(d).as_posix(): p.read_bytes()
        for p in d.rglob("*")
        if p.is_file()
    }


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cap(*names) -> list:
    args = []
    for n in names:
        args += ["--capability", n]
    return args


# ---------------------------------------------------------------------------
# Emits valid request; structural validator agrees
# ---------------------------------------------------------------------------

def test_creator_emits_valid_request(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "out" / "r.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert code == 0, err
    assert out.exists()
    req = load(out)
    assert req["record_type"] == "cam_assist_creation_studio_request"
    assert req["record_version"] == "1.0.0"


def test_generated_request_passes_structural_validator(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "out" / "r.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert code == 0, err
    vcode, vout, verr = run_script(VALIDATE_SCRIPT, out)
    assert vcode == 0, verr + vout


# ---------------------------------------------------------------------------
# Always-emitted invariants
# ---------------------------------------------------------------------------

def test_authority_block_always_emitted(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert load(out)["authority"] == {
        "is_informational": True,
        "does_not_authorize_execution": True,
        "does_not_bypass_human_review": True,
        "does_not_confirm_machine_readiness": True,
        "does_not_require_gcode_generation": True,
    }


def test_direction_always_emitted(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert load(out)["request_direction"] == "cam_assist_to_creation_studio"


def test_core_three_content_refs_emitted(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    contents = load(out)["contents"]
    assert CORE_SLOTS <= set(contents.keys())
    for slot in CORE_SLOTS:
        assert contents[slot]


def test_no_created_at_emitted(tmp_path):
    # The request is deterministic: it carries no created_at timestamp.
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert "created_at" not in load(out)


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

def test_multiple_capabilities_supported_order_preserved(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    run_script(
        CREATE_SCRIPT, "--package", pkg, "--out", out,
        *_cap("tooling_review", "feeds_speeds_recommendation", "simulation_request"),
    )
    assert load(out)["requested_capabilities"] == [
        "tooling_review", "feeds_speeds_recommendation", "simulation_request",
    ]


def test_duplicate_capabilities_deduplicated(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review", "tooling_review"))
    assert load(out)["requested_capabilities"] == ["tooling_review"]


def test_no_capability_is_error(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out)
    assert code == 1
    assert "at least one --capability" in err.lower()


def test_unknown_capability_is_error(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("make_sandwich"))
    assert code == 1
    assert "unknown capability" in err.lower()


# ---------------------------------------------------------------------------
# package_reference resolution
# ---------------------------------------------------------------------------

def test_package_reference_from_manifest_federation(tmp_path):
    pkg = make_package(tmp_path, federated_id="luthiers-toolbox:vcarve:example-001")
    out = tmp_path / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert load(out)["package_reference"] == "luthiers-toolbox:vcarve:example-001"


def test_package_reference_falls_back_to_dir_name(tmp_path):
    pkg = make_package(tmp_path, name="my_pkg")
    out = tmp_path / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert load(out)["package_reference"] == "my_pkg"


# ---------------------------------------------------------------------------
# Optional reference resolution: explicit > conventional > omit
# ---------------------------------------------------------------------------

def test_conventional_bundle_discovered(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_bundle(tmp_path, "pkg")
    out = tmp_path / "out" / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert "traceability_bundle_file" in load(out)["contents"]


def test_conventional_handoff_discovered(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_handoff(tmp_path, "pkg")
    out = tmp_path / "out" / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert "production_shop_handoff_file" in load(out)["contents"]


def test_explicit_bundle_overrides_conventional(tmp_path):
    pkg = make_package(tmp_path)
    write_conventional_bundle(tmp_path, "pkg")
    explicit = tmp_path / "explicit_bundle.json"
    explicit.write_text("{}", encoding="utf-8")
    out = tmp_path / "out" / "r.json"
    run_script(
        CREATE_SCRIPT, "--package", pkg, "--out", out,
        "--traceability-bundle", explicit, *_cap("tooling_review"),
    )
    assert load(out)["contents"]["traceability_bundle_file"].endswith("explicit_bundle.json")


def test_explicit_handoff_included(tmp_path):
    pkg = make_package(tmp_path)
    explicit = tmp_path / "elsewhere" / "custom_handoff.json"
    explicit.parent.mkdir(parents=True)
    explicit.write_text("{}", encoding="utf-8")
    out = tmp_path / "out" / "r.json"
    run_script(
        CREATE_SCRIPT, "--package", pkg, "--out", out,
        "--production-shop-handoff", explicit, *_cap("tooling_review"),
    )
    assert load(out)["contents"]["production_shop_handoff_file"].endswith("custom_handoff.json")


def test_missing_optional_refs_omitted(tmp_path):
    pkg = make_package(tmp_path)  # no conventional bundle/handoff, no explicit flags
    out = tmp_path / "out" / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    contents = load(out)["contents"]
    assert "traceability_bundle_file" not in contents
    assert "production_shop_handoff_file" not in contents


# ---------------------------------------------------------------------------
# request_context
# ---------------------------------------------------------------------------

def test_request_context_omitted_without_flags(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert "request_context" not in load(out)


def test_request_context_emitted_with_flags(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    run_script(
        CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"),
        "--material", "mahogany", "--operator-notes", "Review first.",
    )
    ctx = load(out)["request_context"]
    assert ctx == {"material": "mahogany", "operator_notes": "Review first."}


def test_blank_context_flag_is_rejected(tmp_path):
    # A supplied-but-blank value is most likely an input mistake. Fail clearly
    # instead of silently dropping an argument the caller explicitly provided.
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    code, _stdout, stderr = run_script(
        CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"),
        "--material", "   ",
    )
    assert code == 1
    assert "--material must not be blank" in stderr
    assert not out.exists()


def test_manifest_content_path_must_be_string(tmp_path):
    pkg = make_package(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["strategy_file"] = 42
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "r.json"
    code, _stdout, stderr = run_script(
        CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review")
    )
    assert code == 1
    assert "strategy_file must be a non-blank relative path" in stderr
    assert "Traceback" not in stderr


def test_manifest_content_path_cannot_escape_package(tmp_path):
    pkg = make_package(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["review_packet_file"] = "../outside.md"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "r.json"
    code, _stdout, stderr = run_script(
        CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review")
    )
    assert code == 1
    assert "review_packet_file must stay within the package directory" in stderr


def test_manifest_federated_id_must_be_non_blank_string(tmp_path):
    pkg = make_package(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["federation"] = {"federated_package_id": 42}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "r.json"
    code, _stdout, stderr = run_script(
        CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review")
    )
    assert code == 1
    assert "federated_package_id must be a non-blank string" in stderr
    assert "Traceback" not in stderr


def test_generated_request_with_context_passes_validator(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "out" / "r.json"
    run_script(
        CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"),
        "--material", "mahogany", "--machine-profile", "shopbot-desktop",
    )
    vcode, vout, verr = run_script(VALIDATE_SCRIPT, out)
    assert vcode == 0, verr + vout


# ---------------------------------------------------------------------------
# Path shape: relative to the output file, forward-slashed
# ---------------------------------------------------------------------------

def test_paths_relative_to_output_file(tmp_path):
    examples = tmp_path / "examples"
    pkg = make_package(examples / "packages", name="pkg")
    out = examples / "creation_studio" / "pkg_request.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    ref = load(out)["contents"]["package_manifest_file"]
    assert ref == "../packages/pkg/manifest.json"


def test_paths_use_forward_slashes(tmp_path):
    examples = tmp_path / "examples"
    pkg = make_package(examples / "packages", name="pkg")
    out = examples / "creation_studio" / "pkg_request.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    for ref in load(out)["contents"].values():
        assert "\\" not in ref


def test_default_output_location(tmp_path):
    examples = tmp_path / "examples"
    pkg = make_package(examples / "packages", name="pkg")
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, *_cap("tooling_review"))
    assert code == 0, err
    assert (examples / "creation_studio" / "pkg_request.json").exists()


# ---------------------------------------------------------------------------
# Overwrite protection; no mutation; missing package; determinism
# ---------------------------------------------------------------------------

def test_refuses_overwrite_without_force(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    code1, _o1, _e1 = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert code1 == 0
    code2, _o2, err2 = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert code2 == 1
    assert "already exists" in err2


def test_force_overwrites(tmp_path):
    pkg = make_package(tmp_path)
    out = tmp_path / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, "--force", *_cap("tooling_review"))
    assert code == 0, err


def test_source_package_not_mutated(tmp_path):
    pkg = make_package(tmp_path, federated_id="lt:vcarve:x")
    write_conventional_bundle(tmp_path, "pkg")
    write_conventional_handoff(tmp_path, "pkg")
    before = snapshot(pkg)
    out = tmp_path / "out" / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert snapshot(pkg) == before


def test_missing_package_exits_nonzero(tmp_path):
    code, _o, err = run_script(CREATE_SCRIPT, "--package", tmp_path / "nope", *_cap("tooling_review"))
    assert code != 0
    assert "not found" in err.lower()


def test_absent_manifest_falls_back_to_dir_name(tmp_path):
    # No manifest at all is fine: conventions apply and identity is the dir name.
    pkg = tmp_path / "no_manifest_pkg"
    pkg.mkdir()
    out = tmp_path / "r.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert code == 0, err
    assert load(out)["package_reference"] == "no_manifest_pkg"


def test_corrupt_manifest_is_error(tmp_path):
    # A present-but-unparseable manifest must fail loudly rather than silently
    # falling back to a request built from corrupt/fallback identity.
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_text("{ not valid json", encoding="utf-8")
    out = tmp_path / "r.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert code == 1
    assert "manifest.json" in err
    assert not out.exists()


def test_output_is_deterministic(tmp_path):
    # Regenerating with identical inputs yields byte-identical output (no created_at).
    pkg = make_package(tmp_path)
    write_conventional_bundle(tmp_path, "pkg")
    write_conventional_handoff(tmp_path, "pkg")
    out = tmp_path / "out" / "r.json"
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review", "feeds_speeds_recommendation"))
    first = out.read_bytes()
    run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, "--force", *_cap("tooling_review", "feeds_speeds_recommendation"))
    assert out.read_bytes() == first


# ---------------------------------------------------------------------------
# Exit-code contract: write errors are distinct from argument errors
# ---------------------------------------------------------------------------

def test_write_error_returns_exit_2(tmp_path):
    pkg = make_package(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory", encoding="utf-8")
    out = blocker / "sub" / "r.json"
    code, _o, err = run_script(CREATE_SCRIPT, "--package", pkg, "--out", out, *_cap("tooling_review"))
    assert code == 2, err
    assert "Failed to write" in err


def _load_creator_module():
    spec = importlib.util.spec_from_file_location("_create_csr", CREATE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cross_drive_relpath_reported_cleanly(tmp_path, monkeypatch):
    # os.path.relpath raises ValueError for paths on different Windows drives.
    # That must surface as a clean argument error (exit 1), not a traceback.
    mod = _load_creator_module()
    pkg = make_package(tmp_path)

    def boom(*_a, **_k):
        raise ValueError("path is on mount 'C:', start on mount 'D:'")

    monkeypatch.setattr(mod.os.path, "relpath", boom)
    result = mod.create_request(pkg, ["tooling_review"], output_path=tmp_path / "out" / "r.json")
    assert result.success is False
    assert result.exit_code == 1
    assert "different drives" in result.error
