"""Finding, Severity, Verdict - the lab's shared surface for a linter output.

A `Finding` is a flag the scanner raised for one commitment record. A `Severity` is HIGH,
MEDIUM or INFO. A `Verdict` rolls up a set of findings to one of
`healthy`, `needs-attention`, `unhealthy`, `unknown`.
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
    UNKNOWN = "unknown"


_ORDER = {s: i for i, s in enumerate(Severity.ALL)}


@dataclass(frozen=True)
class Finding(object):
    code: str
    severity: str
    subject: str
    message: str
    lesson: str = "A11"

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "severity": self.severity, "subject": self.subject,
                "message": self.message, "lesson": self.lesson}


def sort_findings(findings: Iterable[Finding]) -> List[Finding]:
    return sorted(findings, key=lambda f: (_ORDER[f.severity], f.subject, f.code))


def verdict_from(findings: Iterable[Finding]) -> str:
    sev = {f.severity for f in findings if f.severity != Severity.INFO}
    if Severity.HIGH in sev:
        return Verdict.UNHEALTHY
    if Severity.MEDIUM in sev:
        return Verdict.NEEDS_ATTENTION
    return Verdict.HEALTHY


def exit_code(v: str) -> int:
    return {Verdict.HEALTHY: 0, Verdict.NEEDS_ATTENTION: 1,
            Verdict.UNHEALTHY: 2, Verdict.UNKNOWN: 2}.get(v, 2)
