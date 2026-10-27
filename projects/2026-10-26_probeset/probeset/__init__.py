"""probeset: six scorable prompt probes for the threads' most-often-broken rules.

Standard library only. The data is six paraphrased probes from the threads (CC-BY-SA-4.0,
`data/probes.json`); the grader is a deterministic text pass over a response, this lab's own.
A clean score means the response's wording did not match any flag pattern - never that the
reasoning behind it is right.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .findings import Finding, Severity, Verdict, verdict_from, exit_code
from .probes import Probe, ProbeSet, load_probes, probe_version
from .grade import grade_response, grade_batch, GradeResult

__all__ = [
    "__version__",
    "Finding",
    "Severity",
    "Verdict",
    "verdict_from",
    "exit_code",
    "Probe",
    "ProbeSet",
    "load_probes",
    "probe_version",
    "grade_response",
    "grade_batch",
    "GradeResult",
]
