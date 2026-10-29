"""Non-authoritative governance pilot.

Importing this package does not authorize an implementation or a manufacturing action.
"""

from governance.kernel.evaluate import evaluate_authorization, verify_registry
from governance.kernel.verdict import Verdict

__all__ = ["Verdict", "evaluate_authorization", "verify_registry"]
