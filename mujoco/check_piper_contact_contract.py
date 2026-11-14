"""Physical-contact diagnostics, distinct from the frozen controller proxy."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import mujoco
import numpy as np
import torch

from check_piper_arm_precontact_motion import _hand_position
from check_piper_contact_handoff_replay import _failure_replay
from reconfigurable_navigation.box_push_runtime import BoxPushArmController
from reconfigurable_navigation.piper_box_runtime import make_episode
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.reachability.contact_geometry import (
    NATIVE_PUSH_APPROACH_DISTANCE, NATIVE_PUSH_HAND_PITCH, PiperContactGeometryReader,
    read_box_contact_sample,
)
from reconfigurable_navigation.reachability.contact_limits import (
    ContactHandoffGuard, ContactLimitDeclaration, ContactLimitMonitor,
    ContactLimitProvenance, ContactLimits,
)
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime
from reconfigurable_navigation.reachability import PiperPositionReachabilityOracle, ReachabilityQuery


class PiperContactContract(unittest.TestCase):
    def setUp(self):
        self.runtime = make_movable_box_navigation_runtime(
            seed=574, box_position=np.array([1.0, 0.08, 0.12]),
            box_size=np.full(3, 0.24), box_yaw=-0.06,
            config_path=DEPLOY / "config_wbc.yaml",
        )

    def test_proxy_and_physical_end_effector_are_distinct(self):
        result = PiperContactGeometryReader(self.runtime).read()
        self.assertGreater(result["proxy_to_end_effector_distance"], 0.19)
        self.assertLess(result["proxy_to_end_effector_distance"], 0.21)
        self.assertEqual({row["body"] for row in result["fingers"]}, {"link7", "link8"})
        self.assertFalse(result["contact_execution_enabled"])
        for row in result["fingers"]:
            self.assertTrue(row["separated_witnesses_valid"])
            self.assertAlmostEqual(
                np.linalg.norm(np.asarray(row["box_point_world"]) - row["finger_point_world"]),
                row["clearance"], places=8,
            )
            self.assertAlmostEqual(row["closing_speed"], 0.0)
            self.assertAlmostEqual(row["tangential_speed"], 0.0)

    def test_default_hand_point_matches_native_piper_adapter(self):
        with patch(
            "reconfigurable_navigation.piper_box_runtime.BoxPushRuntime",
            side_effect=RuntimeError("capture_native_configuration"),
        ) as constructor:
            with self.assertRaisesRegex(RuntimeError, "capture_native_configuration"):
                make_episode("push", "unused-policy", 0, push_ik_mode="pose")
        configuration = constructor.call_args.kwargs["arm_config"]
        self.assertEqual(configuration["hand_body_name"], "end_effector")
        self.assertEqual(configuration["hand_offset"], (0, 0, 0))
        self.assertEqual(configuration["hand_pitch"], NATIVE_PUSH_HAND_PITCH)
        self.assertEqual(configuration["approach_distance"], NATIVE_PUSH_APPROACH_DISTANCE)
        controller = BoxPushArmController(
            self.runtime, self.runtime.model.geom("reachability_box").id,
            np.array([1.5, 0, 0.12]), **configuration,
        )
        np.testing.assert_array_equal(_hand_position(self.runtime), controller.hand_position())
        self.assertGreater(np.linalg.norm(
            _hand_position(self.runtime, "legacy-proxy") - controller.hand_position()
        ), 0.19)

    def test_proxy_definition_does_not_change_collision_measurements(self):
        original = PiperContactGeometryReader(self.runtime).read()
        at_end_effector = PiperContactGeometryReader(self.runtime, proxy_offset=(0, 0, 0.13)).read()
        self.assertLess(at_end_effector["proxy_to_end_effector_distance"], 1e-7)
        self.assertEqual(original["fingers"], at_end_effector["fingers"])

    def test_contact_reader_reports_handoff_without_granting_execution(self):
        guard = Mock()
        guard.check_precontact.return_value = {
            "state": "ready_for_contact",
            "ready_for_contact": True,
            "contact_execution_enabled": False,
        }
        result = PiperContactGeometryReader(self.runtime).read(
            handoff_guard=guard, snapshot_valid=True,
            support_valid=True, nonhand_clearance_valid=True,
            native_orientation_valid=True,
        )
        self.assertEqual(result["contact_handoff"]["state"], "ready_for_contact")
        self.assertFalse(result["contact_handoff"]["contact_execution_enabled"])
        arguments = guard.check_precontact.call_args.kwargs
        self.assertTrue(arguments["snapshot_valid"])
        self.assertTrue(arguments["support_valid"])
        self.assertTrue(arguments["nonhand_clearance_valid"])
        self.assertTrue(arguments["native_orientation_valid"])
        self.assertTrue(arguments["contact_free"])

    def test_reading_uses_fresh_geometry_without_mutating_runtime(self):
        reader = PiperContactGeometryReader(self.runtime)
        self.runtime.data.qpos[self.runtime.joint_qpos_adr[13]] += 0.01
        saved = tuple(values.copy() for values in (
            self.runtime.data.qpos, self.runtime.data.qvel,
            self.runtime.data.ctrl, self.runtime.data.geom_xpos,
        ))
        result = reader.read()
        for before, after in zip(saved, (
            self.runtime.data.qpos, self.runtime.data.qvel,
            self.runtime.data.ctrl, self.runtime.data.geom_xpos,
        )):
            np.testing.assert_array_equal(before, after)
        stale_end = self.runtime.data.xpos[self.runtime.model.body("end_effector").id]
        self.assertGreater(np.linalg.norm(np.asarray(result["end_effector_world"]) - stale_end), 1e-5)

    def test_pose_ik_recovers_known_target_and_restores_state(self):
        runtime = self.runtime
        oracle = PiperPositionReachabilityOracle(runtime)
        scratch = mujoco.MjData(runtime.model)
        scratch.qpos[:] = runtime.data.qpos
        known = np.array([0.15, 1.1, -0.9, 0.35, -0.35, 0.2])
        scratch.qpos[runtime.joint_qpos_adr[12:]] = known
        mujoco.mj_forward(runtime.model, scratch)
        end_effector = runtime.model.body("end_effector").id
        rotation = runtime.data.xmat[runtime.base_id].reshape(3, 3)
        query = ReachabilityQuery(
            np.array([*runtime.data.qpos[:2], np.arctan2(rotation[1, 0], rotation[0, 0])]),
            scratch.xpos[end_effector].copy(),
        )
        quaternion = scratch.xquat[end_effector].copy()
        before = (runtime.data.qpos.copy(), runtime.data.qvel.copy(), runtime.data.ctrl.copy())
        result = oracle.solve(query, target_quaternion=quaternion, initial_joint_positions=known + 0.03)
        self.assertTrue(result.kinematic_feasible)
        self.assertLessEqual(result.position_error, 1e-4)
        self.assertLessEqual(result.orientation_error, 1e-3)
        mirrored = oracle.solve(query, target_quaternion=-quaternion, initial_joint_positions=known + 0.03)
        np.testing.assert_allclose(result.joint_solution, mirrored.joint_solution, atol=1e-10)
        for initial, actual in zip(before, (runtime.data.qpos, runtime.data.qvel, runtime.data.ctrl)):
            np.testing.assert_array_equal(initial, actual)
        scratch.qpos[runtime.joint_qpos_adr[17]] += 0.1
        mujoco.mj_forward(runtime.model, scratch)
        np.testing.assert_allclose(scratch.xpos[end_effector], query.target_position, atol=1e-10)
        rotation_only = oracle.solve(
            query, target_quaternion=scratch.xquat[end_effector].copy(), initial_joint_positions=known,
        )
        self.assertTrue(rotation_only.kinematic_feasible)
        self.assertGreater(rotation_only.iterations, 0)
        self.assertLessEqual(rotation_only.orientation_error, 1e-3)
        for invalid in (np.zeros(4), np.array([2.0, 0, 0, 0]), np.full(4, np.nan)):
            with self.assertRaisesRegex(ValueError, "quaternion"):
                oracle.solve(query, target_quaternion=invalid)
        with self.assertRaisesRegex(ValueError, "legacy offset"):
            oracle.solve(query, target_quaternion=quaternion, hand_offset=(0.15, 0, 0))

    def test_force_on_box_is_invariant_to_contact_geometry_order(self):
        runtime = self.runtime
        reader = PiperContactGeometryReader(runtime)
        box = reader.box_reader.geometry
        hand = reader.finger_geometries[0]
        rotation = runtime.data.geom_xmat[box].reshape(3, 3)
        point = runtime.data.geom_xpos[box] - rotation[:, 0] * 0.12
        samples = []
        for reverse in (False, True):
            frame = rotation.T.copy()
            if reverse:
                frame[:2] *= -1.0
            contact = SimpleNamespace(
                geom1=box if reverse else hand, geom2=hand if reverse else box,
                frame=frame.ravel(), pos=point,
            )
            samples.append(read_box_contact_sample(
                runtime, contact, np.array([5., 1., 0., 0., 0., 0.]), box_geometry=box, region=reader.region
            ))
        for sample in samples:
            np.testing.assert_allclose(sample["force_box_frame"], [5, 1, 0], atol=1e-12)
            self.assertAlmostEqual(sample["normal_speed"], 0.0)
            self.assertAlmostEqual(sample["tangential_speed"], 0.0)

    def test_contact_limits_stop_is_latched_until_fresh_observation(self):
        limits = ContactLimits(10.0, 2.0, 0.02, 0.01, 0.15, 0.07)
        monitor = ContactLimitMonitor(limits)
        sample = dict(
            measurement_valid=True, region_matched=True,
            normal_force=5.0, tangential_force=0.5, normal_speed=0.01,
            tangential_speed=0.002, orientation_error=0.05, tip_distance=0.03,
        )
        conditions = dict(snapshot_valid=True, support_valid=True, nonhand_clearance_valid=True)
        ready = monitor.observe([sample], time=1.0, **conditions)
        self.assertTrue(ready["within_declared_limits"])
        self.assertFalse(ready["contact_execution_enabled"])
        stopped = monitor.observe([sample, dict(sample, normal_force=6.0)], time=1.1, **conditions)
        self.assertIn("normal_force_exceeded", stopped["stop_reasons"])
        self.assertFalse(monitor.observe([sample], time=1.2, **conditions)["within_declared_limits"])
        with self.assertRaisesRegex(ValueError, "fresh valid"):
            monitor.reset_after_reobservation(time=1.2, snapshot_valid=True)
        monitor.reset_after_reobservation(time=1.3, snapshot_valid=True)
        self.assertTrue(monitor.observe([sample], time=1.3, **conditions)["within_declared_limits"])
        self.assertIsNone(ContactLimitMonitor(limits).observe([], time=0.0, **conditions)["within_declared_limits"])

    def test_contact_limits_reject_each_invalid_boundary(self):
        limits = ContactLimits(10.0, 2.0, 0.02, 0.01, 0.15, 0.07)
        valid = dict(
            measurement_valid=True, region_matched=True,
            normal_force=5.0, tangential_force=0.5, normal_speed=0.01,
            tangential_speed=0.002, orientation_error=0.05, tip_distance=0.03,
        )
        for key, value, reason in (
            ("normal_force", -1.0, "outward_normal_force"),
            ("normal_force", 11.0, "normal_force_exceeded"),
            ("tangential_force", 3.0, "tangential_force_exceeded"),
            ("normal_speed", -0.03, "normal_speed_exceeded"),
            ("tangential_speed", 0.02, "tangential_speed_exceeded"),
            ("orientation_error", 0.2, "orientation_error_exceeded"),
            ("tip_distance", 0.08, "contact_too_far_from_native_hand"),
            ("region_matched", False, "contact_outside_designated_region"),
            ("normal_force", float("nan"), "invalid_contact_measurement"),
        ):
            with self.subTest(key=key, value=value):
                result = ContactLimitMonitor(limits).observe(
                    [dict(valid, **{key: value})], time=1.0,
                    snapshot_valid=True, support_valid=True, nonhand_clearance_valid=True,
                )
                self.assertIn(reason, result["stop_reasons"])
                self.assertTrue(result["reobserve_required"])
                self.assertFalse(result["contact_execution_enabled"])

    def test_floor_support_is_not_counted_as_hand_contact(self):
        for _ in range(25):
            self.runtime.hold_default()
        reader = PiperContactGeometryReader(self.runtime)
        without_limits = reader.read()
        self.assertEqual(without_limits["contact_samples"], [])
        self.assertEqual(without_limits["contact_limits_status"], "not_configured")
        declared = ContactLimitMonitor(ContactLimits(10.0, 2.0, 0.02, 0.01, 0.15, 0.07))
        result = reader.read(
            limit_monitor=declared, snapshot_valid=True, support_valid=True,
            nonhand_clearance_valid=True,
        )
        self.assertEqual(result["contact_limits_status"], "await_contact")
        self.assertIsNone(result["contact_limits_assessment"]["within_declared_limits"])
        self.assertFalse(result["contact_execution_enabled"])

    def test_relative_contact_speed_matches_point_jacobians(self):
        runtime = self.runtime
        reader = PiperContactGeometryReader(runtime)
        box = reader.box_reader.geometry
        hand = reader.finger_geometries[0]
        box_joint = runtime.model.joint("reachability_box_joint").id
        box_dof = int(runtime.model.jnt_dofadr[box_joint])
        runtime.data.qvel[runtime.joint_dof_adr[12]] = 0.2
        runtime.data.qvel[box_dof : box_dof + 6] = [0.01, -0.005, 0, 0, 0, 0.05]
        mujoco.mj_forward(runtime.model, runtime.data)
        rotation = runtime.data.geom_xmat[box].reshape(3, 3)
        point = runtime.data.geom_xpos[box] - 0.12 * rotation[:, 0]
        contact = SimpleNamespace(geom1=hand, geom2=box, pos=point, frame=rotation.T.ravel())
        sample = read_box_contact_sample(
            runtime, contact, np.array([5., 0, 0, 0, 0, 0]), box_geometry=box, region=reader.region
        )
        velocities = []
        for geometry in (hand, box):
            jacobian = np.zeros((3, runtime.model.nv))
            mujoco.mj_jac(runtime.model, runtime.data, jacobian, None, point, int(runtime.model.geom_bodyid[geometry]))
            velocities.append(jacobian @ runtime.data.qvel)
        relative = rotation.T @ (velocities[0] - velocities[1])
        self.assertAlmostEqual(sample["normal_speed"], relative[0], places=12)
        self.assertAlmostEqual(sample["tangential_speed"], np.linalg.norm(relative[1:]), places=12)

    def test_contact_limits_require_environment_checks_and_monotonic_time(self):
        limits = ContactLimits(10.0, 2.0, 0.02, 0.01, 0.15, 0.07)
        for key, reason in (
            ("snapshot_valid", "invalid_box_snapshot"),
            ("support_valid", "invalid_support"),
            ("nonhand_clearance_valid", "invalid_nonhand_clearance"),
        ):
            conditions = dict(snapshot_valid=True, support_valid=True, nonhand_clearance_valid=True)
            conditions[key] = np.bool_(False)
            result = ContactLimitMonitor(limits).observe([], time=0.0, **conditions)
            self.assertIn(reason, result["stop_reasons"])
        monitor = ContactLimitMonitor(limits)
        conditions = dict(snapshot_valid=True, support_valid=True, nonhand_clearance_valid=True)
        monitor.observe([], time=1.0, **conditions)
        self.assertIn("invalid_observation_time", monitor.observe([], time=0.9, **conditions)["stop_reasons"])
        with self.assertRaisesRegex(ValueError, "fresh valid"):
            monitor.reset_after_reobservation(time=1.1, snapshot_valid=False)

    def test_handoff_guard_is_fail_closed_and_recovers_only_after_fresh_observation(self):
        guard = ContactHandoffGuard(ContactLimits(10.0, 2.0, 0.02, 0.01, 0.15, 0.07))
        valid = dict(
            snapshot_valid=True, support_valid=True,
            nonhand_clearance_valid=True, designated_face_ready=True,
            native_orientation_valid=True, contact_free=True,
        )
        ready = guard.check_precontact(time=1.0, **valid)
        self.assertEqual(ready["state"], "ready_for_contact")
        self.assertTrue(ready["ready_for_contact"])
        self.assertFalse(ready["contact_execution_enabled"])
        blocked = guard.check_precontact(
            time=1.1, **{**valid, "designated_face_ready": False}
        )
        self.assertEqual(blocked["state"], "stop_reobserve")
        self.assertIn("invalid_designated_contact_face", blocked["stop_reasons"])
        self.assertFalse(guard.check_precontact(time=1.2, **valid)["ready_for_contact"])
        with self.assertRaisesRegex(ValueError, "valid fresh handoff"):
            guard.reset_after_reobservation(
                time=1.2, **{**valid, "contact_free": False}
            )
        guard.reset_after_reobservation(time=1.3, **valid)
        self.assertTrue(guard.check_precontact(time=1.4, **valid)["ready_for_contact"])
        sample = dict(
            measurement_valid=True, region_matched=True,
            normal_force=5.0, tangential_force=0.5, normal_speed=0.01,
            tangential_speed=0.002, orientation_error=0.05, tip_distance=0.03,
        )
        within = guard.observe_contact(
            [sample], time=1.5, snapshot_valid=True,
            support_valid=True, nonhand_clearance_valid=True,
        )
        self.assertTrue(within["within_declared_limits"])
        stopped = guard.observe_contact(
            [dict(sample, normal_force=11.0)], time=1.6,
            snapshot_valid=True, support_valid=True,
            nonhand_clearance_valid=True,
        )
        self.assertEqual(stopped["state"], "stop_reobserve")
        self.assertIn("normal_force_exceeded", stopped["stop_reasons"])
        guard.reset_after_reobservation(time=1.7, **valid)
        self.assertTrue(guard.check_precontact(time=1.8, **valid)["ready_for_contact"])

    def test_readonly_handoff_replay_covers_each_precondition_and_force_stop(self):
        limits = ContactLimits(10.0, 2.0, 0.02, 0.01, 0.15, 0.07)
        conditions = dict(
            snapshot_valid=True, support_valid=True,
            nonhand_clearance_valid=True, designated_face_ready=True,
            native_orientation_valid=True, contact_free=True,
        )
        result = _failure_replay(conditions, limits, time=2.0)
        self.assertEqual(result["baseline"]["state"], "ready_for_contact")
        self.assertEqual(set(result["precondition_failures"]), set(conditions))
        for failure in result["precondition_failures"].values():
            self.assertEqual(failure["stop"]["state"], "stop_reobserve")
            self.assertEqual(failure["latched_after_valid_read"]["state"], "stop_reobserve")
            self.assertEqual(failure["recovered"]["state"], "ready_for_contact")
        self.assertEqual(
            result["contact_limit_failure"]["stop"]["state"], "stop_reobserve"
        )
        self.assertEqual(
            result["contact_limit_failure"]["latched_after_empty_read"]["state"],
            "stop_reobserve",
        )
        self.assertFalse(result["baseline"]["contact_execution_enabled"])

    def test_contact_limit_provenance_is_preserved_in_handoff_state(self):
        declaration = ContactLimitDeclaration(
            limits=ContactLimits(10.0, 2.0, 0.02, 0.01, 0.15, 0.07),
            provenance=ContactLimitProvenance(
                source="unit-test", purpose="contract", calibration_status="diagnostic_only"
            ),
        )
        result = ContactHandoffGuard(declaration).check_precontact(
            time=1.0, snapshot_valid=True, support_valid=True,
            nonhand_clearance_valid=True, designated_face_ready=True,
            native_orientation_valid=True, contact_free=True,
        )
        self.assertEqual(result["limits_provenance"]["source"], "unit-test")
        self.assertEqual(result["limits_provenance"]["calibration_status"], "diagnostic_only")


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main()