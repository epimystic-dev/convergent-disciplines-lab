"""Debiasing by structure, not by awareness.

Implements S8: knowing about a bias does not fix it; procedures do, partly. A high-stakes
estimate or decision starts from a reference-class base rate, runs a pre-mortem, names the
alternatives it discarded, is checked by someone other than the decider, and is revisited after
the original framing has faded. Also presents probabilities as natural frequencies (S7).
"""

from __future__ import annotations

from typing import Any, List, Mapping

from .findings import Finding


def check(record: Mapping[str, Any]) -> List[Finding]:
    out: List[Finding] = []
    rid = str(record.get("id", "?"))
    high = record["stakes"] == "high"
    sev = "MEDIUM" if high else "INFO"
    if record.get("estimate") and not record.get("reference_class"):
        out.append(Finding("DEB-001", sev, rid,
                           "an estimate with no reference class; start from how similar cases went, then adjust", "S8"))
    elif high and not record.get("reference_class"):
        out.append(Finding("DEB-001", sev, rid, "a high-stakes decision with no reference class or base rate", "S8"))
    if high:
        if not record.get("premortem"):
            out.append(Finding("DEB-002", "MEDIUM", rid,
                               "no pre-mortem; assume it failed and write down why", "S8"))
        if not record.get("alternatives_discarded"):
            out.append(Finding("DEB-003", "MEDIUM", rid, "no alternatives recorded as discarded", "S8"))
        check_ = record.get("adversarial_check")
        if not check_:
            out.append(Finding("DEB-004", "MEDIUM", rid,
                               "no adversarial check; make finding the flaw somebody's job", "S8"))
        elif check_["by"].strip().lower() == record["decided_by"].strip().lower():
            out.append(Finding("DEB-004", "HIGH", rid,
                               "the adversarial check was done by the decider; it must be someone else", "S8"))
        if not record.get("revisit_after"):
            out.append(Finding("DEB-005", "INFO", rid, "no revisit date; meet the decision again once the framing fades", "S8"))
        if not record.get("diversification"):
            out.append(Finding("DEB-006", "INFO", rid,
                               "the judgement was not spread across people, methods or models", "S8"))
    return out


def natural_frequency(p: float, n: int = 100) -> str:
    """Render a probability as a count: 0.03 -> 'about 3 in 100'."""
    if not 0.0 <= p <= 1.0:
        raise ValueError("p must lie in [0, 1]")
    if n <= 0:
        raise ValueError("n must be positive")
    k = p * n
    if 0 < k < 1:
        while k < 1 and n < 10 ** 9:
            n *= 10
            k = p * n
    return "about %d in %d" % (int(round(k)), n)
