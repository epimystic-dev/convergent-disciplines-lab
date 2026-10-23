"""The ladder of causation as a claim discipline.

Implements R4: label each causal claim with its rung (1 association, 2 intervention,
3 counterfactual); a rung-2 claim needs explicit causal assumptions and a rung-3 claim a
structural model; an effect that is not identifiable is reported as such, not asserted; and an
inference used in a decision lists the conditions that would defeat it.

The phrasing classifier is a backstop for untagged claims, not a parser of causal language. It
errs toward a higher rung, because the costly mistake is a correlation dressed as a
recommendation, not the reverse.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Mapping

from .findings import Finding

_COUNTERFACTUAL = re.compile(
    r"(?<![a-z-])(would have|would not have|wouldn't have|had (it|they|we|you|he|she) not|if [a-z ,]{0,40} had|"
    r"but for|were it not for|could have been prevented)(?![a-z-])", re.I)
_INTERVENTION = re.compile(
    r"(?<![a-z-])(if (you|we|they|one|the [a-z]+) (take|takes|give|gives|set|sets|raise|raises|lower|lowers|increase|"
    r"increases|decrease|decreases|introduce|introduces|ban|bans|deploy|deploys|switch|switches|adopt|adopts|stop|stops)|"
    r"will (increase|decrease|reduce|raise|lower|cause|improve|worsen|prevent|extend|shorten)|"
    r"(causes|caused|leads? to|led to|results? in|resulted in|the effect of|effective (at|in) (reducing|increasing)|"
    r"should (take|use|adopt|avoid|stop)|we recommend|you should))(?![a-z-])", re.I)
_NONIDENTIFIABLE = re.compile(r"(?<![a-z-])(not identifiable|cannot be identified|is not identified|unidentifiable|"
                              r"cannot be estimated from|not estimable)(?![a-z-])", re.I)

PARITY_METRICS = frozenset(["demographic_parity", "statistical_parity", "equal_opportunity", "equalized_odds",
                            "equalised_odds", "predictive_parity", "disparate_impact"])


def classify_rung(text: str) -> int:
    """Guess the rung a sentence claims, from its phrasing."""
    if _COUNTERFACTUAL.search(text):
        return 3
    if _INTERVENTION.search(text):
        return 2
    return 1


def check(claim: Mapping[str, Any], *, used_in_decision: bool = False) -> List[Finding]:
    out: List[Finding] = []
    cid = str(claim.get("id", "?"))
    declared = claim.get("rung")
    phrased = classify_rung(claim["text"])
    rung = declared if declared is not None else phrased
    if declared is not None and phrased > declared:
        out.append(Finding("CAU-003", "MEDIUM", cid,
                           "tagged rung %d but phrased as rung %d; a correlation dressed as %s"
                           % (declared, phrased, "a recommendation" if phrased == 2 else "a counterfactual"), "R4"))
        rung = phrased
    if rung >= 2 and not claim.get("causal_assumptions"):
        out.append(Finding("CAU-001", "HIGH", cid,
                           "a rung-%d claim with no causal assumptions declared; data alone cannot license it" % rung, "R4"))
    if rung == 3 and not claim.get("structural_model"):
        out.append(Finding("CAU-002", "HIGH", cid, "a counterfactual claim with no structural model behind it", "R4"))
    if (claim.get("identifiable") is False and claim["standing"] in ("settled", "established")
            and not _NONIDENTIFIABLE.search(claim["text"])):
        out.append(Finding("CAU-005", "MEDIUM", cid,
                           "the effect is marked not identifiable but asserted as %s; report it as not identifiable"
                           % claim["standing"], "R4"))
    if rung >= 2 and used_in_decision and not claim.get("defeaters"):
        out.append(Finding("CAU-004", "MEDIUM", cid,
                           "a causal claim used in a decision lists no defeating conditions", "R4"))
    return out


def fairness_check(metrics: Iterable[str]) -> List[Finding]:
    """A parity-only fairness audit answers a rung-3 question with rung-1 surrogates."""
    names = {m.strip().lower() for m in metrics}
    if names and names <= PARITY_METRICS:
        return [Finding("CAU-006", "MEDIUM", "fairness audit",
                        "only parity metrics (%s); counterfactual fairness needs a causal model of attribute, qualification and decision"
                        % ", ".join(sorted(names)), "R4")]
    return []
