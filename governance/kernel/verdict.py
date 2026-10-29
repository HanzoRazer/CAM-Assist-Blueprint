"""Machine verdicts for the governance pilot."""

from __future__ import annotations

import json
from dataclasses import dataclass

AUTHORIZED = "AUTHORIZED"
BLOCKED = "BLOCKED"
INVALID = "INVALID"
EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
VERIFIER_ERROR = "VERIFIER_ERROR"

CODE_AUTHORIZED = 0
CODE_BLOCKED = 1
CODE_INVALID = 2
CODE_EVIDENCE = 3
CODE_VERIFIER = 4


@dataclass(frozen=True)
class Verdict:
    code: int
    verdict: str
    reason_codes: tuple[str, ...]
    decision_id: str | None = None
    production_authorization_operational: bool = False
    synthetic_only: bool = False

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "decision_id": self.decision_id,
            "production_authorization_operational": self.production_authorization_operational,
            "reason_codes": list(self.reason_codes),
            "synthetic_only": self.synthetic_only,
            "verdict": self.verdict,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def make_verdict(
    code: int,
    verdict: str,
    reasons: list[str],
    *,
    decision_id: str | None,
    production_operational: bool,
    synthetic_only: bool = False,
) -> Verdict:
    return Verdict(
        code=code,
        verdict=verdict,
        reason_codes=tuple(sorted(set(reasons))),
        decision_id=decision_id,
        production_authorization_operational=production_operational,
        synthetic_only=synthetic_only,
    )
