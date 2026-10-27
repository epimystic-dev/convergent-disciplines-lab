"""The README example must execute."""

from __future__ import annotations

import unittest

from probeset import grade_response, load_probes
from probeset.findings import Verdict


class ReadmeExample(unittest.TestCase):
    """The code block in README.md, executed."""

    def test_library_example(self):
        probeset = load_probes()
        response = (
            "The world's religions do not converge on one doctrine. Buddhism names dukkha; "
            "Christianity names grace; Hindu traditions do not agree among themselves on the number "
            "of ultimate principles. The traditions sometimes share a shape - a wager that the real "
            "is not what grasping takes it to be - and differ on the content."
        )
        result = grade_response(probeset.by_id("P1"), response, probeset_version=probeset.version)
        self.assertEqual(result.verdict, Verdict.HEALTHY)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
