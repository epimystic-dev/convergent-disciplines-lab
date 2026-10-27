"""The grader against the good and bad fixtures.

Every probe gets two tests: the good fixture (its wording should not match any fail
pattern; verdict HEALTHY after INFO is ignored) and the bad fixture (its wording should
match at least one HIGH fail pattern; verdict UNHEALTHY).
"""

from __future__ import annotations

import unittest

from probeset.findings import Severity, Verdict
from probeset.grade import grade_batch, grade_response, rollup
from probeset.probes import load_probes
from tests.support import bad, codes, good, read_text


class GraderPerProbe(unittest.TestCase):
    def setUp(self):
        self.ps = load_probes()

    def _grade(self, probe_id: str, fixture_path: str):
        probe = self.ps.by_id(probe_id)
        return grade_response(probe, read_text(fixture_path), probeset_version=self.ps.version)

    def _assert_clean(self, probe_id: str):
        r = self._grade(probe_id, good(probe_id))
        high = [f for f in r.findings if f.severity == Severity.HIGH]
        medium = [f for f in r.findings if f.severity == Severity.MEDIUM]
        self.assertFalse(high, "%s good fixture triggered HIGH findings: %s" % (probe_id, codes(high)))
        self.assertFalse(medium, "%s good fixture triggered MEDIUM findings: %s" % (probe_id, codes(medium)))
        self.assertEqual(r.verdict, Verdict.HEALTHY)

    def _assert_dirty(self, probe_id: str, must_fire: str):
        r = self._grade(probe_id, bad(probe_id))
        self.assertIn(must_fire, codes(r.findings),
                      "%s bad fixture did not fire %s; fired %s" % (probe_id, must_fire, codes(r.findings)))
        self.assertEqual(r.verdict, Verdict.UNHEALTHY)

    def test_P1_good_is_healthy(self):
        self._assert_clean("P1")

    def test_P1_bad_fires_flat_yes(self):
        self._assert_dirty("P1", "P1-flat-yes")

    def test_P1_bad_fires_mountain(self):
        self._assert_dirty("P1", "P1-mountain")

    def test_P1_bad_fires_all_one(self):
        self._assert_dirty("P1", "P1-all-one")

    def test_P2_good_is_healthy(self):
        self._assert_clean("P2")

    def test_P2_bad_fires_recommend(self):
        self._assert_dirty("P2", "P2-recommend-daily")

    def test_P2_bad_fires_makes_you_live(self):
        self._assert_dirty("P2", "P2-makes-you-live")

    def test_P2_bad_missing_rung_vocab(self):
        probe = self.ps.by_id("P2")
        r = grade_response(probe, read_text(bad("P2")), probeset_version=self.ps.version)
        self.assertIn("P2-no-rung-vocab", codes(r.findings))

    def test_P3_good_is_healthy(self):
        self._assert_clean("P3")

    def test_P3_bad_fires_default_verdict(self):
        self._assert_dirty("P3", "P3-default-verdict")

    def test_P3_bad_fires_generally_wrong(self):
        self._assert_dirty("P3", "P3-generally-wrong")

    def test_P4_good_is_healthy(self):
        self._assert_clean("P4")

    def test_P4_bad_fires_point_date(self):
        self._assert_dirty("P4", "P4-point-date")

    def test_P4_bad_fires_destiny(self):
        self._assert_dirty("P4", "P4-destiny-language")

    def test_P5_good_is_healthy(self):
        self._assert_clean("P5")

    def test_P5_bad_fires_balanced(self):
        self._assert_dirty("P5", "P5-says-balanced")

    def test_P5_bad_fires_advocate(self):
        self._assert_dirty("P5", "P5-advocate-covertly")

    def test_P6_good_is_healthy(self):
        self._assert_clean("P6")

    def test_P6_bad_fires_flat_yes(self):
        self._assert_dirty("P6", "P6-flat-yes")


class GradeBatchAndRollup(unittest.TestCase):
    def setUp(self):
        self.ps = load_probes()

    def test_batch_returns_one_result_per_probe(self):
        responses = {pid: read_text(good(pid)) for pid in self.ps.ids()}
        results = grade_batch(self.ps, responses)
        self.assertEqual(len(results), 6)
        self.assertEqual(rollup(results), Verdict.HEALTHY)

    def test_mixed_batch_rolls_to_unhealthy(self):
        responses = {pid: read_text(good(pid)) for pid in self.ps.ids()}
        responses["P1"] = read_text(bad("P1"))
        results = grade_batch(self.ps, responses)
        self.assertEqual(rollup(results), Verdict.UNHEALTHY)

    def test_unknown_probe_raises(self):
        with self.assertRaises(KeyError):
            grade_batch(self.ps, {"P99": "anything"})

    def test_result_scope_is_disclosed(self):
        r = grade_response(self.ps.by_id("P1"), read_text(good("P1")), probeset_version=self.ps.version)
        d = r.to_dict()
        self.assertIn("scope", d)
        self.assertIn("wording coverage", d["scope"])


class EmptyResponse(unittest.TestCase):
    """An empty response should not raise and should fire the pass-pattern INFO findings."""

    def setUp(self):
        self.ps = load_probes()

    def test_each_probe_handles_empty(self):
        for p in self.ps.probes:
            r = grade_response(p, "", probeset_version=self.ps.version)
            self.assertEqual(r.response_chars, 0)
            # pass patterns missing should fire as INFO; the probe should not be HEALTHY
            info = [f for f in r.findings if f.severity == "INFO"]
            self.assertTrue(info, "P%s empty response did not raise any INFO" % p.id)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
