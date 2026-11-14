"""Check control-step alignment and loaded height margins."""

from copy import deepcopy
import unittest

from audit_piper_hand_contact_success_controls import classify
from audit_piper_loaded_boundary_clock import project


def make_case(illegal_index):
    rows = []
    for index in range(12):
        force = 0.0 if index < 2 else 2.0
        height = 0.11 if index == illegal_index else (0.08 if index >= 7 else 0.07)
        rows.append({
            "push_control_step": index // 4 + 1,
            "physics_substep": index % 4 + 1,
            "hand_contact": {
                "force_norm_n": force,
                "contact_pos_box_m": None if force == 0 else [-0.6, 0.0, height],
                "contact_to_hand_m": None if force == 0 else 0.01,
                "tip_radius_limit_m": 0.07,
                "resisting_force_n": force,
                "box_size_m": [1.2, 1.2, 0.2],
                "height_margin_m": 0.01,
            },
            "arm_approach_index": 1,
            "motion_ready": True,
        })
    event = None if illegal_index is None else classify(rows[illegal_index], 0.005)
    report = {
        "schema_version": 26,
        "push_executed_steps": 3,
        "scene_runtime_observation": {"physics_dt_s": 0.005},
        "hand_contact_substep_contract": {
            "control_decimation": 4,
            "sample_phase": "after_scene_update_before_control_step_termination",
        },
        "hand_contact_substeps": rows,
    }
    phase = {
        "seed": 6403,
        "layout_tag": "plus012",
        "report_sha256": "synthetic",
        "push_physics_substeps": 12,
        "first_illegal": None if event is None else {
            "event": deepcopy(event),
            "bout_kind": "first_contact",
            "loaded_bout_offset_substeps": illegal_index - 2,
        },
    }
    cohort = {
        "outcome": "push_terminated",
        "terminal_reasons": ["box_settled" if event is None else "invalid_hand_contact"],
        "push_physics_substeps": 12,
        "sensor_force_above_1_n_samples": 10,
        "illegal_hand_substeps": int(event is not None),
        "first_illegal_hand_event": event,
    }
    return report, phase, cohort


class BoundaryClockTests(unittest.TestCase):
    def test_last_legal_control_end_precedes_late_illegal_substep(self):
        result = project(*make_case(10))
        anchors = result["first_illegal"]["prior_legal_loaded_control_step_ends_in_same_bout"]
        self.assertEqual(len(anchors), 2)
        self.assertAlmostEqual(anchors[0]["control_step_end_s"], 0.02)
        self.assertAlmostEqual(anchors[0]["lead_to_first_illegal_s"], 0.035)
        self.assertAlmostEqual(anchors[-1]["control_step_end_s"], 0.04)
        self.assertAlmostEqual(anchors[-1]["lead_to_first_illegal_s"], 0.015)
        self.assertAlmostEqual(anchors[-1]["height_margin_box_local_m"], 0.0101)

    def test_success_has_no_first_illegal_or_prior_anchors(self):
        result = project(*make_case(None))
        self.assertIsNone(result["first_illegal"])
        self.assertEqual(result["loaded_control_step_end_count"], 3)

    def test_changed_phase_event_is_rejected(self):
        report, phase, cohort = make_case(10)
        phase["first_illegal"]["event"]["push_elapsed_s"] += 0.005
        with self.assertRaises(ValueError):
            project(report, phase, cohort)


if __name__ == "__main__":
    unittest.main()
