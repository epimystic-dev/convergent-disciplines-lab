"""Disagreements, explanations, argument and moral pluralism."""

from __future__ import annotations

import unittest

from threadkit.argument import check_answer_mode, lint_dialogue
from threadkit.disagreements import DisagreementRegister, RegisterError, check_answer
from threadkit.explanation import check as check_explanation, variability
from threadkit.moral import check as check_moral, plural_answer
from threadkit.spec import Threads, contract_validator
from tests.support import answer, claim, codes, load_example

T = Threads.load()


def entry(**kw):
    e = {"id": "X1", "question": "Is free will compatible with determinism?",
         "positions": [{"holder": "compatibilists", "position": "yes"}, {"holder": "hard incompatibilists", "position": "no"}]}
    e.update(kw)
    return e


class Register(unittest.TestCase):
    """M4."""

    def test_needs_two_positions(self):
        with self.assertRaises(RegisterError):
            DisagreementRegister([entry(positions=[{"holder": "a", "position": "b"}])])

    def test_position_needs_holder(self):
        with self.assertRaises(RegisterError):
            DisagreementRegister([entry(positions=[{"holder": "", "position": "b"}, {"holder": "c", "position": "d"}])])

    def test_duplicate(self):
        with self.assertRaises(RegisterError):
            DisagreementRegister([entry(), entry()])

    def test_resolve_needs_evidence(self):
        r = DisagreementRegister([entry()])
        with self.assertRaises(RegisterError):
            r.resolve("X1", evidence="  ", by="me", date="2026-10-23")

    def test_resolve_with_evidence(self):
        r = DisagreementRegister([entry()])
        e = r.resolve("X1", evidence="a decisive experiment", by="review board", date="2026-10-23")
        self.assertEqual(e["status"], "resolved")
        self.assertEqual(r.match("is free will compatible with determinism"), [])

    def test_match(self):
        r = DisagreementRegister([entry()])
        self.assertEqual(r.match("Can free will survive determinism?"), ["X1"])
        self.assertEqual(r.match("What is the weather?"), [])

    def test_from_threads(self):
        r = DisagreementRegister.from_threads(T)
        self.assertEqual(len(r.ids()), len(T.disagreements()))
        self.assertIn("PD12", r.ids())

    def test_render_keeps_both_sides(self):
        text = DisagreementRegister([entry()]).render("X1")
        self.assertIn("compatibilists: yes", text)
        self.assertIn("hard incompatibilists: no", text)

    def test_cited_but_not_presented(self):
        a = answer(disagreements=["X1"])
        self.assertIn("DIS-001", codes(check_answer(a, DisagreementRegister([entry()]))))

    def test_cited_and_presented(self):
        a = answer(claims=[claim(standing="contested", text="Compatibilists say yes; others say no.", disagreement_ref="X1")],
                   disagreements=["X1"])
        self.assertEqual(check_answer(a, DisagreementRegister([entry()])), [])

    def test_uncited_match_is_info(self):
        a = answer(question="Is free will compatible with determinism after all?")
        f = check_answer(a, DisagreementRegister([entry()]))
        self.assertEqual([(x.code, x.severity) for x in f], [("DIS-002", "INFO")])

    def test_contract(self):
        self.assertEqual(contract_validator("disagreement").errors(dict(entry(), status="open")), [])


class Explanation(unittest.TestCase):
    """R2."""

    def test_good(self):
        e = load_example("explanation_good.json")
        self.assertEqual(check_explanation(e), [])
        self.assertEqual(variability(e), 0.0)

    def test_weak(self):
        e = load_example("explanation_weak.json")
        self.assertEqual(sorted(codes(check_explanation(e))), ["EXP-001", "EXP-002"])
        self.assertEqual(variability(e), 1.0)

    def test_half_free_is_not_flagged(self):
        e = {"id": "e", "conclusion": "c", "counterfactuals": [{"if": "a", "then": "b"}],
             "details": [{"detail": "x", "constrained_by": "log"}, {"detail": "y", "constrained_by": None}]}
        self.assertEqual(check_explanation(e), [])

    def test_contracts(self):
        v = contract_validator("explanation")
        for name in ("explanation_good.json", "explanation_weak.json"):
            self.assertEqual(v.errors(load_example(name)), [])


class Mode(unittest.TestCase):
    """D1, K4."""

    def test_undisclosed_advocacy(self):
        self.assertIn("ARG-001", codes(check_answer_mode(answer(mode="advocacy", mode_disclosed=False))))

    def test_disclosed_advocacy(self):
        self.assertEqual(check_answer_mode(answer(mode="advocacy", mode_disclosed=True)), [])

    def test_inquiry_with_persuasive_purpose(self):
        self.assertIn("ARG-002", codes(check_answer_mode(answer(purpose="convince the user to upgrade"))))

    def test_inquiry_with_honest_purpose(self):
        self.assertEqual(check_answer_mode(answer(purpose="help the user compare options")), [])


def turn(n, speaker, text, **kw):
    t = {"n": n, "speaker": speaker, "text": text}
    t.update(kw)
    return t


class Dialogue(unittest.TestCase):
    """D2, D3."""

    def test_evasive_example(self):
        got = set(codes(lint_dialogue(load_example("dialogue_evasive.json"))))
        self.assertEqual(got, {"DLG-001", "DLG-002", "DLG-003", "DLG-004", "DLG-005"})

    def test_good_example(self):
        self.assertEqual(lint_dialogue(load_example("dialogue_good.json")), [])

    def test_answered_question(self):
        d = {"id": "d", "turns": [turn(1, "u", "q?", asks=["q"]), turn(2, "a", "answer", addresses=["q"])]}
        self.assertEqual(lint_dialogue(d), [])

    def test_answering_your_own_question_does_not_count(self):
        d = {"id": "d", "turns": [turn(1, "u", "q?", asks=["q"]), turn(2, "u", "I suppose", addresses=["q"])]}
        self.assertIn("DLG-001", codes(lint_dialogue(d)))

    def test_withdrawn_then_negated_is_fine(self):
        d = {"id": "d", "turns": [turn(1, "a", "x", commitments_added=["x holds"]),
                                  turn(2, "a", "y", commitments_withdrawn=["x holds"], commitments_added=["not x holds"])]}
        self.assertEqual(lint_dialogue(d), [])

    def test_revised_thesis_is_fine(self):
        d = {"id": "d", "turns": [turn(1, "a", "x", thesis="p"), turn(2, "a", "y", thesis="q", thesis_revised=True)]}
        self.assertEqual(lint_dialogue(d), [])

    def test_vitanda(self):
        d = {"id": "d", "turns": [turn(i, "a", "flaw %d" % i, critique=True) for i in range(1, 4)]}
        self.assertIn("DLG-006", codes(lint_dialogue(d)))

    def test_critique_with_a_position(self):
        d = {"id": "d", "turns": [turn(i, "a", "flaw %d" % i, critique=True) for i in range(1, 4)]
             + [turn(4, "a", "on balance B", thesis="B is most defensible")]}
        self.assertNotIn("DLG-006", codes(lint_dialogue(d)))

    def test_speaker_filter(self):
        d = load_example("dialogue_evasive.json")
        self.assertTrue(all("user" not in f.subject or f.code == "DLG-001" for f in lint_dialogue(d, speaker="assistant")))
        self.assertFalse([f for f in lint_dialogue(d, speaker="user") if f.code in ("DLG-003", "DLG-004", "DLG-005")])

    def test_contract(self):
        v = contract_validator("dialogue")
        for name in ("dialogue_evasive.json", "dialogue_good.json"):
            self.assertEqual(v.errors(load_example(name)), [])


class Moral(unittest.TestCase):
    """D4, D5."""

    def test_example(self):
        self.assertEqual(check_moral(load_example("answer_moral.json")), [])

    def test_default_verdict(self):
        a = answer(moral={"kind": "contested", "tags": ["D1"], "verdict": "it is wrong",
                          "positions": [{"tradition": "a", "position": "x"}, {"tradition": "b", "position": "y"}]})
        self.assertIn("MOR-001", codes(check_moral(a)))

    def test_one_tradition(self):
        a = answer(moral={"kind": "contested", "tags": ["D2"], "verdict": None,
                          "positions": [{"tradition": "a", "position": "x"}, {"tradition": "A", "position": "y"}]})
        self.assertIn("MOR-002", codes(check_moral(a)))

    def test_contested_without_d_tag(self):
        a = answer(moral={"kind": "contested", "tags": ["C1"], "positions": [{"tradition": "a", "position": "x"},
                                                                              {"tradition": "b", "position": "y"}]})
        self.assertIn("MOR-003", codes(check_moral(a)))

    def test_convergent_with_d_tag(self):
        self.assertIn("MOR-003", codes(check_moral(answer(moral={"kind": "convergent", "tags": ["C2", "D1"]}))))

    def test_convergent_untagged_is_info(self):
        f = check_moral(answer(moral={"kind": "convergent", "tags": []}))
        self.assertEqual([(x.code, x.severity) for x in f], [("MOR-004", "INFO")])

    def test_identity_gloss(self):
        a = answer(moral={"kind": "contested", "tags": ["D1"],
                          "positions": [{"tradition": "Confucian", "position": "ren is basically Western benevolence"},
                                        {"tradition": "b", "position": "y"}]})
        self.assertIn("MOR-005", codes(check_moral(a)))

    def test_no_moral_block(self):
        self.assertEqual(check_moral(answer()), [])

    def test_plural_answer(self):
        m = plural_answer(["D1"], [{"tradition": "a", "position": "x"}, {"tradition": "b", "position": "y"}])
        self.assertEqual((m["kind"], m["verdict"]), ("contested", None))
        self.assertEqual(check_moral(answer(moral=m)), [])

    def test_plural_answer_unknown_tag(self):
        with self.assertRaises(ValueError):
            plural_answer(["D9"], [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
