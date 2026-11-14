"""Focused checks for phase and float-tolerance handling in command-chain audits."""

from __future__ import annotations

import unittest

from audit_piper_push_command_chain import audit_report


def sample(desired: float, pre: float, post: float, geometric: float, velocity: float) -> dict:
    def joints(first: float) -> list[float]:
        return [first, 0.0, 0.0, 0.0, 0.0, 0.0]

    return {"debug_pose_desired": joints(desired),
            "debug_reference_pre_geometry": joints(pre),
            "debug_reference_post_geometry": joints(post),
            "arm_joint_reference": joints(post),
            "debug_gate_geometric_ready": geometric,
            "debug_gate_velocity_ready": velocity}


def report() -> dict:
    return {"failure_history_sample_phase":
            "pre_env_step; controller targets describe previous command; "
            "next_policy_action is the next action",
            "failure_history_step_dt": 0.02, "failure_history_steps": 3,
            "failure_histories": [{"env_id": 2, "episode": 1,
                                   "pre_step_samples": [
                                       sample(1.0 + 1e-10, 1.0, 1.0, 1.0, 1.0),
                                       sample(2.0, 1.0, 1.1, 1.0, 1.0),
                                       sample(2.0, 1.0, 1.0, 0.0, 1.0)]}]}


class CommandChainAuditTests(unittest.TestCase):
    def test_phase_aware_counts_and_tolerance(self):
        result = audit_report(report())
        self.assertEqual(result["totals"], {
            "samples": 3, "ik_pre_exact_different": 3,
            "ik_pre_over_tolerance": 2, "pre_post_exact_different": 1,
            "pre_post_over_tolerance": 1, "post_reference_exact_equal": 3})
        self.assertEqual(result["per_env"][0]["longest_both_ready_run"], 2)
        self.assertEqual(result["per_env"][0]["pre_post_over_tolerance"], 1)

    def test_wrong_phase_or_nonbinary_gate_is_rejected(self):
        data = report()
        data["failure_history_sample_phase"] = "post_env_step"
        with self.assertRaisesRegex(ValueError, "pre-step"):
            audit_report(data)
        data = report()
        data["failure_histories"][0]["pre_step_samples"][0]["debug_gate_geometric_ready"] = 0.5
        with self.assertRaisesRegex(ValueError, "binary gate"):
            audit_report(data)


if __name__ == "__main__":
    unittest.main()
