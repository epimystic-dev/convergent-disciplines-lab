"""The worked critic-search example in docs/WORKED-CONVERGENCE-AUDIT.md.

Both records (before and after the critic finds the shared upstream dialogue) are kept honest
by asserting the exact audit outcomes the doc describes. If the convergence assessor is changed
in a way that moves either ceiling, this test fails together with the doc that cites it.
"""

from __future__ import annotations

import unittest

from threadkit.convergence import assess
from threadkit.spec import contract_validator
from tests.support import codes, load_example

BEFORE = load_example("convergence_before_critic.json")
AFTER = load_example("convergence_after_critic.json")


class CriticSearchWorkedExample(unittest.TestCase):
    def test_both_records_validate(self):
        v = contract_validator("convergence")
        self.assertEqual(v.errors(BEFORE), [])
        self.assertEqual(v.errors(AFTER), [])

    def test_before_critic_sees_three_independent_routes(self):
        a = assess(BEFORE)
        self.assertEqual(a.independent_routes, 3)
        self.assertEqual(a.clusters, [["r-ai-safety"], ["r-planetary"], ["r-precaution"]])

    def test_before_critic_ceiling_is_strong(self):
        a = assess(BEFORE)
        self.assertEqual(a.computed_grade, "strong")
        self.assertEqual(a.declared_grade, "strong")

    def test_before_critic_no_high_or_medium_findings(self):
        severities = {f.severity for f in assess(BEFORE).findings}
        self.assertNotIn("HIGH", severities)
        self.assertNotIn("MEDIUM", severities)

    def test_before_critic_only_construction_bias_caveat_remains(self):
        self.assertEqual(codes(assess(BEFORE).findings), ["CON-008"])

    def test_after_critic_collapses_the_two_in_dialogue(self):
        a = assess(AFTER)
        self.assertEqual(a.independent_routes, 2)
        self.assertEqual(a.clusters, [["r-ai-safety", "r-planetary"], ["r-precaution"]])

    def test_after_critic_ceiling_drops_to_partial(self):
        self.assertEqual(assess(AFTER).computed_grade, "partial")

    def test_after_critic_flags_declared_above_ceiling(self):
        a = assess(AFTER)
        high = [f for f in a.findings if f.severity == "HIGH"]
        self.assertEqual([f.code for f in high], ["CON-001"])
        self.assertEqual(high[0].lesson, "M2")

    def test_only_the_upstream_link_differs(self):
        self.assertEqual(BEFORE["routes"], AFTER["routes"])
        self.assertEqual(BEFORE["shape"], AFTER["shape"])
        self.assertEqual(BEFORE["declared_grade"], AFTER["declared_grade"])
        self.assertNotIn("upstream_links", BEFORE)
        self.assertEqual([link["kind"] for link in AFTER["upstream_links"]], ["active_dialogue"])

    def test_lowering_the_declared_grade_clears_the_high_finding(self):
        audited = dict(AFTER)
        audited["declared_grade"] = "partial"
        self.assertNotIn("CON-001", codes(assess(audited).findings))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
