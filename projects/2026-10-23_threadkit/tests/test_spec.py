"""The threads as data: complete, internally consistent, and in sync with the repository."""

from __future__ import annotations

import importlib
import os
import re
import unittest

import threadkit
from threadkit.spec import CONTRACTS, DATA_DIR, Threads
from tests.support import LAB_ROOT, ROOT_THREADS

T = Threads.load()
STANDINGS = {"settled", "established", "contested", "limit", "bridge", "method"}


class Integrity(unittest.TestCase):
    def test_fifty_eight_lessons(self):
        self.assertEqual(len(T.lessons), 58)

    def test_ids_unique(self):
        self.assertEqual(len(set(T.ids())), len(T.ids()))

    def test_every_strand_present(self):
        self.assertEqual({l["strand"] for l in T.lessons}, set("MRSKDAFP"))

    def test_strand_matches_id(self):
        for l in T.lessons:
            self.assertEqual(l["strand"], l["id"][0])

    def test_every_lesson_complete(self):
        for l in T.lessons:
            for k in ("statement", "rationale", "failure_mode", "practice", "sketch", "example", "test"):
                self.assertTrue(l[k].strip(), "%s.%s empty" % (l["id"], k))

    def test_standings_valid(self):
        for l in T.lessons:
            self.assertIn(l["standing"], STANDINGS)

    def test_chapters_in_range(self):
        for l in T.lessons:
            for c in l["chapters"]:
                self.assertTrue(0 <= c <= 29, (l["id"], c))

    def test_contracts_named_exist(self):
        for l in T.lessons:
            if l["data_contract"]:
                self.assertTrue(os.path.isfile(os.path.join(DATA_DIR, l["data_contract"])), l["id"])

    def test_reference_implementations_import(self):
        for l in T.lessons:
            if l["reference_implementation"]:
                importlib.import_module(l["reference_implementation"])

    def test_convergence_bases_exist(self):
        ids = {c["id"] for c in T.convergences()}
        for l in T.lessons:
            if l["basis"]["kind"] == "convergence":
                self.assertIn(l["basis"]["ref"], ids)

    def test_theses_never_settled(self):
        for l in T.lessons:
            if l["basis"]["kind"] == "author_thesis":
                self.assertNotEqual(l["standing"], "settled")

    def test_four_move_framework_is_the_authors_thesis(self):
        self.assertEqual(T.convergence("CV9")["grade"], "author_thesis")

    def test_audited_lines_match_the_book(self):
        grades = {c["id"]: c["grade"] for c in T.convergences()}
        self.assertEqual((grades["CV1"], grades["CV2"], grades["CV3"]), ("strong", "strong", "strong"))
        self.assertEqual((grades["CV4"], grades["CV5"]), ("partial", "partial"))

    def test_route_counts_match_routes(self):
        for c in T.convergences():
            self.assertEqual(c["route_count"], len(c["routes"]), c["id"])

    def test_strong_needs_three_routes(self):
        for c in T.convergences():
            if c["grade"] == "strong":
                self.assertGreaterEqual(c["route_count"], 3)

    def test_disagreements_have_two_positions(self):
        for d in T.disagreements():
            self.assertGreaterEqual(len(d["positions"]), 2)

    def test_moral_ids(self):
        m = T.moral()
        self.assertEqual([c["id"] for c in m["convergences"]], ["C%d" % i for i in range(1, 8)])
        self.assertEqual([d["id"] for d in m["disagreements"]], ["D%d" % i for i in range(1, 6)])

    def test_six_registers(self):
        self.assertEqual([r["id"] for r in T.registers()],
                         ["settled", "established", "contested", "limit", "bridge", "method"])

    def test_four_moves_and_seven(self):
        f = T.frameworks()
        self.assertEqual(len(f["four_moves"]), 4)
        self.assertEqual(len(f["seven_moves"]), 7)
        self.assertEqual(len(f["integration_failures"]), 4)
        self.assertEqual(len(f["eight_capacities"]), 8)

    def test_derived_lessons_are_labelled(self):
        self.assertTrue(T.select(derivation="derived"))
        self.assertTrue(all(l["derivation"] in ("stated", "derived") for l in T.lessons))

    def test_threads_validate_against_schema(self):
        self.assertEqual(threadkit.threads_validator().errors(T.data), [])

    def test_contracts_load_strictly(self):
        for name in CONTRACTS:
            threadkit.contract_validator(name)

    def test_source_records_adaptation_and_sharealike(self):
        self.assertEqual(T.data["license"], "CC-BY-SA-4.0")
        self.assertTrue(T.data["source"]["adapted"])
        self.assertTrue(T.data["source"]["changes"])


class Lookup(unittest.TestCase):
    def test_get_case_insensitive(self):
        self.assertEqual(T.get("m3")["id"], "M3")

    def test_unknown(self):
        with self.assertRaises(KeyError):
            T.get("Z9")

    def test_select_by_strand(self):
        self.assertEqual([l["id"] for l in T.select(strand="P")], ["P1", "P2"])

    def test_select_by_chapter(self):
        self.assertIn("R4", [l["id"] for l in T.select(chapter=3)])

    def test_context_enforceable_is_a_majority_but_not_all(self):
        ctx = T.context_enforceable()
        self.assertTrue(len(T.lessons) // 2 <= len(ctx) < len(T.lessons))

    def test_governance_only_lessons_exist(self):
        gov = [l["id"] for l in T.lessons if l["enforcement_layers"] == ["governance"]]
        self.assertIn("F7", gov)


class Hygiene(unittest.TestCase):
    """What the published data must never carry."""

    def _blob(self):
        with open(os.path.join(DATA_DIR, "threads.json"), encoding="utf-8") as fh:
            return fh.read().lower()

    def test_no_vendor_or_product_names(self):
        # Assembled from parts so this file does not itself carry the names it screens for.
        names = [a + b for a, b in (("open", "ai"), ("anth", "ropic"), ("deep", "mind"), ("gem", "ini"),
                                    ("co", "pilot"), ("chat", "gpt"), ("cla", "ude"), ("lla", "ma"),
                                    ("mis", "tral"), ("deep", "seek"), ("hugging", "face"))]
        blob = self._blob()
        for bad in names:
            self.assertIsNone(re.search("(?<![a-z])" + bad + "(?![a-z])", blob), bad)

    def test_no_author_identity(self):
        blob = self._blob()
        for bad in [a + b for a, b in (("roh", "an"), ("lin", "kedin"), ("utt", "ar pradesh"))]:
            self.assertNotIn(bad, blob)

    def test_ascii_on_disk(self):
        with open(os.path.join(DATA_DIR, "threads.json"), "rb") as fh:
            self.assertTrue(all(b < 128 for b in fh.read()))


@unittest.skipUnless(os.path.isdir(ROOT_THREADS), "not inside the lab repository")
class InSyncWithRepository(unittest.TestCase):
    def _same(self, a, b):
        with open(a, "rb") as fa, open(b, "rb") as fb:
            self.assertEqual(fa.read().replace(b"\r\n", b"\n"), fb.read().replace(b"\r\n", b"\n"), b)

    def test_threads_json(self):
        self._same(os.path.join(DATA_DIR, "threads.json"), os.path.join(ROOT_THREADS, "threads.json"))

    def test_threads_schema(self):
        self._same(os.path.join(DATA_DIR, "threads.schema.json"), os.path.join(ROOT_THREADS, "threads.schema.json"))

    def test_contracts(self):
        for name in CONTRACTS:
            self._same(os.path.join(DATA_DIR, "schemas", name + ".schema.json"),
                       os.path.join(ROOT_THREADS, "schemas", name + ".schema.json"))

    def test_prompts(self):
        for name in ("threads-system-prompt.md", "threads-agent-addendum.md"):
            self._same(os.path.join(DATA_DIR, "prompts", name), os.path.join(ROOT_THREADS, "prompts", name))

    def test_docs_catalogue_is_generated_output(self):
        doc = os.path.join(LAB_ROOT, "docs", "LESSONS.md")
        if not os.path.isfile(doc):
            self.skipTest("docs/LESSONS.md not present")
        from threadkit.render import catalogue
        with open(doc, encoding="utf-8") as fh:
            self.assertEqual(fh.read().replace("\r\n", "\n"), catalogue(T),
                             "docs/LESSONS.md drifted; regenerate with: python -m threadkit catalogue --output ../../docs/LESSONS.md")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
