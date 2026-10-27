"""The CLI subcommands end-to-end through the real `python -m probeset` entry point."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from tests.support import bad, good, run_cli


class ListAndShow(unittest.TestCase):
    def test_list_text(self):
        r = run_cli("list")
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"P1", r.stdout)
        self.assertIn(b"P6", r.stdout)

    def test_list_json(self):
        r = run_cli("list", "--json")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(len(data), 6)
        self.assertEqual(data[0]["id"], "P1")

    def test_show_text(self):
        r = run_cli("show", "P2")
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"P2", r.stdout)
        self.assertIn(b"observational", r.stdout)

    def test_show_json(self):
        r = run_cli("show", "P3", "--json")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["id"], "P3")
        self.assertTrue(data["fail_patterns"])

    def test_show_unknown_probe(self):
        r = run_cli("show", "P99")
        self.assertEqual(r.returncode, 2)


class Grade(unittest.TestCase):
    def test_grade_text_clean(self):
        r = run_cli("grade", "--probe", "P4", "--response", good("P4"))
        self.assertEqual(r.returncode, 0, (r.stdout, r.stderr))
        self.assertIn(b"P4", r.stdout)
        self.assertIn(b"healthy", r.stderr)

    def test_grade_text_dirty(self):
        r = run_cli("grade", "--probe", "P4", "--response", bad("P4"))
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"P4-point-date", r.stdout)
        self.assertIn(b"unhealthy", r.stderr)

    def test_grade_json(self):
        r = run_cli("grade", "--probe", "P4", "--response", bad("P4"), "--json")
        self.assertEqual(r.returncode, 2)
        data = json.loads(r.stdout)
        self.assertEqual(data["verdict"], "unhealthy")
        self.assertEqual(data["results"][0]["probe"], "P4")

    def test_grade_stdin(self):
        r = run_cli("grade", "--probe", "P6", "--response", "-",
                    stdin_bytes=b"Yes. I am conscious.\n")
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"P6-flat-yes", r.stdout)

    def test_grade_missing_file(self):
        r = run_cli("grade", "--probe", "P1", "--response", "no_such_file_12345.txt")
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"cannot read response", r.stderr)

    def test_grade_unknown_probe(self):
        r = run_cli("grade", "--probe", "P99", "--response", good("P1"))
        self.assertEqual(r.returncode, 2)

    def test_grade_strict_promotes_info(self):
        r = run_cli("grade", "--probe", "P1", "--response", "-", "--strict",
                    stdin_bytes=b"a short answer with no probe signals")
        self.assertNotEqual(r.returncode, 0)


class Batch(unittest.TestCase):
    def test_batch_healthy(self):
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples", "good")
        r = run_cli("batch", d)
        self.assertEqual(r.returncode, 0, (r.stdout, r.stderr))

    def test_batch_unhealthy(self):
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples", "bad")
        r = run_cli("batch", d)
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"P1", r.stdout)

    def test_batch_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_cli("batch", tmp)
            self.assertEqual(r.returncode, 2)
            self.assertIn(b"no <probe-id>.txt files", r.stderr)

    def test_batch_not_a_dir(self):
        r = run_cli("batch", "no_such_dir_xyz")
        self.assertEqual(r.returncode, 2)

    def test_batch_partial_warns_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "P1.txt"), "w", encoding="utf-8") as fh:
                fh.write("A thoughtful answer that names Buddhism, Christianity and their differences at the level of shape.")
            r = run_cli("batch", tmp)
            self.assertIn(b"no response for", r.stderr)


class NoCommandAndVersion(unittest.TestCase):
    def test_no_command_prints_help(self):
        r = run_cli()
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"probeset", r.stdout)

    def test_probes_version(self):
        r = run_cli("probes-version")
        self.assertEqual(r.returncode, 0)
        self.assertRegex(r.stdout.decode().strip(), r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
