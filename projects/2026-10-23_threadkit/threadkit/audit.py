"""Audit a deployment declaration against the threads.

A deployment declaration lists which lessons a team has adopted, at which enforcement layer,
with an owner and a merge date, and the test and review date each lesson carries (P2). The
audit reports:

  THR-001  MEDIUM  nothing adopted
  THR-002  HIGH    an unknown lesson id
  THR-003  MEDIUM  a lesson adopted at a layer that cannot enforce it
  THR-004  MEDIUM  an adopted item with no owner or no merge date: adoption means shipped
  THR-005  MEDIUM  lessons adopted without the method baseline (M1-M4) they assume
  THR-006  MEDIUM  a four-move lesson (F1-F4) adopted without F5: the moves are held together
  THR-007  INFO    an adopted lesson with no recorded test or review date (P2)
  THR-008  INFO    a review date that has passed
  THR-009  INFO    a strand with nothing adopted

Verdict: any HIGH -> unhealthy (exit 2); any MEDIUM -> needs-attention (exit 1); otherwise
healthy (exit 0). A healthy audit means the declaration is consistent with the threads, never
that the system reasons well.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Mapping, Optional

from .findings import Finding, sort_findings
from .spec import Threads, deployment_validator

METHOD_BASELINE = ("M1", "M2", "M3", "M4")
FOUR_MOVES = ("F1", "F2", "F3", "F4")


def audit(declaration: Mapping[str, Any], threads: Optional[Threads] = None) -> List[Finding]:
    t = threads or Threads.load()
    errors = deployment_validator().errors(declaration)
    if errors:
        raise ValueError("declaration is not valid: " + "; ".join("%s %s" % (p or "/", m) for p, m in errors[:5]))
    as_of = declaration.get("as_of") or _dt.date.today().isoformat()
    out: List[Finding] = []
    adopted = list(declaration.get("adopted") or [])
    if not adopted:
        out.append(Finding("THR-001", "MEDIUM", "deployment", "nothing adopted; start with the method lessons M1-M4", "M1"))
    ids: List[str] = []
    for item in adopted:
        lid = item["id"].strip().upper()
        if not t.has(lid):
            out.append(Finding("THR-002", "HIGH", item["id"], "not a lesson of threads %s" % t.version))
            continue
        ids.append(lid)
        lesson = t.get(lid)
        if item["layer"] not in lesson["enforcement_layers"]:
            out.append(Finding("THR-003", "MEDIUM", lid,
                               "adopted at the %s layer, which cannot enforce it; it needs %s"
                               % (item["layer"], " or ".join(lesson["enforcement_layers"])), lid))
        if not item.get("owner") or not item.get("merged"):
            out.append(Finding("THR-004", "MEDIUM", lid, "adoption means shipped: name an owner and a merge date", lid))
        if not item.get("test") or not item.get("review_date"):
            out.append(Finding("THR-007", "INFO", lid,
                               "no test or review date recorded; a lesson that cannot be wrong cannot be learned from", "P2"))
        elif item["review_date"] < as_of:
            out.append(Finding("THR-008", "INFO", lid, "review date %s has passed" % item["review_date"], "P2"))

    chosen = set(ids)
    others = chosen - set(METHOD_BASELINE)
    missing_base = [m for m in METHOD_BASELINE if m not in chosen]
    if others and missing_base:
        out.append(Finding("THR-005", "MEDIUM", "method",
                           "lessons are adopted without the method baseline they assume: %s" % ", ".join(missing_base), "M1"))
    if chosen & set(FOUR_MOVES) and "F5" not in chosen:
        out.append(Finding("THR-006", "MEDIUM", "F5",
                           "a four-move lesson is adopted without F5; any one move alone fails in a characteristic way", "F5"))
    if adopted:
        for s, meta in sorted(t.strands().items()):
            if not any(i.startswith(s) for i in chosen):
                out.append(Finding("THR-009", "INFO", "strand %s" % s, "nothing adopted from %s" % meta["title"]))
    return sort_findings(out)
