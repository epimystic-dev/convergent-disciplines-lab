from __future__ import annotations

import unittest

from threadkit.convergence import assess, effective_witnesses
from threadkit.spec import contract_validator
from tests.support import codes, deepcopy, load_example

GOOD = load_example("convergence_relational.json")
FLAT = load_example("convergence_flattened.json")


def route(i, **kw):
    r = {"id": i, "tradition": "tradition %s" % i, "method": "method %s" % i, "distinct_content": "content %s" % i}
    r.update(kw)
    return r


def record(routes, **kw):
    d = {"id": "cv", "shape": "What is called a thing is a pattern of relation.", "routes": routes,
         "declared_grade": "strong", "falsifier": "a shared upstream source", "disagreements_preserved": ["x"],
         "independent_audit": True}
    d.update(kw)
    return d


class Grades(unittest.TestCase):
    def test_three_independent_routes_strong(self):
        self.assertEqual(assess(record([route("a"), route("b"), route("c")])).computed_grade, "strong")

    def test_two_routes_partial(self):
        a = assess(record([route("a"), route("b")], declared_grade="partial"))
        self.assertEqual(a.computed_grade, "partial")
        self.assertEqual(a.findings, [])

    def test_one_route_withdrawn(self):
        self.assertEqual(assess(record([route("a")], declared_grade="withdrawn")).computed_grade, "withdrawn")

    def test_upstream_link_collapses_routes(self):
        a = assess(record([route("a"), route("b"), route("c")],
                          upstream_links=[{"between": ["a", "b"], "kind": "shared_lineage"}]))
        self.assertEqual(a.independent_routes, 2)
        self.assertIn("CON-001", codes(a.findings))

    def test_chain_of_links(self):
        a = assess(record([route("a"), route("b"), route("c"), route("d")],
                          upstream_links=[{"between": ["a", "b"], "kind": "active_dialogue"},
                                          {"between": ["b", "c"], "kind": "shared_forum"}]))
        self.assertEqual(a.clusters, [["a", "b", "c"], ["d"]])

    def test_shared_method_counts_as_one(self):
        a = assess(record([route("a", method="survey"), route("b", method="Survey"), route("c")]))
        self.assertEqual(a.independent_routes, 2)
        self.assertIn("CON-009", codes(a.findings))

    def test_shared_cosmology_counts_as_one(self):
        a = assess(record([route("a", cosmology="theistic"), route("b", cosmology="theistic"), route("c")]))
        self.assertEqual(a.independent_routes, 2)

    def test_selection_is_thesis(self):
        a = assess(record([route("a"), route("b"), route("c")], selection_is_choice=True))
        self.assertEqual(a.computed_grade, "author_thesis")
        self.assertIn("CON-001", codes(a.findings))

    def test_owning_as_thesis_is_always_allowed(self):
        a = assess(record([route("a"), route("b"), route("c")], declared_grade="author_thesis"))
        self.assertNotIn("CON-001", codes(a.findings))

    def test_declaring_lower_is_allowed(self):
        self.assertNotIn("CON-001", codes(assess(record([route("a"), route("b"), route("c")], declared_grade="partial")).findings))


class AntiCapra(unittest.TestCase):
    """M3."""

    def test_identity_shape(self):
        a = assess(record([route("a"), route("b"), route("c")], shape="Physics is just mysticism in other words."))
        self.assertIn("CON-003", codes(a.findings))
        self.assertEqual(a.computed_grade, "withdrawn")

    def test_one_insight_in_many_words(self):
        self.assertIn("CON-003", codes(assess(record([route("a"), route("b")],
                                                     shape="One truth in many vocabularies.")).findings))

    def test_duplicate_content(self):
        a = assess(record([route("a", distinct_content="all is one"), route("b", distinct_content="All is  one"), route("c")]))
        self.assertIn("CON-002", codes(a.findings))
        self.assertEqual(a.computed_grade, "withdrawn")

    def test_shape_in_one_routes_vocabulary(self):
        a = assess(record([route("a", tradition="Madhyamaka"), route("b"), route("c")],
                          shape="Madhyamaka emptiness holds everywhere."))
        self.assertIn("CON-004", codes(a.findings))

    def test_citation_artefact_dropped(self):
        a = assess(record([route("a"), route("b"), route("c")],
                          upstream_links=[{"between": ["a", "b"], "kind": "citation_artefact"}]))
        self.assertIn("CON-007", codes(a.findings))


class Discipline(unittest.TestCase):
    def test_no_disagreements_recorded(self):
        self.assertIn("CON-005", codes(assess(record([route("a"), route("b")], declared_grade="partial",
                                                     disagreements_preserved=[])).findings))

    def test_construction_bias_caveat(self):
        self.assertIn("CON-008", codes(assess(record([route("a")], declared_grade="withdrawn", independent_audit=False)).findings))

    def test_unknown_route_in_link(self):
        with self.assertRaises(ValueError):
            assess(record([route("a"), route("b")], upstream_links=[{"between": ["a", "z"], "kind": "shared_lineage"}]))

    def test_duplicate_route_ids(self):
        with self.assertRaises(ValueError):
            assess(record([route("a"), route("a")]))


class Examples(unittest.TestCase):
    def test_good_example(self):
        a = assess(GOOD)
        self.assertEqual(a.computed_grade, "strong")
        self.assertEqual([f.severity for f in a.findings], ["INFO"])

    def test_influence_noted_reduces_count(self):
        self.assertEqual(assess(GOOD).independent_routes, 3)

    def test_flattened_example(self):
        a = assess(FLAT)
        self.assertEqual(a.computed_grade, "withdrawn")
        for code in ("CON-001", "CON-002", "CON-003"):
            self.assertIn(code, codes(a.findings))

    def test_examples_validate(self):
        v = contract_validator("convergence")
        self.assertEqual(v.errors(GOOD), [])
        self.assertEqual(v.errors(FLAT), [])

    def test_assessment_dict(self):
        d = assess(deepcopy(GOOD)).to_dict()
        self.assertEqual(d["independent_routes"], 3)

    def test_effective_witnesses(self):
        self.assertEqual(effective_witnesses(["a", "A", "b", " b ", ""]), 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
