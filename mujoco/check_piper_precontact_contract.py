"""Regression checks for bounded precontact pose feedback and task-frame gating."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mujoco
import numpy as np

from check_piper_arm_precontact_motion import (
    ArmMotionMonitor,
    CONTROL,
    PiperArmClearanceChecker,
    PiperSelfClearanceChecker,
    RolloutFailure,
    STATIC_BOX_BODY,
    _orientation_feedback,
    _quaternion_error,
    _base_hold_velocity,
    _designated_hand_environment_safe,
    _world_pose_to_wbc_command,
    main,
    make_static_box_navigation_runtime,
)
from reconfigurable_navigation.piper_locomotion_runtime import PiperLocomotionRuntime
from reconfigurable_navigation.reachability.sweep import PiperConfigurationSweep


class PiperPrecontactContract(unittest.TestCase):
    def test_base_hold_velocity_uses_body_frame_and_limits(self):
        command = _base_hold_velocity(
            np.array([1.0, 2.0, 0.5 * np.pi]),
            np.array([0.0, 0.0, 0.5 * np.pi]),
            position_gain=1.0,
            yaw_gain=2.0,
            maximum_linear_speed=0.5,
            maximum_yaw_rate=0.1,
        )
        np.testing.assert_allclose(command, [2.0, -1.0, 0.0] / np.sqrt(20.0))
        yaw_command = _base_hold_velocity(
            np.array([0.0, 0.0, -np.pi + 0.02]),
            np.array([0.0, 0.0, np.pi - 0.02]),
            position_gain=1.0,
            yaw_gain=4.0,
            maximum_linear_speed=0.5,
            maximum_yaw_rate=0.1,
        )
        np.testing.assert_allclose(yaw_command, [0.0, 0.0, 0.1], atol=1.0e-12)

    def test_designated_hand_environment_requires_nonhand_clearance_and_front_face(self):
        self.assertTrue(_designated_hand_environment_safe(
            unified_environment_safe=False,
            finger_clearance=0.02,
            nonhand_environment_safe=True,
            designated_face_ready=True,
        ))
        self.assertFalse(_designated_hand_environment_safe(
            unified_environment_safe=False,
            finger_clearance=0.02,
            nonhand_environment_safe=False,
            designated_face_ready=True,
        ))
        self.assertFalse(_designated_hand_environment_safe(
            unified_environment_safe=False,
            finger_clearance=0.02,
            nonhand_environment_safe=True,
            designated_face_ready=False,
        ))
        self.assertFalse(_designated_hand_environment_safe(
            unified_environment_safe=False,
            finger_clearance=-1.0e-6,
            nonhand_environment_safe=True,
            designated_face_ready=True,
        ))
        self.assertTrue(_designated_hand_environment_safe(
            unified_environment_safe=True,
            finger_clearance=0.06,
            nonhand_environment_safe=True,
            designated_face_ready=False,
        ))

    def test_gate_hold_keeps_world_command_and_releases_on_gate_loss(self):
        for seed, inject_gate_loss in ((498, False), (498, True), (530, False), (560, False)):
            with self.subTest(seed=seed, inject_gate_loss=inject_gate_loss), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "hold.json"
                arguments = [
                    "check_piper_arm_precontact_motion.py", "--output-json", str(output),
                    "--seed", "498", "--locomotion-policy", "wbc", "--hand-point", "legacy-proxy",
                    "--arm-controller", "unified-wbc", "--wbc-command-ramp-seconds", "4",
                    "--motion-timeout-seconds", "20", "--wbc-midpoint-lift-meters", "0.06",
                    "--static-box-position", "1", "0.08", "0.12",
                    "--static-box-size", "0.24", "0.24", "0.24", "--static-box-yaw", "-0.06",
                    "--hand-target-local", "-0.268", "-0.05", "0.02", "--ik-initial",
                    "-0.17842848783089071", "2.525104739028685", "-1.5559435516664188",
                    "-1.6619972307828335", "-1.169999954319697", "0.378781839383242",
                    "--wbc-hand-feedback-gain", "0.5", "--wbc-hand-feedback-integral-gain", "0.2",
                    "--wbc-hand-feedback-max-meters", "0.06", "--wbc-hand-feedback-gate-margin", "0.005",
                    "--wbc-orientation-feedback-integral-gain", "0.4", "--hold-seconds", "5",
                    "--path-samples", "1001", "--require-static-path-certificate",
                    "--require-motion-sweep-certificate", "--wbc-hold-on-gate",
                ]
                if seed in (530, 560):
                    arguments.extend([
                        "--seed", str(seed), "--static-box-position", "0.9", "0", "0.12",
                        "--static-box-size", "0.2", "0.2", "0.24", "--static-box-yaw", "-0.03",
                        "--hand-target-local", "-0.248", "-0.05", "0.02",
                    ])
                if seed == 560:
                    arguments.extend(["--physics-substeps", "4"])
                original_gate = CONTROL["side_approach_ready"]
                previous_pose = None
                repeated_commands = 0
                injected = False

                def watched_command(runtime, position, quaternion):
                    nonlocal previous_pose, repeated_commands
                    pose = np.concatenate((position, quaternion))
                    repeated_commands = (
                        repeated_commands + 1
                        if previous_pose is not None and np.array_equal(pose, previous_pose)
                        else 0
                    )
                    previous_pose = pose
                    return _world_pose_to_wbc_command(runtime, position, quaternion)

                def controlled_gate(*values):
                    nonlocal injected
                    result = original_gate(*values)
                    if inject_gate_loss and not injected and repeated_commands >= 5 and bool(result[0]):
                        injected = True
                        result = result.clone()
                        result[0] = False
                    return result

                with patch.dict(CONTROL, side_approach_ready=controlled_gate), patch(
                    "sys.argv", arguments
                ), patch(
                    "check_piper_arm_precontact_motion._world_pose_to_wbc_command",
                    side_effect=watched_command,
                ), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 0)
                with output.open() as source:
                    result = json.load(source)["result"]
                motion = result["motion"]
                self.assertEqual(len(result["nav"]["planned_base_pose"]), 3)
                self.assertTrue(result["nav"]["trace"])
                self.assertIn("position_error", result["nav"]["trace"][-1])
                self.assertIn("yaw_error", result["nav"]["trace"][-1])
                self.assertGreaterEqual(motion["stable_seconds"], 5.0)
                self.assertGreaterEqual(motion["wbc_command_hold_seconds"], 4.98)
                self.assertTrue(motion["swept_clearance"]["passed"])
                self.assertTrue(motion["final_hand_gate_passed"])
                self.assertEqual(injected, inject_gate_loss)
                self.assertEqual(motion["wbc_hold_entries"], 2 if inject_gate_loss else 1)
                self.assertEqual(
                    motion["wbc_hold_events"][0]["entry_front_margin"],
                    0.0 if seed == 498 else 0.005,
                )
                if seed == 560:
                    self.assertEqual(motion["wbc_hold_events"][0]["entry_reason"], "stable_gate")
                    self.assertGreaterEqual(motion["wbc_hold_events"][0]["gate_settle_seconds"], 5.0)
                held_poses = {}
                for sample in motion["trace"]:
                    if sample["wbc_command_held"]:
                        first = held_poses.setdefault(sample["wbc_hold_entry"], sample["commanded_world_pose"])
                        np.testing.assert_array_equal(sample["commanded_world_pose"], first)
                self.assertEqual(len(held_poses), motion["wbc_hold_entries"])

    def test_physics_substeps_preserve_control_and_pd_periods(self):
        for substeps in (1, 2, 4):
            with self.subTest(substeps=substeps):
                runtime = make_static_box_navigation_runtime(
                    seed=3, box_position=np.array([0.9, 0.0, 0.1]),
                    box_size=np.array([0.2, 0.2, 0.2]), box_yaw=0.0,
                    physics_substeps=substeps,
                )
                samples = []
                runtime.on_physics_step = lambda: samples.append(
                    (float(runtime.data.time), runtime.data.ctrl.copy())
                )
                runtime.hold_default()
                self.assertEqual(len(samples), 4 * substeps)
                self.assertAlmostEqual(runtime.data.time, 0.02)
                self.assertAlmostEqual(runtime.control_dt, 0.02)
                self.assertAlmostEqual(runtime.pd_dt, 0.005)
                self.assertAlmostEqual(runtime.model.opt.timestep, 0.005 / substeps)
                np.testing.assert_allclose(
                    [sample[0] for sample in samples],
                    runtime.sim_dt * np.arange(1, 4 * substeps + 1),
                )
                for pd_step in range(4):
                    group = samples[pd_step * substeps : (pd_step + 1) * substeps]
                    for _, torque in group:
                        np.testing.assert_array_equal(torque, group[0][1])

    def test_monitor_uses_fresh_geometry_without_changing_policy_state(self):
        runtime = make_static_box_navigation_runtime(
            seed=3, box_position=np.array([0.9, 0.0, 0.1]),
            box_size=np.array([0.2, 0.2, 0.2]), box_yaw=0.0,
        )
        monitor = ArmMotionMonitor(
            runtime, target_world=np.array([0.65, -0.05, 0.13]),
            required_self_clearance=0.05, required_environment_clearance=0.05,
            required_support_margin=0.02, support_violation_grace_seconds=0.2,
        )
        monitor.stage = "arm_motion"
        runtime.hold_default()
        qpos = runtime.data.qpos.copy()
        qvel = runtime.data.qvel.copy()
        cached_geometry = runtime.data.geom_xpos.copy()
        monitor()
        expected = mujoco.MjData(runtime.model)
        expected.qpos[:] = qpos
        mujoco.mj_forward(runtime.model, expected)
        np.testing.assert_allclose(monitor.clearance_data.geom_xpos, expected.geom_xpos)
        self.assertGreater(float(np.max(np.abs(expected.geom_xpos - cached_geometry))), 1e-6)
        np.testing.assert_array_equal(runtime.data.geom_xpos, cached_geometry)
        np.testing.assert_array_equal(runtime.data.qpos, qpos)
        np.testing.assert_array_equal(runtime.data.qvel, qvel)

    def test_feedback_uses_world_rotation_error(self):
        desired = np.array([np.cos(0.2), np.sin(0.2), 0.0, 0.0])
        bias = np.array([np.cos(0.1), 0.0, 0.0, np.sin(0.1)])
        actual = np.empty(4)
        mujoco.mju_mulQuat(actual, bias, desired)
        command, integral = _orientation_feedback(
            actual, desired, np.zeros(3), gain=1.0, control_dt=1.0,
            maximum_radians=0.4,
        )
        np.testing.assert_allclose(integral, [0.0, 0.0, -0.2], atol=1.0e-12)
        response = np.empty(4)
        mujoco.mju_mulQuat(response, bias, command)
        self.assertLess(_quaternion_error(response, desired), 1.0e-7)

    def test_feedback_is_bounded_and_sign_invariant(self):
        actual = np.array([1.0, 0.0, 0.0, 0.0])
        desired = np.array([np.cos(0.1), 0.0, 0.0, np.sin(0.1)])
        integral = np.zeros(3)
        for _ in range(100):
            command, integral = _orientation_feedback(
                actual, desired, integral, gain=1.0, control_dt=0.02,
                maximum_radians=0.05,
            )
        np.testing.assert_allclose(integral, [0.0, 0.0, 0.05], atol=1.0e-12)
        antipodal, same_integral = _orientation_feedback(
            -actual, -desired, integral, gain=1.0, control_dt=0.02,
            maximum_radians=0.05,
        )
        np.testing.assert_allclose(same_integral, integral, atol=1.0e-12)
        self.assertLess(_quaternion_error(command, antipodal), 1.0e-7)
        self.assertAlmostEqual(float(np.linalg.norm(command)), 1.0)

    def test_zero_gain_preserves_nominal_command(self):
        desired = np.array([np.cos(0.2), np.sin(0.2), 0.0, 0.0])
        command, integral = _orientation_feedback(
            np.array([1.0, 0.0, 0.0, 0.0]), desired, np.zeros(3),
            gain=0.0, control_dt=0.02, maximum_radians=0.2,
        )
        np.testing.assert_array_equal(integral, np.zeros(3))
        np.testing.assert_array_equal(command, desired)

    def test_hold_gate_uses_task_pose_not_compensated_command(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "precontact.json"
            arguments = [
                "check_piper_arm_precontact_motion.py", "--output-json", str(output),
                "--seed", "456", "--locomotion-policy", "wbc", "--hand-point", "legacy-proxy",
                "--arm-controller", "unified-wbc", "--wbc-command-ramp-seconds", "4.0",
                "--motion-timeout-seconds", "12.0", "--wbc-midpoint-lift-meters", "0.06",
                "--hand-target-local", "-0.248", "-0.05", "0.02",
                "--static-box-yaw", "-0.03", "--ik-initial",
                "-0.17109422273417915", "2.670194220613747", "-1.8017015957187121",
                "-1.3592372483406894", "-1.169999954319697", "0.14849652221791812",
                "--wbc-hand-feedback-gain", "0.5",
                "--wbc-hand-feedback-integral-gain", "0.4",
                "--wbc-hand-feedback-max-meters", "0.06",
                "--wbc-hand-feedback-gate-margin", "0.005",
                "--wbc-orientation-feedback-integral-gain", "0.4",
                "--require-motion-sweep-certificate",
            ]
            with patch("sys.argv", arguments), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            with output.open() as source:
                report = json.load(source)
        result = report["result"]
        self.assertTrue(result["passed"])
        self.assertTrue(result["motion"]["final_hand_gate_passed"])
        self.assertGreaterEqual(result["motion"]["stable_seconds"], 0.5)
        self.assertLessEqual(result["motion"]["final_end_effector_orientation_error"], 0.15)
        self.assertGreaterEqual(result["motion"]["minimum_environment_clearance"], 0.05)
        self.assertGreaterEqual(result["motion"]["minimum_self_clearance"], 0.05)
        self.assertEqual(report["arguments"]["seed"], 456)
        self.assertTrue(result["motion"]["swept_clearance"]["passed"])
        self.assertEqual(
            result["motion"]["swept_clearance"]["checked_intervals"],
            result["motion"]["dynamic_physics_samples"],
        )


class PiperContinuousJointPathContract(unittest.TestCase):
    def test_sweep_covers_combined_base_and_joint_motion(self):
        runtime = make_static_box_navigation_runtime(
            seed=3, box_position=np.array([0.9, 0.0, 0.1]),
            box_size=np.array([0.2, 0.2, 0.2]), box_yaw=0.03,
        )
        checkers = (
            PiperSelfClearanceChecker(runtime),
            PiperArmClearanceChecker(runtime, protected_body_names=frozenset({STATIC_BOX_BODY})),
        )
        sweeps = [PiperConfigurationSweep(checker) for checker in checkers]
        generator = np.random.default_rng(37)
        nominal = runtime.data.qpos.copy()
        base_address = runtime.env.robot_qpos_adr
        for _ in range(12):
            start = nominal.copy()
            target = nominal.copy()
            start[runtime.joint_qpos_adr] += generator.uniform(-0.04, 0.04, 18)
            target[runtime.joint_qpos_adr] += generator.uniform(-0.08, 0.08, 18)
            target[base_address : base_address + 3] += generator.uniform(-0.01, 0.01, 3)
            axis = generator.normal(size=3)
            axis /= np.linalg.norm(axis)
            delta = np.empty(4)
            mujoco.mju_axisAngle2Quat(delta, axis, 0.08)
            mujoco.mju_mulQuat(
                target[base_address + 3 : base_address + 7], delta,
                start[base_address + 3 : base_address + 7],
            )
            endpoint_distances = []
            for configuration in (start, target):
                runtime.data.qpos[:] = configuration
                mujoco.mj_kinematics(runtime.model, runtime.data)
                endpoint_distances.append([
                    checker.evaluate_current_configuration(required_clearance=0.0).minimum_clearance
                    for checker in checkers
                ])
            lower_bounds = np.min(endpoint_distances, axis=0) - np.array([
                sweep.nearest_endpoint_motion_bound(start, target) for sweep in sweeps
            ])
            velocity = np.empty(runtime.model.nv)
            mujoco.mj_differentiatePos(runtime.model, velocity, 1.0, start, target)
            for fraction in np.linspace(0.0, 1.0, 21):
                runtime.data.qpos[:] = start
                mujoco.mj_integratePos(runtime.model, runtime.data.qpos, velocity, fraction)
                mujoco.mj_kinematics(runtime.model, runtime.data)
                for checker, lower in zip(checkers, lower_bounds):
                    distance = checker.evaluate_current_configuration(required_clearance=0.0).minimum_clearance
                    self.assertGreaterEqual(distance, lower - 1e-10)

    def test_sweep_rejects_unsupported_integrator(self):
        runtime = make_static_box_navigation_runtime(
            seed=3, box_position=np.array([0.9, 0.0, 0.1]),
            box_size=np.array([0.2, 0.2, 0.2]), box_yaw=0.0,
        )
        monitor = ArmMotionMonitor(
            runtime, target_world=np.array([0.65, -0.05, 0.13]),
            required_self_clearance=0.05, required_environment_clearance=0.05,
            required_support_margin=0.02, support_violation_grace_seconds=0.2,
            require_motion_sweep_certificate=True,
        )
        runtime.model.opt.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
        with self.assertRaisesRegex(RolloutFailure, "motion_sweep_unsupported_integrator"):
            monitor.begin_arm_motion()

    def test_motion_bound_covers_between_sample_geometry(self):
        runtime = PiperLocomotionRuntime(seed=3)
        checker = PiperSelfClearanceChecker(runtime)
        generator = np.random.default_rng(29)
        samples = 21
        for _ in range(12):
            start = generator.uniform(checker.arm_low + 0.05, checker.arm_high - 0.05)
            target = generator.uniform(checker.arm_low + 0.05, checker.arm_high - 0.05)
            before = runtime.data.qpos.copy()
            bound = checker.linear_path_sampling_motion_bound(start, target, samples=samples)
            np.testing.assert_array_equal(runtime.data.qpos, before)
            runtime.data.qpos[runtime.joint_qpos_adr[12:]] = start
            mujoco.mj_forward(runtime.model, runtime.data)
            positions = runtime.data.geom_xpos.copy()
            rotations = runtime.data.geom_xmat.reshape(-1, 3, 3).copy()
            runtime.data.qpos[runtime.joint_qpos_adr[12:]] = (
                start + (target - start) / (2.0 * (samples - 1))
            )
            mujoco.mj_forward(runtime.model, runtime.data)
            for geometry in checker.arm_geometries:
                rotation = runtime.data.geom_xmat[geometry].reshape(3, 3)
                angle = np.arccos(np.clip(
                    (np.trace(rotation @ rotations[geometry].T) - 1.0) / 2.0, -1.0, 1.0
                ))
                point_motion = (
                    np.linalg.norm(runtime.data.geom_xpos[geometry] - positions[geometry])
                    + 2.0 * runtime.model.geom_rbound[geometry] * np.sin(angle / 2.0)
                )
                self.assertLessEqual(point_motion, bound + 1.0e-10)
            self.assertAlmostEqual(
                checker.linear_path_sampling_motion_bound(start, target, samples=41),
                bound / 2.0,
            )

    def test_bound_rejects_unsupported_path_inputs(self):
        runtime = PiperLocomotionRuntime(seed=3)
        checker = PiperSelfClearanceChecker(runtime)
        start = runtime.default_qpos[12:].copy()
        self.assertEqual(checker.linear_path_sampling_motion_bound(start, start, samples=2), 0.0)
        with self.assertRaisesRegex(ValueError, "at least two"):
            checker.linear_path_sampling_motion_bound(start, start, samples=1)
        with self.assertRaisesRegex(ValueError, "joint limits"):
            checker.linear_path_sampling_motion_bound(start, checker.arm_high + 1.0, samples=2)
        joint = runtime.model.joint("joint6").id
        runtime.model.jnt_pos[joint, 0] = 0.01
        with self.assertRaisesRegex(ValueError, "origin-anchored"):
            checker.linear_path_sampling_motion_bound(start, start, samples=2)


if __name__ == "__main__":
    unittest.main()