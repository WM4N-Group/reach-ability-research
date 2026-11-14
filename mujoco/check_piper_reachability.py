"""Regression checks for the PIPER fixed-base position-IK oracle."""

import unittest

import mujoco
import numpy as np

from reconfigurable_navigation.piper_box_runtime import make_episode
from reconfigurable_navigation.piper_locomotion_runtime import PiperLocomotionRuntime
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability import (
    PiperPositionReachabilityOracle,
    PiperArmClearanceChecker,
    PiperSelfClearanceChecker,
    PiperQuasiStaticSupportChecker,
    QuasiStaticSupportResult,
    ReachabilityQuery,
    certify_fixed_contact_support_region,
    certify_relative_contact_support_region,
    certify_frozen_precontact_region,
    measure_fixed_contact_support_residual,
    sample_base_pose_perturbations,
    sample_fixed_base,
)


class PiperReachabilityChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = PiperLocomotionRuntime(seed=0, profile_path=PROFILE_PATH)
        self.oracle = PiperPositionReachabilityOracle(self.runtime)
        self.clearance = PiperSelfClearanceChecker(self.runtime)
        self.query = ReachabilityQuery(
            base_pose=np.array([0.0, 0.0, 0.0]),
            target_position=np.zeros(3),
        )

    def test_nominal_end_effector_position_is_kinematically_reachable(self):
        target = self.oracle.end_effector_position(self.query)
        result = self.oracle.solve(
            ReachabilityQuery(self.query.base_pose, target)
        )
        self.assertTrue(result.kinematic_feasible)
        self.assertIsNone(result.failure_reason)
        self.assertLessEqual(result.position_error, self.oracle.tolerance)
        self.assertGreaterEqual(result.joint_limit_margin, 0.0)
        self.assertFalse(result.collision_checked)
        np.testing.assert_allclose(
            result.joint_solution,
            self.runtime.default_qpos[12:],
            atol=1.0e-10,
        )

    def test_distant_target_is_rejected(self):
        result = self.oracle.solve(
            ReachabilityQuery(
                base_pose=self.query.base_pose,
                target_position=np.array([10.0, 0.0, 10.0]),
            )
        )
        self.assertFalse(result.kinematic_feasible)
        self.assertEqual(result.failure_reason, "position_ik_unreachable")
        self.assertGreater(result.position_error, self.oracle.tolerance)

    def test_repeated_query_is_deterministic_and_preserves_runtime_state(self):
        target = self.oracle.end_effector_position(self.query)
        before_qpos = self.runtime.data.qpos.copy()
        before_qvel = self.runtime.data.qvel.copy()
        first = self.oracle.solve(ReachabilityQuery(self.query.base_pose, target))
        second = self.oracle.solve(ReachabilityQuery(self.query.base_pose, target))
        self.assertEqual(first.kinematic_feasible, second.kinematic_feasible)
        self.assertEqual(first.failure_reason, second.failure_reason)
        self.assertEqual(first.iterations, second.iterations)
        self.assertEqual(first.position_error, second.position_error)
        np.testing.assert_array_equal(first.joint_solution, second.joint_solution)
        np.testing.assert_array_equal(self.runtime.data.qpos, before_qpos)
        np.testing.assert_array_equal(self.runtime.data.qvel, before_qvel)

    def test_custom_ik_initial_guess_preserves_runtime_state(self):
        target = self.oracle.end_effector_position(self.query)
        before_qpos = self.runtime.data.qpos.copy()
        initial = np.clip(
            self.runtime.default_qpos[12:] + np.array([0.0, 0.1, -0.1, 0.0, 0.0, 0.0]),
            self.oracle.arm_low,
            self.oracle.arm_high,
        )
        result = self.oracle.solve(
            ReachabilityQuery(self.query.base_pose, target),
            initial_joint_positions=initial,
        )
        self.assertTrue(result.kinematic_feasible)
        self.assertLessEqual(result.position_error, self.oracle.tolerance)
        np.testing.assert_array_equal(self.runtime.data.qpos, before_qpos)
        with self.assertRaisesRegex(ValueError, "initial_joint_positions"):
            self.oracle.solve(self.query, initial_joint_positions=np.full(6, np.nan))
        with self.assertRaisesRegex(ValueError, "joint limits"):
            self.oracle.solve(self.query, initial_joint_positions=self.oracle.arm_high + 1)

    def test_offset_hand_point_ik_and_state_restoration(self):
        nominal = self.runtime.default_qpos[12:].copy()
        target = self.oracle.hand_position(self.query, nominal)
        initial = np.clip(
            nominal + np.array([0.0, 0.1, -0.1, 0.0, 0.0, 0.0]),
            self.oracle.arm_low, self.oracle.arm_high,
        )
        before_qpos = self.runtime.data.qpos.copy()
        result = self.oracle.solve(
            ReachabilityQuery(self.query.base_pose, target),
            initial_joint_positions=initial, hand_offset=(0.15, 0.0, 0.0),
        )
        self.assertTrue(result.kinematic_feasible)
        np.testing.assert_allclose(
            self.oracle.hand_position(self.query, result.joint_solution),
            target, atol=self.oracle.tolerance,
        )
        np.testing.assert_array_equal(self.runtime.data.qpos, before_qpos)
        with self.assertRaisesRegex(ValueError, "hand_offset"):
            self.oracle.solve(self.query, hand_offset=(float("nan"), 0.0, 0.0))

    def test_ik_and_clearance_keep_settled_tilt_when_replacing_yaw(self):
        address = self.oracle.base_qpos_adr
        tilt = np.array([np.cos(0.12), np.sin(0.12), 0.0, 0.0])
        self.runtime.data.qpos[address + 3 : address + 7] = tilt
        mujoco.mj_forward(self.runtime.model, self.runtime.data)
        saved_qpos = self.runtime.data.qpos.copy()
        yaw = 0.35
        expected = np.empty(4)
        mujoco.mju_mulQuat(
            expected,
            np.array([np.cos(yaw / 2), 0.0, 0.0, np.sin(yaw / 2)]),
            tilt,
        )
        pose = np.array([0.02, -0.01, yaw])
        try:
            self.oracle._set_query_state(
                ReachabilityQuery(pose, np.zeros(3)), self.runtime.default_qpos[12:]
            )
            np.testing.assert_allclose(self.runtime.data.qpos[address + 3 : address + 7], expected)
            self.runtime.data.qpos[:] = saved_qpos
            mujoco.mj_forward(self.runtime.model, self.runtime.data)
            self.clearance._set_state(pose, self.runtime.default_qpos[12:])
            np.testing.assert_allclose(self.runtime.data.qpos[address + 3 : address + 7], expected)
        finally:
            self.runtime.data.qpos[:] = saved_qpos
            mujoco.mj_forward(self.runtime.model, self.runtime.data)

    def test_schema_rejects_non_finite_or_wrong_shape_values(self):
        with self.assertRaisesRegex(ValueError, "base_pose"):
            ReachabilityQuery(np.zeros(2), np.zeros(3))
        with self.assertRaisesRegex(ValueError, "target_position"):
            ReachabilityQuery(np.zeros(3), np.array([0.0, np.nan, 0.0]))

    def test_fixed_base_samples_are_json_compatible_and_deterministic(self):
        target = self.oracle.end_effector_position(self.query)
        targets = (target, np.array([10.0, 0.0, 10.0]))
        first = sample_fixed_base(self.oracle, self.query.base_pose, targets)
        second = sample_fixed_base(self.oracle, self.query.base_pose, targets)
        self.assertEqual(first.summary(), second.summary())
        self.assertEqual(first.records(), second.records())
        self.assertEqual(first.summary()["kinematic_feasible"], 1)
        self.assertEqual(first.summary()["kinematic_unreachable"], 1)
        self.assertFalse(first.records()[0]["collision_checked"])
        self.assertFalse(first.records()[0]["self_clearance_checked"])

    def test_base_pose_perturbations_preserve_metadata_and_zero_offset_result(self):
        target = self.oracle.end_effector_position(self.query)
        offsets = (np.zeros(3), np.array([0.02, -0.01, 0.03]))
        first = sample_base_pose_perturbations(
            self.oracle,
            self.query.base_pose,
            target,
            offsets,
            scene_case="nominal-hand-target",
            split="calibration",
        )
        second = sample_base_pose_perturbations(
            self.oracle,
            self.query.base_pose,
            target,
            offsets,
            scene_case="nominal-hand-target",
            split="calibration",
        )
        self.assertEqual(first.records(), second.records())
        zero_offset = first.records()[0]
        self.assertEqual(zero_offset["scene_case"], "nominal-hand-target")
        self.assertEqual(zero_offset["split"], "calibration")
        self.assertEqual(zero_offset["base_pose_offset"], [0.0, 0.0, 0.0])
        self.assertTrue(zero_offset["kinematic_feasible"])
        with self.assertRaisesRegex(ValueError, "split"):
            sample_base_pose_perturbations(
                self.oracle,
                self.query.base_pose,
                target,
                offsets,
                scene_case="nominal-hand-target",
                split="train",
            )

    def test_samples_record_self_clearance_for_kinematic_solutions(self):
        target = self.oracle.end_effector_position(self.query)
        samples = sample_fixed_base(
            self.oracle,
            self.query.base_pose,
            (target,),
            clearance_checker=self.clearance,
            required_self_clearance=0.05,
        )
        record = samples.records()[0]
        self.assertTrue(record["kinematic_feasible"])
        self.assertTrue(record["self_clearance_checked"])
        self.assertTrue(record["self_clearance_safe"])
        self.assertGreaterEqual(record["minimum_self_clearance"], 0.05)
        self.assertEqual(record["self_clearance_pair"]["protected_body"], "base_link")

    def test_samples_label_nominal_zero_margin_as_joint_limit_risk(self):
        target = self.oracle.end_effector_position(self.query)
        samples = sample_fixed_base(
            self.oracle,
            self.query.base_pose,
            (target,),
            required_joint_limit_margin=0.05,
        )
        record = samples.records()[0]
        self.assertTrue(record["kinematic_feasible"])
        self.assertEqual(record["joint_limit_margin"], 0.0)
        self.assertEqual(record["required_joint_limit_margin"], 0.05)
        self.assertFalse(record["joint_limit_safe"])

    def test_self_clearance_accepts_nominal_arm_configuration(self):
        result = self.clearance.evaluate(
            self.query.base_pose,
            self.runtime.default_qpos[12:],
            required_clearance=0.05,
        )
        self.assertTrue(result.safe)
        self.assertGreaterEqual(result.minimum_clearance, 0.05)
        self.assertGreater(result.checked_pairs, 0)
        self.assertIn(result.arm_body, {"link1", "link2", "link3", "link4", "link5", "link6", "link7", "link8"})

    def test_current_configuration_clearance_is_read_only(self):
        qpos = self.runtime.data.qpos.copy()
        qvel = self.runtime.data.qvel.copy()
        ctrl = self.runtime.data.ctrl.copy()
        result = self.clearance.evaluate_current_configuration(required_clearance=0.05)
        self.assertGreater(result.checked_pairs, 0)
        np.testing.assert_array_equal(self.runtime.data.qpos, qpos)
        np.testing.assert_array_equal(self.runtime.data.qvel, qvel)
        np.testing.assert_array_equal(self.runtime.data.ctrl, ctrl)

    def test_self_clearance_rejects_reproducible_penetrating_configuration(self):
        before_qpos = self.runtime.data.qpos.copy()
        unsafe_arm_joint_positions = np.array(
            [0.22818869, 3.00656443, -0.39141992, 1.39235880, -0.21832619, -0.99569988]
        )
        result = self.clearance.evaluate(
            self.query.base_pose,
            unsafe_arm_joint_positions,
            required_clearance=0.0,
        )
        self.assertFalse(result.safe)
        self.assertLess(result.minimum_clearance, 0.0)
        self.assertEqual(result.protected_body, "base_link")
        np.testing.assert_array_equal(self.runtime.data.qpos, before_qpos)

    def test_scene_clearance_rejects_push_box_overlapping_the_nominal_hand(self):
        scene_runtime = make_episode("push", self.runtime.policy_path, seed=0)
        scene_oracle = PiperPositionReachabilityOracle(scene_runtime)
        query = ReachabilityQuery(np.array([0.0, 0.0, 0.0]), np.zeros(3))
        hand_position = scene_oracle.end_effector_position(query)
        box_qpos = scene_runtime.data.joint("push_box_joint").qpos
        box_qpos[:3] = hand_position
        box_qpos[3:7] = [1.0, 0.0, 0.0, 0.0]
        mujoco.mj_forward(scene_runtime.model, scene_runtime.data)
        checker = PiperArmClearanceChecker(
            scene_runtime,
            protected_body_names=frozenset({"push_box"}),
        )
        result = checker.evaluate(
            query.base_pose,
            scene_runtime.default_qpos[12:],
            required_clearance=0.0,
        )
        self.assertFalse(result.safe)
        self.assertLess(result.minimum_clearance, 0.0)
        self.assertEqual(result.protected_body, "push_box")

    def test_scene_clearance_can_separate_fingers_from_nonhand_arm(self):
        scene_runtime = make_episode("push", self.runtime.policy_path, seed=0)
        protected = frozenset({"push_box"})
        arm = scene_runtime.default_qpos[12:]
        all_arm = PiperArmClearanceChecker(
            scene_runtime, protected_body_names=protected
        ).evaluate(self.query.base_pose, arm, required_clearance=0.0)
        fingers = PiperArmClearanceChecker(
            scene_runtime,
            protected_body_names=protected,
            arm_body_names=frozenset({"link7", "link8"}),
        ).evaluate(self.query.base_pose, arm, required_clearance=0.0)
        nonhand = PiperArmClearanceChecker(
            scene_runtime,
            protected_body_names=protected,
            arm_body_names=frozenset({"link1", "link2", "link3", "link4", "link5", "link6"}),
        ).evaluate(self.query.base_pose, arm, required_clearance=0.0)
        self.assertIn(fingers.arm_body, {"link7", "link8"})
        self.assertIn(nonhand.arm_body, {"link1", "link2", "link3", "link4", "link5", "link6"})
        self.assertAlmostEqual(
            all_arm.minimum_clearance,
            min(fingers.minimum_clearance, nonhand.minimum_clearance),
        )

    def test_samples_record_scene_clearance_separately_from_self_clearance(self):
        scene_runtime = make_episode("push", self.runtime.policy_path, seed=0)
        scene_oracle = PiperPositionReachabilityOracle(scene_runtime)
        query = ReachabilityQuery(np.array([0.0, 0.0, 0.0]), np.zeros(3))
        hand_position = scene_oracle.end_effector_position(query)
        box_qpos = scene_runtime.data.joint("push_box_joint").qpos
        box_qpos[:3] = hand_position
        box_qpos[3:7] = [1.0, 0.0, 0.0, 0.0]
        mujoco.mj_forward(scene_runtime.model, scene_runtime.data)
        scene_checker = PiperArmClearanceChecker(
            scene_runtime,
            protected_body_names=frozenset({"push_box"}),
        )
        samples = sample_fixed_base(
            scene_oracle,
            query.base_pose,
            (hand_position,),
            environment_clearance_checker=scene_checker,
            required_environment_clearance=0.0,
        )
        record = samples.records()[0]
        self.assertTrue(record["kinematic_feasible"])
        self.assertFalse(record["self_clearance_checked"])
        self.assertTrue(record["environment_clearance_checked"])
        self.assertFalse(record["environment_clearance_safe"])
        self.assertEqual(record["environment_clearance_pair"]["protected_body"], "push_box")

    def test_frozen_configuration_safety_tube_lower_bounds_scene_clearance(self):
        scene_runtime = make_episode("push", self.runtime.policy_path, seed=0)
        checker = PiperArmClearanceChecker(
            scene_runtime,
            protected_body_names=frozenset({"push_box"}),
        )
        base_pose = np.array([0.0, 0.0, 0.0])
        base_pose_offset = np.array([0.01, -0.01, 0.03])
        tube = checker.certify_frozen_configuration_tube(
            base_pose,
            scene_runtime.default_qpos[12:],
            base_pose_offset=base_pose_offset,
            required_clearance=0.0,
        )
        perturbed = checker.evaluate(
            base_pose + base_pose_offset,
            scene_runtime.default_qpos[12:],
            required_clearance=0.0,
        )
        self.assertTrue(tube.safe)
        self.assertGreater(tube.maximum_arm_rotation_radius, 0.0)
        self.assertGreater(tube.robot_motion_bound, 0.0)
        self.assertGreaterEqual(
            perturbed.minimum_clearance,
            tube.clearance_lower_bound - 1.0e-8,
        )
        bounded = checker.certify_frozen_configuration_tube(
            base_pose,
            scene_runtime.default_qpos[12:],
            base_pose_offset=np.array([0.01, 0.0, 0.01]),
            required_clearance=0.0,
            external_geometry_error_bound=0.01,
        )
        for offset in (np.array([-0.006, 0.008, -0.01]), np.array([0.0, -0.01, 0.01])):
            measured = checker.evaluate(
                base_pose + offset,
                scene_runtime.default_qpos[12:],
                required_clearance=0.0,
            )
            self.assertGreaterEqual(measured.minimum_clearance, bounded.clearance_lower_bound - 1.0e-8)

    def test_frozen_configuration_safety_tube_rejects_nominal_overlap(self):
        scene_runtime = make_episode("push", self.runtime.policy_path, seed=0)
        scene_oracle = PiperPositionReachabilityOracle(scene_runtime)
        base_pose = np.array([0.0, 0.0, 0.0])
        hand_position = scene_oracle.end_effector_position(
            ReachabilityQuery(base_pose, np.zeros(3))
        )
        box_qpos = scene_runtime.data.joint("push_box_joint").qpos
        box_qpos[:3] = hand_position
        box_qpos[3:7] = [1.0, 0.0, 0.0, 0.0]
        mujoco.mj_forward(scene_runtime.model, scene_runtime.data)
        checker = PiperArmClearanceChecker(
            scene_runtime,
            protected_body_names=frozenset({"push_box"}),
        )
        tube = checker.certify_frozen_configuration_tube(
            base_pose,
            scene_runtime.default_qpos[12:],
            base_pose_offset=np.zeros(3),
            required_clearance=0.0,
        )
        self.assertLess(tube.nominal_clearance.minimum_clearance, 0.0)
        self.assertFalse(tube.safe)

    def test_frozen_precontact_region_bounds_continuous_base_and_target_errors(self):
        scene_runtime = make_episode("push", self.runtime.policy_path, seed=0)
        oracle = PiperPositionReachabilityOracle(scene_runtime)
        self_checker = PiperSelfClearanceChecker(scene_runtime)
        environment_checker = PiperArmClearanceChecker(
            scene_runtime, protected_body_names=frozenset({"push_box"})
        )
        base = np.array([0.0, 0.0, 0.0])
        arm = scene_runtime.default_qpos[12:].copy()
        nominal_query = ReachabilityQuery(base, np.zeros(3))
        target, target_quaternion = oracle.end_effector_pose(nominal_query, arm)
        query = ReachabilityQuery(base, target)
        saved_qpos = scene_runtime.data.qpos.copy()
        certificate = certify_frozen_precontact_region(
            oracle, self_checker, environment_checker, query, arm,
            target_quaternion=target_quaternion,
            translation_radius=0.01, yaw_radius=0.02,
            target_position_error_radius=0.005, target_orientation_error_radius=0.01,
            external_geometry_error_radius=0.003,
            required_position_tolerance=0.05, required_orientation_tolerance=0.05,
            required_joint_margin=0.0,
            required_self_clearance=0.0,
            required_environment_clearance=0.0,
        )
        self.assertTrue(certificate.geometric_precontact_safe)
        np.testing.assert_array_equal(scene_runtime.data.qpos, saved_qpos)
        self.assertAlmostEqual(certificate.nominal_position_error, 0.0)
        self.assertLess(certificate.nominal_orientation_error, 1.0e-6)
        for offset in (
            np.array([0.01, 0.0, 0.02]),
            np.array([-0.006, 0.008, -0.02]),
            np.array([0.0, -0.01, 0.0]),
        ):
            perturbed_query = ReachabilityQuery(base + offset, target)
            hand, orientation = oracle.end_effector_pose(perturbed_query, arm)
            shifted_target = target + np.array([0.003, -0.004, 0.0])
            target_yaw = np.array([np.cos(0.005), 0.0, 0.0, np.sin(0.005)])
            shifted_orientation = np.empty(4)
            mujoco.mju_mulQuat(shifted_orientation, target_yaw, target_quaternion)
            self.assertLessEqual(
                np.linalg.norm(hand - shifted_target),
                certificate.position_error_upper_bound + 1.0e-10,
            )
            orientation_error = 2.0 * np.arccos(
                np.clip(abs(np.dot(orientation, shifted_orientation)), 0.0, 1.0)
            )
            self.assertLessEqual(
                orientation_error, certificate.orientation_error_upper_bound + 1.0e-8
            )
            clearance = environment_checker.evaluate(
                perturbed_query.base_pose, arm, required_clearance=0.0
            )
            self.assertGreaterEqual(
                clearance.minimum_clearance,
                certificate.environment_tube.clearance_lower_bound - 1.0e-8,
            )
            self_result = self_checker.evaluate(
                perturbed_query.base_pose, arm, required_clearance=0.0
            )
            self.assertAlmostEqual(
                self_result.minimum_clearance,
                certificate.self_clearance.minimum_clearance,
                places=7,
            )

    def test_frozen_precontact_region_rejects_unmet_or_invalid_assumptions(self):
        scene_runtime = make_episode("push", self.runtime.policy_path, seed=0)
        oracle = PiperPositionReachabilityOracle(scene_runtime)
        self_checker = PiperSelfClearanceChecker(scene_runtime)
        environment_checker = PiperArmClearanceChecker(
            scene_runtime, protected_body_names=frozenset({"push_box"})
        )
        arm = scene_runtime.default_qpos[12:].copy()
        base = np.zeros(3)
        target, target_quaternion = oracle.end_effector_pose(
            ReachabilityQuery(base, np.zeros(3)), arm
        )
        kwargs = dict(
            target_quaternion=target_quaternion,
            translation_radius=0.01, yaw_radius=0.02,
            target_position_error_radius=0.005,
            target_orientation_error_radius=0.01,
            external_geometry_error_radius=0.003,
            required_position_tolerance=0.001,
            required_orientation_tolerance=0.05,
            required_joint_margin=0.0,
            required_self_clearance=0.0,
            required_environment_clearance=0.0,
        )
        certificate = certify_frozen_precontact_region(
            oracle, self_checker, environment_checker,
            ReachabilityQuery(base, target), arm, **kwargs,
        )
        self.assertFalse(certificate.geometric_precontact_safe)
        orientation_rejected = certify_frozen_precontact_region(
            oracle, self_checker, environment_checker,
            ReachabilityQuery(base, target), arm,
            **{**kwargs, "required_position_tolerance": 0.05,
               "required_orientation_tolerance": 0.001},
        )
        self.assertFalse(orientation_rejected.geometric_precontact_safe)
        with self.assertRaisesRegex(ValueError, "yaw_radius"):
            certify_frozen_precontact_region(
                oracle, self_checker, environment_checker,
                ReachabilityQuery(base, target), arm,
                **{**kwargs, "yaw_radius": np.pi + 0.01},
            )
        with self.assertRaisesRegex(ValueError, "external geometry"):
            certify_frozen_precontact_region(
                oracle, self_checker, self_checker,
                ReachabilityQuery(base, target), arm, **kwargs,
            )
        with self.assertRaisesRegex(ValueError, "target_quaternion"):
            certify_frozen_precontact_region(
                oracle, self_checker, environment_checker,
                ReachabilityQuery(base, target), arm,
                **{**kwargs, "target_quaternion": np.zeros(4)},
            )
        different_snapshot = mujoco.MjData(scene_runtime.model)
        different_snapshot.qpos[:] = scene_runtime.data.qpos
        snapshot_checker = PiperArmClearanceChecker(
            scene_runtime,
            protected_body_names=frozenset({"push_box"}),
            data=different_snapshot,
        )
        with self.assertRaisesRegex(ValueError, "same scene snapshot"):
            certify_frozen_precontact_region(
                oracle, self_checker, snapshot_checker,
                ReachabilityQuery(base, target), arm, **kwargs,
            )
        with self.assertRaisesRegex(ValueError, "within \\[-pi, pi\\]"):
            environment_checker.certify_frozen_configuration_tube(
                base, arm, base_pose_offset=np.array([0.0, 0.0, 2.0 * np.pi]),
                required_clearance=0.0,
            )

    def test_quasistatic_support_accepts_settled_nominal_pose(self):
        for _step in range(round(2.0 / self.runtime.control_dt)):
            self.runtime.hold_default()
        support = PiperQuasiStaticSupportChecker(self.runtime).evaluate(
            required_margin=0.02
        )
        self.assertEqual(set(support.supporting_feet), {"FL", "FR", "RL", "RR"})
        self.assertGreater(support.support_margin, 0.02)
        self.assertTrue(support.safe)
        region = certify_fixed_contact_support_region(
            support,
            contact_point_error_radius=0.001,
            center_of_mass_error_radius=0.001,
        )
        self.assertAlmostEqual(region.margin_lower_bound, support.support_margin - 0.002)
        self.assertTrue(region.conditional_support_safe)

    def test_fixed_contact_support_bound_covers_independent_residuals(self):
        from reconfigurable_navigation.reachability.support import _convex_support_margin

        points = np.array([
            [-0.2, -0.2], [0.2, -0.2], [0.2, 0.2], [-0.2, 0.2]
        ])
        nominal = QuasiStaticSupportResult(
            supporting_feet=("FL", "FR", "RR", "RL"),
            support_points=points,
            center_of_mass_xy=np.zeros(2),
            support_margin=0.2,
            required_margin=0.05,
        )
        region = certify_fixed_contact_support_region(
            nominal,
            contact_point_error_radius=0.03,
            center_of_mass_error_radius=0.02,
        )
        self.assertAlmostEqual(region.margin_lower_bound, 0.15)
        self.assertTrue(region.conditional_support_safe)
        rng = np.random.default_rng(91)
        for _ in range(64):
            yaw = rng.uniform(-0.6, 0.6)
            rotation = np.array([
                [np.cos(yaw), -np.sin(yaw)],
                [np.sin(yaw), np.cos(yaw)],
            ])
            translation = rng.uniform(-0.5, 0.5, size=2)
            point_residuals = rng.normal(size=(4, 2))
            point_residuals *= rng.uniform(0.0, 0.03, size=(4, 1)) / np.linalg.norm(
                point_residuals, axis=1, keepdims=True
            )
            com_residual = rng.normal(size=2)
            com_residual *= rng.uniform(0.0, 0.02) / np.linalg.norm(com_residual)
            moved_points = points @ rotation.T + translation + point_residuals
            moved_com = translation + com_residual
            measured = _convex_support_margin(moved_points, moved_com)
            self.assertGreaterEqual(measured, region.margin_lower_bound - 1.0e-12)

    def test_fixed_contact_support_rejects_missing_contacts_or_budget(self):
        two_feet = QuasiStaticSupportResult(
            supporting_feet=("FL", "FR"),
            support_points=np.array([[-0.2, 0.0], [0.2, 0.0]]),
            center_of_mass_xy=np.zeros(2),
            support_margin=None,
            required_margin=0.02,
        )
        region = certify_fixed_contact_support_region(
            two_feet,
            contact_point_error_radius=0.0,
            center_of_mass_error_radius=0.0,
        )
        self.assertIsNone(region.margin_lower_bound)
        self.assertFalse(region.conditional_support_safe)
        points = np.array([[-0.2, -0.2], [0.2, -0.2], [0.2, 0.2], [-0.2, 0.2]])
        nominal = QuasiStaticSupportResult(
            supporting_feet=("FL", "FR", "RR", "RL"),
            support_points=points,
            center_of_mass_xy=np.zeros(2),
            support_margin=0.2,
            required_margin=0.02,
        )
        exhausted = certify_fixed_contact_support_region(
            nominal,
            contact_point_error_radius=0.11,
            center_of_mass_error_radius=0.10,
        )
        self.assertIsNone(exhausted.margin_lower_bound)
        self.assertFalse(exhausted.conditional_support_safe)
        with self.assertRaisesRegex(ValueError, "support_margin"):
            certify_fixed_contact_support_region(
                QuasiStaticSupportResult(
                    supporting_feet=nominal.supporting_feet,
                    support_points=points,
                    center_of_mass_xy=np.zeros(2),
                    support_margin=0.19,
                    required_margin=0.02,
                ),
                contact_point_error_radius=0.0,
                center_of_mass_error_radius=0.0,
            )
        with self.assertRaisesRegex(ValueError, "contact_point_error_radius"):
            certify_fixed_contact_support_region(
                nominal,
                contact_point_error_radius=-0.01,
                center_of_mass_error_radius=0.0,
            )

    def test_relative_contact_support_bound_keeps_correlated_motion(self):
        from reconfigurable_navigation.reachability.support import _convex_support_margin

        points = np.array([[-0.2, -0.2], [0.2, -0.2], [0.2, 0.2], [-0.2, 0.2]])
        nominal = QuasiStaticSupportResult(
            supporting_feet=("FL", "FR", "RR", "RL"),
            support_points=points,
            center_of_mass_xy=np.zeros(2),
            support_margin=0.2,
            required_margin=0.18,
        )
        region = certify_relative_contact_support_region(
            nominal, relative_contact_point_error_radius=0.01
        )
        self.assertAlmostEqual(region.margin_lower_bound, 0.19)
        self.assertTrue(region.conditional_support_safe)
        common_motion = np.array([0.07, -0.04])
        moved_points = points + common_motion + np.array([
            [0.01, 0.0], [-0.01, 0.0], [0.0, -0.01], [0.0, 0.01]
        ])
        moved_com = common_motion
        observed = QuasiStaticSupportResult(
            supporting_feet=nominal.supporting_feet,
            support_points=moved_points,
            center_of_mass_xy=moved_com,
            support_margin=_convex_support_margin(moved_points, moved_com),
            required_margin=0.18,
        )
        residual = measure_fixed_contact_support_residual(
            nominal, np.zeros(3), observed, np.zeros(3)
        )
        self.assertGreater(residual.maximum_contact_point_residual, 0.07)
        self.assertGreater(residual.center_of_mass_residual, 0.07)
        self.assertAlmostEqual(residual.maximum_relative_contact_point_residual, 0.01)
        self.assertGreaterEqual(observed.support_margin, region.margin_lower_bound - 1e-12)
        dropped = QuasiStaticSupportResult(
            supporting_feet=observed.supporting_feet[:2],
            support_points=observed.support_points[:2],
            center_of_mass_xy=observed.center_of_mass_xy,
            support_margin=None,
            required_margin=0.18,
        )
        rejected = measure_fixed_contact_support_residual(
            nominal, np.zeros(3), dropped, np.zeros(3)
        )
        self.assertIsNone(rejected.maximum_relative_contact_point_residual)

    def test_support_residual_removes_common_base_motion_and_matches_feet_by_name(self):
        from reconfigurable_navigation.reachability.support import _convex_support_margin

        points = np.array([[-0.2, -0.2], [0.2, -0.2], [0.2, 0.2], [-0.2, 0.2]])
        reference = QuasiStaticSupportResult(
            supporting_feet=("FL", "FR", "RR", "RL"),
            support_points=points,
            center_of_mass_xy=np.array([0.01, -0.01]),
            support_margin=_convex_support_margin(points, np.array([0.01, -0.01])),
            required_margin=0.02,
        )
        base = np.array([0.0, 0.0, 0.0])
        moved_base = np.array([0.3, -0.4, 0.35])
        cosine, sine = np.cos(moved_base[2]), np.sin(moved_base[2])
        rotation = np.array([[cosine, -sine], [sine, cosine]])
        reordered = [2, 0, 3, 1]
        residuals = np.array([[0.003, 0.0], [0.0, 0.001], [0.0, -0.002], [0.001, 0.0]])
        observed_points = points[reordered] @ rotation.T + moved_base[:2] + residuals
        observed_com = reference.center_of_mass_xy @ rotation.T + moved_base[:2] + np.array([0.004, 0.0])
        observed = QuasiStaticSupportResult(
            supporting_feet=tuple(reference.supporting_feet[index] for index in reordered),
            support_points=observed_points,
            center_of_mass_xy=observed_com,
            support_margin=_convex_support_margin(observed_points, observed_com),
            required_margin=0.02,
        )
        measured = measure_fixed_contact_support_residual(reference, base, observed, moved_base)
        self.assertTrue(measured.contact_set_preserved)
        self.assertAlmostEqual(measured.maximum_contact_point_residual, 0.003)
        self.assertAlmostEqual(measured.center_of_mass_residual, 0.004)
        self.assertAlmostEqual(measured.observed_support_margin, observed.support_margin)
        dropped_foot = QuasiStaticSupportResult(
            supporting_feet=observed.supporting_feet[:3],
            support_points=observed_points[:3],
            center_of_mass_xy=observed_com,
            support_margin=_convex_support_margin(observed_points[:3], observed_com),
            required_margin=0.02,
        )
        rejected = measure_fixed_contact_support_residual(reference, base, dropped_foot, moved_base)
        self.assertFalse(rejected.contact_set_preserved)
        self.assertIsNone(rejected.maximum_contact_point_residual)

    def test_recomputed_support_data_matches_settled_piper_state(self):
        for _step in range(round(2.0 / self.runtime.control_dt)):
            self.runtime.hold_default()
        direct = PiperQuasiStaticSupportChecker(self.runtime).evaluate(required_margin=0.02)
        fresh_data = mujoco.MjData(self.runtime.model)
        fresh_data.qpos[:] = self.runtime.data.qpos
        fresh_data.qvel[:] = self.runtime.data.qvel
        fresh_data.ctrl[:] = self.runtime.data.ctrl
        mujoco.mj_forward(self.runtime.model, fresh_data)
        mujoco.mj_forward(self.runtime.model, self.runtime.data)
        direct = PiperQuasiStaticSupportChecker(self.runtime).evaluate(required_margin=0.02)
        recomputed = PiperQuasiStaticSupportChecker(
            self.runtime, data=fresh_data
        ).evaluate(required_margin=0.02)
        self.assertEqual(direct.supporting_feet, recomputed.supporting_feet)
        np.testing.assert_allclose(direct.support_points, recomputed.support_points, atol=1.0e-8)
        np.testing.assert_allclose(
            direct.center_of_mass_xy, recomputed.center_of_mass_xy, atol=1.0e-8
        )

    def test_quasistatic_support_requires_three_foot_contacts(self):
        for _step in range(round(2.0 / self.runtime.control_dt)):
            self.runtime.hold_default()
        support = PiperQuasiStaticSupportChecker(
            self.runtime,
            foot_geometry_names=("FL", "FR"),
        ).evaluate(required_margin=0.0)
        self.assertEqual(set(support.supporting_feet), {"FL", "FR"})
        self.assertIsNone(support.support_margin)
        self.assertFalse(support.safe)

    def test_quasistatic_support_evaluates_query_configuration_without_mutation(self):
        for _step in range(round(2.0 / self.runtime.control_dt)):
            self.runtime.hold_default()
        checker = PiperQuasiStaticSupportChecker(self.runtime)
        before_qpos = self.runtime.data.qpos.copy()
        support = checker.evaluate_configuration(
            np.array([0.0, 0.0, 0.0]),
            self.runtime.default_qpos[12:],
            required_margin=0.02,
        )
        self.assertTrue(support.safe)
        np.testing.assert_array_equal(self.runtime.data.qpos, before_qpos)

    def test_support_margin_is_positive_inside_and_negative_outside_hull(self):
        from reconfigurable_navigation.reachability.support import _convex_support_margin

        points = np.array([[0.2, 0.2], [0.2, -0.2], [-0.2, -0.2], [-0.2, 0.2]])
        self.assertGreater(_convex_support_margin(points, np.zeros(2)), 0.0)
        self.assertLess(
            _convex_support_margin(points, np.array([0.3, 0.0])),
            0.0,
        )

    def test_samples_record_quasistatic_support_for_kinematic_solutions(self):
        for _step in range(round(2.0 / self.runtime.control_dt)):
            self.runtime.hold_default()
        target = self.oracle.end_effector_position(self.query)
        samples = sample_fixed_base(
            self.oracle,
            self.query.base_pose,
            (target,),
            support_checker=PiperQuasiStaticSupportChecker(self.runtime),
            required_support_margin=0.02,
        )
        record = samples.records()[0]
        self.assertTrue(record["support_checked"])
        self.assertTrue(record["support_safe"])
        self.assertEqual(set(record["supporting_feet"]), {"FL", "FR", "RL", "RR"})


if __name__ == "__main__":
    unittest.main()
