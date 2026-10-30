from __future__ import annotations

import json
import unittest

from threadkit.adapter import (Adapted, Repair, adapt, extract_json_block,
                               govern_free_text, permissive_loads, repair_answer)
from tests.support import answer, claim


class ExtractJsonBlock(unittest.TestCase):
    def test_bare_object_round_trips(self):
        s = "{\n  \"id\": \"a\"\n}"
        self.assertEqual(extract_json_block(s), s)

    def test_fenced_block_is_unwrapped(self):
        s = "```json\n{\"id\": \"a\"}\n```"
        self.assertEqual(extract_json_block(s), "{\"id\": \"a\"}")

    def test_fenced_block_without_language_tag(self):
        s = "```\n{\"id\": \"a\"}\n```"
        self.assertEqual(extract_json_block(s), "{\"id\": \"a\"}")

    def test_preamble_before_object_is_dropped(self):
        s = "Here is the answer record you asked for:\n\n{\"id\": \"a\", \"n\": 1}"
        self.assertEqual(extract_json_block(s), "{\"id\": \"a\", \"n\": 1}")

    def test_trailing_commentary_after_closing_brace_is_dropped(self):
        s = "{\"id\": \"a\"}\n\nLet me know if you want revisions."
        self.assertEqual(extract_json_block(s), "{\"id\": \"a\"}")

    def test_braces_inside_strings_are_ignored(self):
        s = "{\"text\": \"a } with braces { inside a string\"}"
        self.assertEqual(extract_json_block(s), s)

    def test_nested_objects_walked(self):
        s = "{\"a\": {\"b\": {\"c\": 1}}}"
        self.assertEqual(extract_json_block(s), s)

    def test_text_without_braces_returned_stripped(self):
        self.assertEqual(extract_json_block("  no JSON here\n"), "no JSON here")

    def test_preamble_example_does_not_shadow_record(self):
        """A JSON-ish example in prose preamble must not be returned in place of the real
        record. The record (the LAST top-level balanced block) wins.
        """
        s = "Example: {\"k\": 1}. Record: {\"id\": \"a\"}"
        self.assertEqual(extract_json_block(s), "{\"id\": \"a\"}")

    def test_two_balanced_siblings_last_wins(self):
        s = "{\"first\": 1} {\"second\": 2}"
        self.assertEqual(extract_json_block(s), "{\"second\": 2}")

    def test_balanced_then_unterminated_balanced_wins(self):
        """A trailing unterminated block (e.g. a truncated response after an inline example)
        does not override a prior balanced block - we return something a parser can accept.
        """
        s = "{\"ok\": 1} {\"never-closed\":"
        self.assertEqual(extract_json_block(s), "{\"ok\": 1}")

    def test_only_unterminated_returns_tail(self):
        s = "prefix {\"never-closed\":"
        self.assertEqual(extract_json_block(s), "{\"never-closed\":")


class PermissiveLoads(unittest.TestCase):
    def test_strict_json_passes_through(self):
        self.assertEqual(permissive_loads("{\"a\": 1, \"b\": [1, 2]}"), {"a": 1, "b": [1, 2]})

    def test_python_literals_are_translated(self):
        got = permissive_loads("{\"a\": True, \"b\": False, \"c\": None}")
        self.assertEqual(got, {"a": True, "b": False, "c": None})

    def test_python_literals_in_strings_are_not_touched(self):
        got = permissive_loads("{\"note\": \"None of the above\", \"flag\": True}")
        self.assertEqual(got["note"], "None of the above")
        self.assertIs(got["flag"], True)

    def test_trailing_comma_in_object(self):
        self.assertEqual(permissive_loads("{\"a\": 1,}"), {"a": 1})

    def test_trailing_comma_in_array(self):
        self.assertEqual(permissive_loads("{\"xs\": [1, 2, 3,]}"), {"xs": [1, 2, 3]})

    def test_unparseable_input_raises_valueerror(self):
        with self.assertRaises(ValueError) as cm:
            permissive_loads("{not: json at all")
        self.assertIn("could not parse", str(cm.exception))

    def test_unparseable_without_python_or_commas_still_raises(self):
        with self.assertRaises(ValueError):
            permissive_loads("{\"a\": 1 \"b\": 2}")


class RepairAnswer(unittest.TestCase):
    def test_non_dict_passes_through_without_repairs(self):
        rec, reps = repair_answer("just a string")
        self.assertEqual(rec, "just a string")
        self.assertEqual(reps, [])

    def test_clean_record_is_not_mutated_and_no_repairs(self):
        orig = answer(claims=[claim()])
        rec, reps = repair_answer(orig)
        self.assertEqual(reps, [])
        self.assertEqual(rec, orig)
        rec["id"] = "mutated"
        self.assertEqual(orig["id"], "a")

    def test_mode_case_is_normalised(self):
        rec, reps = repair_answer(answer(mode="Inquiry"))
        self.assertEqual(rec["mode"], "inquiry")
        self.assertEqual([r.path for r in reps], ["mode"])
        self.assertEqual(reps[0].before, "Inquiry")

    def test_mode_whitespace_is_tolerated(self):
        rec, reps = repair_answer(answer(mode=" inquiry "))
        self.assertEqual(rec["mode"], "inquiry")
        self.assertEqual(len(reps), 1)

    def test_mode_unknown_value_is_left_alone(self):
        rec, reps = repair_answer(answer(mode="speculation"))
        self.assertEqual(rec["mode"], "speculation")
        self.assertEqual(reps, [])

    def test_deliberation_bare_string_wrapped(self):
        a = answer()
        a["deliberation"] = "fast"
        rec, reps = repair_answer(a)
        self.assertEqual(rec["deliberation"], {"kind": "fast"})
        self.assertEqual([r.path for r in reps], ["deliberation"])

    def test_deliberation_kind_case_normalised(self):
        a = answer(deliberation={"kind": "Fast"})
        rec, reps = repair_answer(a)
        self.assertEqual(rec["deliberation"]["kind"], "fast")
        self.assertEqual([r.path for r in reps], ["deliberation/kind"])

    def test_basis_bare_string_wrapped(self):
        a = answer(claims=[claim(basis="testimony")])
        rec, reps = repair_answer(a)
        self.assertEqual(rec["claims"][0]["basis"], {"kind": "testimony"})
        self.assertEqual([r.path for r in reps], ["claims/0/basis"])

    def test_basis_bare_string_case_normalised_and_wrapped(self):
        a = answer(claims=[claim(basis="Observation")])
        rec, reps = repair_answer(a)
        self.assertEqual(rec["claims"][0]["basis"], {"kind": "observation"})
        self.assertEqual(reps[0].before, "Observation")

    def test_basis_bare_string_unknown_is_left_alone(self):
        a = answer(claims=[claim(basis="guesswork")])
        rec, reps = repair_answer(a)
        self.assertEqual(rec["claims"][0]["basis"], "guesswork")
        self.assertEqual(reps, [])

    def test_rung_numeric_string_coerced(self):
        a = answer(claims=[claim(basis={"kind": "inference"}, rung="2")])
        rec, reps = repair_answer(a)
        self.assertEqual(rec["claims"][0]["rung"], 2)
        self.assertEqual([r.path for r in reps], ["claims/0/rung"])

    def test_rung_non_numeric_string_left_alone(self):
        a = answer(claims=[claim(rung="first")])
        rec, reps = repair_answer(a)
        self.assertEqual(rec["claims"][0]["rung"], "first")
        self.assertEqual(reps, [])

    def test_standing_case_normalised(self):
        a = answer(claims=[claim(standing="Contested")])
        rec, reps = repair_answer(a)
        self.assertEqual(rec["claims"][0]["standing"], "contested")
        self.assertEqual([r.path for r in reps], ["claims/0/standing"])

    def test_source_string_wrapped(self):
        a = answer(claims=[claim(sources=["cohort studies", {"ref": "existing"}])])
        rec, reps = repair_answer(a)
        self.assertEqual(rec["claims"][0]["sources"][0], {"ref": "cohort studies"})
        self.assertEqual(rec["claims"][0]["sources"][1], {"ref": "existing"})
        self.assertEqual([r.path for r in reps], ["claims/0/sources/0"])

    def test_null_moral_is_dropped(self):
        a = answer()
        a["moral"] = None
        rec, reps = repair_answer(a)
        self.assertNotIn("moral", rec)
        self.assertEqual([r.path for r in reps], ["moral"])

    def test_null_coverage_is_dropped(self):
        a = answer()
        a["coverage"] = None
        rec, reps = repair_answer(a)
        self.assertNotIn("coverage", rec)

    def test_forecast_status_case_normalised(self):
        a = answer(claims=[claim(forecast={"framework": "x", "scope": "y",
                                            "window": {"from": "a", "to": "b"},
                                            "status": "Not_Falsified"})])
        rec, reps = repair_answer(a)
        self.assertEqual(rec["claims"][0]["forecast"]["status"], "not_falsified")
        self.assertEqual([r.path for r in reps], ["claims/0/forecast/status"])

    def test_multiple_slips_all_recorded(self):
        a = answer(mode="Inquiry",
                   claims=[claim(standing="Settled", basis="observation", rung="1")])
        a["deliberation"] = "fast"
        rec, reps = repair_answer(a)
        paths = sorted(r.path for r in reps)
        self.assertEqual(paths, ["claims/0/basis", "claims/0/rung",
                                  "claims/0/standing", "deliberation", "mode"])

    def test_repair_output_is_valid_against_the_contract(self):
        from threadkit.spec import contract_validator
        a = answer(mode="Inquiry", claims=[claim(standing="Settled", basis="observation")])
        a["deliberation"] = "fast"
        a["moral"] = None
        rec, reps = repair_answer(a)
        self.assertEqual(contract_validator("answer").errors(rec), [])
        self.assertTrue(reps)


class Adapt(unittest.TestCase):
    def test_fenced_text_with_python_literals_round_trips(self):
        a = answer(mode="Inquiry")
        a["mode_disclosed"] = True
        body = json.dumps(a).replace("true", "True")
        text = "```json\n" + body + "\n```"
        rec, reps, err = adapt(text)
        self.assertIsNone(err)
        self.assertEqual(rec["mode"], "inquiry")
        self.assertEqual(rec["mode_disclosed"], True)

    def test_parse_failure_returns_error(self):
        rec, reps, err = adapt("not JSON at all")
        self.assertIsNone(rec)
        self.assertEqual(reps, [])
        self.assertIsNotNone(err)

    def test_preamble_is_tolerated(self):
        a = answer()
        rec, reps, err = adapt("Here is the record:\n\n" + json.dumps(a))
        self.assertIsNone(err)
        self.assertEqual(rec["id"], a["id"])

    def test_preamble_json_example_does_not_shadow_record(self):
        """The adapter must pick the real record over any JSON-ish example appearing earlier
        in prose. Before this fix, `adapt` returned the preamble's `{"k": 1}` with no parse
        error, and the user then saw a confusing GOV-000 from the governor with no hint that
        the actual record had been silently dropped.
        """
        a = answer(mode="inquiry", claims=[claim(standing="settled", basis={"kind": "observation"})])
        prose = "Example (NOT the record): {\"k\": 1}.\n\nActual record:\n" + json.dumps(a)
        rec, reps, err = adapt(prose)
        self.assertIsNone(err)
        self.assertEqual(rec["id"], a["id"])
        self.assertEqual(rec["mode"], "inquiry")


class GovernFreeText(unittest.TestCase):
    def test_fenced_slipped_record_governed_healthy(self):
        a = answer(mode="Inquiry", claims=[claim(standing="Settled", basis="observation")])
        a["deliberation"] = "fast"
        text = "```\n" + json.dumps(a) + "\n```"
        result = govern_free_text(text)
        self.assertIsInstance(result, Adapted)
        self.assertIsNone(result.parse_error)
        self.assertEqual(result.governed.verdict, "healthy")
        self.assertTrue(result.repairs)
        self.assertTrue(result.governed.text)

    def test_parse_failure_sets_parse_error_and_no_governed(self):
        result = govern_free_text("I cannot answer that right now.")
        self.assertIsNotNone(result.parse_error)
        self.assertIsNone(result.governed)
        self.assertIsNone(result.record)

    def test_schema_invalid_after_repair_produces_gov_000(self):
        text = json.dumps({"id": "a", "mode": "inquiry"})  # no claims, no deliberation
        result = govern_free_text(text)
        self.assertIsNone(result.parse_error)
        self.assertIsNotNone(result.governed)
        self.assertTrue(any(f.code == "GOV-000" for f in result.governed.findings))
        self.assertEqual(result.governed.text, "")

    def test_repairs_do_not_hide_bad_wording_findings(self):
        a = answer(mode="Inquiry",
                   claims=[claim(text="This has been proven beyond doubt.",
                                 standing="Contested", basis="recall")])
        a["deliberation"] = "fast"
        result = govern_free_text(json.dumps(a))
        self.assertIsNotNone(result.governed)
        codes = {f.code for f in result.governed.findings}
        self.assertIn("REG-001", codes)
        self.assertTrue(result.repairs)

    def test_to_dict_is_json_serialisable(self):
        a = answer(mode="Inquiry")
        result = govern_free_text(json.dumps(a))
        payload = result.to_dict()
        json.dumps(payload)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
