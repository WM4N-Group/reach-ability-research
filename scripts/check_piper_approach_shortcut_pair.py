"""Focused provenance checks for the approach-shortcut pair audit."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from audit_piper_approach_shortcut_pair import audit, sha256


def report() -> dict:
    names = ["time_out", "box_settled"]
    return {
        "seed": 3701, "num_envs": 8, "episodes_per_env": 1,
        "episode_length_s": 24.0, "requested_episodes": 8,
        "completed_episodes": 8, "incomplete_episodes": 0,
        "successful_episodes": 0, "termination_flag_names": names,
        "termination_reasons": {"time_out": 8, "box_settled": 0},
        "terminal_states": [
            {"env_id": env, "episode": 1, "elapsed_seconds": 24.0,
             "termination_flags": [True, False], "box_displacement": [0.1, 0.0, 0.0],
             "geometry_minimum_observed": 0.03, "geometry_observed_steps": 1200,
             "safe_approach_complete": True}
            for env in range(8)
        ],
        "checkpoint_sha256": "checkpoint", "evaluation_sha256": "evaluator",
        "control_sha256": {"box_push_ik.py": "ik"}, "actual_physics": {"box_mass": 5},
        "failure_history_step_dt": 0.02, "inspect_env_index": 2,
        "failure_history_sample_phase": "pre_env_step",
        "trace_env2": [
            {"step": step, "env_id": 2, "safe_approach_complete": step == 1,
             "hand_contact": step == 1, "geometry_clearance": 0.03}
            for step in range(2)
        ],
        "push_contact_steps": [0] * 8,
        "unclassified_hand_contact_steps": [0] * 8,
        "max_torque_limit_ratio": 0.8,
    }


class ApproachShortcutPairCheck(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = {name: self.root / f"{name}.json" for name in
                      ("baseline_plan", "baseline_report", "pilot_plan", "pilot_report", "exit")}
        command = ["isaac-python", "baseline/evaluate.py", "--seed", "3701",
                   "--output-json", "baseline/report.json"]
        self.baseline_plan = {
            "command": command, "approach_sha256": "original", "checkpoint_sha256": "checkpoint",
            "evaluator_sha256": "evaluator", "ik_sha256": "ik", "push_control_sha256": "control",
            "push_config_sha256": "config",
        }
        self.write("baseline_plan", self.baseline_plan)
        self.pilot_plan = {
            **self.baseline_plan,
            "command": ["isaac-python", "pilot/evaluate.py", "--seed", "3701",
                        "--output-json", "pilot/report.json"],
            "source_plan_sha256": sha256(self.paths["baseline_plan"]),
            "source_approach_sha256": "original", "candidate_approach_sha256": "shortcut",
            "removed_waypoint_index": 18,
            "screen_result": {"static_pass": True, "edge_start_index": 17, "edge_end_index": 19},
        }
        self.write("pilot_plan", self.pilot_plan)
        self.write("baseline_report", report())
        self.write("pilot_report", report())
        self.write("exit", {"returncode": 0, "report_exists": True,
                            "report_sha256": sha256(self.paths["pilot_report"])})

    def write(self, name: str, value: dict) -> None:
        self.paths[name].write_text(json.dumps(value))

    def run_audit(self) -> dict:
        return audit(*(self.paths[name] for name in
                       ("baseline_plan", "baseline_report", "pilot_plan", "pilot_report", "exit")))

    def test_complete_pair(self) -> None:
        result = self.run_audit()
        self.assertEqual(len(result["per_env"]), 8)
        self.assertEqual(result["observed_goal_by_12_s_delta_in_extended_run"], 0)
        self.assertEqual(result["paired_inspected_trace_delta_s"]["first_legal_hand_contact_s"], 0.0)
        self.assertEqual(result["baseline"]["inspected_trace"]["first_legal_hand_contact_s"], 0.02)
        self.assertIsNone(result["baseline"]["inspected_trace"]["minimum_supported_feet"])
        self.assertIn("unavailable", result["telemetry_coverage"]["per_env_support"])
        self.assertFalse(result["contact_authorized"])

    def test_inspected_support_uses_force_threshold(self) -> None:
        pilot = report()
        pilot["trace_env2"][0]["foot_contact_force_z"] = [3.0, 3.0, 3.0, 3.0]
        pilot["trace_env2"][1]["foot_contact_force_z"] = [2.0, 2.1, 3.0, 0.0]
        self.write("pilot_report", pilot)
        self.write("exit", {"returncode": 0, "report_exists": True,
                            "report_sha256": sha256(self.paths["pilot_report"])})
        inspected = self.run_audit()["candidate"]["inspected_trace"]
        self.assertEqual(inspected["support_observed_steps"], 2)
        self.assertEqual(inspected["minimum_supported_feet"], 2)
        self.assertEqual(inspected["steps_below_three_supported_feet"], 1)

    def test_rejects_changed_evaluation_argument(self) -> None:
        self.pilot_plan["command"][3] = "3702"
        self.write("pilot_plan", self.pilot_plan)
        with self.assertRaisesRegex(ValueError, "Evaluator arguments differ"):
            self.run_audit()

    def test_accepts_another_single_waypoint_candidate(self) -> None:
        self.pilot_plan["removed_waypoint_index"] = 15
        self.pilot_plan["screen_result"] = {
            "static_pass": True, "edge_start_index": 14, "edge_end_index": 16,
        }
        self.write("pilot_plan", self.pilot_plan)
        self.assertEqual(self.run_audit()["removed_waypoint_indices"], [15])

    def test_accepts_screened_long_edge(self) -> None:
        self.pilot_plan["removed_waypoint_index"] = None
        self.pilot_plan["removed_waypoint_indices"] = list(range(2, 14))
        self.pilot_plan["screen_result"] = {
            "static_pass": True, "edge_start_index": 1, "edge_end_index": 14,
        }
        self.write("pilot_plan", self.pilot_plan)
        self.assertEqual(self.run_audit()["removed_waypoint_indices"], list(range(2, 14)))

    def test_rejects_changed_runtime_physics(self) -> None:
        pilot = report()
        pilot["actual_physics"]["box_mass"] = 6
        self.write("pilot_report", pilot)
        self.write("exit", {"returncode": 0, "report_exists": True,
                            "report_sha256": sha256(self.paths["pilot_report"])})
        with self.assertRaisesRegex(ValueError, "Runtime policy, control, or physics differs"):
            self.run_audit()


if __name__ == "__main__":
    unittest.main()
