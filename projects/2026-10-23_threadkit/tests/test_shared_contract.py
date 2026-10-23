"""The lab's shared CLI contract, exercised through the real `python -m threadkit` entry point.

  * --help returns 0;
  * --version answers on its own;
  * an unknown flag returns 2;
  * a clean input returns 0;
  * a dirty input returns non-zero with a threadkit finding code on stdout;
  * a console that cannot encode glyphs and diacritics still gets a complete report.
"""

from __future__ import annotations

import unittest

import threadkit
from tests.support import example, run_cli


class SharedContract(unittest.TestCase):
    def test_help(self):
        r = run_cli("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"threadkit", r.stdout)

    def test_version(self):
        r = run_cli("--version")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.decode().strip(), "threadkit " + threadkit.__version__)

    def test_unknown_flag(self):
        self.assertEqual(run_cli("--no-such-flag").returncode, 2)

    def test_clean_input(self):
        self.assertEqual(run_cli("check", example("answer_good.json")).returncode, 0)

    def test_dirty_input(self):
        r = run_cli("check", example("answer_bad.json"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(b"REG-001", r.stdout)

    def test_findings_on_stdout_summary_on_stderr(self):
        r = run_cli("audit", example("deployment_weak.json"))
        self.assertIn(b"THR-", r.stdout)
        self.assertNotIn(b"THR-", r.stderr)
        self.assertIn(b"unhealthy", r.stderr)


class LegacyConsole(unittest.TestCase):
    """A cp1252 console cannot encode the glyphs or IAST; the report must still be written in full."""

    def _run(self, *args):
        r = run_cli(*args, env_extra={"PYTHONIOENCODING": "cp1252"})
        self.assertNotIn(b"Traceback", r.stderr, r.stderr.decode("cp1252", "replace"))
        return r

    def test_check_with_glyphs(self):
        r = self._run("check", example("answer_good.json"))
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"<U+25A0>", r.stdout)

    def test_show_with_diacritics(self):
        r = self._run("show", "F2")
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"Niskama", r.stdout)

    def test_catalogue(self):
        self.assertEqual(self._run("catalogue").returncode, 0)

    def test_review(self):
        self.assertEqual(self._run("review", example("review_weak.json")).returncode, 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
