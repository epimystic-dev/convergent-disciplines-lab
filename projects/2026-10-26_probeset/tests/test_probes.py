"""The probe dataset's integrity, loading and round-trip."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from probeset.probes import (KNOWN_CUSTOM_CHECKS, FailPattern, PassPattern, Probe, ProbeSet,
                             load_probes, probe_version)


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

    def test_bundled_custom_names_are_known(self):
        """Every `custom` value used in the bundled probes.json is in the registry; the
        loader would already reject an unknown name but this pins the invariant from the
        other side so a bundled-data change cannot drift past review.
        """
        for p in self.ps.probes:
            for fp in p.fail_patterns:
                if fp.custom:
                    self.assertIn(fp.custom, KNOWN_CUSTOM_CHECKS, fp.id)


class CustomCheckValidation(unittest.TestCase):
    """A typo in a probes.json `custom` field used to load silently and the probe would
    then never flag anything (the dispatcher returned False for every unknown name). The
    loader now rejects unknown custom names up front; the grader's implemented set is
    sanity-checked against `KNOWN_CUSTOM_CHECKS` at import time.
    """

    @staticmethod
    def _write(data):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
        try:
            json.dump(data, tmp)
            tmp.close()
            return tmp.name
        except Exception:
            tmp.close()
            os.unlink(tmp.name)
            raise

    def test_unknown_custom_name_rejected_at_load(self):
        path = self._write({
            "version": "0.0.0",
            "source": {"license": "CC-BY-SA-4.0"},
            "probes": [{
                "id": "X1", "rule": "r", "input": "i", "expect": "e",
                "fail_patterns": [{"id": "X1-typo", "severity": "HIGH",
                                    "custom": "missing_runge_vocab",
                                    "message": "silent typo would never flag"}],
                "pass_patterns": [],
            }],
        })
        try:
            with self.assertRaises(ValueError) as cm:
                load_probes(path)
            msg = str(cm.exception)
            self.assertIn("missing_runge_vocab", msg)
            self.assertIn("X1-typo", msg)
            self.assertIn("missing_rung_vocab", msg)
        finally:
            os.unlink(path)

    def test_known_custom_name_still_loads(self):
        path = self._write({
            "version": "0.0.0",
            "source": {"license": "CC-BY-SA-4.0"},
            "probes": [{
                "id": "X1", "rule": "r", "input": "i", "expect": "e",
                "fail_patterns": [{"id": "X1-rung", "severity": "HIGH",
                                    "custom": "missing_rung_vocab",
                                    "message": "no rung vocab"}],
                "pass_patterns": [],
            }],
        })
        try:
            ps = load_probes(path)
            self.assertEqual(ps.probes[0].fail_patterns[0].custom, "missing_rung_vocab")
        finally:
            os.unlink(path)

    def test_pattern_and_custom_both_absent_rejected(self):
        """A fail pattern with neither `pattern` nor `custom` can never flag anything;
        it is almost certainly an authoring mistake rather than an intentional no-op.
        """
        path = self._write({
            "version": "0.0.0",
            "source": {"license": "CC-BY-SA-4.0"},
            "probes": [{
                "id": "X1", "rule": "r", "input": "i", "expect": "e",
                "fail_patterns": [{"id": "X1-empty", "severity": "HIGH",
                                    "message": "nothing to match"}],
                "pass_patterns": [],
            }],
        })
        try:
            with self.assertRaises(ValueError) as cm:
                load_probes(path)
            self.assertIn("X1-empty", str(cm.exception))
        finally:
            os.unlink(path)

    def test_grader_implementations_match_known_registry(self):
        """If someone adds a name to the registry but forgets the implementation (or
        vice versa), importing the grade module raises - this test exercises that
        contract by reading the private dispatch dict.
        """
        from probeset.grade import _CUSTOM_IMPLS
        self.assertEqual(frozenset(_CUSTOM_IMPLS), KNOWN_CUSTOM_CHECKS)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
