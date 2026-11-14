"""Checks for center-screen qualification and conditional run membership."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from audit_piper_lateral_conditional_cohort import expected_runs, qualifies


PROTOCOL = (Path(__file__).resolve().parents[1]
            / "evidence/2026-10-08/lateral-layout-conditional-6201-6208-protocol.json")


def report(settled=False, force=0.0, outcome="push_terminated"):
    return {"outcome": outcome, "terminal": {"reasons": {"box_settled": settled}},
            "hand_contact_substeps": [{"hand_contact": {"force_norm_n": force}}]}


class ConditionalLayoutChecks(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        self.reports = {seed: report() for seed in self.protocol["seeds_in_order"]}

    def test_qualification_requires_success_and_loaded_hand(self):
        self.assertFalse(qualifies(report(settled=True, force=1.0)))
        self.assertFalse(qualifies(report(settled=False, force=2.0)))
        self.assertFalse(qualifies(report(settled=True, force=2.0,
                                          outcome="nav_timeout")))
        self.assertTrue(qualifies(report(settled=True, force=2.0)))

    def test_complete_screen_then_only_qualified_pairs(self):
        self.reports[6202] = report(settled=True, force=2.0)
        self.reports[6207] = report(settled=True, force=3.0)
        qualified, runs = expected_runs(self.protocol, self.reports)
        self.assertEqual(qualified, [6202, 6207])
        self.assertEqual(runs[:8], [(seed, "center") for seed in range(6201, 6209)])
        self.assertEqual(runs[8:], [(6202, "minus012"), (6202, "plus012"),
                                    (6207, "minus012"), (6207, "plus012")])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            expected_runs(self.protocol, {6201: self.reports[6201]})
        changed = deepcopy(self.protocol)
        changed["analysis_frozen_before_run"]["center_screen_denominator"] = 7
        with self.assertRaisesRegex(ValueError, "differs"):
            expected_runs(changed, self.reports)


if __name__ == "__main__":
    unittest.main()
