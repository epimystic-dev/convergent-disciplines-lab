"""Hard-to-vary explanations.

Implements R2: a good explanation's details are constrained by what it explains, and it
commits to counterfactuals (inputs that would have produced a visibly different conclusion).
An explanation whose details are mostly unconstrained could have explained anything.

The score is a prompt for judgement, not an algorithm: deciding what counts as a constraint is
itself a judgement, as the criterion's own author concedes.
"""

from __future__ import annotations

from typing import Any, List, Mapping

from .findings import Finding

EASY_TO_VARY = 0.5


def variability(explanation: Mapping[str, Any]) -> float:
    """The share of details that nothing in the evidence constrains (0 = none free, 1 = all free)."""
    details = explanation["details"]
    if not details:
        return 1.0
    free = sum(1 for d in details if not (d.get("constrained_by") or "").strip())
    return free / float(len(details))


def check(explanation: Mapping[str, Any]) -> List[Finding]:
    out: List[Finding] = []
    eid = str(explanation.get("id", "?"))
    if not explanation.get("counterfactuals"):
        out.append(Finding("EXP-001", "MEDIUM", eid,
                           "commits to no counterfactual; say what input would have changed the conclusion", "R2"))
    v = variability(explanation)
    if v > EASY_TO_VARY:
        out.append(Finding("EXP-002", "MEDIUM", eid,
                           "%d of %d details are constrained by nothing; the explanation is easy to vary"
                           % (round(v * len(explanation["details"])), len(explanation["details"])), "R2"))
    return out
