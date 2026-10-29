"""Path setup and shared governance fixtures."""

from __future__ import annotations

from datetime import datetime
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from governance.kernel.evaluate import load_json  # noqa: E402


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def policy() -> dict:
    return load_json(ROOT / "governance" / "policy" / "governance_policy_v1.json")


@pytest.fixture(scope="session")
def production_roles() -> dict:
    return load_json(ROOT / "governance" / "policy" / "authorized_roles_v1.json")


@pytest.fixture(scope="session")
def synthetic_bundle() -> dict:
    return load_json(ROOT / "governance" / "fixtures" / "valid_synthetic_authorization.json")


@pytest.fixture(scope="session")
def pep_decision() -> dict:
    return load_json(ROOT / "governance" / "fixtures" / "pep_cam_contract_002_proposed.json")


def as_of(bundle: dict) -> datetime:
    text = bundle["as_of"]
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def resolver_for(evidence: dict):
    def resolve(evidence_ref: str) -> dict:
        if evidence_ref not in evidence:
            return {"available": False}
        return evidence[evidence_ref]

    return resolve
