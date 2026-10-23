from __future__ import annotations

import unittest

from threadkit.schema import SchemaError, Validator, check_schema


def V(schema):
    return Validator(schema)


class RefusesUnsupportedKeywords(unittest.TestCase):
    def test_unknown_keyword_refused(self):
        with self.assertRaises(SchemaError):
            V({"type": "object", "patternProperties": {}})

    def test_format_keyword_refused_rather_than_ignored(self):
        with self.assertRaises(SchemaError):
            V({"type": "string", "format": "email"})

    def test_remote_ref_refused(self):
        with self.assertRaises(SchemaError):
            V({"$ref": "https://example.test/other.json"})

    def test_unresolved_local_ref_refused(self):
        with self.assertRaises(SchemaError):
            V({"$ref": "#/$defs/missing"})

    def test_additional_properties_schema_refused(self):
        with self.assertRaises(SchemaError):
            V({"type": "object", "additionalProperties": {"type": "string"}})

    def test_unknown_type_refused(self):
        with self.assertRaises(SchemaError):
            V({"type": "date"})

    def test_bad_pattern_refused(self):
        with self.assertRaises(SchemaError):
            V({"type": "string", "pattern": "("})

    def test_nested_unknown_keyword_refused(self):
        with self.assertRaises(SchemaError):
            check_schema({"type": "object", "properties": {"a": {"type": "string", "maxLength": 3}}})


class Types(unittest.TestCase):
    def test_boolean_is_not_integer(self):
        self.assertFalse(V({"type": "integer"}).is_valid(True))

    def test_integer_is_a_number(self):
        self.assertTrue(V({"type": "number"}).is_valid(3))

    def test_float_is_not_integer(self):
        self.assertFalse(V({"type": "integer"}).is_valid(3.5))

    def test_null(self):
        self.assertTrue(V({"type": "null"}).is_valid(None))
        self.assertFalse(V({"type": "null"}).is_valid(0))

    def test_type_list(self):
        v = V({"type": ["string", "null"]})
        self.assertTrue(v.is_valid(None))
        self.assertTrue(v.is_valid("x"))
        self.assertFalse(v.is_valid(1))


class Keywords(unittest.TestCase):
    def test_enum_distinguishes_true_from_one(self):
        self.assertFalse(V({"enum": [1]}).is_valid(True))

    def test_enum_accepts_null_member(self):
        self.assertTrue(V({"enum": ["a", None]}).is_valid(None))

    def test_const(self):
        v = V({"const": "B"})
        self.assertTrue(v.is_valid("B"))
        self.assertFalse(v.is_valid("A"))

    def test_min_length(self):
        self.assertFalse(V({"type": "string", "minLength": 1}).is_valid(""))

    def test_pattern(self):
        v = V({"type": "string", "pattern": "^[0-9]{4}$"})
        self.assertTrue(v.is_valid("2026"))
        self.assertFalse(v.is_valid("26"))

    def test_minimum_maximum(self):
        v = V({"type": "number", "minimum": 0, "maximum": 1})
        self.assertTrue(v.is_valid(0.5))
        self.assertFalse(v.is_valid(1.5))
        self.assertFalse(v.is_valid(-0.1))

    def test_min_items(self):
        self.assertFalse(V({"type": "array", "minItems": 1}).is_valid([]))

    def test_items_report_index_path(self):
        errs = V({"type": "array", "items": {"type": "string"}}).errors(["a", 2])
        self.assertEqual(errs[0][0], "/1")

    def test_required_and_additional(self):
        v = V({"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"],
               "additionalProperties": False})
        self.assertIn("missing required field 'a'", v.errors({})[0][1])
        self.assertIn("unexpected field 'b'", v.errors({"a": "x", "b": 1})[0][1])

    def test_ref_into_defs(self):
        v = V({"type": "object", "properties": {"x": {"$ref": "#/$defs/s"}}, "$defs": {"s": {"type": "string"}}})
        self.assertTrue(v.is_valid({"x": "ok"}))
        self.assertFalse(v.is_valid({"x": 1}))

    def test_one_of_exactly_one(self):
        v = V({"oneOf": [{"type": "string"}, {"type": "string", "minLength": 3}]})
        self.assertTrue(v.is_valid("ab"))
        self.assertFalse(v.is_valid("abcd"))

    def test_type_mismatch_stops_descent(self):
        v = V({"type": "object", "required": ["a"]})
        self.assertEqual(len(v.errors([])), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
