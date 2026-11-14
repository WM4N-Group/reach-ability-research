"""Focused checks for the descriptive approach-edge time fit."""

from __future__ import annotations

import unittest

from estimate_piper_approach_edge_time import fit


class ApproachEdgeTimeCheck(unittest.TestCase):
    def test_recovers_positive_intercept_and_slope(self) -> None:
        rows = [{"joint_linf_rad": x, "duration_s": 0.2 + 1.5 * x}
                for x in (0.1, 0.5, 1.0, 1.5)]
        intercept, slope = fit(rows)
        self.assertAlmostEqual(intercept, 0.2)
        self.assertAlmostEqual(slope, 1.5)

    def test_rejects_no_distance_variation(self) -> None:
        rows = [{"joint_linf_rad": 0.5, "duration_s": duration}
                for duration in (0.5, 0.6, 0.7)]
        with self.assertRaisesRegex(ValueError, "Insufficient variation"):
            fit(rows)

    def test_rejects_negative_intercept(self) -> None:
        rows = [{"joint_linf_rad": x, "duration_s": -0.1 + 2.0 * x}
                for x in (0.1, 0.5, 1.0, 1.5)]
        with self.assertRaisesRegex(ValueError, "not physically interpretable"):
            fit(rows)


if __name__ == "__main__":
    unittest.main()
