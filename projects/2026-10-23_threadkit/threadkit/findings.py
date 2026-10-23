"""The one finding type every checker in the package returns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

SEVERITIES = ("HIGH", "MEDIUM", "INFO")
_ORDER = {s: i for i, s in enumerate(SEVERITIES)}


@dataclass(frozen=True)
class Finding(object):
    code: str
    severity: str
    subject: str
    message: str
    lesson: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "severity": self.severity, "subject": self.subject,
                "message": self.message, "lesson": self.lesson}


def sort_findings(findings: Iterable[Finding]) -> List[Finding]:
    return sorted(findings, key=lambda f: (_ORDER[f.severity], f.code, f.subject))


def verdict(findings: Iterable[Finding]) -> str:
    sev = {f.severity for f in findings}
    if "HIGH" in sev:
        return "unhealthy"
    if "MEDIUM" in sev:
        return "needs-attention"
    return "healthy"


def exit_code(v: str) -> int:
    return {"healthy": 0, "needs-attention": 1, "unhealthy": 2}.get(v, 2)
