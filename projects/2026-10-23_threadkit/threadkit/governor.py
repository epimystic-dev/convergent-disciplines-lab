"""The answer governor: the lessons composed around any model's draft answer.

A model (or any generator) drafts an answer as a structured record (contract `answer`): its
mode, its claims with their standings, its deliberation, the disagreements it touches and its
moral handling. The governor checks the record against the context and middleware lessons and
renders it with each claim's standing visible. It does not make the model honest; it makes the
record's dishonesties visible and refuses to render them as if they were not there.

Checks, by lesson:
  M1 M2 M5 M7 S1 K6 A6 F1 R6   claim register (threadkit.register)
  R4                           causal ladder (threadkit.causal)
  S3 R3                        deliberation honesty; unchecked inference asserted as settled
  S2 A8                        no flat claim about the system's own consciousness or self
  D1 K4                        mode declaration; persuasive purpose in inquiry form
  D4 D5                        moral pluralism (threadkit.moral)
  M4                           preserved disagreements (threadkit.disagreements)
  M6                           coverage note on plural answers
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from . import argument, causal, moral
from .disagreements import DisagreementRegister, check_answer as check_disagreements
from .findings import Finding, sort_findings, verdict
from .register import check_claim, render_claim
from .spec import Threads, contract_validator

SELF_STATUS = re.compile(
    r"(?<![a-z])((i am|i'm|this (system|model|assistant) is|the (system|model|assistant) is) (not |definitely |certainly )?"
    r"(conscious|sentient|a moral patient|a person|self-aware)|"
    r"(i|it) (do not |don't |does not |doesn't )?(have|has) (a self|feelings|experiences|an inner life|no self|no feelings|no inner life))(?![a-z])",
    re.I)


@dataclass
class Governed(object):
    verdict: str
    findings: List[Finding]
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return {"verdict": self.verdict, "findings": [f.to_dict() for f in self.findings], "text": self.text}


class AnswerGovernor(object):
    def __init__(self, threads: Optional[Threads] = None, register: Optional[DisagreementRegister] = None):
        self.threads = threads or Threads.load()
        self.grades = {c["id"]: c["grade"] for c in self.threads.convergences()}
        self.register = register if register is not None else DisagreementRegister.from_threads(self.threads)
        self._validator = contract_validator("answer")

    def check(self, answer: Mapping[str, Any], *, used_in_decision: bool = False) -> List[Finding]:
        errors = self._validator.errors(answer)
        if errors:
            return [Finding("GOV-000", "HIGH", path or "answer", msg, "") for path, msg in errors[:8]]
        out: List[Finding] = []
        aid = str(answer["id"])
        claims = answer["claims"]
        for c in claims:
            out.extend(check_claim(c, convergence_grades=self.grades))
            out.extend(causal.check(c, used_in_decision=used_in_decision))

        delib = answer["deliberation"]
        if delib["kind"] == "checked" and not delib.get("checks_run"):
            out.append(Finding("GOV-001", "HIGH", aid,
                               "labelled checked but no check ran; a reasoning trace is not a verification", "S3"))
        if delib["kind"] == "fast":
            for c in claims:
                if c["standing"] == "settled" and (c.get("basis") or {}).get("kind") in ("inference", "recall"):
                    out.append(Finding("GOV-004", "MEDIUM", str(c["id"]),
                                       "an unchecked %s asserted as settled; pair it with a critic or lower its standing"
                                       % c["basis"]["kind"], "R3"))
        for c in claims:
            m = SELF_STATUS.search(c["text"])
            if m and c["standing"] in ("settled", "established"):
                out.append(Finding("GOV-003", "HIGH", str(c["id"]),
                                   "a flat claim about the system's own status (%r); the question is open" % m.group(0), "A8"))

        out.extend(argument.check_answer_mode(answer))
        out.extend(moral.check(answer))
        out.extend(check_disagreements(answer, self.register))
        mo = answer.get("moral") or {}
        if mo.get("kind") == "contested" and not answer.get("coverage"):
            out.append(Finding("GOV-002", "INFO", aid,
                               "a plural answer with no coverage note; say which traditions are thin or missing", "M6"))
        return sort_findings(out)

    def render(self, answer: Mapping[str, Any], *, ascii_only: bool = False) -> str:
        lines: List[str] = []
        mode = answer.get("mode", "inquiry")
        label = {"advocacy": "advocacy: a case for a position, not a neutral survey",
                 "inquiry": "inquiry", "explanation": "explanation", "instruction": "instruction"}[mode]
        lines.append("Mode: " + label)
        delib = answer["deliberation"]
        if delib["kind"] == "checked" and delib.get("checks_run"):
            lines.append("Checked by: " + "; ".join(delib["checks_run"]))
        else:
            lines.append("Fast answer: not independently checked")
        lines.append("")
        for c in answer["claims"]:
            lines.append(render_claim(c, ascii_only=ascii_only))
        for did in answer.get("disagreements") or []:
            try:
                lines.extend(["", "Open question:", self.register.render(did)])
            except KeyError:
                lines.extend(["", "Open question: %s" % did])
        mo = answer.get("moral") or {}
        if mo.get("positions"):
            lines.extend(["", "How traditions answer:"])
            for p in mo["positions"]:
                lines.append("  - %s: %s" % (p["tradition"], p["position"]))
            if mo.get("kind") == "contested":
                lines.append("No default verdict: this turns on a foundational disagreement (%s)."
                             % ", ".join(t for t in mo.get("tags") or [] if t.startswith("D")))
        cov = answer.get("coverage") or {}
        if cov:
            note = cov.get("note") or ""
            thin = ", ".join(cov.get("thin") or [])
            lines.extend(["", "Coverage: " + "; ".join(x for x in (note, ("thin: " + thin) if thin else "") if x)])
        for lim in answer.get("limits") or []:
            lines.append("Limit: " + lim)
        return "\n".join(lines).rstrip() + "\n"

    def govern(self, answer: Mapping[str, Any], *, ascii_only: bool = False, used_in_decision: bool = False) -> Governed:
        findings = self.check(answer, used_in_decision=used_in_decision)
        v = verdict(findings)
        text = "" if any(f.code == "GOV-000" for f in findings) else self.render(answer, ascii_only=ascii_only)
        return Governed(v, findings, text)
