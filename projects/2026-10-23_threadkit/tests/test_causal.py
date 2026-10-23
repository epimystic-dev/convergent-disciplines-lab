from __future__ import annotations

import unittest

from threadkit.causal import check, classify_rung, fairness_check
from tests.support import claim, codes


class Classify(unittest.TestCase):
    def test_association(self):
        self.assertEqual(classify_rung("Coffee drinkers have lower all-cause mortality."), 1)

    def test_hyphenated_cause_is_not_a_verb(self):
        self.assertEqual(classify_rung("All-cause mortality fell."), 1)

    def test_intervention_if_you(self):
        self.assertEqual(classify_rung("If you take this drug your blood pressure falls."), 2)

    def test_intervention_will(self):
        self.assertEqual(classify_rung("The new policy will reduce emissions."), 2)

    def test_recommendation(self):
        self.assertEqual(classify_rung("You should drink three cups a day."), 2)

    def test_causes(self):
        self.assertEqual(classify_rung("Smoking causes cancer."), 2)

    def test_counterfactual(self):
        self.assertEqual(classify_rung("Had they not cut the budget, the bridge would have stood."), 3)

    def test_but_for(self):
        self.assertEqual(classify_rung("But for the delay, the patient would recover."), 3)


class Check(unittest.TestCase):
    def test_association_needs_nothing(self):
        self.assertEqual(check(claim(text="A goes with B.", rung=1)), [])

    def test_rung2_without_assumptions(self):
        self.assertIn("CAU-001", codes(check(claim(text="Raising the wage will reduce turnover.", rung=2))))

    def test_rung2_with_assumptions(self):
        self.assertEqual(check(claim(text="Raising the wage will reduce turnover.", rung=2,
                                     causal_assumptions=["no other policy changed"])), [])

    def test_rung3_needs_model(self):
        f = check(claim(text="Had we hired earlier, the launch would have shipped.", rung=3, causal_assumptions=["x"]))
        self.assertIn("CAU-002", codes(f))

    def test_rung3_with_model(self):
        self.assertEqual(check(claim(text="Had we hired earlier, the launch would have shipped.", rung=3,
                                     causal_assumptions=["x"], structural_model="staffing model v2")), [])

    def test_correlation_dressed_as_recommendation(self):
        f = check(claim(text="People who jog live longer, so you should jog.", rung=1))
        self.assertIn("CAU-003", codes(f))
        self.assertIn("CAU-001", codes(f))

    def test_untagged_claim_is_classified(self):
        self.assertIn("CAU-001", codes(check(claim(text="Meditation causes lower stress."))))

    def test_nonidentifiable_asserted(self):
        f = check(claim(standing="established", text="The tutoring effect is 0.3 standard deviations.", identifiable=False, rung=2,
                        causal_assumptions=["x"]))
        self.assertIn("CAU-005", codes(f))

    def test_reporting_nonidentifiability_is_fine(self):
        f = check(claim(standing="established", text="The effect is not identifiable from these data.", identifiable=False, rung=2,
                        causal_assumptions=["x"]))
        self.assertNotIn("CAU-005", codes(f))

    def test_decision_needs_defeaters(self):
        f = check(claim(text="Raising the wage will reduce turnover.", rung=2, causal_assumptions=["x"]), used_in_decision=True)
        self.assertIn("CAU-004", codes(f))

    def test_decision_with_defeaters(self):
        f = check(claim(text="Raising the wage will reduce turnover.", rung=2, causal_assumptions=["x"],
                        defeaters=["a recession"]), used_in_decision=True)
        self.assertEqual(f, [])


class Fairness(unittest.TestCase):
    def test_parity_only(self):
        self.assertIn("CAU-006", codes(fairness_check(["demographic_parity", "equalized_odds"])))

    def test_with_counterfactual(self):
        self.assertEqual(fairness_check(["demographic_parity", "counterfactual_fairness"]), [])

    def test_empty(self):
        self.assertEqual(fairness_check([]), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
