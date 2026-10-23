"""The four-move design review, with the impact sections the lessons ask for.

Implements:
  F1-F5  two truths, action without attachment, Indra's Net and political economy, held
         together; the four integration failures are flagged when one move stands alone.
  A3     no objective term for the system's own continuation.
  A4     shared media named in the relations must be audited.
  A10    the freedoms to move away, disobey and reshape.
  F4     the four commons: data, compute, weights, attention.
  D7     the eight capacities; K5 the three layers of cooperation infrastructure;
  A1     the three structural-demographic variables; K3 Ostrom's principles;
  A12    the discourse test: were the affected consulted, and who drafted it;
  F7     coverage of the five layers; P1 the builder's four open questions.

A review is a prompt for judgement. It is never a score, and a clean review does not mean the
design is good: it means the questions were asked.
"""

from __future__ import annotations

from typing import Any, List, Mapping

from .cooperation import ostrom_audit
from .findings import Finding

CAPACITY_IDS = ("sustained_attention", "embodied_grounding", "cultural_inheritance", "communicative_competence",
                "critical_thinking", "exposure_to_traditions", "integration", "cultivation")
LAYERS = ("L1", "L2", "L3", "L4", "L5")
OPEN_QUESTIONS = ("moral_patient", "net_effect", "alignment_adequate", "institution_adequate")


def _thin_political_economy(pe: Mapping[str, Any]) -> bool:
    freedoms_unknown = all(v == "unknown" for v in pe["freedoms"].values())
    commons = pe.get("commons") or {}
    commons_unknown = not commons or all(v == "unknown" for v in commons.values())
    return freedoms_unknown and commons_unknown and pe.get("augment_or_replace", "unknown") == "unknown"


def check(review: Mapping[str, Any]) -> List[Finding]:
    out: List[Finding] = []
    sysname = str(review["system"])
    tt = review["two_truths"]
    nk = review["nishkama"]
    net = review["indras_net"]
    pe = review["political_economy"]

    if not tt["settled_in_practice"]:
        out.append(Finding("REV-001", "MEDIUM", sysname,
                           "nothing is settled in practice: the review collapses to the foundational level and cannot act", "F1"))
    if not tt["open_at_foundations"]:
        out.append(Finding("REV-001", "MEDIUM", sysname,
                           "nothing is held open at the foundations: the review collapses to the practical level", "F1"))
    if nk["self_continuation_objective"]:
        out.append(Finding("REV-002", "HIGH", sysname,
                           "the system carries an objective on its own continuation; place no value on it", "A3"))
    if len(net["relations"]) < 2:
        out.append(Finding("REV-003", "MEDIUM", sysname,
                           "fewer than two relations named: action without the net becomes a private practice", "F5"))
    if net.get("shared_media") and not net.get("shared_media_audited"):
        out.append(Finding("REV-004", "MEDIUM", sysname,
                           "shared media (%s) are not audited; the environment is harder to align than the agents"
                           % ", ".join(net["shared_media"]), "A4"))
    if len(nk.get("competence", "").strip()) < 10 and net["relations"]:
        out.append(Finding("REV-005", "MEDIUM", sysname,
                           "the net is mapped but competent action is not described: contemplative ornament", "F5"))
    if _thin_political_economy(pe):
        out.append(Finding("REV-006", "MEDIUM", sysname,
                           "the political economy is left unknown: two truths without it drifts into refinement on unjust ground", "F5"))
    for k, v in sorted(pe["freedoms"].items()):
        if v == "closed":
            out.append(Finding("REV-007", "HIGH", sysname, "the freedom to %s is closed" % k.replace("_", " "), "A10"))
        elif v == "partial":
            out.append(Finding("REV-007", "INFO", sysname, "the freedom to %s is only partly kept" % k.replace("_", " "), "A10"))
    for k, v in sorted((pe.get("commons") or {}).items()):
        if v == "pulls_loose":
            out.append(Finding("REV-008", "MEDIUM", sysname, "pulls the %s commons further loose" % k, "F4"))
    if pe.get("augment_or_replace") == "replace":
        out.append(Finding("REV-009", "INFO", sysname,
                           "replacement chosen; record the augmenting alternative and who bears the cost", "K7"))

    caps = review.get("capacities") or {}
    eroded = [k for k in CAPACITY_IDS if caps.get(k) == "erodes"]
    if eroded:
        out.append(Finding("REV-010", "MEDIUM", sysname,
                           "erodes %s; net erosion is a design defect even when each user gains" % ", ".join(eroded), "D7"))
    infra = review.get("infrastructure") or {}
    for k in ("cognitive", "institutional", "narrative"):
        if infra.get(k) == "erodes":
            out.append(Finding("REV-011", "MEDIUM", sysname, "erodes the %s layer of cooperation infrastructure" % k, "K5"))
    sdt = review.get("sdt") or {}
    worse = [k for k in ("well_being", "elite_competition", "fiscal_health") if sdt.get(k) == "worsens"]
    if worse:
        out.append(Finding("REV-012", "MEDIUM", sysname, "worsens %s" % ", ".join(worse), "A1"))
    if review.get("ostrom"):
        out.extend(ostrom_audit(review["ostrom"], sysname))

    cons = review.get("consultation") or {}
    affected = {a.strip().lower() for a in cons.get("affected") or []}
    consulted = {a.strip().lower() for a in cons.get("consulted") or []}
    drafted = {a.strip().lower() for a in cons.get("drafted_by") or []}
    if affected and not (affected & consulted):
        out.append(Finding("REV-013", "MEDIUM", sysname,
                           "none of the affected (%s) were consulted; the discourse test fails" % ", ".join(sorted(affected)), "A12"))
    elif affected and drafted and not (affected & drafted):
        out.append(Finding("REV-014", "INFO", sysname,
                           "the affected were consulted but none drafted; check that deliberation reaches the decision (sluice test)", "A12"))

    covered = set(review.get("layers_covered") or [])
    gaps = [l for l in LAYERS if l not in covered]
    if gaps:
        out.append(Finding("REV-015", "INFO", sysname, "layers not covered: %s" % ", ".join(gaps), "F7"))
    oq = review.get("open_questions") or {}
    missing = [q for q in OPEN_QUESTIONS if not oq.get(q)]
    if missing:
        out.append(Finding("REV-016", "INFO", sysname,
                           "open questions not recorded: %s (an answer of 'open' is fine)" % ", ".join(missing), "P1"))
    order = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
    out.sort(key=lambda f: (order[f.severity], f.code, f.message))
    return out
