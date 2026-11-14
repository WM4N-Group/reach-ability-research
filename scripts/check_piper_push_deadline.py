"""Focused checks for extended-run deadline accounting."""

from copy import deepcopy
import unittest

from audit_piper_push_deadline import audit_report


def report():
    return {
        "seed": 1,
        "requested_episodes": 3,
        "completed_episodes": 3,
        "incomplete_episodes": 0,
        "successful_episodes": 2,
        "episode_length_s": 24.0,
        "termination_flag_names": ["time_out", "box_settled", "base_contact"],
        "termination_reasons": {"time_out": 0, "box_settled": 2,
                                "base_contact": 1},
        "terminal_states": [
            {"env_id": 0, "episode": 1, "elapsed_seconds": 12.0,
             "termination_flags": [False, True, False]},
            {"env_id": 1, "episode": 1, "elapsed_seconds": 12.02,
             "termination_flags": [False, True, False]},
            {"env_id": 2, "episode": 1, "elapsed_seconds": 11.0,
             "termination_flags": [False, False, True]},
        ],
    }


class DeadlineAuditTests(unittest.TestCase):
    def test_boundary_and_censored_outcome_remain_distinct(self):
        result = audit_report(report(), 12.0)
        self.assertEqual(result["observed_goal_by_deadline_in_extended_run"], 1)
        self.assertEqual(result["observed_goal_after_deadline_in_extended_run"], 1)
        self.assertEqual(result["observed_non_goal_terminal_by_deadline"], 1)
        self.assertEqual(result["unresolved_at_deadline_in_extended_run"], 1)
        self.assertEqual(result["original_deadline_acceptance"], "not_evaluated")
        self.assertFalse(result["contact_authorized"])

    def test_bad_denominator_duplicate_or_mismatched_flags_are_rejected(self):
        bad = deepcopy(report())
        bad["incomplete_episodes"] = 1
        with self.assertRaisesRegex(ValueError, "denominator"):
            audit_report(bad, 12.0)
        bad = deepcopy(report())
        bad["terminal_states"][1]["env_id"] = 0
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            audit_report(bad, 12.0)
        bad = deepcopy(report())
        bad["termination_reasons"]["box_settled"] = 1
        with self.assertRaisesRegex(ValueError, "termination counts"):
            audit_report(bad, 12.0)

    def test_incomplete_report_remains_unresolved(self):
        partial = deepcopy(report())
        partial["requested_episodes"] = 4
        partial["incomplete_episodes"] = 1
        result = audit_report(partial, 12.0)
        self.assertEqual(result["unresolved_at_deadline_in_extended_run"], 2)
        with self.assertRaisesRegex(ValueError, "deadline_s"):
            audit_report(partial, float("nan"))
        partial["episode_length_s"] = 12.0
        with self.assertRaisesRegex(ValueError, "must exceed"):
            audit_report(partial, 12.0)


if __name__ == "__main__":
    unittest.main()
