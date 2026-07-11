"""
CAM-A21 tests — product documentation and boundary language.

Witnesses that the product docs exist, the README links them, the CAM Assist /
traditional CAM distinction is stated, and the non-execution + companion-product
boundary language is present. Also checks that every script the workflow guide
references actually exists (documentation must match executable reality).
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCT = REPO_ROOT / "docs" / "product"
README = REPO_ROOT / "README.md"

WHY = PRODUCT / "WHY_CAM_ASSIST_EXISTS.md"
WORKFLOW = PRODUCT / "CAM_ASSIST_WORKFLOW.md"
VS_CAM = PRODUCT / "CAM_ASSIST_VS_CAM_SOFTWARE.md"
CREATION_STUDIO = PRODUCT / "CAM_ASSIST_AND_CAM_CREATION_STUDIO.md"

ALL_PRODUCT_DOCS = [WHY, WORKFLOW, VS_CAM, CREATION_STUDIO]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _norm(p: Path) -> str:
    """Lowercased text with whitespace collapsed, so prose line-wrapping does not
    break phrase assertions."""
    return re.sub(r"\s+", " ", p.read_text(encoding="utf-8").lower())


# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------

def test_product_docs_exist():
    for doc in ALL_PRODUCT_DOCS:
        assert doc.is_file(), doc


def test_readme_links_all_product_docs():
    readme = _read(README)
    for doc in ALL_PRODUCT_DOCS:
        assert doc.name in readme, f"README does not link {doc.name}"


# ---------------------------------------------------------------------------
# Non-execution boundary language
# ---------------------------------------------------------------------------

def test_docs_state_no_gcode_generation():
    why = _norm(WHY)
    assert "g-code" in why and "no g-code" in why
    assert "g-code generation" in _norm(VS_CAM)


def test_docs_state_no_execution_authority():
    why = _norm(WHY)
    assert "does not convert that reasoning into machine execution" in why
    assert "execution authority" in why


def test_docs_distinguish_from_traditional_cam():
    vs = _norm(VS_CAM)
    assert "traditional cam" in vs
    assert "toolpath generation" in vs and "simulation" in vs
    # The comparison must not claim traditional CAM never does traceability.
    assert "vendor-specific or external" in vs


def test_docs_do_not_claim_executable_production_shop_integration():
    cs = _norm(CREATION_STUDIO)
    assert "integration is not complete" in cs
    assert "no cam-creation-studio runtime dependency" in cs


# ---------------------------------------------------------------------------
# Companion-product boundary
# ---------------------------------------------------------------------------

def test_creation_studio_doc_states_repositories_remain_separate():
    cs = _read(CREATION_STUDIO)
    assert "separate repositories" in cs.lower()


def test_creation_studio_doc_states_merger_not_decided():
    cs = _read(CREATION_STUDIO)
    assert "A future merger remains a product decision" in cs


# ---------------------------------------------------------------------------
# Workflow guide matches executable reality
# ---------------------------------------------------------------------------

def test_every_workflow_script_exists():
    referenced = set(re.findall(r"scripts/([A-Za-z0-9_]+\.py)", _read(WORKFLOW)))
    assert referenced, "workflow guide references no scripts"
    for name in sorted(referenced):
        assert (REPO_ROOT / "scripts" / name).is_file(), f"missing script: {name}"
