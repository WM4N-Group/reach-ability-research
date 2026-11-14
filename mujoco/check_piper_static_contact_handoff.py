"""Regression checks for static native-finger handoff eligibility."""

import unittest

import mujoco
import numpy as np

from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime
from search_piper_static_contact_handoff import (
    _candidate_loss, _contact_free_designated_face_ready, _joint2_static_load_ratio,
)


class StaticContactHandoffContract(unittest.TestCase):
    @staticmethod
    def _fingers(*, separated=True, front=True):
        return [
            {
                "body": body,
                "separated_witnesses_valid": separated,
                "box_point_in_front_region": front,
            }
            for body in ("link7", "link8")
        ]

    def test_separated_fingers_without_contact_are_ready(self):
        geometry = {"fingers": self._fingers(), "contact_samples": []}
        self.assertTrue(_contact_free_designated_face_ready(geometry))

    def test_finger_penetration_is_not_ready(self):
        geometry = {
            "fingers": self._fingers(separated=False),
            "contact_samples": [{"body": "link7", "region_matched": True}],
        }
        self.assertFalse(_contact_free_designated_face_ready(geometry))

    def test_any_robot_box_contact_is_not_ready(self):
        geometry = {
            "fingers": self._fingers(),
            "contact_samples": [{"body": "link6", "region_matched": False}],
        }
        self.assertFalse(_contact_free_designated_face_ready(geometry))

    def test_static_load_ratio_on_current_robot_model(self):
        runtime = make_movable_box_navigation_runtime(
            seed=647, box_position=np.array([1.2, 0.0, 0.1]),
            box_size=np.array([1.2, 1.2, 0.2]), box_yaw=0.0,
            box_mass=5.0, config_path=DEPLOY / "config_wbc.yaml",
        )
        dofs = np.asarray(runtime.joint_dof_adr[12:])
        unloaded = _joint2_static_load_ratio(runtime.model, runtime.data, dofs, np.zeros(3))
        reaction = np.array([-20.0, 0.0, 0.0])
        loaded = _joint2_static_load_ratio(runtime.model, runtime.data, dofs, reaction)
        jacobian = np.zeros((3, runtime.model.nv))
        mujoco.mj_jacBody(runtime.model, runtime.data, jacobian, None, runtime.model.body("end_effector").id)
        expected = abs(runtime.data.qfrc_bias[dofs[1]] - jacobian[:, dofs[1]] @ reaction) / 20.0
        self.assertAlmostEqual(loaded, expected)
        self.assertNotAlmostEqual(loaded, unloaded)
        self.assertLess(loaded, 1.0)

    def test_candidate_loss_prefers_joint2_headroom_at_equal_pose(self):
        row = {
            "position_error": 0.0, "orientation_error": 0.0,
            "nonhand_clearance": 0.07, "self_clearance": 0.07,
            "joint2_static_load_ratio": 0.7,
        }
        low_load = _candidate_loss(row, 0.0, 0.8)
        row["joint2_static_load_ratio"] = 0.9
        self.assertLess(low_load, _candidate_loss(row, 0.0, 0.8))


if __name__ == "__main__":
    unittest.main()
