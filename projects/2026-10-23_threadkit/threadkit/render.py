"""Render the threads as a human-readable Markdown catalogue (docs/LESSONS.md)."""

from __future__ import annotations

from typing import List

from .spec import Threads

STANDING_WORD = {"settled": "settled", "established": "well-established", "contested": "contested",
                 "limit": "limit", "bridge": "bridge / commitment", "method": "method note"}


def _basis(lesson) -> str:
    b = lesson["basis"]
    if b["kind"] == "convergence":
        return "convergence %s" % b["ref"]
    if b["kind"] == "author_thesis":
        return "the author's thesis (%s)" % b["ref"]
    if b["kind"] == "method":
        return "the book's method"
    return "framework: %s" % b["ref"]


def catalogue(t: Threads) -> str:
    d = t.data
    out: List[str] = []
    out.append("# The lessons")
    out.append("")
    out.append("*Generated from `threads/threads.json` (version %s) by `python -m threadkit catalogue`. Do not edit by hand. "
               "CC-BY-SA-4.0: adapted from the book named in NOTICE.md.*" % d["version"])
    out.append("")
    out.append(d["description"])
    out.append("")
    out.append("## How to read this")
    out.append("")
    for line in d["how_to_read"]:
        out.append("- " + line)
    out.append("")
    out.append("## The six registers")
    out.append("")
    out.append("| Glyph | Tag | Standing | Assert as |")
    out.append("|---|---|---|---|")
    for r in d["registers"]:
        out.append("| %s | `%s` | %s | %s |" % (r["glyph"], r["ascii"], r["name"], r["assert_as"]))
    out.append("")
    out.append("## Audited convergences")
    out.append("")
    out.append("| Id | Shape | Routes | Grade |")
    out.append("|---|---|---|---|")
    for c in d["convergences"]:
        out.append("| %s | %s | %d | %s |" % (c["id"], c["shape"], c["route_count"], c["grade"]))
    out.append("")
    out.append("## Preserved disagreements")
    out.append("")
    for x in d["disagreements"]:
        out.append("- **%s** %s %s." % (x["id"], x["question"], "; ".join(x["positions"])))
    out.append("")
    out.append("## Index")
    out.append("")
    out.append("| Id | Lesson | Standing | Derivation | Layers |")
    out.append("|---|---|---|---|---|")
    for l in t.lessons:
        out.append("| %s | %s | %s | %s | %s |" % (l["id"], l["name"], STANDING_WORD[l["standing"]], l["derivation"],
                                                 ", ".join(l["enforcement_layers"])))
    out.append("")
    for s, meta in d["strands"].items():
        out.append("## Strand %s: %s" % (s, meta["title"]))
        out.append("")
        out.append("*%s*" % meta["scope"])
        out.append("")
        for l in t.select(strand=s):
            out.append("### %s %s" % (l["id"], l["name"]))
            out.append("")
            out.append("*Standing: %s. Basis: %s. Derivation: %s. Chapters: %s.*" % (
                STANDING_WORD[l["standing"]], _basis(l), l["derivation"], ", ".join(str(c) for c in l["chapters"])))
            out.append("")
            for label, key in (("Rule", "statement"), ("Why", "rationale"), ("Failure it addresses", "failure_mode"),
                               ("In practice", "practice"), ("To build it", "sketch"), ("Example", "example"),
                               ("Test", "test")):
                out.append("**%s.** %s" % (label, l[key]))
                out.append("")
            if l["cautions"]:
                out.append("**Caution.** " + l["cautions"])
                out.append("")
            tail = ["Enforced at: " + ", ".join(l["enforcement_layers"])]
            if l["data_contract"]:
                tail.append("contract: `threads/%s`" % l["data_contract"])
            if l["reference_implementation"]:
                tail.append("code: `%s`" % l["reference_implementation"])
            out.append("*" + "; ".join(tail) + ".*")
            out.append("")
    out.append("## Limits")
    out.append("")
    for line in d["limits"]:
        out.append("- " + line)
    out.append("")
    return "\n".join(out)
