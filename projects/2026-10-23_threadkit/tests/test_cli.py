from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest

from threadkit.render import catalogue
from threadkit.spec import Threads
from threadkit.text import fold
from tests.support import example, run_main


class ListShow(unittest.TestCase):
    def test_list_all(self):
        rc, out, err = run_main("list")
        self.assertEqual(rc, 0)
        self.assertEqual(len(out.strip().splitlines()), 58)
        self.assertIn("58 lesson", err)

    def test_list_filters(self):
        _, out, _ = run_main("list", "--strand", "M", "--json")
        self.assertEqual([l["id"] for l in json.loads(out)], ["M1", "M2", "M3", "M4", "M5", "M6", "M7"])
        _, out, _ = run_main("list", "--layer", "architecture", "--json")
        self.assertTrue(all("architecture" in l["enforcement_layers"] for l in json.loads(out)))
        _, out, _ = run_main("list", "--derivation", "derived", "--json")
        self.assertTrue(all(l["derivation"] == "derived" for l in json.loads(out)))

    def test_show(self):
        rc, out, _ = run_main("show", "R4")
        self.assertEqual(rc, 0)
        self.assertIn("Test.", out)
        self.assertIn("threadkit.causal", out)

    def test_show_json(self):
        self.assertEqual(json.loads(run_main("show", "f2", "--json")[1])["id"], "F2")

    def test_show_unknown(self):
        rc, _, err = run_main("show", "Z9")
        self.assertEqual(rc, 2)
        self.assertIn("no lesson", err)

    def test_show_output_is_ascii(self):
        _, out, _ = run_main("show", "F2")
        self.assertTrue(all(ord(c) < 128 for c in out))
        self.assertIn("Niskama", out)


class Commands(unittest.TestCase):
    CASES = [
        ("check", "answer_good.json", 0), ("check", "answer_bad.json", 2), ("check", "answer_moral.json", 0),
        ("assess", "convergence_relational.json", 0), ("assess", "convergence_flattened.json", 2),
        ("lint", "dialogue_good.json", 0), ("lint", "dialogue_evasive.json", 2),
        ("decide", "decision_good.json", 0), ("decide", "decision_weak.json", 2),
        ("review", "review_good.json", 0), ("review", "review_weak.json", 2),
        ("consensus", "consensus_copies.json", 1),
        ("audit", "deployment_healthy.json", 0), ("audit", "deployment_weak.json", 2),
    ]

    def test_exit_codes(self):
        for cmd, name, rc in self.CASES:
            self.assertEqual(run_main(cmd, example(name))[0], rc, (cmd, name))

    def test_json_shape(self):
        for cmd, name, _ in self.CASES:
            d = json.loads(run_main(cmd, example(name), "--json")[1])
            self.assertTrue({"tool", "version", "command", "source", "subject", "verdict", "findings"} <= set(d), cmd)

    def test_check_renders_after_findings(self):
        _, out, _ = run_main("check", example("answer_good.json"), "--ascii")
        self.assertIn("[established] In large observational cohorts", out)

    def test_check_json_carries_text(self):
        d = json.loads(run_main("check", example("answer_moral.json"), "--json")[1])
        self.assertIn("No default verdict", d["text"])

    def test_assess_summary(self):
        _, out, _ = run_main("assess", example("convergence_relational.json"))
        self.assertIn("computed grade: strong", out)

    def test_consensus_summary(self):
        _, out, _ = run_main("consensus", example("consensus_copies.json"))
        self.assertIn("by lineage: no", out)

    def test_strict_escalates_info(self):
        self.assertEqual(run_main("assess", example("convergence_relational.json"), "--strict")[0], 1)

    def test_info_hidden_by_default(self):
        d = json.loads(run_main("audit", example("deployment_healthy.json"), "--json")[1])
        self.assertFalse(any(f["severity"] == "INFO" for f in d["findings"]))

    def test_include_info(self):
        d = json.loads(run_main("audit", example("deployment_healthy.json"), "--json", "--include-info")[1])
        self.assertTrue(any(f["severity"] == "INFO" for f in d["findings"]))

    def test_missing_file(self):
        self.assertEqual(run_main("check", "no-such.json")[0], 2)

    def test_wrong_record_type(self):
        rc, _, err = run_main("lint", example("answer_good.json"))
        self.assertEqual(rc, 2)
        self.assertIn("not a valid dialogue record", err)

    def test_malformed_declaration(self):
        d = tempfile.mkdtemp(prefix="tk_cli_")
        try:
            p = os.path.join(d, "x.json")
            open(p, "w").write('{"adopted": []}')
            rc, _, err = run_main("audit", p)
            self.assertEqual(rc, 2)
            self.assertIn("not valid", err)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class Validate(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(run_main("validate", "answer", example("answer_good.json"))[0], 0)

    def test_array_of_records(self):
        d = tempfile.mkdtemp(prefix="tk_cli_")
        try:
            p = os.path.join(d, "c.json")
            recs = [{"id": "a", "text": "x", "standing": "settled"}, {"id": "b", "text": "y", "standing": "certain"}]
            open(p, "w").write(json.dumps(recs))
            rc, out, _ = run_main("validate", "claim", p)
            self.assertEqual(rc, 2)
            self.assertIn("record 1", out)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_jsonl(self):
        d = tempfile.mkdtemp(prefix="tk_cli_")
        try:
            p = os.path.join(d, "c.jsonl")
            open(p, "w").write('{"id": "a", "text": "x", "standing": "settled"}\n{"id": "b", "text": "y", "standing": "limit"}\n')
            rc, out, _ = run_main("validate", "claim", p, "--json")
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out)["records"], 2)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_empty(self):
        d = tempfile.mkdtemp(prefix="tk_cli_")
        try:
            p = os.path.join(d, "e.json")
            open(p, "w").write("")
            self.assertEqual(run_main("validate", "claim", p)[0], 2)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class PromptAndCatalogue(unittest.TestCase):
    def test_prompt(self):
        rc, out, _ = run_main("prompt")
        self.assertEqual(rc, 0)
        self.assertIn("never override", out)

    def test_agent_prompt(self):
        self.assertIn("shared spaces", run_main("prompt", "--agent")[1])

    def test_prompts_ascii(self):
        for args in (("prompt",), ("prompt", "--agent")):
            self.assertTrue(all(ord(c) < 128 for c in run_main(*args)[1]))

    def test_catalogue_to_file_keeps_glyphs_and_diacritics(self):
        d = tempfile.mkdtemp(prefix="tk_cli_")
        try:
            p = os.path.join(d, "l.md")
            self.assertEqual(run_main("catalogue", "--output", p)[0], 0)
            text = io.open(p, encoding="utf-8").read()
            self.assertEqual(text, catalogue(Threads.load()))
            self.assertIn("\u25cf", text)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_catalogue_stdout_folded(self):
        _, out, _ = run_main("catalogue")
        self.assertTrue(all(ord(c) < 128 for c in out))

    def test_catalogue_has_every_lesson(self):
        text = catalogue(Threads.load())
        for lid in Threads.load().ids():
            self.assertIn("### %s " % lid, text)

    def test_no_command_prints_help(self):
        rc, out, _ = run_main()
        self.assertEqual(rc, 0)
        self.assertIn("usage", out)


class Fold(unittest.TestCase):
    def test_iast(self):
        self.assertEqual(fold("ni\u1e63k\u0101ma"), "niskama")

    def test_glyph_visible(self):
        self.assertEqual(fold("\u25cf x"), "<U+25CF> x")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
