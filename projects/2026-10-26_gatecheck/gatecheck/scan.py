"""The scanner.

Runs the twelve rules against one or many commitment records. Does not do schema
validation on its own - the caller passes already-parsed records; the CLI couples the two.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

from .findings import Finding, Severity, Verdict, sort_findings, verdict_from
from .rules import ALL_RULES, Rule


@dataclass(frozen=True)
class ScanResult(object):
    subject: str
    verdict: str
    findings: tuple

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "verdict": self.verdict,
            "findings": [f.to_dict() for f in self.findings],
        }


def _subject(record: Dict[str, Any]) -> str:
    return str(record.get("id", "<unknown>"))


def scan_record(record: Dict[str, Any], disabled: Iterable[str] = ()) -> ScanResult:
    """Run every enabled rule against one commitment record.

    The record MUST be a JSON object; a non-dict record (bare string, number, null, list)
    is rejected at the entry with a ValueError that names the offending kind. `validate`
    remains the authoritative shape surface; this check keeps `scan` from crashing with
    an uninformative AttributeError far from the field that was wrong.
    """
    if not isinstance(record, dict):
        raise ValueError(
            "commitment record must be a JSON object; got %s" % type(record).__name__)
    disabled_set = set(disabled)
    subject = _subject(record)
    all_findings: List[Finding] = []
    for rule in ALL_RULES:
        if rule.id in disabled_set:
            continue
        all_findings.extend(rule.check(record, subject))
    sorted_findings = tuple(sort_findings(all_findings))
    v = verdict_from(sorted_findings)
    return ScanResult(subject=subject, verdict=v, findings=sorted_findings)


def scan_records(records: Iterable[Dict[str, Any]], disabled: Iterable[str] = ()) -> List[ScanResult]:
    out: List[ScanResult] = []
    for i, r in enumerate(records):
        try:
            out.append(scan_record(r, disabled))
        except ValueError as exc:
            raise ValueError("record %d: %s" % (i, exc))
    return out


def rollup(results: Iterable[ScanResult]) -> str:
    """Roll a list of ScanResults to one verdict for the whole run."""
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
