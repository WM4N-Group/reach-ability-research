"""Focused contracts for movable precontact boxes and their runtime interfaces."""

import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import mujoco
import numpy as np
import torch

from check_piper_arm_precontact_motion import ArmMotionMonitor, PiperArmClearanceChecker, PiperSelfClearanceChecker, main
from check_piper_locomotion import PhysicsMonitor, RolloutFailure
from reconfigurable_navigation.reachability.box_state import (
    BoxFrontContactRegion, BoxSnapshotGuard, BoxState, BoxStateReader,
)
from reconfigurable_navigation.reachability.sweep import PiperConfigurationSweep
from reconfigurable_navigation.reachability.scenes import (
    STATIC_BOX_BODY,
    STATIC_BOX_GEOMETRY,
    make_movable_box_navigation_runtime,
    make_static_box_navigation_runtime,
)


class PiperMovableBoxContract(unittest.TestCase):
    def setUp(self):
        self.scene = {
            "seed": 3,
            "box_position": np.array([0.9, 0.0, 0.14]),
            "box_size": np.array([0.2, 0.2, 0.24]),
            "box_yaw": 0.03,
        }

    def _monitor(self, runtime, **options):
        return ArmMotionMonitor(
            runtime, target_world=np.array([0.65, -0.05, 0.14]),
            required_self_clearance=0.05, required_environment_clearance=0.05,
            required_support_margin=0.02, support_violation_grace_seconds=0.2,
            **options,
        )

    def test_free_box_preserves_robot_observation_and_actuation(self):
        fixed = make_static_box_navigation_runtime(**self.scene)
        movable = make_movable_box_navigation_runtime(**self.scene, box_mass=1.2)
        self.assertEqual(movable.model.nq, fixed.model.nq + 7)
        self.assertEqual(movable.model.nv, fixed.model.nv + 6)
        self.assertEqual(movable.model.nu, 18)
        self.assertEqual(movable.observation().shape, (210,))
        np.testing.assert_array_equal(movable.observation(), fixed.observation())
        np.testing.assert_array_equal(movable.joint_qpos_adr, fixed.joint_qpos_adr)
        np.testing.assert_array_equal(movable.model.actuator_trnid, fixed.model.actuator_trnid)
        box = movable.model.body(STATIC_BOX_BODY).id
        joint = int(movable.model.body_jntadr[box])
        self.assertEqual(movable.model.jnt_type[joint], mujoco.mjtJoint.mjJNT_FREE)
        self.assertAlmostEqual(movable.model.body_mass[box], 1.2)
        self.assertEqual(fixed.model.body_jntnum[fixed.model.body(STATIC_BOX_BODY).id], 0)

    def test_box_falls_and_is_supported_by_floor(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        box = runtime.model.body(STATIC_BOX_BODY).id
        joint = int(runtime.model.body_jntadr[box])
        address = int(runtime.model.jnt_qposadr[joint])
        initial_height = float(runtime.data.qpos[address + 2])
        for _ in range(15):
            runtime.hold_default()
        height = float(runtime.data.qpos[address + 2])
        self.assertLess(height, initial_height - 0.01)
        self.assertAlmostEqual(height, 0.12, delta=0.002)
        box_geometry = runtime.model.geom(STATIC_BOX_GEOMETRY).id
        contacts = [
            contact for contact in runtime.data.contact
            if box_geometry in (contact.geom1, contact.geom2) and contact.dist <= 0.0
        ]
        self.assertTrue(contacts)
        self.assertTrue(all(
            runtime.model.geom_type[
                contact.geom2 if contact.geom1 == box_geometry else contact.geom1
            ] == mujoco.mjtGeom.mjGEOM_PLANE
            for contact in contacts
        ))

    def test_invalid_mass_is_rejected(self):
        for mass in (0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(mass=mass), self.assertRaisesRegex(ValueError, "box_mass"):
                make_movable_box_navigation_runtime(**self.scene, box_mass=mass)

    def test_precontact_monitor_accepts_box_floor_support(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        monitor = ArmMotionMonitor(
            runtime, target_world=np.array([0.65, -0.05, 0.14]),
            required_self_clearance=0.05, required_environment_clearance=0.05,
            required_support_margin=0.02, support_violation_grace_seconds=0.2,
        )
        runtime.on_physics_step = monitor
        for _ in range(25):
            runtime.hold_default()
        self.assertTrue(monitor.box_is_movable)
        self.assertGreater(monitor.box_floor_contact_samples, 0)
        self.assertIsNone(monitor.first_box_contact)
        self.assertIsNone(monitor.physics.first_illegal_contact)

    def test_robot_floor_contacts_cannot_be_exempted(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        base_geometry = int(np.flatnonzero(runtime.model.geom_bodyid == runtime.base_id)[0])
        with self.assertRaisesRegex(ValueError, "Robot geometry"):
            PhysicsMonitor(
                runtime, np.zeros(3),
                allowed_external_floor_geometries={base_geometry},
            )

    def test_box_state_uses_fresh_geometry_and_world_velocity(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        reader = BoxStateReader(runtime)
        joint = runtime.model.joint("reachability_box_joint").id
        address = int(runtime.model.jnt_qposadr[joint])
        dof = int(runtime.model.jnt_dofadr[joint])
        cached_geometry = runtime.data.geom_xpos.copy()
        runtime.data.qpos[address : address + 3] = [1.0, 0.1, 0.2]
        runtime.data.qpos[address + 3 : address + 7] = [np.cos(np.pi / 4), 0, 0, np.sin(np.pi / 4)]
        runtime.data.qvel[dof : dof + 6] = [0.2, -0.1, 0.05, 0.1, 0.0, 0.3]
        state = reader.read()
        np.testing.assert_allclose(state.position, [1.0, 0.1, 0.2])
        np.testing.assert_allclose(state.linear_velocity, [0.2, -0.1, 0.05], atol=1e-12)
        np.testing.assert_allclose(state.angular_velocity, [0.0, 0.1, 0.3], atol=1e-12)
        angle = np.pi / 2 + self.scene["box_yaw"]
        np.testing.assert_allclose(state.rotation[:, 0], [np.cos(angle), np.sin(angle), 0.0], atol=1e-12)
        local = np.array([-0.1, 0.03, 0.02])
        np.testing.assert_allclose(state.point_local(state.point_world(local)), local, atol=1e-12)
        np.testing.assert_array_equal(runtime.data.geom_xpos, cached_geometry)

    def test_snapshot_guard_rejects_translation_rotation_speed_and_stale_time(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        reader = BoxStateReader(runtime)
        reference = reader.read()
        guard = BoxSnapshotGuard(reference, geometry_radius=reader.radius)
        self.assertTrue(guard.evaluate(reference)["valid"])
        for position_offset, angle, velocity, angular, time in (
            ([0.002, 0, 0], 0.0, [0, 0, 0], [0, 0, 0], 0.0),
            ([0, 0, 0], 0.01, [0, 0, 0], [0, 0, 0], 0.0),
            ([0, 0, 0], 0.0, [0.006, 0, 0], [0, 0, 0], 0.0),
            ([0, 0, 0], 0.0, [0, 0, 0], [0, 0, 0.03], 0.0),
            ([0, 0, 0], 0.0, [0, 0, 0], [0, 0, 0], -0.01),
        ):
            rotation = np.array([np.cos(angle / 2), 0.0, 0.0, np.sin(angle / 2)])
            quaternion = np.empty(4)
            mujoco.mju_mulQuat(quaternion, rotation, reference.quaternion)
            changed = BoxState(time, reference.position + position_offset, quaternion, velocity, angular)
            self.assertFalse(guard.evaluate(changed)["valid"])

    def test_contact_region_tracks_box_pose_and_excludes_wrist_and_edges(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        reader = BoxStateReader(runtime)
        state = reader.read()
        region = BoxFrontContactRegion(reader.size)
        front = state.point_world(np.array([-0.1, 0.0, 0.0]))
        self.assertTrue(region.contains(state, front, "link7"))
        self.assertFalse(region.contains(state, front, "link6"))
        self.assertFalse(region.contains(state, state.point_world(np.array([0.1, 0, 0])), "link7"))
        self.assertFalse(region.contains(state, state.point_world(np.array([-0.1, 0.099, 0])), "link8"))
        shifted = BoxState(state.time, state.position + [0.02, 0, 0], state.quaternion, np.zeros(3), np.zeros(3))
        self.assertFalse(region.contains(shifted, front, "link7"))
        self.assertFalse(region.as_dict()["contact_enabled"])

    def test_sweep_accounts_for_box_rotation_between_endpoints(self):
        scene = dict(self.scene, box_position=np.array([0.8, 0, 0.35]), box_size=np.full(3, 0.2), box_yaw=0.0)
        runtime = make_movable_box_navigation_runtime(**scene)
        checker = PiperArmClearanceChecker(runtime, protected_body_names=frozenset({STATIC_BOX_BODY}))
        with self.assertRaisesRegex(ValueError, "explicitly allowed"):
            PiperConfigurationSweep(checker)
        sweep = PiperConfigurationSweep(checker, moving_body_names=frozenset({STATIC_BOX_BODY}))
        joint = runtime.model.joint("reachability_box_joint").id
        address = int(runtime.model.jnt_qposadr[joint])
        start = runtime.data.qpos.copy()
        target = start.copy()
        target[address + 3 : address + 7] = [np.cos(np.pi / 4), 0, 0, np.sin(np.pi / 4)]
        endpoint_distances = []
        for configuration in (start, target):
            runtime.data.qpos[:] = configuration
            mujoco.mj_kinematics(runtime.model, runtime.data)
            endpoint_distances.append(checker.evaluate_current_configuration(required_clearance=0.0).minimum_clearance)
        bound = sweep.nearest_endpoint_motion_bound(start, target)
        lower = min(endpoint_distances) - bound
        velocity = np.empty(runtime.model.nv)
        mujoco.mj_differentiatePos(runtime.model, velocity, 1.0, start, target)
        minimum = float("inf")
        for fraction in np.linspace(0.0, 1.0, 41):
            runtime.data.qpos[:] = start
            mujoco.mj_integratePos(runtime.model, runtime.data.qpos, velocity, fraction)
            mujoco.mj_kinematics(runtime.model, runtime.data)
            distance = checker.evaluate_current_configuration(required_clearance=0.0).minimum_clearance
            self.assertGreaterEqual(distance, lower - 1e-10)
            minimum = min(minimum, distance)
        self.assertLess(minimum, min(endpoint_distances) - 1e-4)
        own = PiperConfigurationSweep(PiperSelfClearanceChecker(runtime), moving_body_names=frozenset({STATIC_BOX_BODY}))
        self.assertAlmostEqual(own.nearest_endpoint_motion_bound(start, target), 1e-9)

    def test_sweep_counts_box_translation(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        checker = PiperArmClearanceChecker(runtime, protected_body_names=frozenset({STATIC_BOX_BODY}))
        sweep = PiperConfigurationSweep(checker, moving_body_names=frozenset({STATIC_BOX_BODY}))
        joint = runtime.model.joint("reachability_box_joint").id
        address = int(runtime.model.jnt_qposadr[joint])
        start = runtime.data.qpos.copy()
        target = start.copy()
        target[address] += 0.02
        self.assertAlmostEqual(sweep.nearest_endpoint_motion_bound(start, target), 0.01 + 1e-9)

    def test_pose_change_invalidates_snapshot_before_arm_motion(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        monitor = self._monitor(runtime)
        runtime.on_physics_step = monitor
        for _ in range(25):
            runtime.hold_default()
        monitor.capture_box_snapshot("navigation_target")
        joint = runtime.model.joint("reachability_box_joint").id
        address = int(runtime.model.jnt_qposadr[joint])
        runtime.data.qpos[address] += 0.002
        with self.assertRaisesRegex(RolloutFailure, "box_snapshot_invalidated"):
            runtime.hold_default()
        self.assertTrue(monitor.box_stop_event["replan_required"])
        self.assertGreater(monitor.box_stop_event["validity"]["geometry_displacement_bound"], 0.001)
        self.assertEqual(monitor.dynamic_samples, 0)

    def test_box_velocity_invalidates_snapshot_during_arm_motion(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        monitor = self._monitor(runtime, require_motion_sweep_certificate=True)
        runtime.on_physics_step = monitor
        for _ in range(25):
            runtime.hold_default()
        monitor.capture_box_snapshot("arm_target")
        monitor.begin_arm_motion()
        joint = runtime.model.joint("reachability_box_joint").id
        dof = int(runtime.model.jnt_dofadr[joint])
        runtime.data.qvel[dof] = 0.2
        with self.assertRaisesRegex(RolloutFailure, "box_snapshot_invalidated"):
            runtime.hold_default()
        self.assertGreater(monitor.box_stop_event["validity"]["linear_speed"], 0.005)

    def test_unstable_box_cannot_be_captured_as_valid_snapshot(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        joint = runtime.model.joint("reachability_box_joint").id
        dof = int(runtime.model.jnt_dofadr[joint])
        runtime.data.qvel[dof] = 0.02
        monitor = self._monitor(runtime)
        with self.assertRaisesRegex(RolloutFailure, "box_snapshot_unstable"):
            monitor.capture_box_snapshot("arm_target")
        self.assertFalse(monitor.box_stop_event["validity"]["valid"])

    def test_robot_box_contact_still_aborts_precontact(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        joint = runtime.model.joint("reachability_box_joint").id
        address = int(runtime.model.jnt_qposadr[joint])
        runtime.data.qpos[address : address + 3] = runtime.data.xpos[runtime.base_id]
        mujoco.mj_forward(runtime.model, runtime.data)
        monitor = self._monitor(runtime)
        with self.assertRaisesRegex(RolloutFailure, "precontact_box_contact"):
            monitor._check_box_contact()
        self.assertIsNotNone(monitor.first_box_contact)
        self.assertFalse(monitor.first_box_contact["contact_enabled"])
        self.assertFalse(monitor.first_box_contact["designated_front_hand_contact"])

    def test_sweep_rejects_large_box_rotation_per_step(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        monitor = self._monitor(runtime, require_motion_sweep_certificate=True)
        runtime.on_physics_step = monitor
        monitor.begin_arm_motion()
        joint = runtime.model.joint("reachability_box_joint").id
        dof = int(runtime.model.jnt_dofadr[joint])
        runtime.data.qvel[dof + 5] = 1000.0
        with self.assertRaisesRegex(RolloutFailure, "motion_sweep_integration_mismatch"):
            runtime.hold_default()

    def test_navigation_rejection_reports_target_from_observed_box(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "rejected.json"
            arguments = [
                "check_piper_arm_precontact_motion.py", "--output-json", str(output),
                "--box-mode", "movable", "--seed", "3",
                "--box-position", "0.9", "0", "0.14", "--box-size", "0.2", "0.2", "0.24",
                "--box-yaw", "0.03", "--hand-target-local", "-0.248", "-0.05", "0.02",
            ]
            with patch("sys.argv", arguments), patch(
                "check_piper_arm_precontact_motion.NavigateSkill.can_execute", return_value=False
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 1)
            with output.open() as source:
                result = json.load(source)["result"]
        self.assertEqual(result["reason"], "navigation_rejected")
        snapshot = result["box_runtime"]["snapshots"][0]["state"]
        state = BoxState(
            snapshot["time"], snapshot["position"], snapshot["quaternion"],
            snapshot["linear_velocity_world"], snapshot["angular_velocity_world"],
        )
        np.testing.assert_allclose(
            result["candidate"]["target_world"], state.point_world(np.array([-0.248, -0.05, 0.02])),
            rtol=0.0, atol=1e-12,
        )
        self.assertLess(snapshot["position"][2], 0.13)

    def test_contact_label_uses_generation_frame_and_still_aborts(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        monitor = self._monitor(runtime)
        generated_state = monitor.box_state
        point = generated_state.point_world(np.array([-0.1, 0.0, 0.0]))
        hand_body = runtime.model.body("link7").id
        hand_geometry = int(np.flatnonzero(runtime.model.geom_bodyid == hand_body)[0])
        joint = runtime.model.joint("reachability_box_joint").id
        runtime.data.qpos[int(runtime.model.jnt_qposadr[joint])] += 0.02
        monitor.box_state = monitor.box_reader.read()
        self.assertFalse(monitor.box_contact_region.contains(monitor.box_state, point, "link7"))
        contact = SimpleNamespace(
            geom1=monitor.box_geometry, geom2=hand_geometry, dist=-0.001, pos=point,
            frame=np.diag([-1.0, -1.0, 1.0]).ravel(),
        )
        contact_data = SimpleNamespace(
            contact=[contact], time=runtime.sim_dt,
            geom_xpos=runtime.data.geom_xpos, geom_xmat=runtime.data.geom_xmat,
            xpos=runtime.data.xpos, xquat=runtime.data.xquat,
        )
        with patch.object(runtime, "data", contact_data), patch(
            "check_piper_arm_precontact_motion.mujoco.mj_contactForce"
        ), patch(
            "check_piper_arm_precontact_motion.mujoco.mj_objectVelocity"
        ), self.assertRaisesRegex(RolloutFailure, "precontact_box_contact"):
            monitor._check_box_contact()
        self.assertTrue(monitor.first_box_contact["designated_front_hand_contact"])
        self.assertFalse(monitor.first_box_contact["contact_enabled"])
        np.testing.assert_allclose(monitor.first_box_contact["position_box_frame"], [-0.1, 0, 0], atol=1e-12)

    def test_rollout_reports_replan_after_box_pose_jump(self):
        def disturbed_runtime(**options):
            runtime = make_movable_box_navigation_runtime(**options)
            original_step = runtime.step
            joint = runtime.model.joint("reachability_box_joint").id
            address = int(runtime.model.jnt_qposadr[joint])
            steps = 0

            def step_with_box_change(*arguments, **keywords):
                nonlocal steps
                steps += 1
                if steps == 5:
                    runtime.data.qpos[address] += 0.002
                return original_step(*arguments, **keywords)

            runtime.step = step_with_box_change
            return runtime

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "invalidated.json"
            arguments = [
                "check_piper_arm_precontact_motion.py", "--output-json", str(output),
                "--box-mode", "movable", "--seed", "3",
            ]
            with patch("sys.argv", arguments), patch(
                "check_piper_arm_precontact_motion.make_movable_box_navigation_runtime",
                side_effect=disturbed_runtime,
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 1)
            with output.open() as source:
                result = json.load(source)["result"]
        self.assertFalse(result["passed"])
        self.assertEqual(result["reason"], "box_snapshot_invalidated")
        stop = result["box_runtime"]["stop_event"]
        self.assertTrue(stop["replan_required"])
        self.assertFalse(stop["validity"]["valid"])
        self.assertGreater(stop["validity"]["geometry_displacement_bound"], 0.001)
        self.assertGreater(stop["current"]["time"], stop["reference"]["time"])
        self.assertEqual(result["motion"]["control_steps"], 0)

    def test_snapshot_stop_leaves_swept_coverage_incomplete(self):
        runtime = make_movable_box_navigation_runtime(**self.scene)
        monitor = self._monitor(runtime, require_motion_sweep_certificate=True)
        runtime.on_physics_step = monitor
        for _ in range(25):
            runtime.hold_default()
        monitor.capture_box_snapshot("arm_target")
        monitor.begin_arm_motion()
        runtime.hold_default()
        self.assertGreater(monitor.sweep_intervals, 0)
        self.assertEqual(monitor.sweep_intervals, monitor.dynamic_samples)
        joint = runtime.model.joint("reachability_box_joint").id
        runtime.data.qpos[int(runtime.model.jnt_qposadr[joint])] += 0.002
        with self.assertRaisesRegex(RolloutFailure, "box_snapshot_invalidated"):
            runtime.hold_default()
        self.assertEqual(monitor.dynamic_samples, monitor.sweep_intervals + 1)


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main()