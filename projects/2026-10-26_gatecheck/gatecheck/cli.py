"""gatecheck command line.

  scan FILE          lint one commitment record, a JSON array of records or JSONL
  rules              list the twelve rules
  show RULE          one rule in full
  validate FILE      schema-only check against commitment.schema.json
  schema             print the commitment schema

Results go to stdout, diagnostics to stderr. Terminal text is folded to ASCII so it can be
written to any console; `--json` output is ASCII-escaped by the encoder.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, TextIO

from . import __version__
from .findings import Finding, Severity, Verdict, exit_code, sort_findings
from .rules import ALL_RULES, by_id
from .scan import ScanResult, rollup, scan_record
from .schema import SCHEMA_PATH, SchemaError, Validator, load_schema
from .text import fold


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gatecheck",
        description="Lint commitment records against the gate-versus-target discipline (Rule A11).")
    p.add_argument("--version", action="version", version="gatecheck " + __version__)
    sub = p.add_subparsers(dest="command")

    sc = sub.add_parser("scan", help="lint one record, an array of records or JSONL")
    sc.add_argument("path")
    sc.add_argument("--json", action="store_true", help="emit JSON")
    sc.add_argument("--strict", action="store_true", help="treat INFO findings as needs-attention")
    sc.add_argument("--include-info", action="store_true", help="also show INFO findings")
    sc.add_argument("--disable", action="append", default=[], help="disable a rule by id (may be repeated)")

    ru = sub.add_parser("rules", help="list the rule set")
    ru.add_argument("--json", action="store_true", help="emit JSON")

    sh = sub.add_parser("show", help="show one rule")
    sh.add_argument("id")
    sh.add_argument("--json", action="store_true", help="emit JSON")

    va = sub.add_parser("validate", help="schema-only check against commitment.schema.json")
    va.add_argument("path")
    va.add_argument("--json", action="store_true", help="emit JSON")

    sub.add_parser("schema", help="print the commitment schema")

    return p


def _emit(stream: TextIO, text: str) -> None:
    stream.write(fold(text) + "\n")


def _records(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    stripped = raw.strip()
    if not stripped:
        return []
    try:
        data = json.loads(stripped)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        out = []
        for n, line in enumerate(raw.splitlines(), 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError("line %d is not JSON (%s)" % (n, exc.msg))
        return out


def _scan_output_text(results: List[ScanResult], out: TextIO, err: TextIO,
                      include_info: bool, strict: bool) -> int:
    v = rollup(results)
    if strict:
        for r in results:
            if r.verdict == Verdict.HEALTHY and any(f.severity == Severity.INFO for f in r.findings):
                v = Verdict.NEEDS_ATTENTION
                break
    for r in results:
        shown = [f for f in r.findings if f.severity != Severity.INFO or include_info or strict]
        _emit(out, "")
        _emit(out, "%s  %s" % (r.subject, r.verdict))
        if not shown:
            _emit(out, "  (no findings)")
            continue
        for f in shown:
            _emit(out, "  %-6s %s %s" % (f.severity, f.code, f.message))
    _emit(err, "gatecheck %s: %s; %d record(s)" % (__version__, v, len(results)))
    return exit_code(v)


def _scan_output_json(results: List[ScanResult], out: TextIO, err: TextIO,
                      include_info: bool, strict: bool) -> int:
    v = rollup(results)
    if strict:
        for r in results:
            if r.verdict == Verdict.HEALTHY and any(f.severity == Severity.INFO for f in r.findings):
                v = Verdict.NEEDS_ATTENTION
                break
    payload = {"tool": "gatecheck", "version": __version__, "verdict": v, "results": []}
    for r in results:
        d = r.to_dict()
        d["findings"] = [f.to_dict() for f in r.findings
                         if f.severity != Severity.INFO or include_info or strict]
        payload["results"].append(d)
    out.write(json.dumps(payload, indent=2) + "\n")
    _emit(err, "gatecheck %s: %s; %d record(s)" % (__version__, v, len(results)))
    return exit_code(v)


def main(argv: Optional[Sequence[str]] = None, stdout: Optional[TextIO] = None,
         stderr: Optional[TextIO] = None) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    if not args.command:
        _build_parser().print_help(out)
        return 0

    if args.command == "scan":
        try:
            records = _records(args.path)
        except OSError as exc:
            _emit(err, "gatecheck: cannot read %s: %s" % (args.path, exc))
            return 2
        except ValueError as exc:
            _emit(err, "gatecheck: %s" % exc)
            return 2
        if not records:
            _emit(err, "gatecheck: no records in %s" % args.path)
            return 2
        results = [scan_record(r, disabled=args.disable) for r in records]
        if args.json:
            return _scan_output_json(results, out, err, args.include_info, args.strict)
        return _scan_output_text(results, out, err, args.include_info, args.strict)

    if args.command == "rules":
        if args.json:
            out.write(json.dumps([{"id": r.id, "severity": r.severity, "applies_to": r.applies_to,
                                   "summary": r.summary, "description": r.description}
                                  for r in ALL_RULES], indent=2) + "\n")
        else:
            for r in ALL_RULES:
                _emit(out, "%-9s %-7s %-7s %s" % (r.id, r.severity, r.applies_to, r.summary))
        _emit(err, "gatecheck %s: %d rule(s)" % (__version__, len(ALL_RULES)))
        return 0

    if args.command == "show":
        try:
            rule = by_id(args.id)
        except KeyError as exc:
            _emit(err, "gatecheck: %s" % exc.args[0])
            return 2
        if args.json:
            out.write(json.dumps({"id": rule.id, "severity": rule.severity, "applies_to": rule.applies_to,
                                  "summary": rule.summary, "description": rule.description}, indent=2) + "\n")
            return 0
        _emit(out, "%s  %s  (%s, applies to %s)" % (rule.id, rule.summary, rule.severity, rule.applies_to))
        _emit(out, "")
        _emit(out, rule.description)
        return 0

    if args.command == "validate":
        try:
            records = _records(args.path)
        except (OSError, ValueError) as exc:
            _emit(err, "gatecheck: %s" % exc)
            return 2
        if not records:
            _emit(err, "gatecheck: no records in %s" % args.path)
            return 2
        schema = load_schema()
        validator = Validator(schema)
        errors_all: List[Dict[str, str]] = []
        for i, r in enumerate(records):
            errs = validator.errors(r)
            for path, msg in errs:
                errors_all.append({"record": str(i), "path": path, "message": msg})
        if args.json:
            out.write(json.dumps({"tool": "gatecheck", "version": __version__,
                                  "errors": errors_all}, indent=2) + "\n")
        else:
            for e in errors_all:
                _emit(out, "record %s %s: %s" % (e["record"], e["path"], e["message"]))
        v = Verdict.UNHEALTHY if errors_all else Verdict.HEALTHY
        _emit(err, "gatecheck validate: %s; %d record(s), %d error(s)" % (v, len(records), len(errors_all)))
        return 2 if errors_all else 0

    if args.command == "schema":
        with open(SCHEMA_PATH, encoding="utf-8") as fh:
            out.write(fh.read())
            if not out.getvalue().endswith("\n") if hasattr(out, "getvalue") else False:  # pragma: no cover
                out.write("\n")
        return 0

    _emit(err, "gatecheck: unknown command %r" % args.command)
    return 2
