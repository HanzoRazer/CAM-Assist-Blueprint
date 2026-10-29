"""Shared loader for governance command-line checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def policy_paths(root: Path = ROOT) -> tuple[dict, dict]:
    policy = load_json(root / "governance" / "policy" / "governance_policy_v1.json")
    roles = load_json(root / "governance" / "policy" / "authorized_roles_v1.json")
    return policy, roles
