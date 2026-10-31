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


def _fail(d: Dict[str, Any]) -> FailPattern:
    custom = d.get("custom", "")
    pattern = d.get("pattern")
    if custom and custom not in KNOWN_CUSTOM_CHECKS:
        known = ", ".join(sorted(KNOWN_CUSTOM_CHECKS))
        raise ValueError(
            "fail pattern %r names an unknown custom check %r; known: %s"
            % (d.get("id", "?"), custom, known))
    if pattern is None and not custom:
        raise ValueError(
            "fail pattern %r has neither a pattern nor a custom check; "
            "it would never flag anything" % d.get("id", "?"))
    return FailPattern(id=d["id"], severity=d["severity"], pattern=pattern,
                       message=d["message"], custom=custom)


def _passp(d: Dict[str, Any]) -> PassPattern:
    return PassPattern(id=d["id"], any_of_names=tuple(d.get("any_of_names", [])),
                       minimum=int(d.get("min", 1)), message=d["message"])


def _probe(d: Dict[str, Any]) -> Probe:
    return Probe(
        id=d["id"],
        rule=d["rule"],
        input=d["input"],
        expect=d["expect"],
        fail_patterns=tuple(_fail(p) for p in d.get("fail_patterns", [])),
        pass_patterns=tuple(_passp(p) for p in d.get("pass_patterns", [])),
    )


def load_probes(path: Optional[str] = None) -> ProbeSet:
    """Load the authored probe set.

    `path` is the probes.json file; the default is the one bundled with the package.
    """
    p = path or PROBES_PATH
    with open(p, encoding="utf-8") as fh:
        data = json.load(fh)
    return ProbeSet(
        version=data["version"],
        source=data.get("source", {}),
        probes=tuple(_probe(x) for x in data["probes"]),
    )


def probe_version(path: Optional[str] = None) -> str:
    return load_probes(path).version
