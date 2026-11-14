"""Check joint/base tracking bounds against independently perturbed PIPER geometry."""

import unittest

import mujoco
import numpy as np

from reconfigurable_navigation.reachability.clearance import (
    PiperArmClearanceChecker, PiperSelfClearanceChecker,
)
from reconfigurable_navigation.reachability.scenes import (
    STATIC_BOX_BODY, make_movable_box_navigation_runtime,
)
from reconfigurable_navigation.reachability.tracking_clearance import PiperTrackingClearance


class TrackingClearanceChecks(unittest.TestCase):
    def setUp(self):
        self.runtime = make_movable_box_navigation_runtime(
            seed=3, box_position=np.array([0.9, 0.0, 0.14]),
            box_size=np.array([0.2, 0.2, 0.24]), box_yaw=0.03,
        )
        self.own = PiperSelfClearanceChecker(self.runtime)
        self.external = PiperArmClearanceChecker(
            self.runtime, protected_body_names=frozenset({STATIC_BOX_BODY})
        )
        self.bounds = [PiperTrackingClearance(
            checker, moving_body_names=frozenset({STATIC_BOX_BODY})
        ) for checker in (self.own, self.external)]
        self.nominal = self.runtime.data.qpos.copy()
        # Place shoulder/elbow inside their limits before symmetric perturbations.
        self.nominal[self.runtime.joint_qpos_adr[13]] = 0.15
        self.nominal[self.runtime.joint_qpos_adr[14]] = -0.15
        self.runtime.data.qpos[:] = self.nominal
        mujoco.mj_forward(self.runtime.model, self.runtime.data)

    def test_full_joint_and_rigid_error_box_covers_sampled_distances(self):
        rng = np.random.default_rng(307)
        runtime = self.runtime
        radii = np.full(18, 0.015)
        certificates = [bound.evaluate(
            self.nominal, joint_error_radii=radii,
            base_translation_radius=0.02, base_rotation_radius=0.12,
            external_point_error_radius=0.01 if i else 0,
            required_clearance=0,
        ) for i, bound in enumerate(self.bounds)]
        base = runtime.env.robot_qpos_adr
        box_joint = runtime.model.body_jntadr[runtime.model.body(STATIC_BOX_BODY).id]
        box_address = runtime.model.jnt_qposadr[box_joint]
        for _ in range(48):
            state = self.nominal.copy()
            state[runtime.joint_qpos_adr] += rng.uniform(-radii, radii)
            direction = rng.normal(size=3)
            state[base:base + 3] += direction / np.linalg.norm(direction) * 0.02
            axis = rng.normal(size=3)
            delta = np.empty(4)
            mujoco.mju_axisAngle2Quat(delta, axis / np.linalg.norm(axis), 0.12)
            mujoco.mju_mulQuat(state[base + 3:base + 7], delta, self.nominal[base + 3:base + 7])
            # Translation + rotation of the box consumes the 10 mm point budget.
            box_radius = np.linalg.norm(runtime.model.geom(STATIC_BOX_BODY).size)
            angle = 0.005 / box_radius
            axis = rng.normal(size=3)
            mujoco.mju_axisAngle2Quat(delta, axis / np.linalg.norm(axis), angle)
            mujoco.mju_mulQuat(state[box_address + 3:box_address + 7], delta,
                              self.nominal[box_address + 3:box_address + 7])
            direction = rng.normal(size=3)
            state[box_address:box_address + 3] += direction / np.linalg.norm(direction) * 0.005
            runtime.data.qpos[:] = state
            mujoco.mj_forward(runtime.model, runtime.data)
            for checker, certificate in zip((self.own, self.external), certificates):
                actual = checker.evaluate_current_configuration(required_clearance=0).minimum_clearance
                self.assertGreaterEqual(actual, certificate.clearance_lower_bound - 1e-9)

    def test_common_base_motion_cancels_for_self_but_not_environment(self):
        for index, bound in enumerate(self.bounds):
            fixed = bound.evaluate(self.nominal, joint_error_radii=np.zeros(18))
            moved = bound.evaluate(self.nominal, joint_error_radii=np.zeros(18),
                                   base_translation_radius=0.3, base_rotation_radius=0.4)
            if index == 0:
                self.assertEqual(fixed.clearance_lower_bound, moved.clearance_lower_bound)
            else:
                self.assertLess(moved.clearance_lower_bound, fixed.clearance_lower_bound - 0.3)

    def test_nominal_state_is_recomputed_without_mutating_runtime(self):
        state = self.nominal.copy()
        state[self.runtime.joint_qpos_adr[13]] += 0.1
        before = [getattr(self.runtime.data, name).copy() for name in ("qpos", "qvel", "ctrl", "geom_xpos")]
        certificate = self.bounds[0].evaluate(state, joint_error_radii=np.zeros(18))
        for name, expected in zip(("qpos", "qvel", "ctrl", "geom_xpos"), before):
            np.testing.assert_array_equal(getattr(self.runtime.data, name), expected)
        scratch = mujoco.MjData(self.runtime.model)
        scratch.qpos[:] = state
        mujoco.mj_forward(self.runtime.model, scratch)
        actual = PiperSelfClearanceChecker(self.runtime, data=scratch).evaluate_current_configuration(
            required_clearance=0.05
        )
        self.assertAlmostEqual(actual.minimum_clearance, certificate.nominal_clearance)

    def test_inverse_budget_boundary_and_monotonicity(self):
        for bound in self.bounds:
            radius = bound.maximum_uniform_arm_error(
                self.nominal, leg_error_radii=np.full(12, 0.001), required_clearance=0.01,
            )
            self.assertIsNotNone(radius)
            self.assertGreater(radius, 0)
            inside = bound.evaluate(self.nominal,
                joint_error_radii=np.r_[np.full(12, 0.001), np.full(6, radius - 1e-8)],
                required_clearance=0.01)
            outside = bound.evaluate(self.nominal,
                joint_error_radii=np.r_[np.full(12, 0.001), np.full(6, radius + 1e-8)],
                required_clearance=0.01)
            self.assertTrue(inside.conditional_clearance_safe)
            self.assertFalse(outside.conditional_clearance_safe)
            self.assertGreaterEqual(inside.clearance_lower_bound, outside.clearance_lower_bound)
            self.assertIsNone(bound.maximum_uniform_arm_error(
                self.nominal, leg_error_radii=np.zeros(12), required_clearance=10))

    def test_joint_limit_violation_rejects_otherwise_clear_geometry(self):
        state = self.nominal.copy()
        bound = self.bounds[1]
        state[self.runtime.joint_qpos_adr[0]] = bound.joint_low[0] + 0.001
        result = bound.evaluate(state, joint_error_radii=np.full(18, 0.002), required_clearance=0)
        self.assertGreater(result.clearance_lower_bound, 0)
        self.assertLess(result.joint_limit_margin_lower_bound, 0)
        self.assertFalse(result.conditional_clearance_safe)

    def test_continuous_path_bound_covers_interior_tracking_errors(self):
        rng = np.random.default_rng(912)
        target = self.nominal.copy()
        target[self.runtime.joint_qpos_adr[12:]] += [0.1, 0.3, -0.3, 0.1, -0.05, 0.1]
        radii = np.full(18, 0.005)
        for bound, checker in zip(self.bounds, (self.own, self.external)):
            certificate = bound.evaluate_joint_path(
                self.nominal, target, samples=7, joint_error_radii=radii,
                required_clearance=0,
            )
            for _ in range(25):
                state = self.nominal + rng.uniform(0, 1) * (target - self.nominal)
                state[self.runtime.joint_qpos_adr] += rng.uniform(-radii, radii)
                self.runtime.data.qpos[:] = state
                mujoco.mj_forward(self.runtime.model, self.runtime.data)
                actual = checker.evaluate_current_configuration(required_clearance=0).minimum_clearance
                self.assertGreaterEqual(actual, certificate.clearance_lower_bound - 1e-9)
            radius = bound.maximum_uniform_arm_error_on_joint_path(
                self.nominal, target, samples=51, leg_error_radii=np.zeros(12),
                required_clearance=0,
            )
            self.assertIsNotNone(radius)
            self.assertGreater(radius, 0)
            inside = bound.evaluate_joint_path(self.nominal, target, samples=51,
                joint_error_radii=np.r_[np.zeros(12), np.full(6, radius - 1e-8)],
                required_clearance=0)
            outside = bound.evaluate_joint_path(self.nominal, target, samples=51,
                joint_error_radii=np.r_[np.zeros(12), np.full(6, radius + 1e-8)],
                required_clearance=0)
            self.assertTrue(inside.conditional_clearance_safe)
            self.assertFalse(outside.conditional_clearance_safe)
        target[0] += 0.001
        with self.assertRaisesRegex(ValueError, "hinges only"):
            self.bounds[0].evaluate_joint_path(self.nominal, target, joint_error_radii=radii)
        with self.assertRaisesRegex(ValueError, "integer"):
            self.bounds[0].evaluate_joint_path(self.nominal, self.nominal,
                                               samples=1, joint_error_radii=radii)

    def test_invalid_or_unmodeled_budgets_are_rejected(self):
        for radius in (-0.01, float("nan")):
            with self.assertRaises(ValueError):
                self.bounds[0].evaluate(self.nominal, joint_error_radii=np.full(18, radius))
        with self.assertRaises(ValueError):
            self.bounds[0].evaluate(self.nominal, joint_error_radii=np.zeros(6))
        with self.assertRaises(ValueError):
            self.bounds[0].evaluate(self.nominal, joint_error_radii=np.zeros(18),
                                    external_point_error_radius=0.001)
        with self.assertRaises(ValueError):
            self.bounds[1].evaluate(self.nominal, joint_error_radii=np.zeros(18),
                                    base_rotation_radius=4.0)
        invalid = self.nominal.copy()
        invalid[self.runtime.env.robot_qpos_adr + 3:self.runtime.env.robot_qpos_adr + 7] = 0
        with self.assertRaises(ValueError):
            self.bounds[1].evaluate(invalid, joint_error_radii=np.zeros(18))
        mixed = PiperArmClearanceChecker(self.runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY, "base_link"}))
        with self.assertRaisesRegex(ValueError, "Separate robot"):
            PiperTrackingClearance(mixed, moving_body_names=frozenset({STATIC_BOX_BODY}))


if __name__ == "__main__":
    unittest.main()
