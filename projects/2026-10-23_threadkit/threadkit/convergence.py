"""Orthogonality-as-evidence: grade a claimed convergence by the independence of its routes.

Implements:
  M2   agreement counts only across independent routes. Routes linked by a shared upstream
       source (a common translation vocabulary, a shared lineage, a comparative project, active
       dialogue, a shared forum, the synthesist's own frame, direct influence) collapse into one
       cluster, and so do routes that share a method, a validation procedure or a cosmology.
       Three or more independent clusters can support a strong grade; two, partial; one,
       withdrawn. A selection the method did not deliver is the author's thesis.
  M3   the anti-Capra discipline: each route keeps distinct content, the shape is not stated in
       identity language, and the shape is not written in one route's own vocabulary. A
       flattened convergence is treated as an artefact until the difference is restored.
  M4   the routes' disagreements are recorded, not dissolved.
  M6   until an independent audit has run, the construction-bias caveat stays attached.
  M7   a citation artefact is dropped, not counted.

The grade computed here is a ceiling: a careful reader may grade lower. A declared grade above
the ceiling is a finding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence

from .findings import Finding

GRADE_ORDER = {"withdrawn": 0, "partial": 1, "strong": 2}
DEPENDENCE_KINDS = frozenset(["shared_translation_vocabulary", "shared_lineage", "comparative_project",
                              "active_dialogue", "shared_forum", "synthesist_frame", "direct_influence"])
_IDENTITY = re.compile(
    r"(?<![a-z])((is|are) (the same as|identical (to|with)|just|simply|merely|really just|nothing but)|"
    r"all [a-z ]{0,20}(teach|say|mean|express) the same|one (truth|insight|teaching) in (many|different|several) "
    r"(words|vocabularies|languages|guises))(?![a-z])", re.I)


class _Union(object):
    def __init__(self, items: Sequence[str]):
        self.parent = {i: i for i in items}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def join(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def groups(self) -> List[List[str]]:
        out: Dict[str, List[str]] = {}
        for i in self.parent:
            out.setdefault(self.find(i), []).append(i)
        return sorted((sorted(g) for g in out.values()), key=lambda g: g[0])


@dataclass
class Assessment(object):
    computed_grade: str
    declared_grade: str
    clusters: List[List[str]]
    findings: List[Finding] = field(default_factory=list)

    @property
    def independent_routes(self) -> int:
        return len(self.clusters)

    def to_dict(self) -> Dict[str, Any]:
        return {"computed_grade": self.computed_grade, "declared_grade": self.declared_grade,
                "independent_routes": self.independent_routes, "clusters": self.clusters,
                "findings": [f.to_dict() for f in self.findings]}


def _norm(s: Any) -> str:
    return " ".join(str(s or "").lower().split())


def _vocabulary_words(tradition: str) -> List[str]:
    return [w for w in re.findall(r"[a-z]+", tradition.lower()) if len(w) >= 6]


def assess(record: Mapping[str, Any]) -> Assessment:
    """Assess a convergence record (contract `convergence`)."""
    cid = str(record["id"])
    routes = list(record["routes"])
    ids = [r["id"] for r in routes]
    if len(set(ids)) != len(ids):
        raise ValueError("route ids must be unique")
    out: List[Finding] = []
    uf = _Union(ids)
    flattened = False

    for link in record.get("upstream_links") or []:
        unknown = [r for r in link["between"] if r not in uf.parent]
        if unknown:
            raise ValueError("upstream link names unknown route(s): %s" % ", ".join(unknown))
        if link["kind"] == "citation_artefact":
            out.append(Finding("CON-007", "HIGH", ", ".join(link["between"]),
                               "a citation artefact supports this route; drop it rather than count it", "M7"))
            continue
        if link["kind"] in DEPENDENCE_KINDS:
            first = link["between"][0]
            for other in link["between"][1:]:
                uf.join(first, other)

    for key in ("method", "validation", "cosmology"):
        seen: Dict[str, str] = {}
        for r in routes:
            val = _norm(r.get(key))
            if not val:
                continue
            if val in seen:
                uf.join(seen[val], r["id"])
                out.append(Finding("CON-009", "INFO", "%s, %s" % (seen[val], r["id"]),
                                   "the routes share a %s (%r) and are counted as one witness" % (key, r.get(key)), "M2"))
            else:
                seen[val] = r["id"]

    contents: Dict[str, str] = {}
    for r in routes:
        dc = _norm(r.get("distinct_content"))
        if dc in contents:
            flattened = True
            out.append(Finding("CON-002", "HIGH", "%s, %s" % (contents[dc], r["id"]),
                               "two routes carry the same content; the agreement has been written into the translation", "M3"))
        else:
            contents[dc] = r["id"]

    shape = record["shape"]
    m = _IDENTITY.search(shape)
    if m:
        flattened = True
        out.append(Finding("CON-003", "HIGH", cid,
                           "the shape is stated as an identity (%r); state the shared shape and keep each content distinct"
                           % m.group(0), "M3"))
    lowered = shape.lower()
    for r in routes:
        hits = [w for w in _vocabulary_words(r["tradition"]) if w in lowered]
        if hits:
            out.append(Finding("CON-004", "MEDIUM", r["id"],
                               "the shape is written in this route's own vocabulary (%s); state it neutrally" % ", ".join(hits), "M3"))
            break

    if len(routes) >= 2 and not record.get("disagreements_preserved"):
        out.append(Finding("CON-005", "MEDIUM", cid,
                           "no disagreement among the routes is recorded; mark what each disputes and leave it standing", "M4"))
    if not record.get("independent_audit"):
        out.append(Finding("CON-008", "INFO", cid,
                           "no independent audit yet; the construction-bias caveat applies (the assessor built the frame and chose the routes)", "M6"))

    clusters = uf.groups()
    n = len(clusters)
    if record.get("selection_is_choice"):
        computed = "author_thesis"
    elif flattened:
        computed = "withdrawn"
    elif n >= 3:
        computed = "strong"
    elif n == 2:
        computed = "partial"
    else:
        computed = "withdrawn"

    declared = record["declared_grade"]
    # Owning a claim as one's thesis is always allowed; claiming more than the routes support is not.
    if computed == "author_thesis":
        if declared != "author_thesis":
            out.append(Finding("CON-001", "HIGH", cid,
                               "the selection is a choice the method did not deliver, but it is graded %s; own it as a thesis"
                               % declared, "M5"))
    elif declared != "author_thesis" and GRADE_ORDER[declared] > GRADE_ORDER[computed]:
        out.append(Finding("CON-001", "HIGH", cid,
                           "declared %s but the routes support at most %s (%d independent route%s)"
                           % (declared, computed, n, "" if n == 1 else "s"), "M2"))

    order = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
    out.sort(key=lambda f: (order[f.severity], f.code, f.subject))
    return Assessment(computed, declared, clusters, out)


def effective_witnesses(lineages: Sequence[str]) -> int:
    """How many independent witnesses a list of source lineages amounts to."""
    return len({_norm(l) for l in lineages if _norm(l)})
