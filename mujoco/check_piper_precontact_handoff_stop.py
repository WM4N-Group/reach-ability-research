"""Regression checks for diagnostic contact continuation stopping."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from probe_piper_precontact_handoff_response import _simulate_target_with_arm_bias, _stop_reason


class PiperPrecontactHandoffStopContract(unittest.TestCase):
    def test_arm_bias_is_bounded_and_does_not_change_leg_targets(self):
        captured = []
        runtime = SimpleNamespace(
            data=SimpleNamespace(qpos=np.zeros(18)),
            diagnostic_gravity_data=SimpleNamespace(qpos=np.zeros(18), qvel=np.zeros(18), qfrc_bias=np.r_[np.zeros(12), [-20.0] * 6]),
            joint_dof_adr=np.arange(18), kp=np.ones(18) * 40,
            joint_low=np.ones(18) * -1, joint_high=np.ones(18),
            diagnostic_arm_bias_scale=0.1, diagnostic_arm_bias_limit=0.04,
            diagnostic_original_simulate_target=lambda target: captured.append(target.copy()),
            model=object(),
        )
        original = np.zeros(18)
        with patch("probe_piper_precontact_handoff_response.mujoco.mj_forward"):
            _simulate_target_with_arm_bias(runtime, original)
        np.testing.assert_array_equal(original, np.zeros(18))
        np.testing.assert_array_equal(captured[0][:12], original[:12])
        np.testing.assert_allclose(captured[0][12:], -0.04)
        np.testing.assert_array_equal(runtime.diagnostic_arm_target, captured[0][12:])

    def test_first_contact_stops_before_following_steps(self):
        support = SimpleNamespace(supporting_feet=("FL", "FR", "RL"), support_margin=0.04)
        self.assertEqual(_stop_reason([{"body": "link7"}], support, 0.0, 0.08, 0.08), "first_box_contact")

    def test_box_motion_and_support_loss_stop(self):
        support = SimpleNamespace(supporting_feet=("FL", "FR", "RL"), support_margin=0.04)
        self.assertEqual(_stop_reason([], support, 0.0011, 0.08, 0.08), "box_displacement_exceeded")
        self.assertIsNone(_stop_reason([], support, 0.001, 0.08, 0.08))
        self.assertEqual(_stop_reason([], support, 0.0, 0.049, 0.08), "self_clearance_lost")
        self.assertEqual(_stop_reason([], support, 0.0, 0.08, 0.049), "nonhand_clearance_lost")
        self.assertEqual(
            _stop_reason([], SimpleNamespace(supporting_feet=("FL", "FR"), support_margin=0.03), 0.0, 0.08, 0.08),
            "support_lost",
        )
        self.assertEqual(
            _stop_reason([], SimpleNamespace(supporting_feet=("FL", "FR", "RL"), support_margin=None), 0.0, 0.08, 0.08),
            "support_lost",
        )

    def test_support_only_observation_stays_far_from_contact(self):
        support = SimpleNamespace(supporting_feet=("FL", "FR"), support_margin=None)
        self.assertIsNone(_stop_reason([], support, 0.0, 0.08, 0.08, observe_support_only=True, finger_clearance=0.11))
        self.assertEqual(
            _stop_reason([], support, 0.0, 0.08, 0.08, observe_support_only=True, finger_clearance=0.099),
            "baseline_finger_clearance_lost",
        )
        self.assertEqual(
            _stop_reason([{"body": "link7"}], support, 0.0, 0.08, 0.08, observe_support_only=True),
            "first_box_contact",
        )


if __name__ == "__main__":
    unittest.main()