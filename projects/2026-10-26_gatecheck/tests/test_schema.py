"""The tiny JSON Schema validator against the commitment schema."""

from __future__ import annotations

import unittest

from gatecheck.schema import SCHEMA_PATH, Validator, load_schema
from tests.support import bad, load, ok


class ValidSchemaOnConformingFixtures(unittest.TestCase):
    def setUp(self):
        self.v = Validator(load_schema())

    def test_gate_healthy_validates(self):
        errs = self.v.errors(load(ok("gate_healthy")))
        self.assertEqual(errs, [], errs)

    def test_target_healthy_validates(self):
        errs = self.v.errors(load(ok("target_healthy")))
        self.assertEqual(errs, [], errs)


class SchemaCatchesNonConforming(unittest.TestCase):
    def setUp(self):
        self.v = Validator(load_schema())

    def test_unknown_kind_fails_enum(self):
        errs = self.v.errors(load(bad("unknown_kind")))
        self.assertTrue(any("enum" in m.lower() or "one of" in m.lower() for _, m in errs), errs)

    def test_missing_required(self):
        errs = self.v.errors({"id": "x", "title": "y", "kind": "gate"})
        self.assertTrue(any("committed_at" in m for _, m in errs), errs)

    def test_wrong_type_for_dependencies(self):
        rec = load(ok("gate_healthy"))
        rec["dependencies"] = "a dependency as prose"
        errs = Validator(load_schema()).errors(rec)
        self.assertTrue(any("array" in m for _, m in errs), errs)

    def test_passes_additional_properties(self):
        """The schema allows additional properties; a custom field is not an error."""
        rec = load(ok("gate_healthy"))
        rec["custom_field"] = {"any": "value"}
        errs = Validator(load_schema()).errors(rec)
        self.assertEqual(errs, [], errs)


class SchemaLoad(unittest.TestCase):
    def test_schema_path_exists(self):
        import os
        self.assertTrue(os.path.exists(SCHEMA_PATH))

    def test_schema_has_required_fields(self):
        schema = load_schema()
        self.assertIn("required", schema)
        self.assertIn("id", schema["required"])
        self.assertIn("kind", schema["required"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
