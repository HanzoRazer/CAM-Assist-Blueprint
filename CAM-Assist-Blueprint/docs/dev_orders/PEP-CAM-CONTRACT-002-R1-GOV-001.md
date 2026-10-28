# Dev Order — PEP-CAM-CONTRACT-002 / R1-GOV-001

## ADR governance disposition and R2 authorization gate

**Merge guard:** PR #44 remains unmerged until the decision owner explicitly
authorizes retaining this governance record. That documentation decision
does not accept the architecture or authorize R2. No ready mark, tag, or
release is authorized by this record.

```text
order id        PEP-CAM-CONTRACT-002 / R1-GOV-001
date            2026-10-27
repository      HanzoRazer/CAM-Assist-Blueprint
predecessor     PR #43, head 5f736e567dab31439df9b2b66fc5de43bec032f2
mode            governance documentation and verification
r2              BLOCKED
decision owner  UNSET
decision date   UNSET
```

This order records governance status. It does not authorize
interchange schemas, a Toolbox producer, a CAM-Assist admission adapter,
CAM-A32 reconstruction, or manufacturing execution.

## What must be true before R2

All of the following, in an attributable owner decision:

1. Canonical repository identity, accessible to the publisher.
2. Schema identifier, version, and publication location.
3. Frozen validated snapshot, or a recorded rejection of that choice.
4. Evidence-resolution owner and digest protocol.
5. Serialized authority fields and result vocabulary.
6. Canonical JSON and digest exclusion rules, as required by the ADR's
   original approval list.
7. An explicit statement that Phase I test thresholds are not production
   policy, as required by that same list.
8. The relationship to Toolbox's deferred `PEP-V1-CONTRACT-002`, identified
   as unresolved in the PR #43 comment.
9. Disposition of the Tap Tone authority-schema gap identified as an R1
   stop condition: remediation or an explicit non-dependency rationale.

ADR acceptance and R2 authorization are separate actions. Merging a
proposed ADR does not satisfy this gate. The reported Mesh hold remains
uncleared until its authoritative source and any clearing decision are
recorded; missing search results are not clearance. None of these decisions
is supplied by this documentation change.

## Execution result

Witness: `2026-10-28T00:31:14Z` (October 27, 2026, 7:31 PM America/Chicago).
Repository facts are pinned to that witness and the cited revisions; this
is not a claim about the latest state of external repositories.

| Gate | Result |
| --- | --- |
| G0 PR #43 | Merged as `77716972169827e12ce99f6e2aeda5b1f9532586`. Head remains `5f736e5`. No approving review |
| G1 ADR status | R1 text preserved. Disposition section states `proposed`, `decision_owner: null`, `r2_authorized: false` |
| G2 Owner decision | Not present. Recommendations stay recommendations |
| G3 Approval verification | No approval record created |
| G4 R2 determination | `BLOCKED` |
| G5 R2 handoff | Not prepared |

Outcome B (governance incomplete; R2 remains blocked).

The decision/invariant matrix and Mesh-hold evidence are in the
[ADR disposition](../decisions/PEP-CAM-CONTRACT-002-ADR.md#r1-gov-001-decision-disposition).

## Constitutional declarations

Unchanged:

These are local non-execution invariants. The example does not publish
external authority field names or satisfy GOV-D05.

```json
{
  "execution_authority_claim": false,
  "non_execution_declaration": true,
  "requires_human_review": true
}
```

## Negative governance rule

A proposed ADR that is merged is still proposed. `r2_authorized` remains
false until a later revision records who approved which text, when, and
against which repository revision.

The fenced fields, checklist, and merge guard are declarative governance
records. They do not implement a CI merge prohibition or an R2 runtime gate.
