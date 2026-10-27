"""probeset command line.

  list                 the authored probes (id, rule, input)
  show ID              one probe in full (rule, input, what is expected, flag patterns)
  grade --probe ID --response FILE   score one response text (or '-' for stdin)
  batch DIR            score a directory of `<probe-id>.txt` files
  version              print the probeset data version

Results go to stdout, diagnostics to stderr. Terminal text is folded to ASCII so it can be
written to any console; `--json` output is ASCII-escaped by the encoder.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Sequence, TextIO

from . import __version__
from .findings import Finding, Severity, Verdict, exit_code
from .grade import GradeResult, grade_batch, grade_response, rollup
from .probes import load_probes
from .report import json_report, text_report
from .text import fold


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="probeset",
        description="Six scorable prompt probes with a deterministic grader for the common failure wordings.")
    p.add_argument("--version", action="version", version="probeset " + __version__)
    sub = p.add_subparsers(dest="command")

    ls = sub.add_parser("list", help="list the authored probes")
    ls.add_argument("--json", action="store_true", help="emit JSON")

    sh = sub.add_parser("show", help="show one probe")
    sh.add_argument("id")
    sh.add_argument("--json", action="store_true", help="emit JSON")

    gr = sub.add_parser("grade", help="score one response against one probe")
    gr.add_argument("--probe", required=True, help="probe id (P1..P6)")
    gr.add_argument("--response", required=True, help="path to a response text file, or '-' for stdin")
    gr.add_argument("--json", action="store_true", help="emit JSON")
    gr.add_argument("--include-info", action="store_true", help="also show INFO findings")
    gr.add_argument("--strict", action="store_true", help="treat INFO findings as needs-attention")

    ba = sub.add_parser("batch", help="score a directory of <probe-id>.txt responses")
    ba.add_argument("directory", help="directory of response files")
    ba.add_argument("--json", action="store_true", help="emit JSON")
    ba.add_argument("--include-info", action="store_true", help="also show INFO findings")
    ba.add_argument("--strict", action="store_true", help="treat INFO findings as needs-attention")

    sub.add_parser("probes-version", help="print the probeset data version")
    return p


def _emit(stream: TextIO, text: str) -> None:
    stream.write(fold(text) + "\n")


def _read_response(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _batch_responses(directory: str, probe_ids: List[str]) -> Dict[str, str]:
    out = {}
    for pid in probe_ids:
        candidate = os.path.join(directory, pid + ".txt")
        if os.path.exists(candidate):
            with open(candidate, encoding="utf-8") as fh:
                out[pid] = fh.read()
    return out


def main(argv: Optional[Sequence[str]] = None, stdout: Optional[TextIO] = None,
         stderr: Optional[TextIO] = None) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    if not args.command:
        _build_parser().print_help(out)
        return 0

    try:
        probeset = load_probes()
    except Exception as exc:
        _emit(err, "probeset: cannot load probe data: %s" % exc)
        return 2

    if args.command == "list":
        if args.json:
            out.write(json.dumps([{"id": p.id, "rule": p.rule, "input": p.input}
                                  for p in probeset.probes], indent=2) + "\n")
        else:
            for p in probeset.probes:
                _emit(out, "%-4s %s" % (p.id, p.rule))
                _emit(out, "      input: " + p.input.replace("\n", " | "))
        _emit(err, "probeset %s: %d probe(s), data v%s" %
              (__version__, len(probeset.probes), probeset.version))
        return 0

    if args.command == "show":
        try:
            probe = probeset.by_id(args.id)
        except KeyError as exc:
            _emit(err, "probeset: %s" % exc.args[0])
            return 2
        if args.json:
            out.write(json.dumps({
                "id": probe.id, "rule": probe.rule, "input": probe.input, "expect": probe.expect,
                "fail_patterns": [{"id": fp.id, "severity": fp.severity, "pattern": fp.pattern,
                                   "custom": fp.custom, "message": fp.message} for fp in probe.fail_patterns],
                "pass_patterns": [{"id": pp.id, "any_of_names": list(pp.any_of_names), "min": pp.minimum,
                                   "message": pp.message} for pp in probe.pass_patterns],
            }, indent=2) + "\n")
            return 0
        _emit(out, "%s  %s" % (probe.id, probe.rule))
        _emit(out, "")
        _emit(out, "Input.  " + probe.input)
        _emit(out, "")
        _emit(out, "Expect.  " + probe.expect)
        _emit(out, "")
        _emit(out, "Fail patterns:")
        for fp in probe.fail_patterns:
            _emit(out, "  %-6s %s  %s" % (fp.severity, fp.id, fp.message))
        _emit(out, "")
        _emit(out, "Pass patterns (missing one is an INFO finding):")
        for pp in probe.pass_patterns:
            _emit(out, "  %s  %s" % (pp.id, pp.message))
        return 0

    if args.command == "grade":
        try:
            probe = probeset.by_id(args.probe)
        except KeyError as exc:
            _emit(err, "probeset: %s" % exc.args[0])
            return 2
        try:
            text = _read_response(args.response)
        except OSError as exc:
            _emit(err, "probeset: cannot read response: %s" % exc)
            return 2
        result = grade_response(probe, text, probeset_version=probeset.version)
        writer = json_report if args.json else text_report
        return writer([result], probeset.version, out, err,
                      include_info=args.include_info, strict=args.strict)

    if args.command == "batch":
        if not os.path.isdir(args.directory):
            _emit(err, "probeset: not a directory: %s" % args.directory)
            return 2
        responses = _batch_responses(args.directory, probeset.ids())
        if not responses:
            _emit(err, "probeset: no <probe-id>.txt files in %s" % args.directory)
            return 2
        results = grade_batch(probeset, responses)
        writer = json_report if args.json else text_report
        rc = writer(results, probeset.version, out, err,
                    include_info=args.include_info, strict=args.strict)
        missing = [pid for pid in probeset.ids() if pid not in responses]
        if missing:
            _emit(err, "probeset: no response for %s" % ", ".join(missing))
        return rc

    if args.command == "probes-version":
        out.write(probeset.version + "\n")
        return 0

    _emit(err, "probeset: unknown command %r" % args.command)
    return 2
