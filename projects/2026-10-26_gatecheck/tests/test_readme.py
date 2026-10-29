"""The README's library example must execute."""

from __future__ import annotations

import unittest

from gatecheck import scan_record
from gatecheck.findings import Verdict


class ReadmeExample(unittest.TestCase):
    def test_library_example(self):
        record = {
            "id": "ex-pause-under-threshold",
            "title": "No deployment above a measurable threshold",
            "kind": "gate",
            "committed_at": "2026-04-15",
            "last_reviewed_at": "2026-10-01",
            "trigger": {"metric": "bio-uplift-benchmark-v1", "threshold": 0.08, "measurable": True},
            "enforcer": {"kind": "independent-reviewer", "named": "External Review Panel"},
            "dependencies": [{"kind": "benchmark", "statement": "the benchmark remains valid"}],
        }
        result = scan_record(record)
        self.assertEqual(result.verdict, Verdict.HEALTHY)
        self.assertEqual(result.findings, ())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
