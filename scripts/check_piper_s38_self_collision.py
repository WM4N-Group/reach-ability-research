"""Focused checks for the paired s38 self-collision evidence gate."""

from copy import deepcopy
import unittest

from audit_piper_s38_self_collision import ASSET, compare_reports


def reports():
    common = {
        "task": "PUSH", "seed": 7204, "num_envs": 1, "episodes_per_env": 1,
        "episode_length_s": 14.0, "box_mass": 6.0, "box_friction": 0.35,
        "box_height": 0.2, "checkpoint_sha256": "a" * 64,
        "evaluation_sha256": "b" * 64, "evaluation_helpers_sha256": "c" * 64,
        "control_sha256": {"control": "d" * 64},
        "actor_policy_sha256": "e" * 64, "deployment_actor_sha256": "f" * 64,
        "actual_physics": {"box_size": [1.25, 0.95, 0.2],
                           "controller_contract": {"ik_clearance_minimum": 0.1},
                           "robot_asset_sha256": {ASSET: "1" * 64, "robot.usd": "2" * 64}},
        "completed_episodes": 1, "incomplete_episodes": 0, "successful_episodes": 0,
        "termination_reasons": {"time_out": 1, "base_contact": 0},
        "terminal_states": [{"elapsed_seconds": 14.0, "box_displacement": [0.1, 0, 0]}],
    }
    old = deepcopy(common)
    new = deepcopy(common)
    new["actual_physics"]["robot_asset_sha256"][ASSET] = "3" * 64
    new["termination_reasons"] = {"time_out": 0, "base_contact": 1,
                                  "arm_body_clearance": 0}
    new["terminal_states"] = [{
        "elapsed_seconds": 7.82, "box_displacement": [0.00002, 0, 0],
        "hand_contact_valid": False, "safe_approach_complete": True,
        "hand_force": [0.0, 0.0, 0.0],
        "body_contact_forces": [[-2.0, 3.0, 0.0], [2.0, -3.0, 0.0]],
        "ik_clearance_distance": 0.145, "ik_clearance_residual": 0.0,
    }]
    new["contact_body_names"] = ["base", "link6"]
    new["push_contact_steps"] = [0.0]
    return old, new


class S38EvidenceChecks(unittest.TestCase):
    def test_only_articulation_toggle_and_early_base_contact_pass(self):
        old, new = reports()
        result = compare_reports(old, new)
        self.assertEqual(result["replay_terminal_s"], 7.82)

    def test_other_asset_or_physics_change_is_rejected(self):
        old, new = reports()
        new["actual_physics"]["robot_asset_sha256"]["robot.usd"] = "4" * 64
        with self.assertRaisesRegex(ValueError, "other than the articulation"):
            compare_reports(old, new)
        old, new = reports()
        new["actual_physics"]["box_size"][0] = 2.0
        with self.assertRaisesRegex(ValueError, "outside the asset hash table"):
            compare_reports(old, new)

    def test_hand_contact_or_missing_opposed_force_is_rejected(self):
        old, new = reports()
        new["push_contact_steps"] = [1.0]
        with self.assertRaisesRegex(ValueError, "before valid hand contact"):
            compare_reports(old, new)
        old, new = reports()
        new["terminal_states"][0]["body_contact_forces"][1][0] = 1.0
        with self.assertRaisesRegex(ValueError, "opposed"):
            compare_reports(old, new)

    def test_center_distance_proxy_must_still_pass_at_failure(self):
        old, new = reports()
        new["terminal_states"][0]["ik_clearance_distance"] = 0.09
        with self.assertRaisesRegex(ValueError, "center-distance proxy"):
            compare_reports(old, new)


if __name__ == "__main__":
    unittest.main()
