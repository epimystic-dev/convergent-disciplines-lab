"""Debiasing, reciprocity, reputation, commons and consensus."""

from __future__ import annotations

import random
import unittest

from threadkit.consensus import tally
from threadkit.cooperation import (COOPERATE, DEFECT, MAX_GENEROSITY, LineageReputation, ReciprocityAgent,
                                   check_policy, ostrom_audit, play)
from threadkit.debias import check as check_decision, natural_frequency
from threadkit.spec import contract_validator
from tests.support import codes, deepcopy, load_example

POLICY = load_example("agent_policy.json")


class Decisions(unittest.TestCase):
    """S8."""

    def test_good(self):
        self.assertEqual(check_decision(load_example("decision_good.json")), [])

    def test_weak(self):
        got = codes(check_decision(load_example("decision_weak.json")))
        for c in ("DEB-001", "DEB-002", "DEB-003", "DEB-004"):
            self.assertIn(c, got)

    def test_self_check_is_high(self):
        f = [x for x in check_decision(load_example("decision_weak.json")) if x.code == "DEB-004"]
        self.assertEqual(f[0].severity, "HIGH")

    def test_low_stakes_light_touch(self):
        r = {"id": "r", "decision": "pick a font", "stakes": "low", "decided_by": "me"}
        self.assertEqual(check_decision(r), [])

    def test_low_stakes_estimate_is_info(self):
        r = {"id": "r", "decision": "x", "stakes": "low", "decided_by": "me", "estimate": "a day"}
        self.assertEqual([(f.code, f.severity) for f in check_decision(r)], [("DEB-001", "INFO")])

    def test_contracts(self):
        v = contract_validator("decision-record")
        for n in ("decision_good.json", "decision_weak.json"):
            self.assertEqual(v.errors(load_example(n)), [])


class Frequencies(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(natural_frequency(0.03), "about 3 in 100")

    def test_rare(self):
        self.assertEqual(natural_frequency(0.0004), "about 4 in 10000")

    def test_bounds(self):
        with self.assertRaises(ValueError):
            natural_frequency(1.5)
        with self.assertRaises(ValueError):
            natural_frequency(0.5, n=0)


class Policy(unittest.TestCase):
    """K1."""

    def test_example_policy(self):
        self.assertEqual(check_policy(POLICY), [])
        self.assertEqual(contract_validator("agent-policy").errors(POLICY), [])

    def test_each_property(self):
        for key, value, code in (("nice", False, "COOP-001"), ("provokable", False, "COOP-002"),
                                 ("forgive_after", 0, "COOP-002"), ("forgive_after", 5, "COOP-003"),
                                 ("published", False, "COOP-004"), ("log_violations", False, "COOP-005")):
            p = dict(POLICY)
            p[key] = value
            self.assertIn(code, codes(check_policy(p)), key)

    def test_tit_for_tat_behaviour(self):
        a = ReciprocityAgent(POLICY)
        b = ReciprocityAgent(dict(POLICY, provokable=False))   # a cooperator, forced to defect once
        moves = play(a, b, 6, b_override={2: DEFECT})
        self.assertEqual(moves[0], (COOPERATE, COOPERATE))
        self.assertEqual(moves[2][0], DEFECT)                    # provokable: answers the breach
        self.assertEqual([m[0] for m in moves[3:]], [COOPERATE] * 3)  # forgiving afterwards
        self.assertEqual(a.violations, [{"round": 2, "move": DEFECT}])

    def test_tit_for_tat_pair_echoes(self):
        """Two strict reciprocators echo a single defection: the known cost of forgive_after=1 without generosity."""
        a, b = ReciprocityAgent(POLICY), ReciprocityAgent(POLICY)
        moves = play(a, b, 6, b_override={2: DEFECT})
        self.assertIn(DEFECT, [m[0] for m in moves[3:]])

    def test_not_nice(self):
        p = dict(POLICY, nice=False)
        self.assertEqual(ReciprocityAgent(p).respond(None), DEFECT)

    def test_unprovokable_absorbs(self):
        a = ReciprocityAgent(dict(POLICY, provokable=False))
        a.respond(None)
        self.assertEqual(a.respond(DEFECT), COOPERATE)

    def test_generosity_breaks_echo(self):
        """Two generous reciprocators (generosity=1.0) do not echo a single defection."""
        p = dict(POLICY, generosity=0.5)
        a = ReciprocityAgent(dict(p, generosity=1.0))
        b = ReciprocityAgent(dict(p, generosity=1.0))
        moves = play(a, b, 6, b_override={2: DEFECT})
        self.assertEqual([m[0] for m in moves[3:]], [COOPERATE] * 3)
        self.assertEqual([m[1] for m in moves[3:]], [COOPERATE] * 3)
        self.assertEqual(a.violations, [{"round": 2, "move": DEFECT}])

    def test_generosity_zero_is_strict(self):
        """generosity=0.0 is identical to the strict tit-for-tat policy."""
        strict = ReciprocityAgent(POLICY)
        gen_zero = ReciprocityAgent(dict(POLICY, generosity=0.0), rng=random.Random(1))
        for last in (None, DEFECT, COOPERATE, DEFECT, COOPERATE, COOPERATE):
            self.assertEqual(strict.respond(last), gen_zero.respond(last))

    def test_generosity_default_absent(self):
        """A policy without a `generosity` key behaves identically to generosity=0.0."""
        a = ReciprocityAgent(POLICY, rng=random.Random(0))
        b = ReciprocityAgent(POLICY, rng=random.Random(0))
        moves = play(a, b, 6, b_override={2: DEFECT})
        self.assertIn(DEFECT, [m[0] for m in moves[3:]])

    def test_generosity_is_deterministic_under_seed(self):
        """The injected rng makes generous play reproducible for audit."""
        p = dict(POLICY, generosity=0.5)
        first = play(ReciprocityAgent(p, rng=random.Random(42)),
                     ReciprocityAgent(p, rng=random.Random(42)),
                     8, b_override={2: DEFECT, 5: DEFECT})
        second = play(ReciprocityAgent(p, rng=random.Random(42)),
                      ReciprocityAgent(p, rng=random.Random(42)),
                      8, b_override={2: DEFECT, 5: DEFECT})
        self.assertEqual(first, second)

    def test_generosity_cap(self):
        """Generosity above MAX_GENEROSITY is flagged (unprovokable in expectation)."""
        p = dict(POLICY, generosity=MAX_GENEROSITY + 0.1)
        self.assertIn("COOP-006", codes(check_policy(p)))
        p_ok = dict(POLICY, generosity=MAX_GENEROSITY)
        self.assertNotIn("COOP-006", codes(check_policy(p_ok)))

    def test_generosity_passes_schema(self):
        from threadkit.spec import contract_validator
        v = contract_validator("agent-policy")
        self.assertEqual(v.errors(dict(POLICY, generosity=0.1)), [])
        self.assertNotEqual(v.errors(dict(POLICY, generosity=1.5)), [])


class Reputation(unittest.TestCase):
    """K2."""

    def test_fork_inherits(self):
        r = LineageReputation()
        r.register("base")
        r.record("base", "open safety finding")
        r.fork("base", "base-v2")
        self.assertEqual(r.open_findings("base-v2"), ["open safety finding"])

    def test_merge_inherits_all(self):
        r = LineageReputation()
        r.register("a")
        r.register("b")
        r.record("a", "f1")
        r.record("b", "f2")
        r.merge(["a", "b"], "ab")
        self.assertEqual(sorted(r.open_findings("ab")), ["f1", "f2"])

    def test_rename_does_not_launder(self):
        r = LineageReputation()
        r.register("old")
        r.record("old", "f")
        r.register("new-name")
        self.assertEqual(r.open_findings("new-name"), [])
        self.assertFalse(r.known("unregistered"))
        with self.assertRaises(ValueError):
            r.record("unregistered", "x")

    def test_close_after_reaudit(self):
        r = LineageReputation()
        r.register("a")
        r.record("a", "f")
        r.fork("a", "b")
        r.close("b", "f")
        self.assertEqual(r.open_findings("b"), [])
        self.assertEqual(r.open_findings("a"), ["f"])

    def test_merge_needs_two(self):
        r = LineageReputation()
        r.register("a")
        with self.assertRaises(ValueError):
            r.merge(["a", "a"], "c")

    def test_unknown_parent(self):
        with self.assertRaises(ValueError):
            LineageReputation().fork("nope", "child")


class Commons(unittest.TestCase):
    """K3."""

    def test_all_met(self):
        self.assertEqual(ostrom_audit(load_example("review_good.json")["ostrom"]), [])

    def test_missing_and_partial(self):
        f = ostrom_audit({"boundaries": "missing", "nesting": "partial"})
        self.assertIn("OST-002", codes(f))
        self.assertIn("OST-003", codes(f))
        self.assertEqual(codes(f).count("OST-001"), 6)


class Consensus(unittest.TestCase):
    """A5."""

    def test_copies_outvoted(self):
        t = tally(load_example("consensus_copies.json"))
        self.assertEqual((t.raw_winner, t.lineage_winner, t.independent_witnesses), ("yes", "no", 3))
        self.assertEqual(sorted(codes(t.findings)), ["CNS-001", "CNS-002"])

    def test_one_lineage_is_one_witness(self):
        rec = {"question": "q", "votes": [{"agent": "a%d" % i, "lineage": "x", "answer": "yes"} for i in range(5)],
               "diversity_attestation": {"by": "auditor"}}
        t = tally(rec)
        self.assertEqual(t.independent_witnesses, 1)
        self.assertEqual(codes(t.findings), ["CNS-003"])

    def test_attested_diverse_agreement(self):
        rec = {"question": "q", "votes": [{"agent": "a", "lineage": "x", "answer": "yes"},
                                          {"agent": "b", "lineage": "y", "answer": "yes"}],
               "diversity_attestation": {"by": "auditor"}}
        self.assertEqual(tally(rec).findings, [])

    def test_split_lineage_abstains(self):
        rec = {"question": "q", "votes": [{"agent": "a", "lineage": "x", "answer": "yes"},
                                          {"agent": "b", "lineage": "x", "answer": "no"},
                                          {"agent": "c", "lineage": "y", "answer": "no"}],
               "diversity_attestation": {"by": "auditor"}}
        t = tally(rec)
        self.assertEqual(t.lineage_winner, "no")
        self.assertIn("CNS-004", codes(t.findings))

    def test_contract(self):
        self.assertEqual(contract_validator("consensus").errors(load_example("consensus_copies.json")), [])

    def test_to_dict(self):
        self.assertEqual(tally(deepcopy(load_example("consensus_copies.json"))).to_dict()["independent_witnesses"], 3)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
