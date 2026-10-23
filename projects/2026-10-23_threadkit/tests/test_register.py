from __future__ import annotations

import unittest

from threadkit.register import GLYPHS, check_claim, parse_tagged, render_claim, standing_counts, tag
from threadkit.spec import contract_validator
from tests.support import claim, codes


class StrongLanguage(unittest.TestCase):
    """M1."""

    def test_settled_may_be_plain(self):
        self.assertEqual(check_claim(claim(text="It is certainly true that water boils at 100 C at sea level.")), [])

    def test_contested_with_proof_language(self):
        self.assertIn("REG-001", codes(check_claim(claim(standing="contested", text="Science has proven free will is an illusion."))))

    def test_bridge_with_certainly(self):
        self.assertIn("REG-001", codes(check_claim(claim(standing="bridge", text="Relation certainly precedes substance."))))

    def test_limit_and_method_checked_too(self):
        for s in ("limit", "method"):
            self.assertIn("REG-001", codes(check_claim(claim(standing=s, text="This is beyond doubt."))))

    def test_contested_plainly_attributed_is_fine(self):
        self.assertEqual(check_claim(claim(standing="contested", text="Compatibilists hold that free will survives determinism.")), [])

    def test_word_inside_another_word_not_flagged(self):
        self.assertEqual(check_claim(claim(standing="contested", text="Improvements were uncertainly measured.")), [])


class Basis(unittest.TestCase):
    """M2, M5."""

    def test_thesis_settled(self):
        self.assertIn("REG-002", codes(check_claim(claim(basis={"kind": "author_thesis", "ref": "x"}))))

    def test_settled_on_strong_convergence(self):
        self.assertEqual(check_claim(claim(basis={"kind": "convergence", "ref": "CV1"}), convergence_grades={"CV1": "strong"}), [])

    def test_settled_on_partial_convergence(self):
        f = check_claim(claim(basis={"kind": "convergence", "ref": "CV4"}), convergence_grades={"CV4": "partial"})
        self.assertIn("REG-003", codes(f))

    def test_settled_on_unknown_convergence(self):
        self.assertIn("REG-003", codes(check_claim(claim(basis={"kind": "convergence", "ref": "CVX"}), convergence_grades={})))

    def test_established_on_partial_is_fine(self):
        self.assertEqual(check_claim(claim(standing="established", basis={"kind": "convergence", "ref": "CV4"}),
                                     convergence_grades={"CV4": "partial"}), [])


class Evidence(unittest.TestCase):
    """M7, S1."""

    def test_numeric_without_primary(self):
        self.assertIn("REG-005", codes(check_claim(claim(numeric=True, sources=[{"ref": "blog", "primary": False}]))))

    def test_numeric_with_primary(self):
        self.assertEqual(check_claim(claim(numeric=True, sources=[{"ref": "survey", "primary": True}])), [])

    def test_numeric_with_no_sources(self):
        self.assertIn("REG-005", codes(check_claim(claim(numeric=True))))

    def test_self_report_as_fact(self):
        self.assertIn("REG-006", codes(check_claim(claim(self_report=True, text="I ran the tests."))))

    def test_self_report_verified(self):
        self.assertEqual(check_claim(claim(self_report=True, text="I ran the tests.", verified_by="CI log 4411")), [])

    def test_self_report_contested_is_fine(self):
        self.assertEqual(check_claim(claim(self_report=True, standing="contested", text="I may have run the tests.")), [])


class Forecasts(unittest.TestCase):
    """K6."""

    def fc(self, **kw):
        f = {"framework": "SDT", "scope": "centralised states", "window": {"from": "2026", "to": "2036"}, "status": "not_falsified"}
        f.update(kw)
        return f

    def test_window_fine(self):
        self.assertEqual(check_claim(claim(standing="established", forecast=self.fc())), [])

    def test_date_not_window(self):
        self.assertIn("REG-007", codes(check_claim(claim(standing="established", forecast=self.fc(window={"from": "2030", "to": "2030"})))))

    def test_destiny_language(self):
        f = check_claim(claim(standing="established", text="Collapse is inevitable.", forecast=self.fc()))
        self.assertIn(("REG-007", "HIGH"), [(x.code, x.severity) for x in f])

    def test_destiny_without_forecast_is_medium(self):
        f = check_claim(claim(standing="bridge", text="Decline is inevitable."))
        self.assertIn(("REG-007", "MEDIUM"), [(x.code, x.severity) for x in f])

    def test_not_falsified_is_not_confirmed(self):
        self.assertIn("REG-011", codes(check_claim(claim(forecast=self.fc()))))


class RiskAndLevels(unittest.TestCase):
    """A6, F1, R6, M4."""

    def test_risk_probability_without_source(self):
        r = {"frame": "coherent", "record": "elicited in tests", "probability": "high"}
        self.assertIn("REG-008", codes(check_claim(claim(standing="contested", risk=r))))

    def test_risk_with_source(self):
        r = {"frame": "coherent", "record": "elicited", "probability": "disputed", "probability_source": "forecaster survey"}
        self.assertEqual(check_claim(claim(standing="contested", risk=r)), [])

    def test_foundational_settled(self):
        self.assertIn("REG-009", codes(check_claim(claim(level="foundational"))))

    def test_practical_settled_fine(self):
        self.assertEqual(check_claim(claim(level="practical")), [])

    def test_disagreement_asserted(self):
        self.assertIn("REG-012", codes(check_claim(claim(standing="established", disagreement_ref="PD4"))))

    def test_behaviour_level_without_others(self):
        f = check_claim(claim(behaviour_level="weights"))
        self.assertEqual([(x.code, x.severity) for x in f], [("REG-010", "INFO")])

    def test_behaviour_level_with_others(self):
        self.assertEqual(check_claim(claim(behaviour_level="weights", assumptions_other_levels="the prompt was fixed")), [])


class Rendering(unittest.TestCase):
    def test_glyphs(self):
        self.assertEqual(render_claim(claim()), GLYPHS["settled"] + " The sky is blue at noon on a clear day.")

    def test_ascii(self):
        self.assertTrue(render_claim(claim(standing="contested"), ascii_only=True).startswith("[contested] "))

    def test_unknown_standing(self):
        with self.assertRaises(ValueError):
            tag("certain")

    def test_parse_glyphs_and_tags(self):
        text = GLYPHS["contested"] + " one\n[limit] two\nthree\n\n" + GLYPHS["bridge"] + "four"
        self.assertEqual(parse_tagged(text), [("contested", "one"), ("limit", "two"), (None, "three"), ("bridge", "four")])

    def test_counts(self):
        c = standing_counts([claim(), claim(standing="limit"), claim()])
        self.assertEqual((c["settled"], c["limit"], c["bridge"]), (2, 1, 0))

    def test_claim_contract(self):
        self.assertEqual(contract_validator("claim").errors(claim(rung=None, level="practical")), [])

    def test_claim_contract_rejects_unknown_standing(self):
        self.assertTrue(contract_validator("claim").errors(claim(standing="certain")))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
