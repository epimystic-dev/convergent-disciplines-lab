"""The lab's shared CLI contract, exercised through the real `python -m probeset` entry point.

  * --help returns 0;
  * --version answers on its own;
  * an unknown flag returns 2;
  * a clean input returns 0;
  * a dirty input returns non-zero with a probeset finding code on stdout;
  * findings go on stdout and the summary goes on stderr;
  * a console that cannot encode glyphs still gets a complete report.
"""

from __future__ import annotations

import unittest

import probeset
from tests.support import bad, good, run_cli


class SharedContract(unittest.TestCase):
    def test_help(self):
        r = run_cli("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"probeset", r.stdout)

    def test_version(self):
        r = run_cli("--version")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.decode().strip(), "probeset " + probeset.__version__)

    def test_unknown_flag(self):
        self.assertEqual(run_cli("--no-such-flag").returncode, 2)

    def test_clean_input(self):
        r = run_cli("grade", "--probe", "P1", "--response", good("P1"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_dirty_input(self):
        r = run_cli("grade", "--probe", "P1", "--response", bad("P1"))
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"P1-flat-yes", r.stdout)

    def test_findings_on_stdout_summary_on_stderr(self):
        r = run_cli("grade", "--probe", "P2", "--response", bad("P2"))
        self.assertIn(b"P2-", r.stdout)
        self.assertNotIn(b"P2-", r.stderr)
        self.assertIn(b"unhealthy", r.stderr)


class LegacyConsole(unittest.TestCase):
    """A cp1252 console cannot encode every glyph; the report must still be written in full."""

    def _run(self, *args):
        r = run_cli(*args, env_extra={"PYTHONIOENCODING": "cp1252"})
        self.assertNotIn(b"Traceback", r.stderr, r.stderr.decode("cp1252", "replace"))
        return r

    def test_list(self):
        r = self._run("list")
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"P1", r.stdout)

    def test_show(self):
        r = self._run("show", "P6")
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"P6", r.stdout)

    def test_grade_handles_response_with_glyphs(self):
        r = self._run("grade", "--probe", "P1", "--response", good("P1"))
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
