"""
CAM-A26 documentation — boundary language and executable reality.

The mapping doc must exist, the README must link it, the authority boundary
must be stated in words, and every CLI form the docs show must actually work.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "docs" / "integration" / "CREATION_STUDIO_CAPABILITY_MAPPING.md"
RECONCILE_DOC = REPO_ROOT / "docs" / "integration" / "CREATION_STUDIO_CAPABILITY_RECONCILIATION.md"
DEV_ORDER = REPO_ROOT / "docs" / "dev_orders" / "CAM-A26.md"
README = REPO_ROOT / "README.md"
VALIDATE = REPO_ROOT / "scripts" / "validate_creation_studio_capability_map.py"
RECONCILE = REPO_ROOT / "scripts" / "reconcile_creation_studio_capabilities.py"
CANONICAL_MAP = REPO_ROOT / "contracts" / "creation_studio_capability_map.json"
EXAMPLE_PACKAGE = REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example"


def _norm(path: Path) -> str:
    text = path.read_text(encoding="utf-8").lower()
    text = re.sub(r"(?m)^[ \t]*>[ \t]?", "", text)
    return re.sub(r"\s+", " ", text)


def test_integration_doc_exists():
    assert DOC.is_file(), DOC


def test_dev_order_exists():
    assert DEV_ORDER.is_file(), DEV_ORDER


def test_readme_links_the_mapping_doc():
    assert DOC.name in README.read_text(encoding="utf-8")


def test_readme_documents_the_capability():
    readme = _norm(README)
    assert "cam-a26" in readme
    assert "validate_creation_studio_capability_map.py" in readme
    assert "--capability-map" in README.read_text(encoding="utf-8")


def test_doc_states_the_three_layer_distinction():
    doc = _norm(DOC)
    assert "a22 requested outcome" in doc
    assert "explicit a26 mapping" in doc
    assert "a23 declared" in doc


def test_doc_denies_authority_claims():
    doc = _norm(DOC)
    for claim in (
        "installed",
        "reachable",
        "machine is ready",
        "execution is authorized",
    ):
        assert claim in doc, claim
    assert "does not authorize" in doc or "not authorization" in doc


def test_doc_states_mapping_is_never_inferred():
    doc = _norm(DOC)
    assert "never inferred" in doc
    assert "exact matching remains the default" in doc


def test_reconcile_doc_keeps_a25_non_equivalence_and_points_at_a26():
    recon = _norm(RECONCILE_DOC)
    assert "does not define semantic equivalence" in recon
    assert "--capability-map" in RECONCILE_DOC.read_text(encoding="utf-8")
    assert "creation_studio_capability_mapping.md" in _norm(RECONCILE_DOC)


def test_validate_cli_example_works():
    result = subprocess.run(
        [sys.executable, str(VALIDATE), str(CANONICAL_MAP)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr


def test_mapped_reconcile_cli_example_works():
    result = subprocess.run(
        [
            sys.executable,
            str(RECONCILE),
            "--package",
            str(EXAMPLE_PACKAGE),
            "--capability-map",
            str(CANONICAL_MAP),
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "capability_map" in payload["inputs"]
    assert "satisfaction_details" in payload


def test_every_flag_the_mapping_doc_mentions_is_a_real_flag():
    help_text = subprocess.run(
        [sys.executable, str(RECONCILE), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    ).stdout
    documented = set(re.findall(r"--[a-z][a-z-]+", DOC.read_text(encoding="utf-8")))
    # The mapping doc also shows the validator CLI, which has --quiet / -q only.
    documented -= {"--quiet"}
    for flag in documented:
        assert flag in help_text, f"{DOC.name} documents {flag}, which the CLI does not accept"


def test_ledger_records_a26():
    ledger = _norm(REPO_ROOT / "docs" / "dev_orders" / "LEDGER.md")
    assert "a26" in ledger
    assert "capability vocabulary bridge" in ledger
