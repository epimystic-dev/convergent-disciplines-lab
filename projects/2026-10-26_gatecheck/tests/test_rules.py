"""Each rule against its intended fixture."""

from __future__ import annotations

import unittest

from gatecheck.findings import Severity, Verdict
from gatecheck.rules import ALL_RULES
from gatecheck.scan import rollup, scan_record
from tests.support import bad, codes, load, ok


class HealthyFixtures(unittest.TestCase):
    def test_gate_healthy(self):
        r = scan_record(load(ok("gate_healthy")))
        self.assertEqual(r.verdict, Verdict.HEALTHY,
                         "healthy gate fired findings: %s" % codes(r.findings))

    def test_target_healthy(self):
        r = scan_record(load(ok("target_healthy")))
        self.assertEqual(r.verdict, Verdict.HEALTHY,
                         "healthy target fired findings: %s" % codes(r.findings))


class RuleFires(unittest.TestCase):
    def _assert_fires(self, fixture: str, rule_id: str, must_be_unhealthy: bool = True):
        r = scan_record(load(bad(fixture)))
        self.assertIn(rule_id, codes(r.findings),
                      "%s did not fire against %s; fired %s" % (rule_id, fixture, codes(r.findings)))
        if must_be_unhealthy:
            self.assertEqual(r.verdict, Verdict.UNHEALTHY)

    def test_GATE_001_no_trigger(self):
        self._assert_fires("gate_no_trigger", "GATE-001")

    def test_GATE_002_no_enforcer(self):
        self._assert_fires("gate_no_enforcer", "GATE-002")

    def test_GATE_003_self_attested(self):
        r = scan_record(load(bad("gate_self_attested")))
        self.assertIn("GATE-003", codes(r.findings))
        self.assertEqual(r.verdict, Verdict.NEEDS_ATTENTION)

    def test_GATE_004_competitor_contingent(self):
        r = scan_record(load(bad("competitor_contingent")))
        self.assertIn("GATE-004", codes(r.findings))

    def test_GATE_005_missing_dates(self):
        r = scan_record(load(bad("missing_dates")))
        count = sum(1 for f in r.findings if f.code == "GATE-005")
        self.assertGreaterEqual(count, 2,
                                "GATE-005 should fire for each missing date; got %d" % count)
        self.assertEqual(r.verdict, Verdict.NEEDS_ATTENTION)

    def test_GATE_006_no_deps(self):
        r = scan_record(load(bad("gate_no_deps")))
        self.assertIn("GATE-006", codes(r.findings))
        # GATE-006 is INFO; verdict should be HEALTHY unless --strict
        self.assertEqual(r.verdict, Verdict.HEALTHY)

    def test_GATE_007_escape_broader(self):
        self._assert_fires("escape_broader", "GATE-007")

    def test_GATE_007_competitor_contingent_no_scope(self):
        r = scan_record(load(bad("competitor_contingent")))
        self.assertIn("GATE-007", codes(r.findings))

    def test_GATE_008_target_incomplete(self):
        r = scan_record(load(bad("target_incomplete")))
        count = sum(1 for f in r.findings if f.code == "GATE-008")
        self.assertGreaterEqual(count, 2,
                                "GATE-008 should fire for missing metric and deadline; got %d" % count)
        self.assertEqual(r.verdict, Verdict.UNHEALTHY)

    def test_GATE_009_stale_review(self):
        r = scan_record(load(bad("stale_review")))
        self.assertIn("GATE-009", codes(r.findings))
        self.assertEqual(r.verdict, Verdict.NEEDS_ATTENTION)

    def test_GATE_010_unknown_kind(self):
        self._assert_fires("unknown_kind", "GATE-010")

    def test_GATE_011_prose_trigger(self):
        r = scan_record(load(bad("trigger_prose_only")))
        self.assertIn("GATE-011", codes(r.findings))

    def test_GATE_012_verifiable_no_external(self):
        r = scan_record(load(bad("verifiable_no_check")))
        self.assertIn("GATE-012", codes(r.findings))


class RuleRegistry(unittest.TestCase):
    def test_twelve_rules(self):
        self.assertEqual(len(ALL_RULES), 12)

    def test_rule_ids_unique_and_padded(self):
        ids = [r.id for r in ALL_RULES]
        self.assertEqual(len(ids), len(set(ids)))
        for rid in ids:
            self.assertRegex(rid, r"^GATE-\d{3}$")

    def test_rule_ids_contiguous(self):
        ids = [int(r.id.split("-")[1]) for r in ALL_RULES]
        self.assertEqual(ids, list(range(1, len(ids) + 1)))

    def test_rule_severity_known(self):
        for r in ALL_RULES:
            self.assertIn(r.severity, Severity.ALL)

    def test_rule_applies_to_known(self):
        for r in ALL_RULES:
            self.assertIn(r.applies_to, ("gate", "target", "any"))

    def test_rule_description_is_not_empty(self):
        for r in ALL_RULES:
            self.assertTrue(r.description.strip(), r.id)

    def test_rules_are_frozen(self):
        with self.assertRaises(Exception):
            ALL_RULES[0].severity = "nope"  # type: ignore[misc]


class Disable(unittest.TestCase):
    def test_disable_rule(self):
        r = scan_record(load(bad("gate_self_attested")), disabled=["GATE-003"])
        self.assertNotIn("GATE-003", codes(r.findings))


class Rollup(unittest.TestCase):
    def test_rollup_mixed(self):
        results = [
            scan_record(load(ok("gate_healthy"))),
            scan_record(load(bad("gate_self_attested"))),
        ]
        self.assertEqual(rollup(results), Verdict.NEEDS_ATTENTION)

    def test_rollup_unhealthy(self):
        results = [
            scan_record(load(ok("gate_healthy"))),
            scan_record(load(bad("gate_no_trigger"))),
        ]
        self.assertEqual(rollup(results), Verdict.UNHEALTHY)

    def test_rollup_healthy(self):
        results = [scan_record(load(ok("gate_healthy")))]
        self.assertEqual(rollup(results), Verdict.HEALTHY)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
