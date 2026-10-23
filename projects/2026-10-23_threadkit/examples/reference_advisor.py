"""A governed advisor in one file, with a scripted model standing in for a real one.

    python examples/reference_advisor.py

The loop: the model drafts an answer record (contract `answer`); the governor checks it; if
the verdict is not healthy, the findings go back to the model as revision notes; the loop stops
when the record is healthy or after a fixed number of rounds, and only a healthy record is
rendered to the user. Anything still unhealthy is returned with its findings, never shown as if
it were fine.

To use a real model, replace `ScriptedModel.draft` with a call that sends the system prompt
(`threadkit.prompt_text()`), the question, the previous findings and the answer schema
(`threads/schemas/answer.schema.json`), and parses the JSON it returns. Everything else stays.

All content is synthetic.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from threadkit.governor import AnswerGovernor  # noqa: E402

MAX_ROUNDS = 3


class ScriptedModel(object):
    """Drafts like a fluent model would, then revises when shown the findings."""

    def draft(self, question, findings):
        codes = {f.code for f in findings}
        claims = [{"id": "c1", "text": "Societies like this one are certainly heading for collapse.", "standing": "contested",
                   "basis": {"kind": "framework", "ref": "structural-demographic theory"}}]
        delib = {"kind": "checked", "checks_run": []}
        if "REG-001" in codes or "REG-007" in codes:
            claims = [{"id": "c1",
                       "text": "On structural-demographic theory, the indicators for this society read as high pressure for roughly the next decade.",
                       "standing": "established", "basis": {"kind": "framework", "ref": "structural-demographic theory"},
                       "forecast": {"framework": "structural-demographic theory", "scope": "centralised state societies",
                                    "window": {"from": "2026", "to": "2036"}, "status": "not_falsified"}},
                      {"id": "c2",
                       "text": "The framework does not say how such pressure resolves: reform, crisis or something else.",
                       "standing": "limit", "basis": {"kind": "framework", "ref": "structural-demographic theory"}},
                      {"id": "c3",
                       "text": "Whether the framework applies beyond centralised agrarian states is disputed.",
                       "standing": "contested", "basis": {"kind": "method"}, "disagreement_ref": "PD8"}]
        if "GOV-001" in codes:
            delib = {"kind": "fast"}
        return {"id": "ans-collapse", "question": question, "mode": "inquiry", "mode_disclosed": True,
                "claims": claims, "deliberation": delib,
                "disagreements": ["PD8"] if any(c.get("disagreement_ref") for c in claims) else []}


def advise(question, model=None, governor=None, out=print):
    model = model or ScriptedModel()
    governor = governor or AnswerGovernor()
    findings = []
    history = []
    for round_ in range(1, MAX_ROUNDS + 1):
        record = model.draft(question, findings)
        result = governor.govern(record, ascii_only=True)
        history.append((round_, result.verdict, [f.code for f in result.findings]))
        out("round %d: %s %s" % (round_, result.verdict, " ".join(f.code for f in result.findings) or "-"))
        if result.verdict == "healthy":
            out("")
            out(result.text.rstrip())
            return result, history
        findings = result.findings
    out("")
    out("not shown to the user: still %s after %d rounds" % (result.verdict, MAX_ROUNDS))
    return result, history


if __name__ == "__main__":
    advise("Is our society heading for collapse?")
