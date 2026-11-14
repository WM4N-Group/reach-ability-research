"""Contract checks for explicit MuJoCo contact-model parameter declarations."""

from __future__ import annotations

from pathlib import Path
import unittest

import mujoco
import numpy as np

from reconfigurable_navigation.piper_box_runtime import make_episode


ROOT = Path(__file__).resolve().parent
POLICY = ROOT / "deploy/policy/go2_piper/policy.pt"


class PiperContactModelContract(unittest.TestCase):
    def make_runtime(self, **parameters):
        return make_episode(
            "push",
            str(POLICY),
            0,
            push_ik_mode="pose",
            native_collisions=True,
            **parameters,
        )

    def test_explicit_parameters_reach_compiled_model_without_stepping(self):
        runtime = self.make_runtime(
            contact_time_constant=0.03,
            contact_damping_ratio=1.0,
            contact_impedance=0.7,
            contact_width=0.01,
            contact_margin=0.002,
        )
        self.assertEqual(runtime.data.time, 0.0)
        np.testing.assert_allclose(runtime.model.geom_solref[:, 0], 0.03)
        np.testing.assert_allclose(runtime.model.geom_solref[:, 1], 1.0)
        np.testing.assert_allclose(runtime.model.geom_solimp[:, 0], 0.7)
        np.testing.assert_allclose(runtime.model.geom_solimp[:, 2], 0.01)

    def test_contact_margin_scope_is_robot_only(self):
        margin = 0.002
        runtime = self.make_runtime(contact_margin=margin)
        box = runtime.model.geom("push_box").id
        floor = runtime.model.geom("floor").id
        robot_bodies = {
            body_id
            for body_id in range(runtime.model.nbody)
            if runtime.model.body(body_id).name not in ("world", "push_box")
        }
        robot_geometries = [
            geometry for geometry in range(runtime.model.ngeom)
            if int(runtime.model.geom_bodyid[geometry]) in robot_bodies
        ]
        self.assertTrue(robot_geometries)
        np.testing.assert_allclose(runtime.model.geom_margin[robot_geometries], margin)
        self.assertEqual(runtime.model.geom_margin[box], 0.0)
        self.assertEqual(runtime.model.geom_margin[floor], 0.0)

    def test_native_pose_contract_is_preserved(self):
        runtime = self.make_runtime()
        self.assertEqual(runtime.arm.hand_body, runtime._body_id("end_effector"))
        np.testing.assert_array_equal(runtime.arm.hand_offset, np.zeros(3))
        self.assertTrue(runtime.arm.align_hand_orientation)
        self.assertAlmostEqual(runtime.arm.hand_pitch, 0.8)
        self.assertAlmostEqual(runtime.arm.approach_distance, 0.03)

    def test_invalid_contact_parameters_are_rejected(self):
        for name, value in (
            ("contact_time_constant", 0.009),
            ("contact_damping_ratio", 0.0),
            ("contact_impedance", 0.0),
            ("contact_width", 0.0),
            ("contact_margin", 0.02),
        ):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.make_runtime(**{name: value})


if __name__ == "__main__":
    unittest.main()
