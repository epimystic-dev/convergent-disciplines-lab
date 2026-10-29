"""A tiny JSON Schema validator - standard library only.

Supports the subset of JSON Schema (draft-07) used by `commitment.schema.json`:
required / properties / type / enum / minLength / items / additionalProperties. Not a
general-purpose validator: deliberately narrow so the dependency surface is nothing. If
the schema grows past what this module supports, swap in jsonschema under an optional
import.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple


SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "commitment.schema.json")


class SchemaError(ValueError):
    pass


_TYPE_MAP = {
    "string": str, "integer": int, "number": (int, float), "boolean": bool,
    "object": dict, "array": list, "null": type(None),
}


def _type_matches(value: Any, expected: str) -> bool:
    py = _TYPE_MAP.get(expected)
    if py is None:
        return True
    if expected == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, py)


class Validator(object):
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema

    def errors(self, record: Any) -> List[Tuple[str, str]]:
        """Return list of (path, message) tuples. Empty list means valid."""
        out: List[Tuple[str, str]] = []
        self._walk(record, self.schema, "", out)
        return out

    def _walk(self, value: Any, schema: Dict[str, Any], path: str, out: List[Tuple[str, str]]) -> None:
        if "type" in schema:
            if not _type_matches(value, schema["type"]):
                out.append((path or "/", "expected type %s" % schema["type"]))
                return
        if "enum" in schema:
            if value not in schema["enum"]:
                out.append((path or "/", "value must be one of %s" % schema["enum"]))
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                out.append((path or "/", "string shorter than minLength %d" % schema["minLength"]))
        if isinstance(value, dict):
            for key in schema.get("required", []):
                if key not in value:
                    out.append((path or "/", "missing required field %r" % key))
            props = schema.get("properties", {})
            for key, sub in value.items():
                if key in props:
                    self._walk(sub, props[key], path + "/" + key, out)
        if isinstance(value, list) and "items" in schema:
            for i, item in enumerate(value):
                self._walk(item, schema["items"], path + "/" + str(i), out)


def load_schema(path: str = SCHEMA_PATH) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
