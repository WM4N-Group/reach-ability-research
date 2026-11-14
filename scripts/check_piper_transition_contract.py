"""Regression checks for the normalized transition export audit."""

import copy
import unittest

from audit_piper_transition_contract import audit


def ready_state(time_s=2.0):
    return {
        "sample_time_s": time_s,
        "remaining_s": 48.0 - time_s,
        "base_pos_m": [0.0, 0.0, 0.3],
        "base_lin_vel_m_s": [0.0, 0.0, 0.0],
        "base_ang_vel_rad_s": [0.0, 0.0, 0.0],
        "foot_normal_force_n": [50.0] * 4,
        "joint_pos_rad": [0.0] * 18,
        "joint_vel_rad_s": [0.0] * 18,
        "joint_effort_ratio": [0.1] * 18,
        "hand_box_rel_pos_m": [0.2, 0.0, 0.1],
        "min_clearance_m": 0.05,
        "observation_history_valid": True,
    }


def cohort():
    source_keys = ("nav_actor", "push_actor", "push_legs", "transition_control",
                   "evaluator", "assets", "task")
    return {
        "schema_version": 1,
        "episode_budget_s": 48.0,
        "requested_episodes": 3,
        "requested_episode_keys": [{"env_id": env, "episode": 1} for env in range(3)],
        "source_hashes": {name: "a" * 64 for name in source_keys},
        "state_conventions": {
            "joint_names": [f"joint_{index}" for index in range(18)],
            "foot_order": ["FL", "FR", "RL", "RR"],
            "base_position_frame": "environment_local",
            "base_velocity_frame": "world",
            "hand_box_relative_frame": "base_link",
            "clearance_definition": "minimum_arm_to_base_surface_distance_m",
        },
        "episodes": [
            {"env_id": 0, "episode": 1, "terminal_phase": "nav",
             "terminal_reason": "nav_timeout", "terminal_time_s": 1.0, "events": []},
            {"env_id": 1, "episode": 1, "terminal_phase": "transition",
             "terminal_reason": "support_lost", "terminal_time_s": 1.5,
             "events": [{"name": "transition_started", "time_s": 1.0},
                        {"name": "transition_failed", "time_s": 1.5}]},
            {"env_id": 2, "episode": 1, "terminal_phase": "push",
             "terminal_reason": "box_settled", "terminal_time_s": 20.0,
             "events": [{"name": "transition_started", "time_s": 1.0},
                        {"name": "transition_ready", "time_s": 2.0,
                         "state": ready_state()},
                        {"name": "skill_started", "time_s": 2.0}]},
        ],
    }


class TransitionContractCheck(unittest.TestCase):
    def test_full_denominator_and_ready_state(self):
        result = audit(cohort())
        self.assertEqual(result["terminal_phase_counts"],
                         {"nav": 1, "push": 1, "transition": 1})
        self.assertEqual(result["transition_ready_count"], 1)
        self.assertEqual(result["ready_with_valid_observation_history"], 1)

    def test_missing_episode_is_rejected(self):
        data = cohort()
        data["episodes"].pop()
        with self.assertRaisesRegex(ValueError, "full NAV-start denominator"):
            audit(data)

    def test_duplicate_episode_is_rejected(self):
        data = cohort()
        data["episodes"][1]["env_id"] = 0
        with self.assertRaisesRegex(ValueError, "Duplicate episode"):
            audit(data)

    def test_wrong_episode_identity_is_rejected(self):
        data = cohort()
        data["episodes"][1]["env_id"] = 4
        with self.assertRaisesRegex(ValueError, "launch manifest"):
            audit(data)

    def test_future_state_is_rejected(self):
        data = cohort()
        data["episodes"][2]["events"][1]["state"]["sample_time_s"] = 3.0
        with self.assertRaisesRegex(ValueError, "different sample time"):
            audit(data)

    def test_missing_coordinate_convention_is_rejected(self):
        data = cohort()
        del data["state_conventions"]["hand_box_relative_frame"]
        with self.assertRaisesRegex(ValueError, "hand_box_relative_frame"):
            audit(data)

    def test_task_clock_reset_is_rejected(self):
        data = cohort()
        data["episodes"][2]["events"][1]["state"]["remaining_s"] = 48.0
        with self.assertRaisesRegex(ValueError, "reset or inconsistent task clock"):
            audit(data)

    def test_push_before_ready_is_rejected(self):
        data = cohort()
        data["episodes"][2]["events"] = [
            {"name": "transition_started", "time_s": 1.0},
            {"name": "skill_started", "time_s": 2.0},
        ]
        with self.assertRaisesRegex(ValueError, "without current READY"):
            audit(data)

    def test_refresh_and_revocation_follow_source_event_contract(self):
        data = cohort()
        data["episodes"][2]["events"] = [
            {"name": "transition_started", "time_s": 1.0},
            {"name": "transition_ready", "time_s": 2.0, "state": ready_state()},
            {"name": "transition_ready_refreshed", "time_s": 2.2,
             "state": ready_state(2.2)},
            {"name": "transition_ready_revoked", "time_s": 2.4},
            {"name": "transition_ready", "time_s": 2.6, "state": ready_state(2.6)},
            {"name": "skill_started", "time_s": 2.6},
        ]
        result = audit(data)
        self.assertEqual(result["ready_refresh_events"], 1)
        self.assertEqual(result["ready_revocation_events"], 1)

    def test_revoked_ready_cannot_start_push(self):
        data = cohort()
        data["episodes"][2]["events"].insert(2,
            {"name": "transition_ready_revoked", "time_s": 2.0})
        with self.assertRaisesRegex(ValueError, "without current READY"):
            audit(data)

    def test_invalid_history_is_counted_without_authorizing(self):
        data = copy.deepcopy(cohort())
        data["episodes"][2]["events"][1]["state"]["observation_history_valid"] = False
        result = audit(data)
        self.assertEqual(result["ready_without_valid_observation_history"], 1)
        self.assertIn("no reachability calibration or online authorization", result["scope"])

    def test_legacy_report_is_not_a_transition_export(self):
        with self.assertRaisesRegex(ValueError, "normalized transition contract"):
            audit({"schema_version": 30, "handoff": {"motion_ready": False}})


if __name__ == "__main__":
    unittest.main()
