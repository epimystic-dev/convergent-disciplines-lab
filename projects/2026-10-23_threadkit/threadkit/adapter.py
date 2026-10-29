"""Free-text to governed answer: extract the record, repair common schema slips, govern.

A model prompted for an answer record (contract `answer`) sometimes replies with a markdown
code fence around the JSON, a line of preamble before it, Python literal booleans in place of
JSON ones, trailing commas, or small shape slips (a bare `basis: "testimony"` where the
contract wants `{"kind": "testimony"}`, a bare `deliberation: "fast"`, a rung emitted as the
string "2" rather than the integer 2). Rather than fail the governor on these, the adapter
strips the common envelopes, parses permissively and makes surgical repairs - without
changing meaning - so the governor sees a valid record. Every change is logged.

The repairs are deliberately narrow: they only touch shape (string-for-object slips),
enum capitalisation (`Inquiry` -> `inquiry`), numeric-string-for-integer (`"2"` -> `2`) and
null-for-optional-nested-object slips. Nothing here changes a claim's text, its standing,
its basis.kind, or any other content-bearing field. If a model mislabels a claim's standing
the governor's REG-* findings will still catch it - the adapter does not launder it.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .governor import AnswerGovernor, Governed

_FENCE_RE = re.compile(r"^```(?:[a-zA-Z0-9_+-]+)?[ \t]*\n(.*?)\n```[ \t]*$", re.S)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
_PY_TRUE = re.compile(r"(?<![A-Za-z_0-9])True(?![A-Za-z_0-9])")
_PY_FALSE = re.compile(r"(?<![A-Za-z_0-9])False(?![A-Za-z_0-9])")
_PY_NONE = re.compile(r"(?<![A-Za-z_0-9])None(?![A-Za-z_0-9])")
_STRING_RE = re.compile(r"\"(?:\\.|[^\"\\])*\"", re.S)

_MODE_VALUES = ("inquiry", "advocacy", "explanation", "instruction")
_STANDING_VALUES = ("settled", "established", "contested", "limit", "bridge", "method")
_LEVEL_VALUES = ("practical", "foundational")
_BEHAVIOUR_LEVEL_VALUES = ("weights", "training_data", "prompt_context", "interface", "institution")
_BASIS_KIND_VALUES = ("observation", "inference", "testimony", "recall",
                      "convergence", "framework", "author_thesis", "method")
_DELIBERATION_KIND_VALUES = ("fast", "checked")
_MORAL_KIND_VALUES = ("none", "convergent", "contested")
_FORECAST_STATUS_VALUES = ("not_falsified", "confirmed", "falsified")


@dataclass(frozen=True)
class Repair(object):
    """One recorded change the adapter made to the record."""

    path: str
    note: str
    before: Any
    after: Any

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "note": self.note, "before": self.before, "after": self.after}


@dataclass
class Adapted(object):
    """The outcome of running the adapter end-to-end."""

    record: Optional[Any]
    repairs: List[Repair] = field(default_factory=list)
    parse_error: Optional[str] = None
    governed: Optional[Governed] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"record": self.record, "repairs": [r.to_dict() for r in self.repairs],
                "parse_error": self.parse_error,
                "governed": self.governed.to_dict() if self.governed is not None else None}


def extract_json_block(text: str) -> str:
    """Pull the JSON object out of free-form text.

    If the text is wrapped in a ``` fence (optionally language-tagged), the fenced content is
    taken. Otherwise, the substring from the first `{` through its matching close brace is
    taken by counting brackets while respecting string literals. If there is no `{` the
    stripped input is returned unchanged, so the caller still sees whatever the model emitted.
    """
    s = text.strip()
    m = _FENCE_RE.match(s)
    if m is not None:
        s = m.group(1).strip()
    start = s.find("{")
    if start < 0:
        return s
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(s)):
        ch = s[i]
        if escape:
            escape = False
            continue
        if in_string:
            if ch == "\\":
                escape = True
            elif ch == "\"":
                in_string = False
            continue
        if ch == "\"":
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return s[start:]


def _patch_outside_strings(text: str) -> str:
    """Apply the Python-literal and trailing-comma substitutions, but only in the regions
    that are not inside JSON string literals. Walking the string literals first keeps us
    from corrupting values that happen to contain the words True, False or None (or a
    trailing comma inside a quoted sentence).
    """
    def patch(chunk: str) -> str:
        chunk = _PY_TRUE.sub("true", chunk)
        chunk = _PY_FALSE.sub("false", chunk)
        chunk = _PY_NONE.sub("null", chunk)
        chunk = _TRAILING_COMMA_RE.sub(r"\1", chunk)
        return chunk

    parts: List[str] = []
    i = 0
    for m in _STRING_RE.finditer(text):
        parts.append(patch(text[i:m.start()]))
        parts.append(m.group(0))
        i = m.end()
    parts.append(patch(text[i:]))
    return "".join(parts)


def permissive_loads(text: str) -> Any:
    """json.loads with light repairs for Python literals and trailing commas.

    Tries strict JSON first; on failure, retries after replacing word-bounded True / False /
    None with their JSON forms and removing trailing commas before `}` and `]` - but only
    outside string literals, so a value like `"None of the above"` is left untouched. Does
    not accept comments, single-quoted strings or any other non-JSON extension - a model
    that emits those should have its prompt tightened, not its output silently guessed at.
    Raises ValueError (with the strict parser's message) if neither pass succeeds.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as first:
        patched = _patch_outside_strings(text)
        if patched == text:
            raise ValueError("could not parse as JSON: %s" % first.msg)
        try:
            return json.loads(patched)
        except json.JSONDecodeError:
            raise ValueError("could not parse as JSON: %s" % first.msg)


def _canonical(value: Any, allowed: Tuple[str, ...]) -> Optional[str]:
    """If value is a string whose casefolded, stripped form equals one of `allowed`, return
    the canonical member; otherwise return None. Lets the caller detect both case slips
    (`Inquiry`) and already-clean values (`inquiry`) with one comparison.
    """
    if not isinstance(value, str):
        return None
    folded = value.strip().casefold()
    for member in allowed:
        if folded == member.casefold():
            return member
    return None


def _normalise_enum(container: Dict[str, Any], key: str, allowed: Tuple[str, ...],
                    path: str, repairs: List[Repair]) -> None:
    if key not in container:
        return
    canon = _canonical(container[key], allowed)
    if canon is not None and container[key] != canon:
        repairs.append(Repair(path, "enum case normalised", container[key], canon))
        container[key] = canon


def repair_answer(record: Any) -> Tuple[Any, List[Repair]]:
    """Repair the common schema slips on an answer record.

    Returns (new_record, repairs). The input is not mutated; a deep copy is made and the
    copy is returned alongside the list of changes applied to it. If `record` is not a dict,
    it is returned unchanged with an empty repairs list - the governor will emit GOV-000 for
    a non-object record and the adapter does not pretend otherwise.

    Repairs applied, by path:
      - `mode`                                       enum case normalisation
      - `deliberation`                               bare string -> {"kind": ...}
      - `deliberation/kind`                          enum case normalisation
      - `moral`, `coverage`                          null -> field dropped
      - `moral/kind`                                 enum case normalisation
      - `claims/<i>/standing`                        enum case normalisation
      - `claims/<i>/level`                           enum case normalisation
      - `claims/<i>/behaviour_level`                 enum case normalisation
      - `claims/<i>/basis`                           bare string -> {"kind": ...}
      - `claims/<i>/basis/kind`                      enum case normalisation
      - `claims/<i>/rung`                            "1"/"2"/"3" -> int
      - `claims/<i>/sources/<j>`                     bare string -> {"ref": ...}
      - `claims/<i>/forecast/status`                 enum case normalisation
    """
    repairs: List[Repair] = []
    if not isinstance(record, dict):
        return record, repairs
    record = copy.deepcopy(record)

    _normalise_enum(record, "mode", _MODE_VALUES, "mode", repairs)

    delib = record.get("deliberation")
    if isinstance(delib, str):
        canon = _canonical(delib, _DELIBERATION_KIND_VALUES)
        if canon is not None:
            repairs.append(Repair("deliberation", "string wrapped as {kind: ...}", delib, {"kind": canon}))
            record["deliberation"] = {"kind": canon}
    elif isinstance(delib, dict):
        _normalise_enum(delib, "kind", _DELIBERATION_KIND_VALUES, "deliberation/kind", repairs)

    for key in ("moral", "coverage"):
        if key in record and record[key] is None:
            repairs.append(Repair(key, "null optional nested object dropped", None, None))
            del record[key]

    moral = record.get("moral")
    if isinstance(moral, dict):
        _normalise_enum(moral, "kind", _MORAL_KIND_VALUES, "moral/kind", repairs)

    claims = record.get("claims")
    if isinstance(claims, list):
        for i, c in enumerate(claims):
            if not isinstance(c, dict):
                continue
            prefix = "claims/" + str(i)
            _normalise_enum(c, "standing", _STANDING_VALUES, prefix + "/standing", repairs)
            _normalise_enum(c, "level", _LEVEL_VALUES, prefix + "/level", repairs)
            _normalise_enum(c, "behaviour_level", _BEHAVIOUR_LEVEL_VALUES, prefix + "/behaviour_level", repairs)

            b = c.get("basis")
            if isinstance(b, str):
                canon = _canonical(b, _BASIS_KIND_VALUES)
                if canon is not None:
                    repairs.append(Repair(prefix + "/basis", "string wrapped as {kind: ...}", b, {"kind": canon}))
                    c["basis"] = {"kind": canon}
            elif isinstance(b, dict):
                _normalise_enum(b, "kind", _BASIS_KIND_VALUES, prefix + "/basis/kind", repairs)

            r = c.get("rung")
            if isinstance(r, str) and r.strip() in {"1", "2", "3"}:
                v = int(r.strip())
                repairs.append(Repair(prefix + "/rung", "numeric string coerced to integer", r, v))
                c["rung"] = v

            srcs = c.get("sources")
            if isinstance(srcs, list):
                for j, s in enumerate(srcs):
                    if isinstance(s, str) and s.strip():
                        repairs.append(Repair(prefix + "/sources/" + str(j),
                                              "string wrapped as {ref: ...}", s, {"ref": s}))
                        srcs[j] = {"ref": s}

            fc = c.get("forecast")
            if isinstance(fc, dict):
                _normalise_enum(fc, "status", _FORECAST_STATUS_VALUES, prefix + "/forecast/status", repairs)

    return record, repairs


def adapt(text: str) -> Tuple[Optional[Any], List[Repair], Optional[str]]:
    """Extract, parse and repair; return (record, repairs, parse_error).

    `parse_error` is None when the extracted block parsed (strict or permissive) and the
    record (which may still be schema-invalid) is returned. On parse failure, `record` is
    None, `repairs` is empty and `parse_error` carries the strict parser's message.
    """
    block = extract_json_block(text)
    try:
        parsed = permissive_loads(block)
    except ValueError as exc:
        return None, [], str(exc)
    record, repairs = repair_answer(parsed)
    return record, repairs, None


def govern_free_text(text: str, governor: Optional[AnswerGovernor] = None, *,
                     used_in_decision: bool = False, ascii_only: bool = False) -> Adapted:
    """Adapt free-form text and govern the resulting record.

    If parsing fails, returns an Adapted with record=None, repairs=[], governed=None and
    parse_error set. Otherwise the record (possibly repaired) is governed; a schema-invalid
    record after repair produces GOV-000 findings on the Governed value, not an exception.
    """
    record, repairs, err = adapt(text)
    if err is not None:
        return Adapted(record=None, repairs=repairs, parse_error=err, governed=None)
    g = (governor or AnswerGovernor()).govern(record, ascii_only=ascii_only,
                                              used_in_decision=used_in_decision)
    return Adapted(record=record, repairs=repairs, parse_error=None, governed=g)
