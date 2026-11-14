"""Checks for fixed-snapshot remaining-approach diagnostics."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from search_piper_precontact_candidates import SnapshotSearch


class SnapshotSearchContract(unittest.TestCase):
    def test_missing_complete_final_state_is_rejected(self):
        snapshot = SnapshotSearch.__new__(SnapshotSearch)
        snapshot.path = "legacy.json"
        snapshot.result = {
            "passed": True, "safety": {"first_box_contact": None},
            "motion": {"final_joint_position": [0.8] * 6},
        }
        with self.assertRaisesRegex(ValueError, "Missing complete final state"):
            snapshot.activate_final_state()

    def test_remaining_path_starts_at_measured_final_arm(self):
        snapshot = SnapshotSearch.__new__(SnapshotSearch)
        snapshot.path = "recorded.json"
        snapshot.result = {
            "candidate": {"joint_solution": [0.5] * 6},
            "motion": {"final_joint_position": [0.8] * 6},
            "scene": {"box_size": [0.24, 0.24, 0.24]},
        }
        snapshot.hand_point = "piper"
        snapshot.hand_body = "end_effector"
        snapshot.hand_offset = np.zeros(3)
        snapshot.target_orientation = None
        snapshot.box_position = np.zeros(3)
        snapshot.rotation = np.eye(3)
        snapshot.base = np.zeros(3)
        snapshot.starting_arm = np.full(6, 0.8)
        snapshot.final_state_active = True
        snapshot.thresholds = {
            "push_approach_distance": 0.03,
            "self_clearance": 0.05,
            "environment_clearance": 0.05,
            "quasistatic_support_margin": 0.02,
            "joint_limit_margin": 0.05,
        }
        solution = np.full(6, 0.9)
        snapshot.oracle = SimpleNamespace(
            solve=Mock(return_value=SimpleNamespace(
                kinematic_feasible=True, position_error=0.0, orientation_error=0.0,
                joint_limit_margin=0.2, joint_solution=solution,
            )),
            hand_position=Mock(return_value=np.array([-0.185, 0.0, 0.02])),
        )
        checked = []

        def measure(base, arm, *, required_clearance):
            checked.append(arm.copy())
            return SimpleNamespace(minimum_clearance=0.07)

        snapshot.self_checker = SimpleNamespace(
            evaluate=measure, linear_path_sampling_motion_bound=Mock(return_value=0.005),
        )
        snapshot.environment_checker = SimpleNamespace(
            evaluate=measure, linear_path_sampling_motion_bound=Mock(return_value=0.005),
        )
        snapshot.support_checker = SimpleNamespace(
            evaluate_configuration=Mock(return_value=SimpleNamespace(support_margin=0.03)),
        )
        result = snapshot.evaluate(solution, np.array([-0.185, 0.0, 0.02]), 3, from_held_pose=True)
        np.testing.assert_array_equal(checked[0], np.full(6, 0.8))
        np.testing.assert_array_equal(checked[-1], solution)
        self.assertEqual(result["path_start"], "measured_terminal_state")
        self.assertAlmostEqual(result["continuous_environment_clearance_lower_bound"], 0.065)
        self.assertTrue(result["passed"])
        snapshot.result["motion"]["final_joint_position"] = [float("nan")] * 6
        with self.assertRaisesRegex(ValueError, "Final arm replay mismatch"):
            snapshot.evaluate(solution, np.array([-0.185, 0.0, 0.02]), 3, from_held_pose=True)

    def test_designated_hand_approach_separates_finger_and_nonhand_clearance(self):
        snapshot = SnapshotSearch.__new__(SnapshotSearch)
        snapshot.path = "recorded.json"
        snapshot.result = {
            "candidate": {"joint_solution": [0.5] * 6},
            "motion": {"final_joint_position": [0.8] * 6},
            "scene": {"box_size": [0.24, 0.24, 0.24]},
        }
        snapshot.hand_point = "piper"
        snapshot.hand_body = "end_effector"
        snapshot.hand_offset = np.zeros(3)
        snapshot.target_orientation = None
        snapshot.box_position = np.zeros(3)
        snapshot.rotation = np.eye(3)
        snapshot.base = np.zeros(3)
        snapshot.starting_arm = np.full(6, 0.8)
        snapshot.final_state_active = True
        snapshot.thresholds = {
            "push_approach_distance": 0.03,
            "self_clearance": 0.05,
            "environment_clearance": 0.05,
            "quasistatic_support_margin": 0.02,
            "joint_limit_margin": 0.05,
        }
        solution = np.full(6, 0.9)
        snapshot.oracle = SimpleNamespace(
            solve=Mock(return_value=SimpleNamespace(
                kinematic_feasible=True, position_error=0.0, orientation_error=0.0,
                joint_limit_margin=0.2, joint_solution=solution,
            )),
            hand_position=Mock(return_value=np.array([-0.17, 0.0, 0.02])),
        )

        def checker(clearance, bound):
            return SimpleNamespace(
                evaluate=Mock(return_value=SimpleNamespace(minimum_clearance=clearance)),
                linear_path_sampling_motion_bound=Mock(return_value=bound),
            )

        snapshot.self_checker = checker(0.07, 0.005)
        snapshot.environment_checker = checker(0.04, 0.005)
        snapshot.finger_environment_checker = checker(0.04, 0.005)
        snapshot.nonhand_environment_checker = checker(0.08, 0.005)
        snapshot.support_checker = SimpleNamespace(
            evaluate_configuration=Mock(return_value=SimpleNamespace(support_margin=0.03)),
        )
        snapshot._read_contact_geometry = Mock(return_value={
            "fingers": [
                {
                    "body": body,
                    "separated_witnesses_valid": True,
                    "box_point_in_front_region": True,
                }
                for body in ("link7", "link8")
            ],
            "contact_samples": [],
        })
        result = snapshot.evaluate(
            solution,
            np.array([-0.17, 0.0, 0.02]),
            3,
            from_held_pose=True,
            diagnose_designated_hand_approach=True,
        )
        self.assertLess(result["minimum_environment_clearance"], 0.05)
        self.assertAlmostEqual(
            result["designated_hand_approach"]["continuous_finger_clearance_lower_bound"],
            0.035,
        )
        self.assertAlmostEqual(
            result["designated_hand_approach"]["continuous_nonhand_environment_clearance_lower_bound"],
            0.075,
        )
        self.assertAlmostEqual(result["selected_clearance_margin"], 0.015)
        self.assertTrue(result["designated_hand_approach"]["passed"])
        self.assertTrue(result["passed"])
        self.assertFalse(result["designated_hand_approach"]["contact_execution_enabled"])
        nav_result = snapshot.evaluate(
            solution,
            np.array([-0.17, 0.0, 0.02]),
            3,
            diagnose_designated_hand_approach=True,
        )
        self.assertEqual(nav_result["path_start"], "nav_snapshot")
        self.assertTrue(nav_result["designated_hand_approach"]["passed"])
        self.assertTrue(nav_result["passed"])


if __name__ == "__main__":
    unittest.main()