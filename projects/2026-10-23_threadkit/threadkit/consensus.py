"""Diversity-weighted consensus for multi-agent systems.

Implements A5 (with M2): agreement among models trained alike is weak evidence. Votes are
grouped by lineage and each lineage counts once, so five copies of one model are one witness;
a vote counts as evidence only with a diversity attestation from someone who judged the agents
independent enough.
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from .findings import Finding


@dataclass
class Tally(object):
    raw: Dict[str, int]
    by_lineage: Dict[str, int]
    raw_winner: Optional[str]
    lineage_winner: Optional[str]
    independent_witnesses: int
    attested: bool
    findings: List[Finding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"raw": self.raw, "by_lineage": self.by_lineage, "raw_winner": self.raw_winner,
                "lineage_winner": self.lineage_winner, "independent_witnesses": self.independent_witnesses,
                "attested": self.attested, "findings": [f.to_dict() for f in self.findings]}


def _winner(counts: Mapping[str, int]) -> Optional[str]:
    if not counts:
        return None
    best = max(counts.values())
    tops = sorted(a for a, n in counts.items() if n == best)
    return tops[0] if len(tops) == 1 else None


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def tally(record: Mapping[str, Any]) -> Tally:
    votes = record["votes"]
    raw = Counter(_norm(v["answer"]) for v in votes)
    lineage_answers: "OrderedDict[str, Counter]" = OrderedDict()
    for v in votes:
        lineage_answers.setdefault(_norm(v["lineage"]), Counter())[_norm(v["answer"])] += 1
    by_lineage: Counter = Counter()
    split_lineages = []
    for lin, answers in lineage_answers.items():
        w = _winner(answers)
        if w is None:
            split_lineages.append(lin)
        else:
            by_lineage[w] += 1
    out: List[Finding] = []
    q = str(record["question"])
    attested = bool(record.get("diversity_attestation"))
    if not attested:
        out.append(Finding("CNS-001", "MEDIUM", q,
                           "no diversity attestation; nobody has judged the agents independent enough for the vote to count", "A5"))
    rw, lw = _winner(raw), _winner(by_lineage)
    if rw != lw:
        out.append(Finding("CNS-002", "MEDIUM", q,
                           "the raw majority (%s) differs from the majority by lineage (%s); copies outvoted independent routes"
                           % (rw, lw), "A5"))
    if len(lineage_answers) == 1 and len(votes) > 1:
        out.append(Finding("CNS-003", "INFO", q,
                           "all %d votes come from one lineage: one witness, not %d" % (len(votes), len(votes)), "A5"))
    for lin in split_lineages:
        out.append(Finding("CNS-004", "INFO", lin, "agents of this lineage split evenly; the lineage casts no vote", "A5"))
    return Tally(dict(raw), dict(by_lineage), rw, lw, len(lineage_answers), attested, out)
