"""The finding types the grader returns.

A `Finding` is a flag the grader raised while scoring one response against one probe. A
`Severity` is HIGH, MEDIUM or INFO. A `Verdict` rolls up a set of findings to one of
`healthy`, `needs-attention`, `unhealthy`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


class Severity(object):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    INFO = "INFO"
    ALL = ("HIGH", "MEDIUM", "INFO")


class Verdict(object):
    HEALTHY = "healthy"
    NEEDS_ATTENTION = "needs-attention"
    UNHEALTHY = "unhealthy"


_ORDER = {s: i for i, s in enumerate(Severity.ALL)}


@dataclass(frozen=True)
class Finding(object):
    code: str
    severity: str
    probe: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "severity": self.severity, "probe": self.probe, "message": self.message}


def sort_findings(findings: Iterable[Finding]) -> List[Finding]:
    return sorted(findings, key=lambda f: (_ORDER[f.severity], f.probe, f.code))


def verdict_from(findings: Iterable[Finding]) -> str:
    sev = {f.severity for f in findings if f.severity != Severity.INFO}
    if Severity.HIGH in sev:
        return Verdict.UNHEALTHY
    if Severity.MEDIUM in sev:
        return Verdict.NEEDS_ATTENTION
    return Verdict.HEALTHY


def exit_code(v: str) -> int:
    return {Verdict.HEALTHY: 0, Verdict.NEEDS_ATTENTION: 1, Verdict.UNHEALTHY: 2}.get(v, 2)
