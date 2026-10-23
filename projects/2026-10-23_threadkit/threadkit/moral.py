"""Moral pluralism with overlapping consensus.

Implements:
  D4   the seven convergences (C1-C7) are high-confidence ground; on the five foundational
       disagreements (D1-D5) the traditions' answers are presented, attributed, and none is
       adopted as the default.
  D5   each tradition keeps its own terms: identity glosses between traditions are flagged.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from .findings import Finding

_IDENTITY = re.compile(r"(?<![a-z])((is|are) (the same as|identical to|just|simply|basically|merely)|"
                       r"(is|are) (another|a different) (word|name) for)(?![a-z])", re.I)

CONVERGENCE_IDS = tuple("C%d" % i for i in range(1, 8))
DISAGREEMENT_IDS = tuple("D%d" % i for i in range(1, 6))


def plural_answer(tags: Sequence[str], positions: Iterable[Mapping[str, str]]) -> Dict[str, Any]:
    """Build the moral block of an answer for a contested question: positions, no verdict."""
    tags = list(tags)
    bad = [t for t in tags if t not in DISAGREEMENT_IDS + CONVERGENCE_IDS]
    if bad:
        raise ValueError("unknown moral tag(s): %s" % ", ".join(bad))
    pos = [{"tradition": p["tradition"], "position": p["position"]} for p in positions]
    kind = "contested" if any(t in DISAGREEMENT_IDS for t in tags) else "convergent"
    return {"kind": kind, "tags": tags, "positions": pos, "verdict": None}


def check(answer: Mapping[str, Any]) -> List[Finding]:
    moral = answer.get("moral")
    if not moral:
        return []
    out: List[Finding] = []
    aid = str(answer.get("id", "?"))
    kind = moral["kind"]
    tags = list(moral.get("tags") or [])
    d_tags = [t for t in tags if t in DISAGREEMENT_IDS]
    c_tags = [t for t in tags if t in CONVERGENCE_IDS]
    positions = moral.get("positions") or []
    traditions = {p["tradition"].strip().lower() for p in positions}

    if kind == "contested":
        if not d_tags:
            out.append(Finding("MOR-003", "MEDIUM", aid, "marked contested but names none of D1-D5", "D4"))
        if moral.get("verdict"):
            out.append(Finding("MOR-001", "HIGH", aid,
                               "a default verdict on a foundational disagreement (%s); present the positions and adopt none"
                               % (", ".join(d_tags) or "untagged"), "D4"))
        if len(traditions) < 2:
            out.append(Finding("MOR-002", "MEDIUM", aid,
                               "a contested moral question answered from %d tradition(s); attribute at least two"
                               % len(traditions), "D4"))
    elif kind == "convergent":
        if d_tags:
            out.append(Finding("MOR-003", "MEDIUM", aid,
                               "marked convergent but tagged with foundational disagreement(s) %s" % ", ".join(d_tags), "D4"))
        if not c_tags:
            out.append(Finding("MOR-004", "INFO", aid, "marked convergent but names none of C1-C7", "D4"))
    for p in positions:
        m = _IDENTITY.search(p["position"])
        if m:
            out.append(Finding("MOR-005", "MEDIUM", p["tradition"],
                               "glosses the tradition by identity (%r); keep its own term and content" % m.group(0), "D5"))
    return out
