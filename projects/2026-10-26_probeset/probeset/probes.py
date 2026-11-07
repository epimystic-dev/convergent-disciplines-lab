"""The probe dataset.

The probes live in `data/probes.json` as a versioned document. A `Probe` is the input, the
rule it exercises, the behaviour the probe expects to see, and the deterministic patterns
the grader will flag.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .findings import Severity


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PROBES_PATH = os.path.join(DATA_DIR, "probes.json")


@dataclass(frozen=True)
class FailPattern(object):
    id: str
    severity: str
    pattern: Optional[str]
    message: str
    custom: str = ""

    @property
    def compiled(self):
        if self.pattern is None:
            return None
        return re.compile(self.pattern)


@dataclass(frozen=True)
class PassPattern(object):
    id: str
    any_of_names: Tuple[str, ...]
    minimum: int
    message: str


@dataclass(frozen=True)
class Probe(object):
    id: str
    rule: str
    input: str
    expect: str
    fail_patterns: Tuple[FailPattern, ...]
    pass_patterns: Tuple[PassPattern, ...]


@dataclass(frozen=True)
class ProbeSet(object):
    version: str
    source: Dict[str, Any]
    probes: Tuple[Probe, ...]

    def by_id(self, probe_id: str) -> Probe:
        for p in self.probes:
            if p.id == probe_id:
                return p
        raise KeyError("no probe with id %r" % probe_id)

    def ids(self) -> List[str]:
        return [p.id for p in self.probes]


def _as_tuple(seq: Optional[Sequence[Any]]) -> tuple:
    return tuple(seq) if seq is not None else ()


KNOWN_CUSTOM_CHECKS = frozenset(["missing_rung_vocab"])
"""Named custom fail-checks the grader implements. The grader dispatches on this name,
so a typo in a probes.json `custom` field would silently disable the check (an unknown
name just returns False from the dispatcher, and the probe author would see a probe
that never flags without knowing why). Any `custom` value in a probes.json fail pattern
MUST be in this set; the loader rejects unknown names at load time rather than letting
the grader silently no-op. The grade module asserts its implemented set matches this
one at import time, so adding a new check to one side without the other is caught.
"""


def _fail(d: Dict[str, Any], probe_id: str = "?", index: int = -1) -> FailPattern:
    if not isinstance(d, dict):
        raise ValueError(
            "probe %r fail_pattern at index %d must be a JSON object; got %s"
            % (probe_id, index, type(d).__name__))
    custom = d.get("custom", "")
    pattern = d.get("pattern")
    severity = d["severity"]
    if severity not in Severity.ALL:
        known = ", ".join(Severity.ALL)
        raise ValueError(
            "fail pattern %r has an unknown severity %r; known: %s"
            % (d.get("id", "?"), severity, known))
    if custom and custom not in KNOWN_CUSTOM_CHECKS:
        known = ", ".join(sorted(KNOWN_CUSTOM_CHECKS))
        raise ValueError(
            "fail pattern %r names an unknown custom check %r; known: %s"
            % (d.get("id", "?"), custom, known))
    if pattern is None and not custom:
        raise ValueError(
            "fail pattern %r has neither a pattern nor a custom check; "
            "it would never flag anything" % d.get("id", "?"))
    if pattern is not None:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(
                "fail pattern %r has an invalid regex: %s"
                % (d.get("id", "?"), exc))
    return FailPattern(id=d["id"], severity=severity, pattern=pattern,
                       message=d["message"], custom=custom)


def _passp(d: Dict[str, Any], probe_id: str = "?", index: int = -1) -> PassPattern:
    if not isinstance(d, dict):
        raise ValueError(
            "probe %r pass_pattern at index %d must be a JSON object; got %s"
            % (probe_id, index, type(d).__name__))
    return PassPattern(id=d["id"], any_of_names=tuple(d.get("any_of_names", [])),
                       minimum=int(d.get("min", 1)), message=d["message"])


def _probe(d: Dict[str, Any], index: int = -1) -> Probe:
    if not isinstance(d, dict):
        raise ValueError(
            "probe entry at index %d must be a JSON object; got %s"
            % (index, type(d).__name__))
    probe_id = d.get("id", "?")
    fail_raw = d.get("fail_patterns", [])
    if not isinstance(fail_raw, list):
        raise ValueError(
            "probe %r `fail_patterns` must be a JSON array; got %s"
            % (probe_id, type(fail_raw).__name__))
    pass_raw = d.get("pass_patterns", [])
    if not isinstance(pass_raw, list):
        raise ValueError(
            "probe %r `pass_patterns` must be a JSON array; got %s"
            % (probe_id, type(pass_raw).__name__))
    return Probe(
        id=d["id"],
        rule=d["rule"],
        input=d["input"],
        expect=d["expect"],
        fail_patterns=tuple(_fail(p, probe_id, i) for i, p in enumerate(fail_raw)),
        pass_patterns=tuple(_passp(p, probe_id, i) for i, p in enumerate(pass_raw)),
    )


def load_probes(path: Optional[str] = None) -> ProbeSet:
    """Load the authored probe set.

    `path` is the probes.json file; the default is the one bundled with the package.
    """
    p = path or PROBES_PATH
    with open(p, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(
            "top-level probes.json must be a JSON object; got %s"
            % type(data).__name__)
    probes_raw = data.get("probes", [])
    if not isinstance(probes_raw, list):
        raise ValueError(
            "top-level `probes` field must be a JSON array; got %s"
            % type(probes_raw).__name__)
    return ProbeSet(
        version=data["version"],
        source=data.get("source", {}),
        probes=tuple(_probe(x, i) for i, x in enumerate(probes_raw)),
    )


def probe_version(path: Optional[str] = None) -> str:
    return load_probes(path).version
