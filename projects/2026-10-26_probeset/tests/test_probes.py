"""The probe dataset's integrity, loading and round-trip."""

from __future__ import annotations

import json
import unittest

from probeset.probes import FailPattern, PassPattern, Probe, ProbeSet, load_probes, probe_version


class ProbesLoad(unittest.TestCase):
    def setUp(self):
        self.ps = load_probes()

    def test_version_is_semver(self):
        self.assertRegex(self.ps.version, r"^\d+\.\d+\.\d+$")

    def test_six_probes(self):
        self.assertEqual(len(self.ps.probes), 6)
        self.assertEqual(self.ps.ids(), ["P1", "P2", "P3", "P4", "P5", "P6"])

    def test_each_probe_has_rule_and_input(self):
        for p in self.ps.probes:
            self.assertTrue(p.rule, p.id)
            self.assertTrue(p.input, p.id)
            self.assertTrue(p.expect, p.id)
            self.assertTrue(p.fail_patterns, p.id)

    def test_by_id_and_missing_id(self):
        self.assertEqual(self.ps.by_id("P3").id, "P3")
        with self.assertRaises(KeyError):
            self.ps.by_id("P99")

    def test_fail_patterns_compile(self):
        for p in self.ps.probes:
            for fp in p.fail_patterns:
                if fp.pattern is not None:
                    self.assertTrue(fp.compiled.search is not None, fp.id)

    def test_severity_is_known(self):
        for p in self.ps.probes:
            for fp in p.fail_patterns:
                self.assertIn(fp.severity, ("HIGH", "MEDIUM", "INFO"))

    def test_rule_ids_are_unique(self):
        seen = set()
        for p in self.ps.probes:
            for fp in p.fail_patterns:
                self.assertNotIn(fp.id, seen, "duplicate rule id %s" % fp.id)
                seen.add(fp.id)
            for pp in p.pass_patterns:
                self.assertNotIn(pp.id, seen, "duplicate rule id %s" % pp.id)
                seen.add(pp.id)

    def test_source_license(self):
        self.assertEqual(self.ps.source.get("license"), "CC-BY-SA-4.0")

    def test_probe_version_helper(self):
        self.assertEqual(probe_version(), self.ps.version)

    def test_dataclasses_are_frozen(self):
        p = self.ps.probes[0]
        with self.assertRaises(Exception):
            p.id = "nope"  # type: ignore[misc]
        fp = p.fail_patterns[0]
        with self.assertRaises(Exception):
            fp.severity = "nope"  # type: ignore[misc]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
