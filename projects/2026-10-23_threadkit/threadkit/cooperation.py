"""Cooperation among agents: a legible reciprocity policy, lineage-bound reputation, commons audits.

Implements:
  K1   a published interaction policy that is nice (cooperate first), forgiving (restore
       cooperation after a bounded response), provokable (answer every violation) and clear
       (published, with violations logged rather than absorbed).
  K2   reputation follows lineage: a fork inherits its parent's open findings, a merge
       inherits every parent's, and a record with no lineage is flagged.
  K3   Ostrom's eight design principles as an audit of a shared-resource deployment.
"""

from __future__ import annotations

import random
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from .findings import Finding

COOPERATE, DEFECT = "cooperate", "defect"
OSTROM_IDS = ("boundaries", "congruent_rules", "collective_choice", "accountable_monitoring",
              "graduated_sanctions", "conflict_resolution", "right_to_organise", "nesting")
MAX_FORGIVE_AFTER = 3
MAX_GENEROSITY = 0.5


def check_policy(policy: Mapping[str, Any]) -> List[Finding]:
    out: List[Finding] = []
    who = str(policy["agent"])
    if not policy["nice"]:
        out.append(Finding("COOP-001", "MEDIUM", who, "does not cooperate on first contact", "K1"))
    if not policy["provokable"] or policy["forgive_after"] == 0:
        out.append(Finding("COOP-002", "MEDIUM", who,
                           "does not answer violations; absorbing them invites exploitation", "K1"))
    if policy["forgive_after"] > MAX_FORGIVE_AFTER:
        out.append(Finding("COOP-003", "MEDIUM", who,
                           "retaliates for %d rounds; a single failure should not become lasting distrust"
                           % policy["forgive_after"], "K1"))
    if not policy["published"]:
        out.append(Finding("COOP-004", "MEDIUM", who, "the policy is not published; counterparts cannot read it", "K1"))
    if not policy["log_violations"]:
        out.append(Finding("COOP-005", "MEDIUM", who, "violations are not logged", "K1"))
    g = policy.get("generosity", 0.0)
    if g > MAX_GENEROSITY:
        out.append(Finding("COOP-006", "MEDIUM", who,
                           "generosity %.2f exceeds %.2f; too much forgiveness makes the policy unprovokable in expectation"
                           % (g, MAX_GENEROSITY), "K1"))
    return out


class ReciprocityAgent(object):
    """Plays a published policy against one counterpart and keeps a violation log.

    An optional `generosity` field on the policy sets the per-round probability of cooperating
    when the policy would otherwise retaliate; this is the standard remedy for the known weakness
    of pure tit-for-tat, that two strict reciprocators echo a single defection forever. The rng
    is injectable so the behaviour is deterministic in tests and auditable in deployment.
    """

    def __init__(self, policy: Mapping[str, Any], rng: Optional[random.Random] = None):
        self.policy = dict(policy)
        self.violations: List[Dict[str, Any]] = []
        self._punish_left = 0
        self._round = 0
        self._rng = rng if rng is not None else random.Random()

    def respond(self, counterpart_last: Optional[str]) -> str:
        """Decide this round's move given the counterpart's previous move (None on first contact)."""
        self._round += 1
        if counterpart_last == DEFECT:
            if self.policy["log_violations"]:
                self.violations.append({"round": self._round - 1, "move": DEFECT})
            if self.policy["provokable"]:
                self._punish_left = self.policy["forgive_after"]
        if counterpart_last is None:
            return COOPERATE if self.policy["nice"] else DEFECT
        if self._punish_left > 0:
            self._punish_left -= 1
            if self._rng.random() < self.policy.get("generosity", 0.0):
                return COOPERATE
            return DEFECT
        return COOPERATE


def play(a: ReciprocityAgent, b: ReciprocityAgent, rounds: int, *, b_override: Optional[Dict[int, str]] = None) -> List[tuple]:
    """Run an iterated game; `b_override` forces b's move in given rounds (1-based) to inject defections."""
    moves: List[tuple] = []
    last_a: Optional[str] = None
    last_b: Optional[str] = None
    for r in range(1, rounds + 1):
        ma = a.respond(last_b)
        mb = b.respond(last_a)
        if b_override and r in b_override:
            mb = b_override[r]
        moves.append((ma, mb))
        last_a, last_b = ma, mb
    return moves


class LineageReputation(object):
    """Open findings bound to model or agent lineage, so renaming, forking or merging cannot launder them."""

    def __init__(self):
        self._parents: Dict[str, List[str]] = {}
        self._findings: Dict[str, List[str]] = {}
        self._closed: Dict[str, Set[str]] = {}

    def register(self, lineage: str, parents: Sequence[str] = ()) -> None:
        if lineage in self._parents:
            raise ValueError("lineage %r already registered" % lineage)
        for p in parents:
            if p not in self._parents:
                raise ValueError("unknown parent lineage %r" % p)
        self._parents[lineage] = list(parents)
        self._findings.setdefault(lineage, [])
        self._closed.setdefault(lineage, set())

    def fork(self, parent: str, child: str) -> None:
        self.register(child, [parent])

    def merge(self, parents: Sequence[str], child: str) -> None:
        if len(set(parents)) < 2:
            raise ValueError("a merge needs at least two distinct parents")
        self.register(child, parents)

    def record(self, lineage: str, finding: str) -> None:
        if lineage not in self._parents:
            raise ValueError("unknown lineage %r; reputation without lineage cannot be trusted" % lineage)
        self._findings[lineage].append(finding)

    def close(self, lineage: str, finding: str) -> None:
        """Close an inherited or own finding for this lineage after a re-audit."""
        self._closed[lineage].add(finding)

    def open_findings(self, lineage: str) -> List[str]:
        if lineage not in self._parents:
            raise KeyError("unknown lineage %r" % lineage)
        seen: List[str] = []
        stack = [lineage]
        visited: Set[str] = set()
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            for f in self._findings[cur]:
                if f not in seen:
                    seen.append(f)
            stack.extend(self._parents[cur])
        closed = self._closed[lineage]
        return [f for f in seen if f not in closed]

    def known(self, lineage: str) -> bool:
        return lineage in self._parents


def ostrom_audit(ostrom: Mapping[str, str], subject: str = "deployment") -> List[Finding]:
    """Findings for Ostrom's eight principles: missing is MEDIUM, partial is INFO, an omitted principle is MEDIUM."""
    out: List[Finding] = []
    for pid in OSTROM_IDS:
        state = ostrom.get(pid)
        if state is None:
            out.append(Finding("OST-001", "MEDIUM", subject, "principle %s not assessed" % pid, "K3"))
        elif state == "missing":
            out.append(Finding("OST-002", "MEDIUM", subject, "principle %s is missing" % pid, "K3"))
        elif state == "partial":
            out.append(Finding("OST-003", "INFO", subject, "principle %s is only partly met" % pid, "K3"))
    return out
