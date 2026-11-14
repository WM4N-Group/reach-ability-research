"""Checks for loaded-bout window and first-illegal event accounting."""

import unittest

from audit_piper_hand_contact_success_controls import classify
from audit_piper_phase_window_holdout import project


def make_case(illegal_index):
    forces = [0.0, 2.0, 2.0, 2.0, 0.0, 2.0, 2.0, 0.0]
    rows = []
    for index, force in enumerate(forces):
        rows.append({
            "push_control_step": index // 4 + 1,
            "physics_substep": index % 4 + 1,
            "arm_approach_index": 1,
            "motion_ready": True,
            "hand_contact": {
                "force_norm_n": force,
                "contact_pos_box_m": (None if force == 0 else
                                      [-0.6, 0.0, 0.11 if index == illegal_index else 0.07]),
                "contact_to_hand_m": None if force == 0 else 0.01,
                "tip_radius_limit_m": 0.07,
                "resisting_force_n": force,
                "box_size_m": [1.2, 1.2, 0.2],
                "height_margin_m": 0.01,
            },
        })
    event = classify(rows[illegal_index], 0.005)
    return ({
        "schema_version": 26,
        "push_executed_steps": 2,
        "scene_runtime_observation": {"physics_dt_s": 0.005},
        "hand_contact_substep_contract": {
            "control_decimation": 4,
            "sample_phase": "after_scene_update_before_control_step_termination",
        },
        "hand_contact_substeps": rows,
    }, {
        "seed": 6401,
        "layout_tag": "center",
        "outcome": "push_terminated",
        "terminal_reasons": ["invalid_hand_contact"],
        "report_sha256": "synthetic",
        "push_physics_substeps": 8,
        "sensor_force_above_1_n_samples": 5,
        "illegal_hand_substeps": 1,
        "first_illegal_hand_event": event,
    })


class PhaseWindowTests(unittest.TestCase):
    def test_late_first_bout_event_is_a_frozen_window_miss(self):
        report, record = make_case(3)
        result = project(report, record, 2)
        self.assertEqual(result["loaded_bout_count"], 2)
        self.assertEqual(result["recontact_bout_count"], 1)
        self.assertEqual(result["longest_interbout_unloaded_substeps"], 1)
        self.assertEqual(result["first_illegal"]["bout_kind"], "first_contact")
        self.assertEqual(result["first_illegal"]["loaded_bout_offset_substeps"], 2)
        self.assertFalse(result["first_illegal"]["inside_frozen_window"])
        self.assertEqual(result["window_bouts_without_illegal"], 2)

    def test_second_recontact_substep_is_hit_but_first_bout_is_unmarked(self):
        report, record = make_case(6)
        result = project(report, record, 2)
        self.assertEqual(result["first_illegal"]["bout_kind"], "recontact")
        self.assertEqual(result["first_illegal"]["loaded_bout_offset_substeps"], 1)
        self.assertTrue(result["first_illegal"]["inside_frozen_window"])
        self.assertEqual(result["window_bouts_with_illegal"], 1)
        self.assertEqual(result["window_bouts_without_illegal"], 1)


if __name__ == "__main__":
    unittest.main()
