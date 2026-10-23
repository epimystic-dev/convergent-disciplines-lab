"""threadkit command line.

  list                 lessons, filtered by strand, layer, standing, chapter or derivation
  show ID              one lesson in full
  check FILE           govern an answer record: findings, then the rendered answer (exit 0 / 1 / 2)
  assess FILE          grade a convergence claim by the independence of its routes
  lint FILE            points-of-defeat linter for a structured dialogue
  review FILE          four-move design review
  decide FILE          check a decision record's debiasing structure
  consensus FILE       diversity-weighted tally of multi-agent votes
  audit FILE           check a deployment declaration against the threads
  validate CONTRACT FILE   check JSON or JSONL records against a data contract (exit 0 / 2)
  prompt               print the drop-in system prompt (or --agent for the agent addendum)
  catalogue            render the Markdown catalogue (to --output FILE, UTF-8)

Results go to stdout, diagnostics to stderr. Terminal text is folded to ASCII so it can be
written to any console; --json output is ASCII-escaped by the encoder.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from typing import Any, Callable, List, Optional, Sequence, TextIO

from . import __version__
from . import argument, consensus, convergence, debias, review
from .audit import audit
from .findings import Finding, exit_code, sort_findings, verdict
from .governor import AnswerGovernor
from .render import catalogue
from .spec import CONTRACTS, Threads, contract_validator, prompt_text
from .text import fold

LAYERS = ["context", "middleware", "architecture", "governance"]
STANDINGS = ["settled", "established", "contested", "limit", "bridge", "method"]


def _findings_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("path")
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.add_argument("--include-info", action="store_true", help="also report INFO findings")
    p.add_argument("--strict", action="store_true", help="treat INFO findings as needs-attention")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="threadkit",
        description="Reference tools for the threads: query the lessons, govern answers, grade convergence "
                    "claims, lint dialogues, review designs and audit deployments.")
    p.add_argument("--version", action="version", version="threadkit " + __version__)
    sub = p.add_subparsers(dest="command")

    ls = sub.add_parser("list", help="list lessons")
    ls.add_argument("--strand", choices=list("MRSKDAFP"))
    ls.add_argument("--layer", choices=LAYERS)
    ls.add_argument("--standing", choices=STANDINGS)
    ls.add_argument("--chapter", type=int)
    ls.add_argument("--derivation", choices=["stated", "derived"])
    ls.add_argument("--json", action="store_true", help="emit JSON")

    sh = sub.add_parser("show", help="show one lesson")
    sh.add_argument("id")
    sh.add_argument("--json", action="store_true", help="emit JSON")

    ck = sub.add_parser("check", help="govern an answer record")
    _findings_args(ck)
    ck.add_argument("--ascii", action="store_true", help="render standings as [tags] instead of glyphs")
    ck.add_argument("--decision", action="store_true", help="the answer feeds a decision (causal defeaters required)")

    for name, helptext in (("assess", "grade a convergence claim"), ("lint", "lint a structured dialogue"),
                           ("review", "four-move design review"), ("decide", "check a decision record"),
                           ("consensus", "diversity-weighted multi-agent tally"), ("audit", "audit a deployment declaration")):
        _findings_args(sub.add_parser(name, help=helptext))

    va = sub.add_parser("validate", help="validate records against a data contract")
    va.add_argument("contract", choices=list(CONTRACTS))
    va.add_argument("path", help="a JSON record, a JSON array of records, or JSONL")
    va.add_argument("--json", action="store_true", help="emit JSON")

    pr = sub.add_parser("prompt", help="print the drop-in system prompt")
    pr.add_argument("--agent", action="store_true", help="print the addendum for tool-using agents")

    ca = sub.add_parser("catalogue", help="render the Markdown catalogue")
    ca.add_argument("--output", help="write to this file (UTF-8) instead of stdout")
    return p


def _emit(stream: TextIO, text: str) -> None:
    stream.write(fold(text) + "\n")


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _records(path: str) -> List[Any]:
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


def _report(args, out: TextIO, err: TextIO, findings: List[Finding], subject: str, extra: Optional[dict] = None,
            after: str = "") -> int:
    findings = sort_findings(findings)
    shown = [f for f in findings if f.severity != "INFO" or args.include_info or args.strict]
    v = verdict([f for f in findings if f.severity != "INFO"])
    if args.strict and v == "healthy" and any(f.severity == "INFO" for f in findings):
        v = "needs-attention"
    if args.json:
        payload = {"tool": "threadkit", "version": __version__, "command": args.command, "source": args.path,
                   "subject": subject, "verdict": v, "findings": [f.to_dict() for f in shown]}
        if extra:
            payload.update(extra)
        out.write(json.dumps(payload, indent=2) + "\n")
    else:
        for f in shown:
            _emit(out, "%-6s %s %s: %s%s" % (f.severity, f.code, f.subject, f.message,
                                             (" [%s]" % f.lesson) if f.lesson else ""))
        if after:
            if shown:
                _emit(out, "")
            out.write(fold(after))
    _emit(err, "threadkit: %s; %d finding(s) for %s" % (v, len(shown), subject))
    return exit_code(v)


def _validated(name: str, record: Any) -> None:
    errs = contract_validator(name).errors(record)
    if errs:
        raise ValueError("not a valid %s record: %s" % (name, "; ".join("%s %s" % (p or "/", m) for p, m in errs[:4])))


def main(argv: Optional[Sequence[str]] = None, stdout: Optional[TextIO] = None,
         stderr: Optional[TextIO] = None) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    if not args.command:
        _build_parser().print_help(out)
        return 0
    try:
        t = Threads.load()
        if args.command == "list":
            rows = t.select(strand=args.strand, layer=args.layer, standing=args.standing,
                            chapter=args.chapter, derivation=args.derivation)
            if args.json:
                out.write(json.dumps([{"id": l["id"], "name": l["name"], "standing": l["standing"],
                                       "derivation": l["derivation"], "chapters": l["chapters"],
                                       "enforcement_layers": l["enforcement_layers"]} for l in rows], indent=2) + "\n")
            else:
                for l in rows:
                    _emit(out, "%-4s %-12s %-8s %-62s %s" % (l["id"], l["standing"], l["derivation"], l["name"],
                                                            "/".join(l["enforcement_layers"])))
            _emit(err, "threadkit: %d lesson(s)" % len(rows))
            return 0

        if args.command == "show":
            try:
                l = t.get(args.id)
            except KeyError as exc:
                _emit(err, "threadkit: %s" % exc.args[0])
                return 2
            if args.json:
                out.write(json.dumps(l, indent=2) + "\n")
                return 0
            _emit(out, "%s  %s  (strand %s; standing %s; %s; chapters %s)" % (
                l["id"], l["name"], l["strand"], l["standing"], l["derivation"], ", ".join(str(c) for c in l["chapters"])))
            for label, key in (("Rule", "statement"), ("Why", "rationale"), ("Failure it addresses", "failure_mode"),
                               ("In practice", "practice"), ("To build it", "sketch"), ("Example", "example"),
                               ("Test", "test"), ("Caution", "cautions")):
                if l[key]:
                    _emit(out, "")
                    _emit(out, label + ".  " + l[key])
            _emit(out, "")
            _emit(out, "Enforced at: " + ", ".join(l["enforcement_layers"]))
            if l["data_contract"]:
                _emit(out, "Data contract: threads/" + l["data_contract"])
            if l["reference_implementation"]:
                _emit(out, "Code: " + l["reference_implementation"])
            return 0

        if args.command == "validate":
            try:
                records = _records(args.path)
            except (OSError, ValueError) as exc:
                _emit(err, "threadkit: cannot read %s: %s" % (args.path, exc))
                return 2
            validator = contract_validator(args.contract)
            results = []
            for i, rec in enumerate(records):
                errs = validator.errors(rec)
                results.append({"record": i, "valid": not errs,
                                "errors": [{"path": a, "message": b} for a, b in errs]})
            bad = [r for r in results if not r["valid"]]
            if args.json:
                out.write(json.dumps({"contract": args.contract, "records": len(records),
                                      "invalid": len(bad), "results": results}, indent=2) + "\n")
            else:
                for r in bad:
                    for e in r["errors"]:
                        _emit(out, "record %d %s: %s" % (r["record"], e["path"], e["message"]))
            if not records:
                _emit(err, "threadkit: no records in %s" % args.path)
                return 2
            _emit(err, "threadkit: %d of %d record(s) valid against %s" % (len(records) - len(bad), len(records), args.contract))
            return 2 if bad else 0

        if args.command == "prompt":
            out.write(fold(prompt_text(agent=args.agent)))
            return 0

        if args.command == "catalogue":
            text = catalogue(t)
            if args.output:
                with io.open(args.output, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text)
                _emit(err, "threadkit: wrote %s" % args.output)
            else:
                out.write(fold(text))
            return 0

        try:
            record = _load_json(args.path)
        except (OSError, ValueError) as exc:
            _emit(err, "threadkit: cannot read %s: %s" % (args.path, exc))
            return 2
        try:
            if args.command == "check":
                g = AnswerGovernor(t).govern(record, ascii_only=args.ascii, used_in_decision=args.decision)
                return _report(args, out, err, g.findings, str(record.get("id", args.path)),
                               {"text": g.text}, after=g.text)
            if args.command == "assess":
                _validated("convergence", record)
                a = convergence.assess(record)
                summary = "computed grade: %s (declared %s); independent routes: %d\n" % (
                    a.computed_grade, a.declared_grade, a.independent_routes)
                return _report(args, out, err, a.findings, record["id"], a.to_dict(), after=summary)
            if args.command == "lint":
                _validated("dialogue", record)
                return _report(args, out, err, argument.lint_dialogue(record), record["id"])
            if args.command == "review":
                _validated("design-review", record)
                return _report(args, out, err, review.check(record), record["system"])
            if args.command == "decide":
                _validated("decision-record", record)
                return _report(args, out, err, debias.check(record), record["id"])
            if args.command == "consensus":
                _validated("consensus", record)
                tl = consensus.tally(record)
                summary = "by lineage: %s (%d independent witness%s); raw: %s\n" % (
                    tl.lineage_winner, tl.independent_witnesses, "" if tl.independent_witnesses == 1 else "es", tl.raw_winner)
                return _report(args, out, err, tl.findings, record["question"], tl.to_dict(), after=summary)
            if args.command == "audit":
                return _report(args, out, err, audit(record, t), str(record.get("system", args.path)))
        except (ValueError, KeyError) as exc:
            _emit(err, "threadkit: %s" % (exc.args[0] if exc.args else exc))
            return 2
    except KeyboardInterrupt:  # pragma: no cover
        return 130
    return 2
