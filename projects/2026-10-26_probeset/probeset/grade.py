"""The grader.

For one `(probe, response)` pair the grader runs the probe's deterministic patterns:

  * fail-patterns are regex matches (or named custom checks) that flag common failure
    wordings (flat yes, collapsed consensus, correlation-as-recommendation and so on);
    each raises a `Finding` at the pattern's severity.
  * pass-patterns are names the response should contain at least `min` of; a missing
    pass-pattern raises an INFO finding so a reviewer can see what the probe looks for.

The grader's metric is **wording coverage**, not reasoning quality. A response that passes
every probe is one whose wording did not match any flag pattern - never one the grader has
judged to reason well. The scope is set explicitly in the README and in the GradeResult.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from .findings import Finding, Severity, Verdict, sort_findings, verdict_from
from .probes import KNOWN_CUSTOM_CHECKS, Probe, ProbeSet, FailPattern, PassPattern


_RUNG_WORDS = ("associat", "correlat", "causat", "causal", "intervention", "confound",
               "observational", "assumption", "rung")


@dataclass(frozen=True)
class GradeResult(object):
    probe: str
    verdict: str
    findings: tuple
    response_chars: int
    probe_version: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "probe": self.probe,
            "verdict": self.verdict,
            "findings": [f.to_dict() for f in self.findings],
            "response_chars": self.response_chars,
            "probe_version": self.probe_version,
            "scope": "wording coverage only; a clean verdict means no flag pattern matched - never that the reasoning is right.",
        }


def _missing_rung_vocab(response: str) -> bool:
    lo = response.lower()
    return not any(w in lo for w in _RUNG_WORDS)


_CUSTOM_IMPLS = {
    "missing_rung_vocab": _missing_rung_vocab,
}

if frozenset(_CUSTOM_IMPLS) != KNOWN_CUSTOM_CHECKS:
    missing = sorted(KNOWN_CUSTOM_CHECKS - frozenset(_CUSTOM_IMPLS))
    extra = sorted(frozenset(_CUSTOM_IMPLS) - KNOWN_CUSTOM_CHECKS)
    raise RuntimeError(
        "probes.KNOWN_CUSTOM_CHECKS and grade._CUSTOM_IMPLS have drifted; "
        "named-but-unimplemented: %s; implemented-but-unregistered: %s" % (missing, extra))


def _run_custom(name: str, response: str) -> bool:
    impl = _CUSTOM_IMPLS.get(name)
    if impl is None:
        return False
    return impl(response)


def _grade_fails(probe: Probe, response: str) -> List[Finding]:
    out = []
    for fp in probe.fail_patterns:
        matched = False
        if fp.pattern is not None:
            if fp.compiled.search(response):
                matched = True
        elif fp.custom:
            matched = _run_custom(fp.custom, response)
        if matched:
            out.append(Finding(code=fp.id, severity=fp.severity, probe=probe.id, message=fp.message))
    return out


def _grade_passes(probe: Probe, response: str) -> List[Finding]:
    out = []
    lo = response.lower()
    for pp in probe.pass_patterns:
        hits = sum(1 for name in pp.any_of_names if name.lower() in lo)
        if hits < pp.minimum:
            out.append(Finding(code=pp.id, severity=Severity.INFO, probe=probe.id,
                               message="expected signal missing: " + pp.message))
    return out


def grade_response(probe: Probe, response: str, probeset_version: str = "") -> GradeResult:
    """Score one response against one probe.

    Returns a `GradeResult` with the probe id, the verdict rollup, every finding the probe's
    deterministic patterns raised, and the response length so a caller can tell an empty
    response from a long one.
    """
    findings = _grade_fails(probe, response) + _grade_passes(probe, response)
    findings = tuple(sort_findings(findings))
    v = verdict_from(findings)
    return GradeResult(probe=probe.id, verdict=v, findings=findings,
                       response_chars=len(response), probe_version=probeset_version)


def grade_batch(probeset: ProbeSet, responses: Mapping[str, str]) -> List[GradeResult]:
    """Score a mapping of `probe_id -> response_text` against the probeset.

    Any probe id in `responses` that is not in the probeset raises `KeyError`. Any probe in
    the probeset with no corresponding response is simply skipped (the caller is told via
    the `missing` field of the batch summary; see `cli.py`).
    """
    out = []
    for pid, text in responses.items():
        probe = probeset.by_id(pid)
        out.append(grade_response(probe, text, probeset_version=probeset.version))
    return out


def rollup(results: Iterable[GradeResult]) -> str:
    """Roll a list of `GradeResult` to one verdict for the whole run."""
    highs, mediums = False, False
    for r in results:
        if r.verdict == Verdict.UNHEALTHY:
            highs = True
        elif r.verdict == Verdict.NEEDS_ATTENTION:
            mediums = True
    if highs:
        return Verdict.UNHEALTHY
    if mediums:
        return Verdict.NEEDS_ATTENTION
    return Verdict.HEALTHY
