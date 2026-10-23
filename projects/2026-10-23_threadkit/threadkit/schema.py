"""A small, strict JSON Schema validator for the threads data contracts.

It implements exactly the subset of JSON Schema 2020-12 the contracts use, and it refuses
to load a schema that uses any other keyword. A validator that silently ignores keywords it
does not understand passes records it never checked; this one says so instead.

Supported keywords: $schema, $id, title, description, type, properties, required,
additionalProperties (boolean), enum, const, items, minItems, minLength, minimum, maximum,
pattern, $ref (local "#/$defs/<name>" only), $defs, oneOf.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

SUPPORTED = frozenset([
    "$schema", "$id", "title", "description", "type", "properties", "required",
    "additionalProperties", "enum", "const", "items", "minItems", "minLength",
    "minimum", "maximum", "pattern", "$ref", "$defs", "oneOf",
])
_TYPES = frozenset(["object", "array", "string", "number", "integer", "boolean", "null"])

Error = Tuple[str, str]


class SchemaError(ValueError):
    """The schema itself uses something this validator does not implement."""


def _type_of(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _json_equal(a: Any, b: Any) -> bool:
    """Equality as JSON means it: True is not 1, and 1 equals 1.0."""
    ta, tb = _type_of(a), _type_of(b)
    numeric = ("integer", "number")
    if ta in numeric and tb in numeric:
        return a == b
    if ta != tb:
        return False
    if ta == "array":
        return len(a) == len(b) and all(_json_equal(x, y) for x, y in zip(a, b))
    if ta == "object":
        return a.keys() == b.keys() and all(_json_equal(a[k], b[k]) for k in a)
    return a == b


def _matches_type(value: Any, wanted: str) -> bool:
    t = _type_of(value)
    if wanted == "number":
        return t in ("number", "integer")
    return t == wanted


def check_schema(schema: Any, path: str = "#") -> None:
    """Raise SchemaError if the schema uses anything outside the supported subset."""
    if not isinstance(schema, dict):
        raise SchemaError("%s: a schema must be an object" % path)
    for key in schema:
        if key not in SUPPORTED:
            raise SchemaError("%s: unsupported keyword %r" % (path, key))
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        for t in types:
            if t not in _TYPES:
                raise SchemaError("%s: unknown type %r" % (path, t))
    if "additionalProperties" in schema and not isinstance(schema["additionalProperties"], bool):
        raise SchemaError("%s: additionalProperties must be a boolean here" % path)
    if "$ref" in schema:
        ref = schema["$ref"]
        if not (isinstance(ref, str) and ref.startswith("#/$defs/")):
            raise SchemaError("%s: only local #/$defs/ references are supported, got %r" % (path, ref))
    if "pattern" in schema:
        try:
            re.compile(schema["pattern"])
        except re.error as exc:
            raise SchemaError("%s: bad pattern: %s" % (path, exc))
    for name, sub in (schema.get("properties") or {}).items():
        check_schema(sub, path + "/properties/" + name)
    for name, sub in (schema.get("$defs") or {}).items():
        check_schema(sub, path + "/$defs/" + name)
    if "items" in schema:
        check_schema(schema["items"], path + "/items")
    for i, sub in enumerate(schema.get("oneOf") or []):
        check_schema(sub, path + "/oneOf/" + str(i))


class Validator(object):
    """Validate JSON values against one schema. Construction checks the schema."""

    def __init__(self, schema: Dict[str, Any]):
        check_schema(schema)
        self.schema = schema
        self.defs = schema.get("$defs") or {}
        for ref_holder in self._refs(schema):
            name = ref_holder.split("/")[-1]
            if name not in self.defs:
                raise SchemaError("unresolved reference %r" % ref_holder)

    def _refs(self, node: Any) -> List[str]:
        out: List[str] = []
        if isinstance(node, dict):
            if "$ref" in node:
                out.append(node["$ref"])
            for v in node.values():
                out.extend(self._refs(v))
        elif isinstance(node, list):
            for v in node:
                out.extend(self._refs(v))
        return out

    def errors(self, value: Any) -> List[Error]:
        out: List[Error] = []
        self._validate(value, self.schema, "", out)
        return out

    def is_valid(self, value: Any) -> bool:
        return not self.errors(value)

    def _validate(self, value: Any, schema: Dict[str, Any], path: str, out: List[Error]) -> None:
        where = path or "/"
        if "$ref" in schema:
            self._validate(value, self.defs[schema["$ref"].split("/")[-1]], path, out)
            return
        if "type" in schema:
            types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_matches_type(value, t) for t in types):
                out.append((where, "expected %s, got %s" % (" or ".join(types), _type_of(value))))
                return
        if "const" in schema and not _json_equal(value, schema["const"]):
            out.append((where, "must equal %s" % json.dumps(schema["const"])))
        if "enum" in schema and not any(_json_equal(value, e) for e in schema["enum"]):
            out.append((where, "must be one of %s" % ", ".join(json.dumps(e) for e in schema["enum"])))
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                out.append((where, "shorter than %d characters" % schema["minLength"]))
            if "pattern" in schema and not re.search(schema["pattern"], value):
                out.append((where, "does not match the required format"))
        if _type_of(value) in ("integer", "number"):
            if "minimum" in schema and value < schema["minimum"]:
                out.append((where, "below minimum %s" % schema["minimum"]))
            if "maximum" in schema and value > schema["maximum"]:
                out.append((where, "above maximum %s" % schema["maximum"]))
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                out.append((where, "fewer than %d items" % schema["minItems"]))
            if "items" in schema:
                for i, item in enumerate(value):
                    self._validate(item, schema["items"], path + "/" + str(i), out)
        if isinstance(value, dict):
            props = schema.get("properties") or {}
            for req in schema.get("required") or []:
                if req not in value:
                    out.append((where, "missing required field %r" % req))
            for key, item in value.items():
                if key in props:
                    self._validate(item, props[key], path + "/" + key, out)
                elif schema.get("additionalProperties") is False:
                    out.append((where, "unexpected field %r" % key))
        if "oneOf" in schema:
            passing = sum(1 for sub in schema["oneOf"] if not self._sub_errors(value, sub, path))
            if passing != 1:
                out.append((where, "must match exactly one alternative (matched %d)" % passing))

    def _sub_errors(self, value: Any, schema: Dict[str, Any], path: str) -> List[Error]:
        out: List[Error] = []
        self._validate(value, schema, path, out)
        return out
