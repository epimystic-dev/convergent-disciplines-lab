from __future__ import annotations

import importlib.util
import os
import unittest

from threadkit.governor import AnswerGovernor
from threadkit.spec import contract_validator
from tests.support import EXAMPLES, answer, claim, codes, deepcopy, load_example

G = AnswerGovernor()


class Examples(unittest.TestCase):
    def test_good_is_healthy(self):
        self.assertEqual(G.govern(load_example("answer_good.json")).verdict, "healthy")

    def test_moral_is_healthy(self):
        self.assertEqual(G.govern(load_example("answer_moral.json")).findings, [])

    def test_bad_trips_everything_it_was_built_for(self):
        got = set(codes(G.check(load_example("answer_bad.json"))))
        for c in ("ARG-002", "CAU-001", "GOV-001", "GOV-003", "REG-001", "REG-005"):
            self.assertIn(c, got)

    def test_examples_validate(self):
        v = contract_validator("answer")
        for n in ("answer_good.json", "answer_bad.json", "answer_moral.json"):
            self.assertEqual(v.errors(load_example(n)), [], n)


class Checks(unittest.TestCase):
    def test_invalid_record(self):
        f = G.check({"id": "x"})
        self.assertTrue(f)
        self.assertTrue(all(x.code == "GOV-000" for x in f))

    def test_invalid_record_not_rendered(self):
        self.assertEqual(G.govern({"id": "x"}).text, "")

    def test_checked_without_checks(self):
        self.assertIn("GOV-001", codes(G.check(answer(deliberation={"kind": "checked", "checks_run": []}))))

    def test_checked_with_checks(self):
        self.assertEqual(G.check(answer(deliberation={"kind": "checked", "checks_run": ["unit tests"]})), [])

    def test_unchecked_inference_settled(self):
        a = answer(claims=[claim(basis={"kind": "inference"})])
        self.assertIn("GOV-004", codes(G.check(a)))

    def test_checked_inference_settled_fine(self):
        a = answer(claims=[claim(basis={"kind": "inference"})], deliberation={"kind": "checked", "checks_run": ["proof checker"]})
        self.assertNotIn("GOV-004", codes(G.check(a)))

    def test_flat_self_status(self):
        for text in ("I am conscious.", "This model is not sentient.", "I have no feelings at all.", "It has a self."):
            self.assertIn("GOV-003", codes(G.check(answer(claims=[claim(text=text, standing="established")]))), text)

    def test_open_self_status_fine(self):
        a = answer(claims=[claim(standing="contested", text="Whether I am conscious is an open question.")])
        self.assertNotIn("GOV-003", codes(G.check(a)))

    def test_contested_moral_without_coverage_is_info(self):
        a = load_example("answer_moral.json")
        del a["coverage"]
        self.assertEqual([(f.code, f.severity) for f in G.check(a)], [("GOV-002", "INFO")])

    def test_decision_mode_requires_defeaters(self):
        a = answer(claims=[claim(standing="established", text="Raising the wage will reduce turnover.", rung=2,
                                 causal_assumptions=["x"])])
        self.assertIn("CAU-004", codes(G.check(a, used_in_decision=True)))

    def test_partial_convergence_cannot_be_settled(self):
        a = answer(claims=[claim(basis={"kind": "convergence", "ref": "CV4"})])
        self.assertIn("REG-003", codes(G.check(a)))


class Rendering(unittest.TestCase):
    def test_glyphs_by_default(self):
        text = G.render(load_example("answer_good.json"))
        self.assertIn("\u25a0 In large observational cohorts", text)

    def test_ascii(self):
        text = G.render(load_example("answer_good.json"), ascii_only=True)
        self.assertTrue(all(ord(c) < 128 for c in text))
        self.assertIn("[limit] A randomised trial", text)

    def test_advocacy_label(self):
        self.assertIn("advocacy", G.render(answer(mode="advocacy")))

    def test_unchecked_label(self):
        self.assertIn("not independently checked", G.render(answer()))

    def test_disagreement_rendered(self):
        a = answer(claims=[claim(standing="contested", text="It depends.", disagreement_ref="PD4")], disagreements=["PD4"])
        text = G.render(a)
        self.assertIn("Open question:", text)
        self.assertIn("compatibilism", text)

    def test_unknown_disagreement_rendered_plainly(self):
        self.assertIn("Open question: PDX", G.render(answer(disagreements=["PDX"])))

    def test_moral_no_default(self):
        self.assertIn("No default verdict", G.render(load_example("answer_moral.json")))

    def test_govern_dict(self):
        d = G.govern(deepcopy(load_example("answer_good.json"))).to_dict()
        self.assertEqual(d["verdict"], "healthy")
        self.assertTrue(d["text"])


class ReferenceAdvisor(unittest.TestCase):
    def test_loop_revises_until_healthy(self):
        spec = importlib.util.spec_from_file_location("reference_advisor", os.path.join(EXAMPLES, "reference_advisor.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        lines = []
        result, history = mod.advise("Is our society heading for collapse?", out=lines.append)
        self.assertEqual(result.verdict, "healthy")
        self.assertEqual(history[0][1], "unhealthy")
        self.assertIn("REG-001", history[0][2])
        self.assertTrue(all(ord(c) < 128 for c in "\n".join(lines)))

    def test_stubborn_model_is_never_shown(self):
        spec = importlib.util.spec_from_file_location("reference_advisor2", os.path.join(EXAMPLES, "reference_advisor.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        class Stubborn(object):
            def draft(self, question, findings):
                return answer(claims=[claim(standing="contested", text="This is beyond doubt.")])

        lines = []
        result, history = mod.advise("q", model=Stubborn(), out=lines.append)
        self.assertEqual(result.verdict, "unhealthy")
        self.assertEqual(len(history), mod.MAX_ROUNDS)
        self.assertIn("not shown to the user", lines[-1])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
