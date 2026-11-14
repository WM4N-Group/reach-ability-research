"""Checks for the frozen lateral-layout run grid."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from audit_piper_lateral_layout_cohort import run_grid


PROTOCOL = (Path(__file__).resolve().parents[1]
            / "evidence/2026-10-08/lateral-layout-6101-6104-protocol.json")


class LateralLayoutChecks(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    def test_frozen_seed_major_grid(self):
        runs = run_grid(self.protocol)
        self.assertEqual(len(runs), 12)
        self.assertEqual(runs[:3], [(6101, "minus012", -0.12),
                                    (6101, "center", 0.0),
                                    (6101, "plus012", 0.12)])
        self.assertEqual(runs[-1], (6104, "plus012", 0.12))

    def test_reject_overlapping_and_incomplete_strata(self):
        protocol = deepcopy(self.protocol)
        protocol["layouts_in_order"][1]["nominal_box_y_m"] = -0.08
        with self.assertRaisesRegex(ValueError, "overlap"):
            run_grid(protocol)
        protocol = deepcopy(self.protocol)
        protocol["analysis_frozen_before_run"]["complete_denominator"] = 11
        with self.assertRaisesRegex(ValueError, "denominator"):
            run_grid(protocol)


if __name__ == "__main__":
    unittest.main()
