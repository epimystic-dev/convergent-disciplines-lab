"""Design reviews and deployment audits."""

from __future__ import annotations

import unittest

from threadkit.audit import audit
from threadkit.findings import exit_code, verdict
from threadkit.review import check as check_review
from threadkit.spec import contract_validator
from tests.support import codes, deepcopy, load_example

GOOD = load_example("review_good.json")
WEAK = load_example("review_weak.json")
HEALTHY = load_example("deployment_healthy.json")
DWEAK = load_example("deployment_weak.json")


class Review(unittest.TestCase):
    def test_good(self):
        self.assertEqual(check_review(GOOD), [])

    def test_weak_trips_what_it_was_built_for(self):
        got = set(codes(check_review(WEAK)))
        for c in ("REV-001", "REV-002", "REV-003", "REV-004", "REV-005", "REV-007", "REV-010", "REV-011", "REV-013"):
            self.assertIn(c, got)

    def test_contracts(self):
        v = contract_validator("design-review")
        self.assertEqual(v.errors(GOOD), [])
        self.assertEqual(v.errors(WEAK), [])

    def test_self_continuation_is_high(self):
        r = deepcopy(GOOD)
        r["nishkama"]["self_continuation_objective"] = True
        self.assertEqual([(f.code, f.severity) for f in check_review(r)], [("REV-002", "HIGH")])

    def test_thin_political_economy(self):
        r = deepcopy(GOOD)
        r["political_economy"] = {"who_gains": "unknown", "who_pays": "unknown", "augment_or_replace": "unknown",
                                  "freedoms": {"move_away": "unknown", "disobey": "unknown", "reshape": "unknown"}}
        self.assertIn("REV-006", codes(check_review(r)))

    def test_commons_pulled_loose(self):
        r = deepcopy(GOOD)
        r["political_economy"]["commons"]["attention"] = "pulls_loose"
        self.assertIn("REV-008", codes(check_review(r)))

    def test_replace_is_info(self):
        r = deepcopy(GOOD)
        r["political_economy"]["augment_or_replace"] = "replace"
        self.assertEqual([(f.code, f.severity) for f in check_review(r)], [("REV-009", "INFO")])

    def test_partial_freedom_is_info(self):
        r = deepcopy(GOOD)
        r["political_economy"]["freedoms"]["reshape"] = "partial"
        self.assertEqual([(f.code, f.severity) for f in check_review(r)], [("REV-007", "INFO")])

    def test_sdt_worsens(self):
        r = deepcopy(GOOD)
        r["sdt"]["elite_competition"] = "worsens"
        self.assertIn("REV-012", codes(check_review(r)))

    def test_sluice_info(self):
        r = deepcopy(GOOD)
        r["consultation"]["drafted_by"] = ["vendor"]
        self.assertEqual([(f.code, f.severity) for f in check_review(r)], [("REV-014", "INFO")])

    def test_layers_and_questions_info(self):
        r = deepcopy(GOOD)
        r["layers_covered"] = ["L1"]
        del r["open_questions"]
        got = [(f.code, f.severity) for f in check_review(r)]
        self.assertIn(("REV-015", "INFO"), got)
        self.assertIn(("REV-016", "INFO"), got)

    def test_ostrom_included(self):
        r = deepcopy(GOOD)
        r["ostrom"]["nesting"] = "missing"
        self.assertIn("OST-002", codes(check_review(r)))


class Audit(unittest.TestCase):
    def test_healthy(self):
        f = audit(HEALTHY)
        self.assertEqual(verdict([x for x in f if x.severity != "INFO"]), "healthy")

    def test_weak(self):
        got = set(codes(audit(DWEAK)))
        for c in ("THR-002", "THR-003", "THR-004", "THR-005", "THR-006", "THR-007"):
            self.assertIn(c, got)
        self.assertEqual(verdict(audit(DWEAK)), "unhealthy")

    def test_nothing_adopted(self):
        self.assertEqual(codes(audit({"system": "s", "adopted": []})), ["THR-001"])

    def test_review_date_passed(self):
        d = deepcopy(HEALTHY)
        d["as_of"] = "2027-02-01"
        self.assertIn("THR-008", codes(audit(d)))

    def test_f5_satisfies_integration(self):
        d = deepcopy(HEALTHY)
        for lid in ("F1", "F5"):
            d["adopted"].append({"id": lid, "layer": "governance", "owner": "o", "merged": "2026-10-01",
                                 "test": "t", "review_date": "2027-01-01"})
        self.assertNotIn("THR-006", codes(audit(d)))

    def test_lowercase_id_accepted(self):
        d = deepcopy(HEALTHY)
        d["adopted"][0]["id"] = "m1"
        self.assertNotIn("THR-002", codes(audit(d)))

    def test_malformed(self):
        with self.assertRaises(ValueError):
            audit({"adopted": []})
        with self.assertRaises(ValueError):
            audit({"system": "s", "adopted": [{"id": "M1", "layer": "vibes"}]})

    def test_exit_codes(self):
        self.assertEqual([exit_code(v) for v in ("healthy", "needs-attention", "unhealthy", "odd")], [0, 1, 2, 2])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
