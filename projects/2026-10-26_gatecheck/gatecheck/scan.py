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
    """Run every enabled rule against one commitment record."""
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
    return [scan_record(r, disabled) for r in records]


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
