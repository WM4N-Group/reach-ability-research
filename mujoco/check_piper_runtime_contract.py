"""Focused contract checks for PIPER initialization and shared NAV runtime hooks."""

import unittest

import mujoco
import numpy as np
import torch

from check_piper_locomotion import PhysicsMonitor, RolloutFailure
from check_piper_arm_precontact_motion import _world_pose_to_wbc_command
from reconfigurable_navigation.piper_locomotion_runtime import PiperLocomotionRuntime


class PiperRuntimeContract(unittest.TestCase):
    def setUp(self):
        self.runtime = PiperLocomotionRuntime(seed=3)

    def test_nominal_initialization_is_within_joint_limits(self):
        runtime = self.runtime
        positions = runtime.data.qpos[runtime.joint_qpos_adr]
        self.assertTrue(np.all(positions >= runtime.joint_low))
        self.assertTrue(np.all(positions <= runtime.joint_high))
        self.assertLessEqual(float(np.max(np.abs(positions - runtime.default_qpos))), 0.015)
        self.assertAlmostEqual(runtime.data.qpos[runtime.env.robot_qpos_adr + 2], 0.35)
        self.assertEqual(runtime.data.time, 0.0)

    def test_policy_observation_uses_named_training_joint_order(self):
        runtime = self.runtime
        offsets = np.linspace(-0.003, 0.003, 18)
        runtime.data.qpos[runtime.joint_qpos_adr] = runtime.default_qpos + offsets
        runtime.reset()
        policy_names = tuple(
            f"{leg}_{joint}_joint"
            for leg in ("FR", "FL", "RR", "RL")
            for joint in ("hip", "thigh", "calf")
        ) + tuple(f"joint{index}" for index in range(1, 7))
        expected = []
        for name in policy_names:
            joint_id = mujoco.mj_name2id(runtime.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            address = runtime.model.jnt_qposadr[joint_id]
            nominal_index = np.flatnonzero(runtime.joint_qpos_adr == address).item()
            expected.append(runtime.data.qpos[address] - runtime.default_qpos[nominal_index])
        observation = runtime.observation()
        self.assertEqual(observation.shape, (210,))
        np.testing.assert_allclose(observation[18:72].reshape(3, 18), np.tile(expected, (3, 1)), atol=1e-8)

    def test_controller_reset_preserves_physical_state(self):
        runtime = self.runtime
        runtime.hold_default()
        before = (runtime.data.qpos.copy(), runtime.data.qvel.copy(), float(runtime.data.time))
        runtime.last_action.fill(1.0)
        runtime.reset()
        np.testing.assert_array_equal(runtime.data.qpos, before[0])
        np.testing.assert_array_equal(runtime.data.qvel, before[1])
        self.assertEqual(runtime.data.time, before[2])
        np.testing.assert_array_equal(runtime.last_action, np.zeros(18))

    def test_physics_callback_can_abort_inside_control_period(self):
        runtime = self.runtime
        times = []

        def stop_after_three_steps():
            times.append(float(runtime.data.time))
            if len(times) == 3:
                raise RolloutFailure("injected_abort")

        runtime.on_physics_step = stop_after_three_steps
        with self.assertRaisesRegex(RolloutFailure, "injected_abort"):
            runtime.hold_default()
        np.testing.assert_allclose(times, runtime.sim_dt * np.arange(1, 4))
        self.assertAlmostEqual(runtime.data.time, 3 * runtime.sim_dt)

    def test_monitor_rejects_unexpected_physical_reset(self):
        runtime = self.runtime
        monitor = PhysicsMonitor(runtime, np.zeros(3))
        runtime.on_physics_step = monitor
        runtime.hold_default()
        mujoco.mj_resetData(runtime.model, runtime.data)
        with self.assertRaisesRegex(RolloutFailure, "unexpected_physics_reset"):
            monitor()

    def test_wbc_command_preserves_world_pose_in_mixed_frame(self):
        runtime = self.runtime
        mount = runtime.model.body("Piper").id
        desired_position = runtime.data.xpos[mount] + np.array([0.5, -0.1, 0.2])
        desired_quaternion = runtime.data.xquat[runtime.model.body("end_effector").id].copy()
        command = _world_pose_to_wbc_command(
            runtime, desired_position, desired_quaternion
        )
        mount_rotation = runtime.data.xmat[mount].reshape(3, 3)
        reconstructed_position = runtime.data.xpos[mount] + mount_rotation @ np.array(
            [command[0], command[1], 0.0]
        )
        reconstructed_position[2] = command[2]
        reconstructed_quaternion = np.empty(4)
        mujoco.mju_mulQuat(
            reconstructed_quaternion, runtime.data.xquat[mount], command[3:]
        )
        np.testing.assert_allclose(reconstructed_position, desired_position, atol=1e-12)
        self.assertAlmostEqual(
            abs(float(reconstructed_quaternion @ desired_quaternion)), 1.0, places=12
        )


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main()