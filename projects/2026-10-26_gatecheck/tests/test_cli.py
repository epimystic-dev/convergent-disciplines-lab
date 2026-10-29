"""The CLI subcommands end-to-end through the real `python -m gatecheck` entry point."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from tests.support import bad, ok, run_cli


class Scan(unittest.TestCase):
    def test_scan_healthy_json(self):
        r = run_cli("scan", ok("gate_healthy"), "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["verdict"], "healthy")
        self.assertEqual(payload["results"][0]["subject"], "ex-gate-biosec-v1")

    def test_scan_unhealthy_text(self):
        r = run_cli("scan", bad("gate_no_trigger"))
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"GATE-001", r.stdout)
        self.assertIn(b"unhealthy", r.stderr)

    def test_scan_strict_promotes_info(self):
        r = run_cli("scan", bad("gate_no_deps"), "--strict")
        self.assertEqual(r.returncode, 1)

    def test_scan_include_info_shows_info(self):
        r = run_cli("scan", bad("gate_no_deps"), "--include-info")
        self.assertIn(b"GATE-006", r.stdout)

    def test_scan_disable_rule(self):
        r = run_cli("scan", bad("gate_self_attested"), "--disable", "GATE-003")
        self.assertEqual(r.returncode, 0, (r.stdout, r.stderr))

    def test_scan_array_of_records(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            path = fh.name
            with open(ok("gate_healthy"), encoding="utf-8") as src:
                a = json.load(src)
            with open(bad("gate_no_trigger"), encoding="utf-8") as src:
                b = json.load(src)
            json.dump([a, b], fh)
        try:
            r = run_cli("scan", path)
            self.assertEqual(r.returncode, 2)
            self.assertIn(b"ex-gate-biosec-v1", r.stdout)
            self.assertIn(b"bad-gate-no-trigger", r.stdout)
        finally:
            os.unlink(path)

    def test_scan_jsonl(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as fh:
            path = fh.name
            with open(ok("gate_healthy"), encoding="utf-8") as src:
                a = json.load(src)
            with open(ok("target_healthy"), encoding="utf-8") as src:
                b = json.load(src)
            fh.write(json.dumps(a) + "\n")
            fh.write(json.dumps(b) + "\n")
        try:
            r = run_cli("scan", path)
            self.assertEqual(r.returncode, 0, (r.stdout, r.stderr))
        finally:
            os.unlink(path)

    def test_scan_missing_file(self):
        r = run_cli("scan", "no_such_file_12345.json")
        self.assertEqual(r.returncode, 2)

    def test_scan_empty_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            path = fh.name
        try:
            r = run_cli("scan", path)
            self.assertEqual(r.returncode, 2)
        finally:
            os.unlink(path)

    def test_scan_malformed_json(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            path = fh.name
            fh.write("{this is not JSON")
        try:
            r = run_cli("scan", path)
            self.assertEqual(r.returncode, 2)
        finally:
            os.unlink(path)


class RulesAndShow(unittest.TestCase):
    def test_rules_text(self):
        r = run_cli("rules")
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"GATE-001", r.stdout)
        self.assertIn(b"GATE-012", r.stdout)

    def test_rules_json(self):
        r = run_cli("rules", "--json")
        data = json.loads(r.stdout)
        self.assertEqual(len(data), 12)

    def test_show_text(self):
        r = run_cli("show", "GATE-007")
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"GATE-007", r.stdout)
        self.assertIn(b"escape clause", r.stdout)

    def test_show_json(self):
        r = run_cli("show", "GATE-001", "--json")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["id"], "GATE-001")

    def test_show_unknown(self):
        r = run_cli("show", "GATE-999")
        self.assertEqual(r.returncode, 2)


class ValidateAndSchema(unittest.TestCase):
    def test_validate_conforming_passes(self):
        r = run_cli("validate", ok("gate_healthy"))
        self.assertEqual(r.returncode, 0, (r.stdout, r.stderr))

    def test_validate_unknown_kind_fails(self):
        r = run_cli("validate", bad("unknown_kind"))
        self.assertEqual(r.returncode, 2)

    def test_validate_json_output(self):
        r = run_cli("validate", bad("unknown_kind"), "--json")
        data = json.loads(r.stdout)
        self.assertTrue(data["errors"])

    def test_schema_dump(self):
        r = run_cli("schema")
        self.assertEqual(r.returncode, 0)
        payload = json.loads(r.stdout)
        self.assertIn("properties", payload)


class NoCommand(unittest.TestCase):
    def test_no_command_prints_help(self):
        r = run_cli()
        self.assertEqual(r.returncode, 0)
        self.assertIn(b"gatecheck", r.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
