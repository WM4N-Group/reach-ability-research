"""Focused checks for source transition event and control trace consistency."""

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from audit_piper_source_transition_trace import audit


class SourceTransitionTraceCheck(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.report_path = self.root / "report.json"
        self.trace_path = self.root / "control.jsonl"
        self.sample = {
            "step": 0, "time_s": 0.0, "q": [0.0] * 18, "dq": [0.0] * 18,
            "pd_target": [0.1] * 18, "applied_joint_command": [0.4] * 18,
            "torque": [0.0] * 18, "gates": {"position": True},
            "history_valid_frames": 3, "stable_seconds": 0.5,
        }
        self.report = {
            "seed": 1, "control_dt": 0.02, "samples": 1,
            "outcome": "entry_ready_probe_only", "terminal": {},
            "events": [
                {"contract_version": 1, "event": "transition_started", "step": 0,
                 "time_s": 0.0, "source_id": "source", "object_id": "box0",
                 "source_skill": "NAV", "destination_skill": "PUSH"},
                {"contract_version": 1, "event": "transition_ready", "step": 0,
                 "time_s": 0.0, "source_id": "source", "object_id": "box0",
                 "source_skill": "NAV", "destination_skill": "PUSH",
                 "entry_state": {
                     "step": 0, "physical_time_s": 0.0, "source_id": "source",
                     "object_id": "box0", "joint_position": [0.0] * 18,
                     "joint_velocity": [0.0] * 18, "applied_position_target": [0.1] * 18,
                     "applied_torque": [0.0] * 18, "gates": {"position": True},
                     "history_valid_frames": 3, "stable_seconds": 0.5,
                 }},
            ],
        }

    def run_audit(self):
        self.report_path.write_text(json.dumps(self.report), encoding="utf-8")
        self.trace_path.write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
        return audit(self.report_path, self.trace_path)

    def test_ready_snapshot_matches_pd_target_not_actor_command(self):
        self.assertTrue(self.run_audit()["ready_probe_only"])

    def test_changed_ready_pd_target_is_rejected(self):
        self.report["events"][1]["entry_state"]["applied_position_target"][0] = 0.2
        with self.assertRaisesRegex(ValueError, "applied_position_target"):
            self.run_audit()

    def test_changed_event_time_is_rejected(self):
        self.report["events"][1]["time_s"] = 0.02
        with self.assertRaisesRegex(ValueError, "Event contract or time"):
            self.run_audit()

    def test_probe_cannot_claim_skill_started(self):
        self.report["events"].append({**self.report["events"][0], "event": "skill_started"})
        with self.assertRaisesRegex(ValueError, "READY probe"):
            self.run_audit()

    def test_runtime_error_keeps_incomplete_start_in_denominator(self):
        self.report.update(outcome="runtime_error", entry_state=None)
        self.report["events"] = self.report["events"][:1]
        result = self.run_audit()
        self.assertTrue(result["incomplete_runtime_error"])
        self.assertFalse(result["ready_probe_only"])

    def test_runtime_error_rejects_ready_snapshot(self):
        self.report["outcome"] = "runtime_error"
        with self.assertRaisesRegex(ValueError, "Runtime error has inconsistent"):
            self.run_audit()

    def test_entry_timeout_remains_distinct_from_safety_failure(self):
        self.report.update(outcome="entry_timeout", entry_state=None,
                           terminal={"time_out": True, "base_contact": False})
        self.report["events"][1] = {
            **self.report["events"][0], "event": "transition_failed",
            "reason": "ENTRY_TIMEOUT",
        }
        result = self.run_audit()
        self.assertTrue(result["entry_timeout"])
        self.assertFalse(result["pre_entry_safety_failure"])

    def test_entry_timeout_rejects_native_safety_failure(self):
        self.report.update(outcome="entry_timeout", entry_state=None,
                           terminal={"time_out": True, "base_contact": True})
        self.report["events"][1] = {
            **self.report["events"][0], "event": "transition_failed",
            "reason": "ENTRY_TIMEOUT",
        }
        with self.assertRaisesRegex(ValueError, "Entry timeout has inconsistent"):
            self.run_audit()

    def test_continuous_push_requires_activation_after_ready(self):
        self.report.update(outcome="nav_to_push_settled_no_exit", samples=2,
                           push_activation_time_s=0.0, physical_resets_after_initial=0,
                           control_events=[{"event": "push_activated", "step": 0, "time_s": 0.0}],
                           terminal={"box_settled": True, "base_contact": False})
        self.sample["push_active"] = False
        second = {**self.sample, "step": 1, "time_s": 0.02,
                  "push_active": True, "phase": "push_v212"}
        self.report_path.write_text(json.dumps(self.report), encoding="utf-8")
        self.trace_path.write_text(json.dumps(self.sample) + "\n" + json.dumps(second) + "\n",
                                   encoding="utf-8")
        self.assertTrue(audit(self.report_path, self.trace_path)["push_settled_no_exit"])
        second["push_active"] = False
        self.trace_path.write_text(json.dumps(self.sample) + "\n" + json.dumps(second) + "\n",
                                   encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Continuous PUSH outcome"):
            audit(self.report_path, self.trace_path)

    def test_runtime_error_after_push_activation_is_not_entry_failure(self):
        self.report.update(outcome="runtime_error", samples=2, entry_state={"step": 0},
                           push_activation_time_s=0.0, physical_resets_after_initial=0,
                           control_events=[{"event": "push_activated", "step": 0, "time_s": 0.0}],
                           error="stance allocation failed")
        self.sample["push_active"] = False
        second = {**self.sample, "step": 1, "time_s": 0.02, "push_active": True}
        self.report_path.write_text(json.dumps(self.report), encoding="utf-8")
        self.trace_path.write_text(json.dumps(self.sample) + "\n" + json.dumps(second) + "\n",
                                   encoding="utf-8")
        self.assertTrue(audit(self.report_path, self.trace_path)["post_entry_runtime_error"])

    def test_exit_failure_requires_settled_request_before_safety_terminal(self):
        self.report.update(outcome="native_termination_during_exit", samples=3,
                           push_activation_time_s=0.0, push_settled_time_s=0.02,
                           push_settled_state={"step": 1, "time_s": 0.02,
                                               "q": self.sample["q"], "dq": self.sample["dq"],
                                               "pd_target": self.sample["pd_target"],
                                               "torque": self.sample["torque"]},
                           physical_resets_after_initial=0,
                           control_events=[{"event": "push_activated", "step": 0, "time_s": 0.0},
                                           {"event": "native_push_settled_exit_requested",
                                            "step": 1, "time_s": 0.02}],
                           terminal={"box_settled": False, "invalid_hand_contact": True})
        self.sample["push_active"] = False
        second = {**self.sample, "step": 1, "time_s": 0.02, "push_active": True,
                  "native_push_settled": True, "exit_requested": True, "exit_hold": False}
        third = {**second, "step": 2, "time_s": 0.04}
        self.report_path.write_text(json.dumps(self.report), encoding="utf-8")
        self.trace_path.write_text("\n".join(json.dumps(row) for row in
                                               (self.sample, second, third)) + "\n", encoding="utf-8")
        self.assertTrue(audit(self.report_path, self.trace_path)["exit_safety_termination"])
        third["exit_requested"] = False
        self.trace_path.write_text("\n".join(json.dumps(row) for row in
                                               (self.sample, second, third)) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Exit safety termination"):
            audit(self.report_path, self.trace_path)

    def test_stable_extended_arm_exit_does_not_imply_nav_return(self):
        gates = {"transfer_complete": True, "velocity": True, "hand_unloaded": True,
                 "box_still_settled": True}
        self.report.update(outcome="push_exit_stable_arm_extended_no_nav", samples=3,
                           push_activation_time_s=0.0, push_settled_time_s=0.02,
                           physical_resets_after_initial=0,
                           control_events=[{"event": "push_activated", "step": 0, "time_s": 0.0},
                                           {"event": "native_push_settled_exit_requested",
                                            "step": 1, "time_s": 0.02},
                                           {"event": "exit_four_contact_braking_started_not_ready",
                                            "step": 1, "time_s": 0.02},
                                           {"event": "exit_loaded_hold_requested",
                                            "step": 2, "time_s": 0.04}],
                           exit_state={"step": 2, "time_s": 0.04,
                                       "exit_stable_gates": gates, "exit_stable_seconds": 0.5,
                                       "exit_hold": True, "exit_brake_hold": True,
                                       "q": self.sample["q"], "dq": self.sample["dq"],
                                       "pd_target": self.sample["pd_target"],
                                       "torque": self.sample["torque"]})
        self.sample["push_active"] = False
        second = {**self.sample, "step": 1, "time_s": 0.02, "push_active": True}
        third = {**second, "step": 2, "time_s": 0.04, "exit_hold": True,
                 "native_push_settled": True, "exit_stable_gates": gates,
                 "exit_stable_seconds": 0.5, "phase": "exit_loaded_hold_arm_extended"}
        self.report_path.write_text(json.dumps(self.report), encoding="utf-8")
        self.trace_path.write_text("\n".join(json.dumps(row) for row in
                                               (self.sample, second, third)) + "\n", encoding="utf-8")
        result = audit(self.report_path, self.trace_path)
        self.assertTrue(result["extended_arm_exit_stable"])
        self.assertFalse(result["return_nav_executed"])
        third["exit_stable_gates"] = {**gates, "velocity": False}
        self.trace_path.write_text("\n".join(json.dumps(row) for row in
                                               (self.sample, second, third)) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Stable extended-arm exit"):
            audit(self.report_path, self.trace_path)

    def test_preparation_before_ready_uses_actual_activation_state(self):
        self.report.update(outcome="native_termination_during_push", samples=3,
                           push_activation_time_s=0.02, physical_resets_after_initial=0,
                           control_events=[{"event": "push_activated", "step": 1, "time_s": 0.02}],
                           entry_state={"step": 1, "time_s": 0.02,
                                        "q": self.sample["q"], "dq": self.sample["dq"],
                                        "pd_target": self.sample["pd_target"],
                                        "torque": self.sample["torque"]},
                           terminal={"box_settled": False, "invalid_hand_contact": True})
        self.sample["push_active"] = False
        second = {**self.sample, "step": 1, "time_s": 0.02}
        third = {**second, "step": 2, "time_s": 0.04, "push_active": True}
        self.report["events"][1]["step"] = 1
        self.report["events"][1]["time_s"] = 0.02
        self.report["events"][1]["entry_state"]["step"] = 1
        self.report["events"][1]["entry_state"]["physical_time_s"] = 0.02
        self.report_path.write_text(json.dumps(self.report), encoding="utf-8")
        self.trace_path.write_text("\n".join(json.dumps(row) for row in
                                               (self.sample, second, third)) + "\n", encoding="utf-8")
        self.assertTrue(audit(self.report_path, self.trace_path)["push_safety_termination"])
        self.report["entry_state"]["step"] = 0
        self.report_path.write_text(json.dumps(self.report), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "PUSH activation"):
            audit(self.report_path, self.trace_path)
        self.report["entry_state"]["step"] = 1
        self.report["terminal"] = {"box_settled": False, "actual_surface_clearance": True}
        self.report_path.write_text(json.dumps(self.report), encoding="utf-8")
        self.assertTrue(audit(self.report_path, self.trace_path)["push_safety_termination"])

    def test_full_chain_requires_trace_matched_return_and_goal(self):
        names = ["push_activated", "native_push_settled_exit_requested",
                 "exit_four_contact_braking_started_not_ready", "exit_loaded_hold_requested",
                 "exit_retraction_started", "return_nav_requested_after_stowed_ready",
                 "return_nav_activated_after_three_real_history_frames",
                 "return_nav_arrival_four_contact_braking"]
        steps = [1, 2, 2, 3, 4, 5, 6, 7]
        rows = []
        for step in range(11):
            row = deepcopy(self.sample)
            row.update(step=step, time_s=step * 0.02, push_active=step > 1)
            rows.append(row)
        rows[2]["native_push_settled"] = True
        rows[4].update(exit_stable_gates={"four_loaded_feet": True}, exit_stable_seconds=0.5)
        rows[5].update(retracted_ready=True, retracted_ready_seconds=0.5)
        rows[-1].update(
            phase="return_nav_arrival_brake", native_push_settled=True,
            retracted_ready=True, retracted_ready_seconds=0.5,
            exit_stable_gates={"four_loaded_feet": True, "box_still_settled": True},
            return_nav={"active": False, "arrival_brake": True,
                        "goal_error_m": 0.03, "travel_m": 0.22},
            return_nav_stable_seconds=0.5, foot_forces=[[0, 0, 20]] * 4,
        )
        self.report.update(
            outcome="nav_push_stow_nav_target_stable", samples=len(rows),
            physical_resets_after_initial=0, push_activation_time_s=0.02,
            control_events=[{"event": name, "step": step, "time_s": step * 0.02}
                            for name, step in zip(names, steps)],
            entry_state=rows[1], push_settled_state=rows[2],
            exit_loaded_stable_state=rows[4], stowed_exit_state=rows[5],
            return_nav_final_state=rows[-1],
        )
        ready = self.report["events"][1]
        ready["step"] = 1
        ready["time_s"] = 0.02
        ready["entry_state"]["step"] = 1
        ready["entry_state"]["physical_time_s"] = 0.02

        def check():
            self.report_path.write_text(json.dumps(self.report), encoding="utf-8")
            self.trace_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                                       encoding="utf-8")
            return audit(self.report_path, self.trace_path)

        self.assertTrue(check()["full_chain_target_stable"])
        self.assertTrue(check()["return_nav_executed"])
        self.report["return_nav_final_state"] = {**rows[-1], "return_nav_stable_seconds": 0.6}
        with self.assertRaisesRegex(ValueError, "return state"):
            check()
        self.report["return_nav_final_state"] = rows[-1]
        rows[-1]["return_nav"]["goal_error_m"] = 0.06
        with self.assertRaisesRegex(ValueError, "return state"):
            check()
        rows[-1]["return_nav"]["goal_error_m"] = 0.03
        rows[-1]["foot_forces"][3] = [0, 0, 0]
        with self.assertRaisesRegex(ValueError, "return state"):
            check()
        rows[-1]["foot_forces"][3] = [0, 0, 20]
        self.report["control_events"].pop()
        with self.assertRaisesRegex(ValueError, "event sequence"):
            check()


if __name__ == "__main__":
    unittest.main()
