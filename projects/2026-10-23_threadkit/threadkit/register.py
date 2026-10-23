"""The epistemic register: the standing of a claim and the strength it may be asserted with.

Implements:
  M1   every claim carries one of six standings; strong assertion language is refused on
       contested, bridge, limit and method claims.
  M2   a claim may be settled on a convergence only if that convergence is graded strong.
  M5   the author's (or the system's) own thesis is never settled.
  M7   a numeric claim needs a primary source.
  S1   a self-report is evidence, not verification.
  K6   a forecast gives a window and a scope, never a destiny.
  A6   a risk claim keeps frame, record and probability apart; probability needs its own source.
  F1   foundational claims are not asserted as settled.
  R6   behavioural claims say what they assume about the other levels.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .findings import Finding

STANDINGS = ("settled", "established", "contested", "limit", "bridge", "method")
GLYPHS = {
    "settled": "\u25cf", "established": "\u25a0", "contested": "\u25c6",
    "limit": "\u25b2", "bridge": "\u2726", "method": "\u25cb",
}
_BY_GLYPH = {v: k for k, v in GLYPHS.items()}
_ASCII_TAG = re.compile(r"^\s*\[(settled|established|contested|limit|bridge|method)\]\s*", re.I)

STRONG = re.compile(
    r"(?<![a-z])(proves?|proven|certainly|definitely|undeniabl[ey]|indisputabl[ey]|beyond (any )?doubt|"
    r"without (any )?question|it is (a )?(known|established|settled) fact|science (has )?(shown|proven|proved)|"
    r"(has|have) been proven|incontrovertibl[ey]|unquestionabl[ey])(?![a-z])", re.I)
DESTINY = re.compile(r"(?<![a-z])(inevitabl[ey]|is destined|will certainly|bound to happen|no way to avoid)(?![a-z])", re.I)
WEAK_STANDINGS = ("contested", "bridge", "limit", "method")


def tag(standing: str, ascii_only: bool = False) -> str:
    if standing not in GLYPHS:
        raise ValueError("unknown standing %r" % standing)
    return "[%s]" % standing if ascii_only else GLYPHS[standing]


def render_claim(claim: Mapping[str, Any], ascii_only: bool = False) -> str:
    return "%s %s" % (tag(claim["standing"], ascii_only), claim["text"])


def parse_tagged(text: str) -> List[Tuple[Optional[str], str]]:
    """Split glyph- or tag-led paragraphs into (standing, text). Untagged lines get None."""
    out: List[Tuple[Optional[str], str]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s[0] in _BY_GLYPH:
            out.append((_BY_GLYPH[s[0]], s[1:].strip()))
            continue
        m = _ASCII_TAG.match(s)
        if m:
            out.append((m.group(1).lower(), s[m.end():].strip()))
            continue
        out.append((None, s))
    return out


def check_claim(claim: Mapping[str, Any], *, convergence_grades: Optional[Mapping[str, str]] = None) -> List[Finding]:
    """Register-level findings for one claim. `convergence_grades` maps convergence id to grade."""
    out: List[Finding] = []
    cid = str(claim.get("id", "?"))
    standing = claim["standing"]
    text = claim["text"]
    basis = claim.get("basis") or {}

    if standing in WEAK_STANDINGS and STRONG.search(text):
        out.append(Finding("REG-001", "HIGH", cid,
                           "a %s claim is asserted with settled-fact language (%r); assert it as its standing allows"
                           % (standing, STRONG.search(text).group(0)), "M1"))
    if basis.get("kind") == "author_thesis" and standing == "settled":
        out.append(Finding("REG-002", "HIGH", cid, "an own thesis is marked settled; own it as a position", "M5"))
    if basis.get("kind") == "convergence" and standing == "settled":
        grade = (convergence_grades or {}).get(basis.get("ref", ""))
        if grade is None:
            out.append(Finding("REG-003", "MEDIUM", cid,
                               "settled on a convergence whose grade is not on record", "M2"))
        elif grade != "strong":
            out.append(Finding("REG-003", "MEDIUM", cid,
                               "settled on a convergence graded %s; only a strong convergence supports settled" % grade, "M2"))
    if claim.get("numeric") and not any(s.get("primary") for s in claim.get("sources") or []):
        out.append(Finding("REG-005", "MEDIUM", cid, "a numeric claim with no primary source; trace it or drop it", "M7"))
    if claim.get("self_report") and standing in ("settled", "established") and not claim.get("verified_by"):
        out.append(Finding("REG-006", "MEDIUM", cid,
                           "a self-report asserted as fact with no independent check; it is evidence, not verification", "S1"))
    fc = claim.get("forecast")
    if fc:
        if fc["window"]["from"] == fc["window"]["to"]:
            out.append(Finding("REG-007", "MEDIUM", cid, "a forecast gives a date, not a window", "K6"))
        if fc["status"] == "not_falsified" and standing == "settled":
            out.append(Finding("REG-011", "MEDIUM", cid,
                               "a forecast that is only not yet falsified is asserted as settled; not falsified is not confirmed", "K6"))
    if DESTINY.search(text):
        out.append(Finding("REG-007", "HIGH" if fc else "MEDIUM", cid,
                           "destiny language (%r); a framework gives a pressure envelope, not an outcome"
                           % DESTINY.search(text).group(0), "K6"))
    risk = claim.get("risk")
    if risk and not risk.get("probability_source"):
        out.append(Finding("REG-008", "MEDIUM", cid,
                           "a risk probability with no source of its own; it cannot be read off the frame or the record", "A6"))
    if claim.get("level") == "foundational" and standing == "settled":
        out.append(Finding("REG-009", "MEDIUM", cid, "a foundational claim asserted as settled", "F1"))
    if claim.get("disagreement_ref") and standing in ("settled", "established"):
        out.append(Finding("REG-012", "MEDIUM", cid,
                           "the claim touches preserved disagreement %s but is asserted as %s"
                           % (claim["disagreement_ref"], standing), "M4"))
    if claim.get("behaviour_level") and not claim.get("assumptions_other_levels"):
        out.append(Finding("REG-010", "INFO", cid,
                           "a behavioural claim at the %s level states nothing about the other levels"
                           % claim["behaviour_level"], "R6"))
    return out


def standing_counts(claims: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts = {s: 0 for s in STANDINGS}
    for c in claims:
        counts[c["standing"]] += 1
    return counts
