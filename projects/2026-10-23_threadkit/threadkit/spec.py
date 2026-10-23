"""Load and query the threads: registers, convergences, disagreements, frameworks and lessons.

The package carries its own copy of threads/threads.json and the data-contract schemas, so it
works installed; tests assert the copy matches the repository's canonical files.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .schema import Validator

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
THREADS_PATH = os.path.join(DATA_DIR, "threads.json")
SCHEMA_DIR = os.path.join(DATA_DIR, "schemas")
PROMPT_DIR = os.path.join(DATA_DIR, "prompts")

CONTRACTS = (
    "agent-policy", "answer", "claim", "consensus", "convergence", "decision-record",
    "design-review", "dialogue", "disagreement", "explanation",
)


def _read_json(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class Threads(object):
    """The threads as data, with the lookups an implementer needs."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.lessons: List[Dict[str, Any]] = list(data["lessons"])
        self._by_id = {l["id"]: l for l in self.lessons}

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Threads":
        return cls(_read_json(path or THREADS_PATH))

    @property
    def version(self) -> str:
        return self.data["version"]

    def ids(self) -> List[str]:
        return [l["id"] for l in self.lessons]

    def get(self, lid: str) -> Dict[str, Any]:
        key = lid.strip().upper()
        if key not in self._by_id:
            raise KeyError("no lesson %r; known: %s" % (lid, ", ".join(self.ids())))
        return self._by_id[key]

    def has(self, lid: str) -> bool:
        return lid.strip().upper() in self._by_id

    def select(self, strand: Optional[str] = None, layer: Optional[str] = None,
               standing: Optional[str] = None, chapter: Optional[int] = None,
               derivation: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for l in self.lessons:
            if strand is not None and l["strand"] != strand.upper():
                continue
            if layer is not None and layer not in l["enforcement_layers"]:
                continue
            if standing is not None and l["standing"] != standing:
                continue
            if chapter is not None and chapter not in l["chapters"]:
                continue
            if derivation is not None and l["derivation"] != derivation:
                continue
            out.append(l)
        return out

    def context_enforceable(self) -> List[str]:
        """Lessons a model can apply in its own reasoning and wording when instructed."""
        return [l["id"] for l in self.lessons if "context" in l["enforcement_layers"]]

    def strands(self) -> Dict[str, Dict[str, str]]:
        return dict(self.data["strands"])

    def registers(self) -> List[Dict[str, str]]:
        return list(self.data["registers"])

    def convergence(self, cid: str) -> Dict[str, Any]:
        for c in self.data["convergences"]:
            if c["id"] == cid:
                return c
        raise KeyError("no convergence %r" % cid)

    def convergences(self) -> List[Dict[str, Any]]:
        return list(self.data["convergences"])

    def disagreements(self) -> List[Dict[str, Any]]:
        return list(self.data["disagreements"])

    def moral(self) -> Dict[str, Any]:
        return self.data["moral"]

    def frameworks(self) -> Dict[str, Any]:
        return self.data["frameworks"]


def load(path: Optional[str] = None) -> Threads:
    return Threads.load(path)


def contract_validator(name: str) -> Validator:
    """A strict validator for one of the data contracts in threads/schemas/."""
    if name not in CONTRACTS:
        raise KeyError("no contract %r; known: %s" % (name, ", ".join(CONTRACTS)))
    return Validator(_read_json(os.path.join(SCHEMA_DIR, name + ".schema.json")))


def threads_validator() -> Validator:
    return Validator(_read_json(os.path.join(DATA_DIR, "threads.schema.json")))


def deployment_validator() -> Validator:
    return Validator(_read_json(os.path.join(DATA_DIR, "deployment.schema.json")))


def prompt_text(agent: bool = False) -> str:
    """The drop-in prompt text: everything below the first horizontal rule of the prompt file."""
    name = "threads-agent-addendum.md" if agent else "threads-system-prompt.md"
    with open(os.path.join(PROMPT_DIR, name), encoding="utf-8") as fh:
        text = fh.read()
    marker = "\n---\n"
    return text.split(marker, 1)[1].lstrip("\n") if marker in text else text
