"""Report rendering.

The text report folds every character outside printable ASCII to `<U+XXXX>` so a console on
a legacy code page can still write it. The JSON report sends ASCII-escaped payloads for the
same reason - a `--json` pipe is unreadable if the writer crashes.
"""

from __future__ import annotations

import json
from typing import Dict, Iterable, List, TextIO

from . import __version__
from .findings import Finding, Severity, Verdict, exit_code
from .grade import GradeResult, rollup
from .text import fold


def _emit(stream: TextIO, text: str) -> None:
    stream.write(fold(text) + "\n")


def text_report(results: List[GradeResult], probeset_version: str, out: TextIO, err: TextIO,
                include_info: bool = False, strict: bool = False) -> int:
    """Write a human-readable report. Findings on stdout, summary on stderr."""
    v = rollup(results)
    if strict:
        for r in results:
            if any(f.severity == Severity.INFO for f in r.findings) and r.verdict == Verdict.HEALTHY:
                v = Verdict.NEEDS_ATTENTION
                break
    for r in results:
        _emit(out, "")
        _emit(out, "%s  %s" % (r.probe, r.verdict))
        shown = [f for f in r.findings if f.severity != Severity.INFO or include_info or strict]
        if not shown:
            _emit(out, "  (no flag pattern matched)")
            continue
        for f in shown:
            _emit(out, "  %-6s %-28s %s" % (f.severity, f.code, f.message))
    _emit(err, "probeset %s: %s; %d probe(s) over probes v%s" %
          (__version__, v, len(results), probeset_version))
    return exit_code(v)


def json_report(results: List[GradeResult], probeset_version: str, out: TextIO, err: TextIO,
                include_info: bool = False, strict: bool = False) -> int:
    """Write a JSON report. One payload on stdout, one summary line on stderr."""
    v = rollup(results)
    if strict:
        for r in results:
            if any(f.severity == Severity.INFO for f in r.findings) and r.verdict == Verdict.HEALTHY:
                v = Verdict.NEEDS_ATTENTION
                break
    payload = {
        "tool": "probeset",
        "version": __version__,
        "probes_version": probeset_version,
        "verdict": v,
        "results": [],
        "scope": "wording coverage only; the grader does not judge reasoning.",
    }
    for r in results:
        shown = [f for f in r.findings if f.severity != Severity.INFO or include_info or strict]
        d = dict(r.to_dict())
        d["findings"] = [f.to_dict() for f in shown]
        payload["results"].append(d)
    out.write(json.dumps(payload, indent=2) + "\n")
    _emit(err, "probeset %s: %s; %d probe(s) over probes v%s" %
          (__version__, v, len(results), probeset_version))
    return exit_code(v)
