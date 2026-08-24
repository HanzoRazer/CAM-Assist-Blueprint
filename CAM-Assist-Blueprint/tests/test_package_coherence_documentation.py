"""CAM-A28 documentation — authority language and executable CLI forms."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "docs" / "integration" / "PACKAGE_COHERENCE_AUDIT.md"
DEV_ORDER = REPO_ROOT / "docs" / "dev_orders" / "CAM-A28.md"
README = REPO_ROOT / "README.md"
SCRIPT = REPO_ROOT / "scripts" / "audit_package_coherence.py"
LEDGER = REPO_ROOT / "docs" / "dev_orders" / "LEDGER.md"
EXAMPLE = REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example"


def _norm(path: Path) -> str:
    text = path.read_text(encoding="utf-8").lower()
    text = re.sub(r"(?m)^[ \t]*>[ \t]?", "", text)
    return re.sub(r"\s+", " ", text)


def test_docs_exist():
    assert DOC.is_file()
    assert DEV_ORDER.is_file()
    assert SCRIPT.is_file()


def test_readme_links_the_audit():
    readme = README.read_text(encoding="utf-8")
    assert "audit_package_coherence.py" in readme
    assert DOC.name in readme
    assert "cam-a28" in readme.lower()


def test_authority_boundary_is_stated():
    doc = _norm(DOC)
    assert "does not mean the machining strategy is correct" in doc
    assert "approved" in doc
    assert "machine-ready" in doc or "machine ready" in doc
    assert "authorized for execution" in doc


def test_example_debt_is_classified_honestly():
    doc = _norm(DOC)
    assert "example/repository debt" in doc
    assert "missing_reference" in doc
    assert "decision record" in doc
    assert "revision lineage" in doc


def test_documented_cli_forms_work():
    help_text = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    ).stdout
    assert "--package" in help_text
    assert "--json" in help_text
    assert "--fail-on-errors" in help_text
    for flag in ("--package", "--json", "--fail-on-errors"):
        assert flag in help_text
        assert flag in DOC.read_text(encoding="utf-8")


def test_ledger_records_a27_merged_and_a28():
    ledger = _norm(LEDGER)
    assert "a27" in ledger
    assert "7f20320" in LEDGER.read_text(encoding="utf-8")
    assert "package coherence audit" in ledger
    assert "a29+" in ledger or "a29" in ledger


def test_example_package_still_exists():
    assert (EXAMPLE / "manifest.json").is_file()
