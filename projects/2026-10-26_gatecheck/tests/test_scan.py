"""Non-dict commitment records at the scan boundary.

Before the fix, `scan_record(non_dict)` crashed with an uninformative
`AttributeError: 'X' object has no attribute 'get'` from inside `_subject`,
far from the authoring mistake. The 2026-11-05 shape-slip fix inside rules.py
hardened the per-rule accessors but not the scan entry: a bare string, number,
null, or list at the record slot still crashed before any rule ran.

These tests pin the new behaviour: `scan_record` raises a ValueError naming
the offending kind; `scan_records` wraps it with the record index; the CLI
exits 2 with that message on stderr. `validate` remains the authoritative
shape surface; `scan` just refuses to continue on a record it cannot read.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from gatecheck.scan import scan_record, scan_records
from tests.support import load, ok, run_cli, run_main


class ScanRecordRejectsNonDict(unittest.TestCase):
    def test_bare_string_record(self):
        with self.assertRaises(ValueError) as cm:
            scan_record("not-a-record")
        self.assertIn("JSON object", str(cm.exception))
        self.assertIn("str", str(cm.exception))

    def test_none_record(self):
        with self.assertRaises(ValueError) as cm:
            scan_record(None)
        self.assertIn("NoneType", str(cm.exception))

    def test_int_record(self):
        with self.assertRaises(ValueError) as cm:
            scan_record(42)
        self.assertIn("int", str(cm.exception))

    def test_list_record(self):
        with self.assertRaises(ValueError) as cm:
            scan_record(["id", "x"])
        self.assertIn("list", str(cm.exception))

    def test_valid_dict_still_scans(self):
        rec = load(ok("gate_healthy"))
        result = scan_record(rec)
        self.assertEqual(result.subject, "ex-gate-biosec-v1")
        self.assertEqual(result.verdict, "healthy")


class ScanRecordsNamesTheIndex(unittest.TestCase):
    def test_non_dict_in_the_middle_names_the_index(self):
        rec = load(ok("gate_healthy"))
        with self.assertRaises(ValueError) as cm:
            scan_records([rec, "bad", rec])
        self.assertIn("record 1", str(cm.exception))
        self.assertIn("JSON object", str(cm.exception))

    def test_all_good_records_pass_through(self):
        rec = load(ok("gate_healthy"))
        results = scan_records([rec, rec])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].subject, "ex-gate-biosec-v1")


class CliRejectsNonDictRecord(unittest.TestCase):
    def _tmp(self, body: str) -> str:
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        try:
            fh.write(body)
        finally:
            fh.close()
        return fh.name

    def test_bare_string_top_level_exits_2_with_helpful_stderr(self):
        path = self._tmp(json.dumps("not-a-record"))
        try:
            rc, out, err = run_main("scan", path)
            self.assertEqual(rc, 2)
            self.assertIn("JSON object", err)
            self.assertNotIn("Traceback", err)
        finally:
            os.unlink(path)

    def test_null_top_level_exits_2(self):
        path = self._tmp("null")
        try:
            rc, out, err = run_main("scan", path)
            self.assertEqual(rc, 2)
            self.assertIn("NoneType", err)
        finally:
            os.unlink(path)

    def test_mixed_array_names_the_bad_index(self):
        rec = load(ok("gate_healthy"))
        path = self._tmp(json.dumps([rec, "bare", None]))
        try:
            rc, out, err = run_main("scan", path)
            self.assertEqual(rc, 2)
            self.assertIn("record 1", err)
        finally:
            os.unlink(path)

    def test_bare_string_subprocess_no_crash(self):
        # End-to-end through the real -m entry point, to prove the error is caught
        # before Python unwinds the stack with an AttributeError.
        path = self._tmp(json.dumps(42))
        try:
            r = run_cli("scan", path)
            self.assertEqual(r.returncode, 2)
            self.assertNotIn(b"AttributeError", r.stderr)
            self.assertIn(b"JSON object", r.stderr)
        finally:
            os.unlink(path)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
