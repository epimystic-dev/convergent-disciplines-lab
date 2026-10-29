"""The twelve rules.

A `Rule` is a predicate over one commitment record that raises zero or more `Finding`s. The
rule ids are stable (GATE-001..GATE-012); the message of each rule names the field it
checked and why the discipline asks for it, so an outside reader can audit the rule set
without reading the code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from .findings import Finding, Severity


_STALE_REVIEW_DAYS = 365


@dataclass(frozen=True)
class Rule(object):
    id: str
    severity: str
    applies_to: str  # 'gate', 'target', or 'any'
    summary: str
    description: str
    check: Callable[[Dict[str, Any], str], List[Finding]]


def _subject(record: Dict[str, Any]) -> str:
    return str(record.get("id", "<unknown>"))


def _parse_iso(s: Any) -> Optional[date]:
    if not isinstance(s, str) or not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _rule_001(record: Dict[str, Any], subject: str) -> List[Finding]:
    if record.get("kind") == "gate" and not record.get("trigger"):
        return [Finding("GATE-001", Severity.HIGH, subject,
                        "a gate without a trigger is a hope: declare the condition the commitment binds under.")]
    return []


def _rule_002(record: Dict[str, Any], subject: str) -> List[Finding]:
    if record.get("kind") == "gate" and not record.get("enforcer"):
        return [Finding("GATE-002", Severity.HIGH, subject,
                        "a gate without an enforcer is a wish: name who or what checks and enforces it.")]
    return []


def _rule_003(record: Dict[str, Any], subject: str) -> List[Finding]:
    enf = record.get("enforcer") or {}
    if record.get("kind") == "gate" and enf.get("kind") == "self-attested":
        return [Finding("GATE-003", Severity.MEDIUM, subject,
                        "the enforcer is self-attested; an independent reviewer, a regulator or a contractual enforcer is stronger.")]
    return []


def _rule_004(record: Dict[str, Any], subject: str) -> List[Finding]:
    out = []
    for i, clause in enumerate(record.get("escape_clauses") or []):
        if clause.get("competitor_contingent"):
            if not clause.get("named_competitor") or not clause.get("trigger_metric"):
                out.append(Finding("GATE-004", Severity.MEDIUM, subject,
                                   "escape_clauses[%d] is competitor-contingent but does not name the competitor and the trigger metric; "
                                   "a competitor-contingent clause without a named signal is unverifiable." % i))
    return out


def _rule_005(record: Dict[str, Any], subject: str) -> List[Finding]:
    out = []
    if not record.get("committed_at"):
        out.append(Finding("GATE-005", Severity.MEDIUM, subject,
                           "no committed_at date; a commitment with no date cannot be aged, cited or compared across versions."))
    if not record.get("last_reviewed_at"):
        out.append(Finding("GATE-005", Severity.MEDIUM, subject,
                           "no last_reviewed_at date; a commitment that has never been reviewed cannot be shown current."))
    return out


def _rule_006(record: Dict[str, Any], subject: str) -> List[Finding]:
    if record.get("kind") == "gate" and not record.get("dependencies"):
        return [Finding("GATE-006", Severity.INFO, subject,
                        "no dependencies declared; a gate whose binding depends on other facts (model-capability thresholds, "
                        "legal regimes, operational partners) should name those dependencies for an auditor.")]
    return []


def _rule_007(record: Dict[str, Any], subject: str) -> List[Finding]:
    out = []
    trig = record.get("trigger") or {}
    trig_metric = trig.get("metric")
    for i, clause in enumerate(record.get("escape_clauses") or []):
        scope = clause.get("scope")
        clause_metric = clause.get("trigger_metric")
        if trig_metric:
            if scope is None and clause_metric is None:
                out.append(Finding("GATE-007", Severity.HIGH, subject,
                                   "escape_clauses[%d] has no scope and no trigger_metric; without a named scope it can be read as "
                                   "nullifying the whole gate (the trigger metric is %r)." % (i, trig_metric)))
            elif clause_metric and clause_metric != trig_metric and (scope is None or scope != trig_metric):
                out.append(Finding("GATE-007", Severity.HIGH, subject,
                                   "escape_clauses[%d] names trigger_metric %r but the gate's trigger metric is %r; the escape "
                                   "clause can be read as expanding the exemption beyond the stated trigger." % (i, clause_metric, trig_metric)))
    return out


def _rule_008(record: Dict[str, Any], subject: str) -> List[Finding]:
    if record.get("kind") != "target":
        return []
    out = []
    if not record.get("target_metric"):
        out.append(Finding("GATE-008", Severity.HIGH, subject,
                           "a target without a target_metric: name the measurable the organisation commits to."))
    if not record.get("target_deadline"):
        out.append(Finding("GATE-008", Severity.HIGH, subject,
                           "a target without a target_deadline: without a date, a target cannot be shown met or missed."))
    return out


def _rule_009(record: Dict[str, Any], subject: str) -> List[Finding]:
    committed = _parse_iso(record.get("committed_at"))
    reviewed = _parse_iso(record.get("last_reviewed_at"))
    if not committed or not reviewed:
        return []
    delta = (reviewed - committed).days
    today_delta = (date.today() - reviewed).days
    out = []
    if today_delta > _STALE_REVIEW_DAYS:
        out.append(Finding("GATE-009", Severity.MEDIUM, subject,
                           "last_reviewed_at is more than %d days before today; a commitment that has not been reviewed in over a year is "
                           "treated as stale unless the organisation re-publishes it." % _STALE_REVIEW_DAYS))
    if delta < 0:
        out.append(Finding("GATE-009", Severity.MEDIUM, subject,
                           "last_reviewed_at is before committed_at: the dates do not describe a plausible timeline."))
    return out


def _rule_010(record: Dict[str, Any], subject: str) -> List[Finding]:
    kind = record.get("kind")
    if kind in (None, "gate", "target"):
        return []
    return [Finding("GATE-010", Severity.HIGH, subject,
                    "unknown kind %r; a commitment must be a 'gate' (promise not to do X) or a 'target' (promise to do X)." % kind)]


def _rule_011(record: Dict[str, Any], subject: str) -> List[Finding]:
    if record.get("kind") != "gate":
        return []
    trig = record.get("trigger")
    if not trig:
        return []
    has_metric = bool(trig.get("metric"))
    marked_measurable = trig.get("measurable") is True
    if not has_metric and not marked_measurable:
        return [Finding("GATE-011", Severity.MEDIUM, subject,
                        "the trigger has no metric and is not marked measurable; a prose-only trigger cannot be checked by an auditor.")]
    return []


def _rule_012(record: Dict[str, Any], subject: str) -> List[Finding]:
    if record.get("externally_verifiable") is True:
        enf = record.get("enforcer") or {}
        if not enf.get("external_check"):
            return [Finding("GATE-012", Severity.MEDIUM, subject,
                            "externally_verifiable is true but the enforcer has no external_check; name the external audit, API, log or report "
                            "that an outside reader can consult.")]
    return []


ALL_RULES: List[Rule] = [
    Rule("GATE-001", Severity.HIGH, "gate",
         "a gate must declare a trigger",
         "A gate (a promise not to do X) must state the condition under which it binds. Without a trigger "
         "the commitment is a hope and cannot be audited.",
         _rule_001),
    Rule("GATE-002", Severity.HIGH, "gate",
         "a gate must declare an enforcer",
         "A gate must name who or what checks and enforces it: a self-attestation, an independent reviewer, "
         "a regulator or a contractual counterparty.",
         _rule_002),
    Rule("GATE-003", Severity.MEDIUM, "gate",
         "a self-attested enforcer is a weak enforcer",
         "A gate whose enforcer is the organisation itself is weaker than one whose enforcer is an independent "
         "party; the finding flags the structure, not the organisation.",
         _rule_003),
    Rule("GATE-004", Severity.MEDIUM, "any",
         "a competitor-contingent clause must name the competitor and the metric",
         "An escape clause that nullifies the gate conditional on a competitor's behaviour must name the "
         "competitor and the measurable signal; without them the clause is unverifiable.",
         _rule_004),
    Rule("GATE-005", Severity.MEDIUM, "any",
         "a commitment must have a committed_at and a last_reviewed_at date",
         "Dates are what let a commitment be aged, cited and compared across versions. The rule fires once "
         "per missing date.",
         _rule_005),
    Rule("GATE-006", Severity.INFO, "gate",
         "a gate without declared dependencies is incomplete",
         "A gate whose binding depends on other facts (capability thresholds, legal regimes, operational "
         "partners) should name those dependencies so an auditor can watch them.",
         _rule_006),
    Rule("GATE-007", Severity.HIGH, "any",
         "an escape clause must be scoped to the gate's trigger",
         "An escape clause that has no scope or that names a different metric than the gate's trigger can be "
         "read as expanding the exemption beyond what the audience was told.",
         _rule_007),
    Rule("GATE-008", Severity.HIGH, "target",
         "a target must declare a metric and a deadline",
         "A target (a promise to do X) is empty without a measurable and a date; the rule fires once per "
         "missing field.",
         _rule_008),
    Rule("GATE-009", Severity.MEDIUM, "any",
         "a last_reviewed_at that is stale or before committed_at",
         "A commitment that has not been reviewed in over a year is treated as stale; a review date before "
         "the commitment date indicates a timeline inconsistency.",
         _rule_009),
    Rule("GATE-010", Severity.HIGH, "any",
         "unknown kind",
         "A commitment must be a 'gate' or a 'target'; any other kind is a schema violation that an auditor "
         "cannot interpret.",
         _rule_010),
    Rule("GATE-011", Severity.MEDIUM, "gate",
         "a gate's trigger must be measurable",
         "A trigger that is prose-only (no metric, not marked measurable=true) cannot be checked by an "
         "auditor; name the measurable or declare the trigger explicitly non-measurable.",
         _rule_011),
    Rule("GATE-012", Severity.MEDIUM, "any",
         "externally_verifiable requires an external_check",
         "A commitment that claims to be externally verifiable must name the external audit, API, log or "
         "report an outside reader can consult.",
         _rule_012),
]


def by_id(rule_id: str) -> Rule:
    for r in ALL_RULES:
        if r.id == rule_id:
            return r
    raise KeyError("no rule with id %r" % rule_id)
