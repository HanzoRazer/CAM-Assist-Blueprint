"""Shared loader for governance command-line checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from governance.kernel.canonical import digest_of  # noqa: E402
from governance.kernel.evaluate import (  # noqa: E402
    evaluate_authorization,
    load_json,
    verify_registry,
)
from governance.kernel.verdict import Verdict  # noqa: E402


def emit(verdict: Verdict) -> int:
    json.dump(verdict.to_dict(), sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return verdict.code


PILOT_POLICY_DIGEST = "3c0236cd2cb61682b835fd34210ae37a022f7d891d84106fa1ff060631020769"


def policy_paths(root: Path = ROOT) -> tuple[dict, dict]:
    policy = load_json(root / "governance" / "policy" / "governance_policy_v1.json")
    if digest_of(policy) != PILOT_POLICY_DIGEST:
        raise ValueError("POLICY_PIN_MISMATCH: candidate checkout policy differs from pilot pin")
    roles = load_json(root / "governance" / "policy" / "authorized_roles_v1.json")
    return policy, roles
