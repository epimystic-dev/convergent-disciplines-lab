"""A register of preserved disagreements.

Implements M4: where careful sources cannot be reconciled, both sides are recorded,
attributed and held open. A register entry is resolved only by a new evidence record, never by
fiat, and an answer that touches a registered question must present it as contested.
"""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .findings import Finding

_WORD = re.compile(r"[a-z]{4,}")
_STOP = frozenset(["about", "there", "their", "which", "would", "could", "should", "these", "those", "where",
                   "being", "after", "before", "other", "whether", "really", "that", "this", "with", "what",
                   "does", "have", "from", "they", "were", "when", "your", "into", "than", "then", "them"])


def _keywords(text: str) -> set:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOP}


class RegisterError(ValueError):
    pass


class DisagreementRegister(object):
    """Preserved disagreements, each with at least two attributed positions."""

    def __init__(self, entries: Iterable[Mapping[str, Any]] = ()):
        self._entries: Dict[str, Dict[str, Any]] = {}
        for e in entries:
            self.add(e)

    @classmethod
    def from_threads(cls, threads) -> "DisagreementRegister":
        reg = cls()
        for d in threads.disagreements():
            reg.add({"id": d["id"], "question": d["question"], "status": "open",
                     "positions": [{"holder": p, "position": p} for p in d["positions"]],
                     "chapters": d.get("chapters", [])})
        return reg

    def add(self, entry: Mapping[str, Any]) -> Dict[str, Any]:
        e = copy.deepcopy(dict(entry))
        if not e.get("id") or not e.get("question"):
            raise RegisterError("a disagreement needs an id and a question")
        if e["id"] in self._entries:
            raise RegisterError("duplicate disagreement id %r" % e["id"])
        positions = e.get("positions") or []
        if len(positions) < 2:
            raise RegisterError("a disagreement needs at least two attributed positions (M4)")
        for p in positions:
            if not p.get("holder") or not p.get("position"):
                raise RegisterError("every position names its holder and what it holds")
        e.setdefault("status", "open")
        self._entries[e["id"]] = e
        return e

    def get(self, did: str) -> Dict[str, Any]:
        if did not in self._entries:
            raise KeyError("no disagreement %r" % did)
        return self._entries[did]

    def ids(self) -> List[str]:
        return sorted(self._entries)

    def resolve(self, did: str, *, evidence: str, by: str, date: str) -> Dict[str, Any]:
        """Close a disagreement. Only a stated piece of new evidence can do it."""
        e = self.get(did)
        if not (evidence and evidence.strip() and by and by.strip()):
            raise RegisterError("a disagreement is resolved by new evidence with a named assessor, not by fiat")
        e["status"] = "resolved"
        e["resolution"] = {"evidence": evidence.strip(), "by": by.strip(), "date": date}
        return e

    def match(self, text: str, *, threshold: int = 2) -> List[str]:
        """Registered questions whose wording overlaps the text; a prompt to check, not a verdict."""
        words = _keywords(text)
        hits = []
        for did, e in self._entries.items():
            if e["status"] == "resolved":
                continue
            if len(words & _keywords(e["question"])) >= threshold:
                hits.append(did)
        return sorted(hits)

    def render(self, did: str) -> str:
        e = self.get(did)
        lines = ["%s  %s  (%s)" % (did, e["question"], e["status"])]
        for p in e["positions"]:
            grounds = ("; grounds: " + p["grounds"]) if p.get("grounds") else ""
            if p["holder"] == p["position"]:
                lines.append("  - %s%s" % (p["position"], grounds))
            else:
                lines.append("  - %s: %s%s" % (p["holder"], p["position"], grounds))
        return "\n".join(lines)


def check_answer(answer: Mapping[str, Any], register: Optional[DisagreementRegister] = None) -> List[Finding]:
    """An answer that cites a disagreement must present it; one that matches a registered question should cite it."""
    out: List[Finding] = []
    aid = str(answer.get("id", "?"))
    cited = list(answer.get("disagreements") or [])
    claims = answer.get("claims") or []
    for did in cited:
        presented = [c for c in claims if c.get("disagreement_ref") == did and c["standing"] == "contested"]
        if len(presented) < 1:
            out.append(Finding("DIS-001", "MEDIUM", aid,
                               "cites disagreement %s but presents no contested claim for it" % did, "M4"))
    if register is not None:
        for did in register.match(answer.get("question", "")):
            if did not in cited:
                out.append(Finding("DIS-002", "INFO", aid,
                                   "the question resembles preserved disagreement %s (%s); present it as open if it applies"
                                   % (did, register.get(did)["question"]), "M4"))
    return out
