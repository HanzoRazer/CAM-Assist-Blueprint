"""
CAM-A25 documentation — boundary language and executable reality.

Follows the convention set by test_product_documentation.py: the doc must exist,
the README must link it, the authority boundary must be stated in words, and
every CLI form the docs show must actually work.

The last point is the one that rots silently. A doc promising a flag that was
renamed is worse than no doc, so the CLI examples are executed rather than
trusted.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "docs" / "integration" / "CREATION_STUDIO_CAPABILITY_RECONCILIATION.md"
DEV_ORDER = REPO_ROOT / "docs" / "dev_orders" / "CAM-A25.md"
README = REPO_ROOT / "README.md"
SCRIPT = REPO_ROOT / "scripts" / "reconcile_creation_studio_capabilities.py"
EXAMPLE_PACKAGE = REPO_ROOT / "examples" / "packages" / "ltb_vcarve_synthetic_example"


def _norm(path: Path) -> str:
    """Lowercased, whitespace-collapsed, so prose wrapping cannot break a phrase.

    Blockquote markers are stripped first. Without that, a phrase wrapped inside a
    `>` block collapses to "... in the > supplied ...", which defeats the very
    wrapping-independence this normalizer exists to provide.
    """
    text = path.read_text(encoding="utf-8").lower()
    text = re.sub(r"(?m)^[ \t]*>[ \t]?", "", text)
    return re.sub(r"\s+", " ", text)


# --- existence and linkage ---------------------------------------------------


def test_integration_doc_exists():
    assert DOC.is_file(), DOC


def test_readme_links_the_integration_doc():
    assert DOC.name in README.read_text(encoding="utf-8")


def test_readme_documents_the_capability():
    readme = _norm(README)
    assert "cam-a25" in readme
    assert "reconcile_creation_studio_capabilities.py" in readme


# --- authority boundary ------------------------------------------------------


def test_doc_states_what_satisfied_actually_means():
    doc = _norm(DOC)
    assert (
        "means only that a requested capability identifier appears in the supplied "
        "capability profile" in doc
    )


def test_doc_states_both_authority_invariants():
    doc = _norm(DOC)
    assert "compatibility finding, not a prohibition" in doc
    assert "declaration match, not authorization" in doc


def test_doc_denies_the_things_a_match_does_not_establish():
    doc = _norm(DOC)
    for claim in ("installed", "reachable", "operational", "machine-ready", "safe"):
        assert claim in doc, f"doc does not disclaim {claim!r}"
    assert "no execution authority" in doc or "grants no execution authority" in doc


def test_doc_states_the_non_goal_on_semantic_equivalence():
    assert "does not define semantic equivalence" in _norm(DOC)


# --- the divergence explanation ----------------------------------------------


def test_doc_explains_divergence_without_implying_studio_supports_nothing():
    # The misreading this section exists to prevent.
    doc = _norm(DOC)
    assert "does not mean cam-creation-studio supports nothing" in doc
    assert "different identifier namespaces" in doc


def test_doc_states_the_divergence_trigger_conditions():
    doc = _norm(DOC)
    assert "namespace_divergence" in doc
    # An empty intersection alone must not be presented as sufficient.
    assert "trivially empty" in doc


# --- ephemerality and the model/report separation ----------------------------


def test_doc_states_the_result_is_not_a_stored_contract():
    doc = _norm(DOC)
    assert "not a repository contract" in doc
    assert "no reconciliation schema" in doc


def test_doc_separates_the_core_model_from_the_serialized_report():
    # The distinction Phase 4 was careful to preserve: provenance composes around
    # the reconciliation rather than becoming part of it.
    doc = _norm(DOC)
    assert "belongs to the **ephemeral serialized report**" in DOC.read_text(encoding="utf-8").lower() or (
        "belongs to the" in doc and "serialized report" in doc
    )
    assert "never folded into it" in doc


def test_dev_order_records_the_four_key_core_alongside_the_five_key_report():
    dev = _norm(DEV_ORDER)
    assert "4 keys" in dev and "5 keys" in dev
    assert "four-key core model remains the reconciliation result" in dev


def test_doc_states_versions_are_not_interpreted():
    doc = _norm(DOC)
    assert "surfaced, never interpreted" in doc
    assert "profile_version" in doc


# --- documented CLI forms actually work --------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_readme_default_invocation_works():
    result = _run("--package", str(EXAMPLE_PACKAGE))
    assert result.returncode == 0, result.stderr


def test_readme_json_invocation_works():
    import json

    result = _run("--package", str(EXAMPLE_PACKAGE), "--json")
    assert result.returncode == 0, result.stderr
    assert set(json.loads(result.stdout)) == {
        "inputs",
        "satisfied",
        "unsatisfied",
        "declared_but_unrequested",
        "findings",
    }


def test_readme_strict_invocation_exits_nonzero_on_todays_contracts():
    # The shipped vocabularies are disjoint, so everything requested is
    # unsatisfied and strict mode fails. If this ever exits 0 the vocabularies
    # have converged and the divergence section needs revisiting.
    result = _run("--package", str(EXAMPLE_PACKAGE), "--json", "--fail-on-unsatisfied")
    assert result.returncode == 1, result.stderr


def test_every_flag_the_docs_mention_is_a_real_flag():
    help_text = _run("--help").stdout
    documented = set(re.findall(r"--[a-z][a-z-]+", DOC.read_text(encoding="utf-8")))
    for flag in documented:
        assert flag in help_text, f"{DOC.name} documents {flag}, which the CLI does not accept"
