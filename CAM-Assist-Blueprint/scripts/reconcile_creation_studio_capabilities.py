#!/usr/bin/env python3
"""
CAM-A25: reconcile a Creation Studio request against a capability profile.

Compares two contracts that already exist:

    CAM-A22 request   requested_capabilities[]        what CAM Assist asks for
    CAM-A23 profile   capabilities[].capability_id    what Creation Studio declares

and reports three sets, by EXACT identifier comparison:

    satisfied                = requested & declared
    unsatisfied              = requested - declared
    declared_but_unrequested = declared - requested

`declared_but_unrequested` is deliberately not called `undeclared`, which would
be confusable with the unsatisfied case -- a capability that WAS requested and is
NOT declared.

WHAT THIS DOES NOT DO
---------------------
No synonym mapping, alias table, ontology translation, semantic inference, or
fuzzy/prefix matching. A25 does not define semantic equivalence between A22
request identifiers and A23 capability identifiers.

Versions are surfaced for traceability, never interpreted. `profile_version` is
owned by CAM-Creation-Studio; inferring compatibility from it here would recreate
the coupling A23's open vocabulary exists to avoid.

AUTHORITY
---------
An unsatisfied capability is a compatibility finding, NOT a prohibition.
A satisfied capability is a declaration match, NOT authorization.

`satisfied` means only that the requested identifier appears in the supplied
profile. It does not mean Creation Studio is installed, reachable, operational,
correctly configured, machine-ready, safe, or able to produce acceptable
machining output. This module grants no execution authority and selects no
capability on anyone's behalf.

This file is reference-only tooling. It reads two records and writes nothing.
"""
from __future__ import annotations

import textwrap
from typing import NamedTuple

# Human-report wrap width. The canonical finding message stays a single string in
# the JSON output; only the console rendering is wrapped.
REPORT_WIDTH = 69

# --- finding codes -----------------------------------------------------------

NAMESPACE_DIVERGENCE = "namespace_divergence"

NAMESPACE_DIVERGENCE_MESSAGE = (
    "The request and capability-profile vocabularies are both non-empty "
    "but share no identifiers."
)

SEVERITY_WARNING = "warning"

ADVISORY_NOTICE = (
    "ADVISORY ONLY - identifier matches do not imply execution authority,\n"
    "machine readiness, or downstream availability."
)


class Finding(NamedTuple):
    """A derived diagnosis about the reconciliation as a whole."""

    code: str
    severity: str
    message: str

    def as_dict(self) -> dict:
        return {"code": self.code, "severity": self.severity, "message": self.message}


class Reconciliation(NamedTuple):
    """The complete result. Sets are sorted, so output never depends on input order."""

    satisfied: list[str]
    unsatisfied: list[str]
    declared_but_unrequested: list[str]
    findings: list[Finding]

    @property
    def requested_count(self) -> int:
        return len(self.satisfied) + len(self.unsatisfied)

    @property
    def declared_count(self) -> int:
        return len(self.satisfied) + len(self.declared_but_unrequested)

    def has_finding(self, code: str) -> bool:
        return any(f.code == code for f in self.findings)

    def as_dict(self) -> dict:
        """Ephemeral serialization of the calculation.

        NOT a repository contract, schema, or stored sidecar. It exists so CI can
        consume the same numbers a human reads, and may be reshaped by a later
        capability without a migration.
        """
        return {
            "satisfied": self.satisfied,
            "unsatisfied": self.unsatisfied,
            "declared_but_unrequested": self.declared_but_unrequested,
            "findings": [f.as_dict() for f in self.findings],
        }


def reconcile(requested: list[str], declared: list[str]) -> Reconciliation:
    """Compare two capability vocabularies by exact identifier.

    Pure: no filesystem, no clock, no network. Duplicates within either input are
    collapsed -- both contracts already declare uniqueItems, and a duplicate must
    not inflate a count here.
    """
    requested_set = set(requested)
    declared_set = set(declared)

    satisfied = sorted(requested_set & declared_set)
    unsatisfied = sorted(requested_set - declared_set)
    declared_but_unrequested = sorted(declared_set - requested_set)

    findings: list[Finding] = []

    # Fires only when both vocabularies are non-empty and share nothing. That is a
    # materially different architectural state from "two capabilities are
    # missing", so it must not render as an ordinary unsatisfied count.
    #
    # An empty intersection is NOT sufficient on its own: with an empty request or
    # an empty profile the intersection is trivially empty and says nothing about
    # whether the vocabularies agree.
    if requested_set and declared_set and not satisfied:
        findings.append(
            Finding(
                code=NAMESPACE_DIVERGENCE,
                severity=SEVERITY_WARNING,
                message=NAMESPACE_DIVERGENCE_MESSAGE,
            )
        )

    return Reconciliation(
        satisfied=satisfied,
        unsatisfied=unsatisfied,
        declared_but_unrequested=declared_but_unrequested,
        findings=findings,
    )


def format_report(result: Reconciliation) -> str:
    """Human-readable report. Counts first, then findings, then the boundary."""
    lines = [
        f"Requested:                {result.requested_count}",
        f"Satisfied:                {len(result.satisfied)}",
        f"Unsatisfied:              {len(result.unsatisfied)}",
        f"Declared but unrequested: {len(result.declared_but_unrequested)}",
    ]

    for finding in result.findings:
        lines.append("")
        lines.append(f"[{finding.severity.upper()}] {finding.code}")
        lines.extend(textwrap.wrap(finding.message, width=REPORT_WIDTH))

    lines.append("")
    lines.append(ADVISORY_NOTICE)
    return "\n".join(lines)
