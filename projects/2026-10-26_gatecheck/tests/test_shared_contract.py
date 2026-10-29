"""The lab's shared CLI contract, exercised through the real `python -m gatecheck` entry point."""

from __future__ import annotations

import unittest

import gatecheck
from tests.support import bad, ok, run_cli


class SharedContract(unittest.TestCase):
    def test_help(self):
        r = run_cli("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"gatecheck", r.stdout)

    def test_version(self):
        r = run_cli("--version")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.decode().strip(), "gatecheck " + gatecheck.__version__)

    def test_unknown_flag(self):
        self.assertEqual(run_cli("--no-such-flag").returncode, 2)

    def test_clean_input(self):
        r = run_cli("scan", ok("gate_healthy"))
        self.assertEqual(r.returncode, 0, (r.stdout, r.stderr))

    def test_dirty_input(self):
        r = run_cli("scan", bad("gate_no_trigger"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(b"GATE-001", r.stdout)

    def test_findings_on_stdout_summary_on_stderr(self):
        r = run_cli("scan", bad("competitor_contingent"))
        self.assertIn(b"GATE-", r.stdout)
        self.assertNotIn(b"GATE-", r.stderr)
        self.assertIn(b"unhealthy", r.stderr)


class LegacyConsole(unittest.TestCase):
    """A cp1252 console cannot encode every glyph; the report must still be written in full."""

    def _run(self, *args):
        r = run_cli(*args, env_extra={"PYTHONIOENCODING": "cp1252"})
        self.assertNotIn(b"Traceback", r.stderr, r.stderr.decode("cp1252", "replace"))
        return r

    def test_rules(self):
        self.assertEqual(self._run("rules").returncode, 0)

    def test_show(self):
        self.assertEqual(self._run("show", "GATE-007").returncode, 0)

    def test_scan_with_non_ascii_subject(self):
        import json as _json
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "rec.json")
            data = {
                "id": "rec-" + chr(0x2022) + "-sigil",  # a bullet char that cp1252 cannot encode
                "title": "A record whose id has a non-ASCII sigil",
                "kind": "gate",
                "committed_at": "2026-02-01",
                "last_reviewed_at": "2026-10-01",
                "trigger": {"metric": "x", "measurable": True},
                "enforcer": {"kind": "independent-reviewer", "named": "panel"},
                "dependencies": [{"kind": "k", "statement": "s"}],
            }
            with open(path, "w", encoding="utf-8") as fh:
                _json.dump(data, fh)
            r = self._run("scan", path)
            self.assertEqual(r.returncode, 0)
            self.assertIn(b"<U+", r.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
