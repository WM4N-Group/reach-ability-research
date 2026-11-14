"""Execute one provenance-visible PIPER precontact arm candidate without contact."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
import torch

from check_piper_locomotion import PhysicsMonitor, RolloutFailure
from check_piper_navigation import observation
from check_piper_startup import sha256
from reconfigurable_navigation.box_push_runtime import CONTROL, CONTROL_PATH, batch
from reconfigurable_navigation.locomotion_runtime import MJ_POLICY_INDICES, POLICY_MJ_INDICES
from reconfigurable_navigation.piper_locomotion_runtime import DEPLOY
from reconfigurable_navigation.piper_robot_profile import PROFILE_PATH
from reconfigurable_navigation.reachability import (
    PiperArmClearanceChecker,
    PiperPositionReachabilityOracle,
    PiperQuasiStaticSupportChecker,
    PiperSelfClearanceChecker,
    ReachabilityQuery,
    STATIC_BOX_BODY,
    make_static_box_navigation_runtime,
)
from reconfigurable_navigation.reachability.clearance import ARM_BODY_NAMES
from reconfigurable_navigation.representations import SkillAction, SkillType
from reconfigurable_navigation.reachability.sweep import PiperConfigurationSweep
from reconfigurable_navigation.reachability.box_state import (
    BoxFrontContactRegion, BoxSnapshotGuard, BoxState, BoxStateReader,
)
from reconfigurable_navigation.reachability.scenes import make_movable_box_navigation_runtime
from reconfigurable_navigation.reachability.contact_geometry import (
    NATIVE_PUSH_APPROACH_DISTANCE, PiperContactGeometryReader, native_push_orientation,
    read_box_contact_sample,
)
from reconfigurable_navigation.skills.base import SkillStatus
from reconfigurable_navigation.skills.navigate import NavigateConfig, NavigateSkill, wrap_angle


HAND_OFFSET = np.array([0.15, 0.0, 0.0], dtype=np.float64)


def _designated_hand_environment_safe(
    *,
    unified_environment_safe: bool,
    finger_clearance: float,
    nonhand_environment_safe: bool,
    designated_face_ready: bool,
) -> bool:
    return bool(
        finger_clearance >= 0.0
        and nonhand_environment_safe
        and (unified_environment_safe or designated_face_ready)
    )


def _base_pose(runtime, target: np.ndarray) -> np.ndarray:
    robot_state = observation(runtime, target).robot_state
    return np.array([robot_state[0], robot_state[1], robot_state[5]], dtype=np.float64)


def _base_hold_velocity(
    reference_pose: np.ndarray,
    current_pose: np.ndarray,
    *,
    position_gain: float,
    yaw_gain: float,
    maximum_linear_speed: float,
    maximum_yaw_rate: float,
) -> np.ndarray:
    reference = np.asarray(reference_pose, dtype=np.float64)
    current = np.asarray(current_pose, dtype=np.float64)
    if reference.shape != (3,) or current.shape != (3,) or not np.isfinite((reference, current)).all():
        raise ValueError("Base hold poses must contain three finite values")
    values = (position_gain, yaw_gain, maximum_linear_speed, maximum_yaw_rate)
    if not np.isfinite(values).all() or min(values) < 0.0:
        raise ValueError("Base hold gains and limits must be finite and non-negative")
    cosine, sine = np.cos(current[2]), np.sin(current[2])
    error_world = reference[:2] - current[:2]
    command = np.array([
        position_gain * (cosine * error_world[0] + sine * error_world[1]),
        position_gain * (-sine * error_world[0] + cosine * error_world[1]),
        np.clip(yaw_gain * wrap_angle(reference[2] - current[2]), -maximum_yaw_rate, maximum_yaw_rate),
    ])
    planar_speed = float(np.linalg.norm(command[:2]))
    if planar_speed > maximum_linear_speed:
        command[:2] *= maximum_linear_speed / planar_speed
    return command


def hand_point_parameters(hand_point: str) -> tuple[str, tuple[float, float, float]]:
    if hand_point == "piper":
        return "end_effector", (0.0, 0.0, 0.0)
    if hand_point == "legacy-proxy":
        return "link6", tuple(HAND_OFFSET)
    raise ValueError("Unknown hand point reference")


def _hand_position(runtime, hand_point: str = "piper") -> np.ndarray:
    body_name, offset = hand_point_parameters(hand_point)
    body = runtime.model.body(body_name).id
    rotation = runtime.data.xmat[body].reshape(3, 3)
    return runtime.data.xpos[body].copy() + rotation @ np.asarray(offset)


def _box_local_position(world_position, monitor, box_position, box_rotation):
    if monitor.box_state is not None:
        return monitor.box_state.point_local(world_position)
    return box_rotation.T @ (world_position - box_position)


def _candidate_end_effector_world_pose(
    runtime, arm_joint_positions: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    saved_qpos = runtime.data.qpos.copy()
    saved_qvel = runtime.data.qvel.copy()
    saved_ctrl = runtime.data.ctrl.copy()
    try:
        runtime.data.qpos[runtime.joint_qpos_adr[12:]] = arm_joint_positions
        runtime.data.qvel.fill(0.0)
        mujoco.mj_forward(runtime.model, runtime.data)
        end_effector = runtime.model.body("end_effector").id
        return (
            runtime.data.xpos[end_effector].copy(),
            runtime.data.xquat[end_effector].copy(),
        )
    finally:
        runtime.data.qpos[:] = saved_qpos
        runtime.data.qvel[:] = saved_qvel
        runtime.data.ctrl[:] = saved_ctrl
        mujoco.mj_forward(runtime.model, runtime.data)


def _contact_geometry_at_configuration(
    oracle,
    query: ReachabilityQuery,
    arm_joint_positions: np.ndarray,
    reader: PiperContactGeometryReader,
) -> dict[str, object]:
    saved_state = oracle._save_state()
    try:
        oracle._set_query_state(query, arm_joint_positions)
        return reader.read()
    finally:
        oracle._restore_state(*saved_state)


def _world_pose_to_wbc_command(
    runtime, position_world: np.ndarray, quaternion_world: np.ndarray
) -> np.ndarray:
    mount = runtime.model.body("Piper").id
    mount_rotation = runtime.data.xmat[mount].reshape(3, 3)
    relative_position = mount_rotation.T @ (
        np.asarray(position_world, dtype=np.float64) - runtime.data.xpos[mount]
    )
    inverse_mount = np.empty(4, dtype=np.float64)
    mujoco.mju_negQuat(inverse_mount, runtime.data.xquat[mount])
    relative_quaternion = np.empty(4, dtype=np.float64)
    mujoco.mju_mulQuat(
        relative_quaternion,
        inverse_mount,
        np.asarray(quaternion_world, dtype=np.float64),
    )
    relative_quaternion /= np.linalg.norm(relative_quaternion)
    if relative_quaternion[0] < 0.0:
        relative_quaternion *= -1.0
    return np.array(
        [
            relative_position[0],
            relative_position[1],
            position_world[2],
            *relative_quaternion,
        ],
        dtype=np.float64,
    )


def _quaternion_error(actual: np.ndarray, desired: np.ndarray) -> float:
    inverse_desired = np.empty(4, dtype=np.float64)
    mujoco.mju_negQuat(inverse_desired, desired)
    difference = np.empty(4, dtype=np.float64)
    mujoco.mju_mulQuat(difference, actual, inverse_desired)
    if difference[0] < 0.0:
        difference *= -1.0
    rotation_vector = np.empty(3, dtype=np.float64)
    mujoco.mju_quat2Vel(rotation_vector, difference, 1.0)
    return float(np.linalg.norm(rotation_vector))


def _slerp_quaternion(
    start: np.ndarray, target: np.ndarray, fraction: float
) -> np.ndarray:
    start_quaternion = np.asarray(start, dtype=np.float64)
    target_quaternion = np.asarray(target, dtype=np.float64).copy()
    dot = float(start_quaternion @ target_quaternion)
    if dot < 0.0:
        target_quaternion *= -1.0
        dot = -dot
    if dot > 0.9995:
        result = start_quaternion + fraction * (
            target_quaternion - start_quaternion
        )
        return result / np.linalg.norm(result)
    angle = math.acos(np.clip(dot, -1.0, 1.0))
    scale = math.sin(angle)
    return (
        math.sin((1.0 - fraction) * angle) / scale * start_quaternion
        + math.sin(fraction * angle) / scale * target_quaternion
    )


def _orientation_feedback(
    actual: np.ndarray,
    desired: np.ndarray,
    integral: np.ndarray,
    *,
    gain: float,
    control_dt: float,
    maximum_radians: float,
) -> tuple[np.ndarray, np.ndarray]:
    inverse_actual = actual.copy()
    inverse_actual[1:] *= -1.0
    error = np.empty(4, dtype=np.float64)
    mujoco.mju_mulQuat(error, desired, inverse_actual)
    if error[0] < 0.0:
        error *= -1.0
    error_vector = np.zeros(3, dtype=np.float64)
    mujoco.mju_quat2Vel(error_vector, error, 1.0)
    integral = integral + gain * control_dt * error_vector
    magnitude = float(np.linalg.norm(integral))
    if magnitude > maximum_radians:
        integral *= maximum_radians / magnitude
        magnitude = maximum_radians
    correction = np.array([1.0, 0.0, 0.0, 0.0])
    if magnitude > 0.0:
        mujoco.mju_axisAngle2Quat(correction, integral / magnitude, magnitude)
    command = np.empty(4, dtype=np.float64)
    mujoco.mju_mulQuat(command, correction, desired)
    return command, integral


def _policy_joint_target(runtime) -> np.ndarray:
    runtime.velocity_command.fill(0.0)
    policy_observation = torch.from_numpy(runtime.observation()).unsqueeze(0)
    with torch.inference_mode():
        action = runtime.policy(policy_observation).squeeze(0).cpu().numpy()
    action = np.clip(action, -runtime.action_clip, runtime.action_clip).astype(
        np.float64
    )
    target_policy = (
        runtime.default_qpos[MJ_POLICY_INDICES]
        + action * runtime.action_scale[MJ_POLICY_INDICES]
    )
    return np.clip(
        target_policy[POLICY_MJ_INDICES], runtime.joint_low, runtime.joint_high
    )


class ArmMotionMonitor:
    def __init__(
        self,
        runtime,
        *,
        target_world: np.ndarray,
        required_self_clearance: float,
        required_environment_clearance: float,
        required_support_margin: float,
        support_violation_grace_seconds: float,
        require_motion_sweep_certificate: bool = False,
        maximum_box_displacement: float = 0.001,
        maximum_box_linear_speed: float = 0.005,
        maximum_box_angular_speed: float = 0.02,
        hand_point: str = "piper",
        diagnose_designated_hand_approach: bool = False,
    ) -> None:
        self.runtime = runtime
        hand_point_parameters(hand_point)
        if diagnose_designated_hand_approach and hand_point != "piper":
            raise ValueError("Designated hand approach diagnosis requires the piper hand point")
        self.hand_point = hand_point
        self.diagnose_designated_hand_approach = diagnose_designated_hand_approach
        self.box_geometry = runtime.model.geom(STATIC_BOX_BODY).id
        box_body = int(runtime.model.geom_bodyid[self.box_geometry])
        box_joint = int(runtime.model.body_jntadr[box_body])
        self.box_is_movable = bool(
            runtime.model.body_jntnum[box_body] == 1
            and runtime.model.jnt_type[box_joint] == mujoco.mjtJoint.mjJNT_FREE
        )
        self.box_reader = BoxStateReader(runtime) if self.box_is_movable else None
        self.box_state = self.box_reader.read() if self.box_reader is not None else None
        self.box_contact_region = BoxFrontContactRegion(self.box_reader.size) if self.box_reader is not None else None
        self.box_guard = None
        self.box_snapshots = []
        self.box_guard_result = None
        self.box_stop_event = None
        self.maximum_box_displacement = 0.0
        self.maximum_box_linear_speed = 0.0
        self.maximum_box_angular_speed = 0.0
        self.box_validity_limits = {
            "maximum_displacement": maximum_box_displacement,
            "maximum_linear_speed": maximum_box_linear_speed,
            "maximum_angular_speed": maximum_box_angular_speed,
        }
        self.physics = PhysicsMonitor(
            runtime, np.zeros(3),
            allowed_external_floor_geometries=(
                frozenset({self.box_geometry}) if self.box_is_movable else frozenset()
            ),
        )
        self.clearance_data = mujoco.MjData(runtime.model)
        self.self_clearance = PiperSelfClearanceChecker(runtime, data=self.clearance_data)
        self.environment_clearance = PiperArmClearanceChecker(
            runtime, protected_body_names=frozenset({STATIC_BOX_BODY}), data=self.clearance_data
        )
        self.contact_geometry_reader = (
            PiperContactGeometryReader(runtime)
            if diagnose_designated_hand_approach else None
        )
        if self.contact_geometry_reader is not None:
            finger_bodies = self.contact_geometry_reader.region.hand_bodies
            self.finger_environment_clearance = PiperArmClearanceChecker(
                runtime,
                protected_body_names=frozenset({STATIC_BOX_BODY}),
                arm_body_names=finger_bodies,
                data=self.clearance_data,
            )
            self.nonhand_environment_clearance = PiperArmClearanceChecker(
                runtime,
                protected_body_names=frozenset({STATIC_BOX_BODY}),
                arm_body_names=ARM_BODY_NAMES - finger_bodies,
                data=self.clearance_data,
            )
        else:
            self.finger_environment_clearance = None
            self.nonhand_environment_clearance = None
        self.support = PiperQuasiStaticSupportChecker(runtime)
        self.target_world = target_world.copy()
        self.required_self_clearance = required_self_clearance
        self.required_environment_clearance = required_environment_clearance
        self.required_support_margin = required_support_margin
        self.support_violation_grace_seconds = support_violation_grace_seconds
        self.box_floor_contact_samples = 0
        self.stage = "navigation"
        self.reference = runtime.data.qpos[runtime.joint_qpos_adr[12:]].copy()
        self.track_reference = True
        self.dynamic_samples = 0
        self.minimum_self_clearance = float("inf")
        self.minimum_environment_clearance = float("inf")
        self.minimum_finger_environment_clearance = float("inf")
        self.minimum_nonhand_environment_clearance = float("inf")
        self.current_self_clearance = None
        self.current_environment_clearance = None
        self.current_finger_environment_clearance = None
        self.current_nonhand_environment_clearance = None
        self.current_designated_face_ready = None
        self.minimum_support_margin = float("inf")
        self.minimum_supporting_feet = 4
        self.support_violation_steps = 0
        self.maximum_support_violation_steps = 0
        self.maximum_reference_tracking_error = 0.0
        self.maximum_hand_position_error = 0.0
        self.first_box_contact = None
        self.failure_snapshot = None
        self.require_motion_sweep_certificate = require_motion_sweep_certificate
        self.sweep_previous_qpos = None
        self.sweep_previous_clearances = None
        self.sweep_intervals = 0
        self.minimum_swept_self_clearance = float("inf")
        self.minimum_swept_environment_clearance = float("inf")
        self.minimum_swept_finger_environment_clearance = float("inf")
        self.minimum_swept_nonhand_environment_clearance = float("inf")
        self.maximum_integration_residual = 0.0
        moving_bodies = frozenset({STATIC_BOX_BODY}) if self.box_is_movable else frozenset()
        sweep_clearance_checkers = [self.self_clearance, self.environment_clearance]
        if diagnose_designated_hand_approach:
            sweep_clearance_checkers.extend((
                self.finger_environment_clearance,
                self.nonhand_environment_clearance,
            ))
        self.sweep_checkers = (
            tuple(
                PiperConfigurationSweep(checker, moving_body_names=moving_bodies)
                for checker in sweep_clearance_checkers
            )
            if require_motion_sweep_certificate else None
        )

    def capture_box_snapshot(self, stage: str):
        if self.box_reader is None:
            return None
        self.box_state = self.box_reader.read()
        self.box_guard = BoxSnapshotGuard(
            self.box_state, geometry_radius=self.box_reader.radius, **self.box_validity_limits
        )
        self.box_guard_result = self.box_guard.evaluate(self.box_state)
        self.box_snapshots.append({"stage": stage, "state": self.box_state.as_dict()})
        if not self.box_guard_result["valid"]:
            self._stop_for_box_state("box_snapshot_unstable")
        return self.box_state

    def _stop_for_box_state(self, reason: str) -> None:
        self.box_stop_event = {
            "reason": reason, "replan_required": True,
            "reference": self.box_guard.reference.as_dict(),
            "current": self.box_state.as_dict(), "validity": self.box_guard_result,
        }
        raise RolloutFailure(reason)

    def begin_arm_motion(self) -> None:
        self.stage = "arm_motion"
        if self.require_motion_sweep_certificate:
            if self.runtime.model.opt.integrator != mujoco.mjtIntegrator.mjINT_EULER:
                raise RolloutFailure("motion_sweep_unsupported_integrator")
            self._refresh_clearance_geometry()
            self.sweep_previous_qpos = self.runtime.data.qpos.copy()
            self.sweep_previous_clearances = (
                self.self_clearance.evaluate_current_configuration(required_clearance=0.0).minimum_clearance,
                self.environment_clearance.evaluate_current_configuration(required_clearance=0.0).minimum_clearance,
            )
            if self.diagnose_designated_hand_approach:
                self.sweep_previous_clearances += (
                    self.finger_environment_clearance.evaluate_current_configuration(
                        required_clearance=0.0
                    ).minimum_clearance,
                    self.nonhand_environment_clearance.evaluate_current_configuration(
                        required_clearance=0.0
                    ).minimum_clearance,
                )

    def _refresh_clearance_geometry(self) -> None:
        self.clearance_data.qpos[:] = self.runtime.data.qpos
        self.clearance_data.mocap_pos[:] = self.runtime.data.mocap_pos
        self.clearance_data.mocap_quat[:] = self.runtime.data.mocap_quat
        mujoco.mj_kinematics(self.runtime.model, self.clearance_data)

    def _check_swept_clearance(
        self,
        self_result,
        environment_result,
        support_result,
        finger_environment_result=None,
        nonhand_environment_result=None,
    ) -> None:
        current = self.runtime.data.qpos
        predicted = self.sweep_previous_qpos.copy()
        mujoco.mj_integratePos(
            self.runtime.model, predicted, self.runtime.data.qvel, self.runtime.sim_dt
        )
        residual = float(np.max(np.abs(predicted - current)))
        self.maximum_integration_residual = max(self.maximum_integration_residual, residual)
        free_joints = np.flatnonzero(self.runtime.model.jnt_type == mujoco.mjtJoint.mjJNT_FREE)
        angular_step = max(
            float(np.linalg.norm(self.runtime.data.qvel[
                int(self.runtime.model.jnt_dofadr[joint]) + 3 : int(self.runtime.model.jnt_dofadr[joint]) + 6
            ])) * self.runtime.sim_dt
            for joint in free_joints
        )
        if residual > 1.0e-12 or angular_step >= math.pi:
            raise RolloutFailure("motion_sweep_integration_mismatch")
        clearances = (self_result.minimum_clearance, environment_result.minimum_clearance)
        if self.diagnose_designated_hand_approach:
            clearances += (
                finger_environment_result.minimum_clearance,
                nonhand_environment_result.minimum_clearance,
            )
        lower_bounds = [
            min(previous, clearance) - checker.nearest_endpoint_motion_bound(self.sweep_previous_qpos, current)
            for previous, clearance, checker in zip(
                self.sweep_previous_clearances, clearances, self.sweep_checkers
            )
        ]
        self.minimum_swept_self_clearance = min(self.minimum_swept_self_clearance, lower_bounds[0])
        self.minimum_swept_environment_clearance = min(self.minimum_swept_environment_clearance, lower_bounds[1])
        if self.diagnose_designated_hand_approach:
            self.minimum_swept_finger_environment_clearance = min(
                self.minimum_swept_finger_environment_clearance, lower_bounds[2]
            )
            self.minimum_swept_nonhand_environment_clearance = min(
                self.minimum_swept_nonhand_environment_clearance, lower_bounds[3]
            )
        self.sweep_intervals += 1
        self.sweep_previous_qpos = current.copy()
        self.sweep_previous_clearances = clearances
        checks = [
            (lower_bounds[0], self.required_self_clearance, "dynamic_swept_self_clearance"),
        ]
        if self.diagnose_designated_hand_approach:
            checks.extend((
                (lower_bounds[2], 0.0, "dynamic_swept_finger_contact"),
                (
                    lower_bounds[3],
                    self.required_environment_clearance,
                    "dynamic_swept_nonhand_environment_clearance",
                ),
            ))
        else:
            checks.append((
                lower_bounds[1],
                self.required_environment_clearance,
                "dynamic_swept_environment_clearance",
            ))
        for lower, threshold, reason in checks:
            if lower < threshold:
                self._record_failure(reason, self_result, environment_result, support_result)
                raise RolloutFailure(reason)

    def __call__(self) -> None:
        if self.stage == "arm_motion":
            self.dynamic_samples += 1
        self.physics.stage = self.stage
        self.physics()
        if self.box_reader is not None:
            self.box_state = self.box_reader.read()
        self._check_box_contact()
        if self.box_guard is not None:
            self.box_guard_result = self.box_guard.evaluate(self.box_state)
            self.maximum_box_displacement = max(
                self.maximum_box_displacement, self.box_guard_result["geometry_displacement_bound"]
            )
            self.maximum_box_linear_speed = max(self.maximum_box_linear_speed, self.box_guard_result["linear_speed"])
            self.maximum_box_angular_speed = max(self.maximum_box_angular_speed, self.box_guard_result["angular_speed"])
            if not self.box_guard_result["valid"]:
                self._stop_for_box_state("box_snapshot_invalidated")
        if self.stage != "arm_motion":
            return
        self._refresh_clearance_geometry()
        self_result = self.self_clearance.evaluate_current_configuration(
            required_clearance=self.required_self_clearance
        )
        environment_result = self.environment_clearance.evaluate_current_configuration(
            required_clearance=self.required_environment_clearance
        )
        finger_environment_result = None
        nonhand_environment_result = None
        designated_face_ready = None
        if self.diagnose_designated_hand_approach:
            finger_environment_result = self.finger_environment_clearance.evaluate_current_configuration(
                required_clearance=0.0
            )
            nonhand_environment_result = self.nonhand_environment_clearance.evaluate_current_configuration(
                required_clearance=self.required_environment_clearance
            )
            contact_geometry = self.contact_geometry_reader.read()
            if not np.isclose(
                contact_geometry["minimum_finger_clearance"],
                finger_environment_result.minimum_clearance,
                rtol=0.0,
                atol=1.0e-10,
            ):
                raise RolloutFailure("contact_geometry_cache_mismatch")
            designated_face_ready = bool(contact_geometry["fingers"]) and all(
                finger["separated_witnesses_valid"]
                and finger["box_point_in_front_region"]
                for finger in contact_geometry["fingers"]
            )
        self.current_self_clearance = self_result
        self.current_environment_clearance = environment_result
        self.current_finger_environment_clearance = finger_environment_result
        self.current_nonhand_environment_clearance = nonhand_environment_result
        self.current_designated_face_ready = designated_face_ready
        support_result = self.support.evaluate(
            required_margin=self.required_support_margin
        )
        self.minimum_self_clearance = min(
            self.minimum_self_clearance, self_result.minimum_clearance
        )
        self.minimum_environment_clearance = min(
            self.minimum_environment_clearance, environment_result.minimum_clearance
        )
        if self.diagnose_designated_hand_approach:
            self.minimum_finger_environment_clearance = min(
                self.minimum_finger_environment_clearance,
                finger_environment_result.minimum_clearance,
            )
            self.minimum_nonhand_environment_clearance = min(
                self.minimum_nonhand_environment_clearance,
                nonhand_environment_result.minimum_clearance,
            )
        self.minimum_supporting_feet = min(
            self.minimum_supporting_feet, len(support_result.supporting_feet)
        )
        if support_result.support_margin is not None:
            self.minimum_support_margin = min(
                self.minimum_support_margin, support_result.support_margin
            )
        self.support_violation_steps = (
            0 if support_result.safe else self.support_violation_steps + 1
        )
        self.maximum_support_violation_steps = max(
            self.maximum_support_violation_steps, self.support_violation_steps
        )
        arm = self.runtime.data.qpos[self.runtime.joint_qpos_adr[12:]]
        if self.track_reference:
            self.maximum_reference_tracking_error = max(
                self.maximum_reference_tracking_error,
                float(np.max(np.abs(arm - self.reference))),
            )
        self.maximum_hand_position_error = max(
            self.maximum_hand_position_error,
            float(np.linalg.norm(_hand_position(self.runtime, self.hand_point) - self.target_world)),
        )
        if not self_result.safe:
            self._record_failure("dynamic_self_clearance", self_result, environment_result, support_result)
            raise RolloutFailure("dynamic_self_clearance")
        designated_environment_safe = bool(
            self.diagnose_designated_hand_approach
            and _designated_hand_environment_safe(
                unified_environment_safe=environment_result.safe,
                finger_clearance=finger_environment_result.minimum_clearance,
                nonhand_environment_safe=nonhand_environment_result.safe,
                designated_face_ready=designated_face_ready,
            )
        )
        if not environment_result.safe and not designated_environment_safe:
            self._record_failure("dynamic_environment_clearance", self_result, environment_result, support_result)
            raise RolloutFailure("dynamic_environment_clearance")
        if self.require_motion_sweep_certificate:
            self._check_swept_clearance(
                self_result,
                environment_result,
                support_result,
                finger_environment_result,
                nonhand_environment_result,
            )
        if (
            not support_result.safe
            and self.support_violation_steps * self.runtime.sim_dt
            >= self.support_violation_grace_seconds
        ):
            self._record_failure("dynamic_quasistatic_support", self_result, environment_result, support_result)
            raise RolloutFailure("dynamic_quasistatic_support")

    def _record_failure(
        self, reason: str, self_result, environment_result, support_result
    ) -> None:
        base_rotation = self.runtime.data.xmat[self.runtime.base_id].reshape(3, 3)
        self.failure_snapshot = {
            "reason": reason,
            "time": float(self.runtime.data.time),
            "base_position": self.runtime.data.qpos[
                self.runtime.env.robot_qpos_adr : self.runtime.env.robot_qpos_adr + 3
            ].tolist(),
            "base_yaw": float(np.arctan2(base_rotation[1, 0], base_rotation[0, 0])),
            "arm_joint_position": self.runtime.data.qpos[
                self.runtime.joint_qpos_adr[12:]
            ].tolist(),
            "hand_position": _hand_position(self.runtime, self.hand_point).tolist(),
            "minimum_self_clearance": self_result.minimum_clearance,
            "self_clearance_bodies": [self_result.arm_body, self_result.protected_body],
            "minimum_environment_clearance": environment_result.minimum_clearance,
            "environment_clearance_bodies": [
                environment_result.arm_body,
                environment_result.protected_body,
            ],
            "finger_environment_clearance": (
                self.current_finger_environment_clearance.minimum_clearance
                if self.current_finger_environment_clearance is not None else None
            ),
            "nonhand_environment_clearance": (
                self.current_nonhand_environment_clearance.minimum_clearance
                if self.current_nonhand_environment_clearance is not None else None
            ),
            "designated_face_ready": self.current_designated_face_ready,
            "supporting_feet": list(support_result.supporting_feet),
            "support_margin": support_result.support_margin,
        }

    def _check_box_contact(self) -> None:
        for contact_index, contact in enumerate(self.runtime.data.contact):
            if self.box_geometry not in (contact.geom1, contact.geom2) or contact.dist > 0.0:
                continue
            other = contact.geom2 if contact.geom1 == self.box_geometry else contact.geom1
            if self.box_is_movable and other == self.physics.floor_geom:
                self.box_floor_contact_samples += 1
                continue
            force = np.zeros(6)
            mujoco.mj_contactForce(
                self.runtime.model, self.runtime.data, contact_index, force
            )
            self.first_box_contact = {
                "time": float(self.runtime.data.time),
                "body": self.runtime.model.body(
                    int(self.runtime.model.geom_bodyid[other])
                ).name,
                "normal_force": float(force[0]),
                "depth": float(-contact.dist),
            }
            if self.box_is_movable:
                contact_local = self.runtime.data.geom_xmat[self.box_geometry].reshape(3, 3).T @ (
                    contact.pos - self.runtime.data.geom_xpos[self.box_geometry]
                )
                self.first_box_contact.update(
                    position_world=contact.pos.tolist(),
                    position_box_frame=contact_local.tolist(),
                    contact_pose_source="MuJoCo contact-generation geometry cache",
                    designated_front_hand_contact=self.box_contact_region.contains_local(
                        contact_local,
                        self.runtime.model.body(int(self.runtime.model.geom_bodyid[other])).name,
                    ),
                    contact_enabled=False,
                    contact_measurement=read_box_contact_sample(
                        self.runtime, contact, force,
                        box_geometry=self.box_geometry, region=self.box_contact_region,
                    ),
                )
            raise RolloutFailure("precontact_box_contact" if self.box_is_movable else "static_box_contact")

    @staticmethod
    def finite_minimum(value: float) -> float | None:
        return value if np.isfinite(value) else None


def _capture_held_step_state_v2(runtime, monitor, episode_state: dict[str, object]) -> dict[str, object]:
    state_type = mujoco.mjtState.mjSTATE_INTEGRATION
    integration_state = np.empty(
        mujoco.mj_stateSize(runtime.model, state_type), dtype=np.float64
    )
    mujoco.mj_getState(runtime.model, runtime.data, integration_state, state_type)
    return {
        "schema_version": 2,
        "mujoco_integration_state_spec": int(state_type),
        "mujoco_integration_state": integration_state.tolist(),
        "policy_observation_history": [frame.tolist() for frame in runtime.history],
        "last_action": runtime.last_action.tolist(),
        "velocity_command": runtime.velocity_command.tolist(),
        "ee_command": runtime.ee_command.tolist(),
        **episode_state,
        "support_violation_steps": monitor.support_violation_steps,
        "sweep_previous_qpos": (
            monitor.sweep_previous_qpos.tolist()
            if monitor.sweep_previous_qpos is not None else None
        ),
        "sweep_previous_clearances": (
            list(monitor.sweep_previous_clearances)
            if monitor.sweep_previous_clearances is not None else None
        ),
        "current_environment_clearance": (
            monitor.current_environment_clearance.minimum_clearance
            if monitor.current_environment_clearance is not None else None
        ),
        "current_nonhand_environment_clearance": (
            monitor.current_nonhand_environment_clearance.minimum_clearance
            if monitor.current_nonhand_environment_clearance is not None else None
        ),
        "current_designated_face_ready": monitor.current_designated_face_ready,
        "box_guard_reference": (
            monitor.box_guard.reference.as_dict()
            if monitor.box_guard is not None else None
        ),
        "physics_monitor_last_time": monitor.physics.last_time,
    }


def _restore_held_step_state_v2(
    runtime, monitor, state: dict[str, object], *, fresh_data: bool = False
) -> None:
    if (state["schema_version"] != 2
            or state["mujoco_integration_state_spec"] != int(mujoco.mjtState.mjSTATE_INTEGRATION)):
        raise ValueError("Unsupported held-step state snapshot")
    state_type = mujoco.mjtState.mjSTATE_INTEGRATION
    integration_state = np.asarray(state["mujoco_integration_state"], dtype=np.float64)
    if integration_state.shape != (mujoco.mj_stateSize(runtime.model, state_type),):
        raise ValueError("Held-step MuJoCo state size does not match model")
    data = mujoco.MjData(runtime.model) if fresh_data else runtime.data
    mujoco.mj_setState(runtime.model, data, integration_state, state_type)
    if fresh_data:
        mujoco.mj_forward(runtime.model, data)
        runtime.data = data
        runtime.env.data = data
        monitor.support.data = data
    frames = [np.asarray(frame, dtype=np.float32) for frame in state["policy_observation_history"]]
    if len(frames) != runtime.history.maxlen or any(frame.shape != (70,) for frame in frames):
        raise ValueError("Held-step policy history does not match runtime")
    runtime.history.clear()
    runtime.history.extend(frames)
    runtime.last_action[:] = state["last_action"]
    runtime.velocity_command[:] = state["velocity_command"]
    runtime.ee_command[:] = state["ee_command"]
    monitor.target_world = np.asarray(state["target_world"], dtype=np.float64)
    monitor.support_violation_steps = state["support_violation_steps"]
    monitor.sweep_previous_qpos = (
        np.asarray(state["sweep_previous_qpos"], dtype=np.float64)
        if state["sweep_previous_qpos"] is not None else None
    )
    monitor.sweep_previous_clearances = (
        tuple(state["sweep_previous_clearances"])
        if state["sweep_previous_clearances"] is not None else None
    )
    monitor.physics.last_time = state["physics_monitor_last_time"]


def run_episode(
    args: argparse.Namespace, *, cold_context: dict[str, object] | None = None,
    cold_hold_entry_not_before_control_step: int | None = None,
) -> dict[str, object]:
    if cold_hold_entry_not_before_control_step is not None and cold_context is None:
        raise ValueError("Diagnostic hold-entry delay requires a cold continuation")
    box_position = np.asarray(args.static_box_position, dtype=np.float64)
    box_size = np.asarray(args.static_box_size, dtype=np.float64)
    target_local = np.asarray(args.hand_target_local, dtype=np.float64)
    target_step_local = np.asarray(
        getattr(args, "hold_target_step_local", (0.0, 0.0, 0.0)), dtype=np.float64
    )
    target_step_after_seconds = float(getattr(args, "hold_target_step_after_seconds", 1.0))
    if (target_step_local.shape != (3,) or not np.isfinite(target_step_local).all()
            or not np.isfinite(target_step_after_seconds)
            or target_step_after_seconds <= 0.0):
        raise ValueError("Hold target step must have finite coordinates and positive timing")
    target_step_enabled = bool(np.any(target_step_local))
    target_step_probe = bool(getattr(args, "hold_target_step_probe", False))
    restore_report_path = getattr(args, "hold_state_restore_json", None)
    restore_mode = getattr(args, "hold_state_restore_mode", "inplace")
    if restore_mode not in ("inplace", "fresh-data"):
        raise ValueError("Unsupported held-step restore mode")
    restore_state = None
    if restore_report_path is not None:
        restore_report = json.loads(Path(restore_report_path).read_text())
        restore_event = restore_report["result"]["motion"]["target_step_event"]
        restore_state = restore_event["closed_loop_state_v2"]
        if not target_step_enabled or restore_event["applied"] is not False:
            raise ValueError("Held-step restore requires a candidate and baseline probe")
    if (target_step_enabled or target_step_probe) and (
        args.arm_controller != "unified-wbc"
        or not args.wbc_hold_on_gate
        or target_step_after_seconds >= args.hold_seconds
    ):
        raise ValueError("Hold target step requires WBC hold and timing before completion")
    ik_initial = np.asarray(args.ik_initial, dtype=np.float64)
    hand_body_name, hand_offset = hand_point_parameters(args.hand_point)
    cosine, sine = math.cos(args.static_box_yaw), math.sin(args.static_box_yaw)
    box_rotation = np.array(
        [[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    target_world = box_position + box_rotation @ target_local
    make_runtime = (
        make_movable_box_navigation_runtime if args.box_mode == "movable"
        else make_static_box_navigation_runtime
    )
    runtime = make_runtime(
        seed=args.seed,
        box_position=box_position,
        box_size=box_size,
        box_yaw=args.static_box_yaw,
        config_path=DEPLOY / (
            "config_wbc.yaml" if args.locomotion_policy == "wbc" else "config.yaml"
        ),
        physics_substeps=args.physics_substeps,
        **({"box_mass": args.box_mass} if args.box_mode == "movable" else {}),
    )
    oracle = PiperPositionReachabilityOracle(runtime)
    static_self = PiperSelfClearanceChecker(runtime)
    static_environment = PiperArmClearanceChecker(
        runtime, protected_body_names=frozenset({STATIC_BOX_BODY})
    )
    static_contact_geometry = (
        PiperContactGeometryReader(runtime)
        if args.diagnose_designated_hand_approach else None
    )
    if static_contact_geometry is not None:
        finger_bodies = static_contact_geometry.region.hand_bodies
        static_finger_environment = PiperArmClearanceChecker(
            runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=finger_bodies,
        )
        static_nonhand_environment = PiperArmClearanceChecker(
            runtime,
            protected_body_names=frozenset({STATIC_BOX_BODY}),
            arm_body_names=ARM_BODY_NAMES - finger_bodies,
        )
    else:
        static_finger_environment = None
        static_nonhand_environment = None
    static_support = PiperQuasiStaticSupportChecker(runtime)
    monitor = ArmMotionMonitor(
        runtime,
        target_world=target_world,
        required_self_clearance=args.required_self_clearance,
        required_environment_clearance=args.required_environment_clearance,
        required_support_margin=args.required_support_margin,
        support_violation_grace_seconds=args.support_violation_grace_seconds,
        require_motion_sweep_certificate=args.require_motion_sweep_certificate,
        maximum_box_displacement=args.box_max_displacement,
        maximum_box_linear_speed=args.box_max_linear_speed,
        maximum_box_angular_speed=args.box_max_angular_speed,
        hand_point=args.hand_point,
        diagnose_designated_hand_approach=args.diagnose_designated_hand_approach,
    )
    runtime.on_physics_step = monitor
    reason = "completed"
    candidate = None
    target_orientation_world = None
    actual_base_pose = np.zeros(3, dtype=np.float64)
    planned_base_pose = np.zeros(3, dtype=np.float64)
    nav_trace = []
    starting_arm = runtime.data.qpos[runtime.joint_qpos_adr[12:]].copy()
    precontact_state = None
    static_path = None
    endpoint_designated_hand_approach = None
    trace = []
    cold_control_history = []
    stable_steps = 0
    motion_steps = 0
    maximum_gravity_compensation = 0.0
    maximum_target_clipping = 0.0
    maximum_hand_feedback_correction = 0.0
    maximum_orientation_feedback_correction = 0.0
    arm_motion_start_base_position = None
    arm_motion_start_base_pose = None
    maximum_base_hold_linear_command = 0.0
    maximum_base_hold_yaw_command = 0.0
    end_effector_target_position = None
    end_effector_target_quaternion = None
    initial_wbc_command = None
    final_wbc_command = None
    maximum_end_effector_orientation_error = 0.0
    maximum_arm_speed = 0.0
    held_wbc_pose = None
    wbc_hold_entries = 0
    wbc_hold_events = []
    wbc_command_hold_steps = 0
    hold_entry_wait_steps = 0
    target_step_event = None
    target_step_first_settled_time = None
    try:
        if cold_context is None:
            for _ in range(round(args.initial_settle_seconds / runtime.control_dt)):
                runtime.hold_default()
            navigation_box = monitor.capture_box_snapshot("navigation_target")
            if navigation_box is not None:
                box_position = navigation_box.position.copy()
                box_rotation = navigation_box.rotation
                target_world = navigation_box.point_world(target_local)
                monitor.target_world = target_world.copy()
                box_yaw = float(np.arctan2(box_rotation[1, 0], box_rotation[0, 0]))
                cosine, sine = math.cos(box_yaw), math.sin(box_yaw)
            else:
                box_yaw = args.static_box_yaw
            planned_base_pose = np.array(
                [
                    box_position[0]
                    - (box_size[0] / 2.0 + args.nav_front_standoff) * cosine
                    - args.nav_lateral_offset * sine,
                    box_position[1]
                    - (box_size[0] / 2.0 + args.nav_front_standoff) * sine
                    + args.nav_lateral_offset * cosine,
                    box_yaw,
                ],
                dtype=np.float64,
            )
            skill = NavigateSkill(NavigateConfig(yaw_gain=args.nav_yaw_gain))
            action = SkillAction(SkillType.NAV, planned_base_pose)
            if not skill.can_execute(observation(runtime, planned_base_pose), action):
                raise RolloutFailure("navigation_rejected")
            skill.reset(action)
            nav_trace_stride = max(1, round(0.1 / runtime.control_dt))
            for nav_step in range(skill.config.timeout_steps):
                command = skill.step(observation(runtime, planned_base_pose))
                runtime.step(command.velocity, command.end_effector_pose)
                current_base_pose = _base_pose(runtime, planned_base_pose)
                if nav_step % nav_trace_stride == 0 or skill.status != SkillStatus.RUNNING:
                    nav_trace.append({
                        "step": nav_step + 1,
                        "time": float(runtime.data.time),
                        "base_pose": current_base_pose.tolist(),
                        "position_error": float(
                            np.linalg.norm(planned_base_pose[:2] - current_base_pose[:2])
                        ),
                        "yaw_error": float(
                            wrap_angle(planned_base_pose[2] - current_base_pose[2])
                        ),
                        "velocity_command": command.velocity.tolist(),
                        "status": skill.status.value,
                    })
                if skill.status != SkillStatus.RUNNING:
                    break
            if skill.status != SkillStatus.SUCCEEDED:
                raise RolloutFailure(skill.failure_reason or "navigation_timeout")
            monitor.stage = "post_navigation_settle"
            for _ in range(round(args.post_nav_settle_seconds / runtime.control_dt)):
                runtime.step(np.zeros(3))
            arm_box = monitor.capture_box_snapshot("arm_target")
            if arm_box is not None:
                box_position = arm_box.position.copy()
                box_rotation = arm_box.rotation
                target_world = arm_box.point_world(target_local)
                monitor.target_world = target_world.copy()
                box_yaw = float(np.arctan2(box_rotation[1, 0], box_rotation[0, 0]))
                cosine, sine = math.cos(box_yaw), math.sin(box_yaw)
            actual_base_pose = _base_pose(runtime, planned_base_pose)
            starting_arm = runtime.data.qpos[runtime.joint_qpos_adr[12:]].copy()
            precontact_state = {
                "qpos": runtime.data.qpos.tolist(),
                "qvel": runtime.data.qvel.tolist(),
                "ctrl": runtime.data.ctrl.tolist(),
                "time": float(runtime.data.time),
            }
            query = ReachabilityQuery(actual_base_pose, target_world)
            if args.native_push_pose:
                box_quaternion = np.empty(4)
                mujoco.mju_mat2Quat(box_quaternion, box_rotation.ravel())
                target_orientation_world = native_push_orientation(box_quaternion)
            candidate = oracle.solve(
                query,
                hand_offset=hand_offset if args.hand_point == "legacy-proxy" else None,
                initial_joint_positions=ik_initial,
                target_quaternion=target_orientation_world,
            )
            if not candidate.kinematic_feasible:
                raise RolloutFailure(candidate.failure_reason or "candidate_ik")
            endpoint_self = static_self.evaluate(
                actual_base_pose,
                candidate.joint_solution,
                required_clearance=args.required_self_clearance,
            )
            endpoint_environment = static_environment.evaluate(
                actual_base_pose,
                candidate.joint_solution,
                required_clearance=args.required_environment_clearance,
            )
            if args.diagnose_designated_hand_approach:
                endpoint_finger_environment = static_finger_environment.evaluate(
                    actual_base_pose,
                    candidate.joint_solution,
                    required_clearance=0.0,
                )
                endpoint_nonhand_environment = static_nonhand_environment.evaluate(
                    actual_base_pose,
                    candidate.joint_solution,
                    required_clearance=args.required_environment_clearance,
                )
                endpoint_contact_geometry = _contact_geometry_at_configuration(
                    oracle, query, candidate.joint_solution, static_contact_geometry
                )
                endpoint_designated_face_ready = bool(endpoint_contact_geometry["fingers"]) and all(
                    finger["separated_witnesses_valid"]
                    and finger["box_point_in_front_region"]
                    for finger in endpoint_contact_geometry["fingers"]
                )
                endpoint_contact_free = not endpoint_contact_geometry["contact_samples"]
                endpoint_designated_hand_approach = {
                    "scope": "Static designated-finger endpoint diagnosis; no contact execution permission",
                    "contact_execution_enabled": False,
                    "finger_clearance": endpoint_finger_environment.minimum_clearance,
                    "nonhand_environment_clearance": endpoint_nonhand_environment.minimum_clearance,
                    "designated_face_ready": endpoint_designated_face_ready,
                    "contact_free": endpoint_contact_free,
                    "fingers": endpoint_contact_geometry["fingers"],
                    "passed": bool(
                        endpoint_finger_environment.minimum_clearance >= 0.0
                        and endpoint_nonhand_environment.safe
                        and endpoint_designated_face_ready
                        and endpoint_contact_free
                    ),
                }
            endpoint_support = static_support.evaluate_configuration(
                actual_base_pose,
                candidate.joint_solution,
                required_margin=args.required_support_margin,
            )
            hand_world = oracle.hand_position(
                query, candidate.joint_solution, body_name=hand_body_name, offset=hand_offset
            )
            hand_local = box_rotation.T @ (hand_world - box_position)
            endpoint_hand_gate = bool(
                bool(
                    CONTROL["side_approach_ready"](
                        batch(hand_local), box_size[0] / 2.0, args.push_approach_distance
                    )[0]
                )
                and abs(hand_local[2]) < 0.06
            )
            endpoint_passed = bool(
                candidate.joint_limit_margin >= args.required_joint_limit_margin
                and endpoint_self.safe
                and (
                    endpoint_designated_hand_approach["passed"]
                    if args.diagnose_designated_hand_approach
                    else endpoint_environment.safe
                )
                and endpoint_support.safe
                and endpoint_hand_gate
            )
            path_self = []
            path_self_bodies = []
            path_environment = []
            path_environment_bodies = []
            path_finger_environment = []
            path_nonhand_environment = []
            path_designated_face_ready = []
            path_support = []
            for fraction in np.linspace(0.0, 1.0, args.path_samples):
                arm = starting_arm + fraction * (candidate.joint_solution - starting_arm)
                self_clearance = static_self.evaluate(
                    actual_base_pose,
                    arm,
                    required_clearance=args.required_self_clearance,
                )
                environment_clearance = static_environment.evaluate(
                    actual_base_pose,
                    arm,
                    required_clearance=args.required_environment_clearance,
                )
                path_self.append(self_clearance.minimum_clearance)
                path_self_bodies.append(
                    [self_clearance.arm_body, self_clearance.protected_body]
                )
                path_environment.append(environment_clearance.minimum_clearance)
                path_environment_bodies.append(
                    [
                        environment_clearance.arm_body,
                        environment_clearance.protected_body,
                    ]
                )
                if args.diagnose_designated_hand_approach:
                    finger_environment = static_finger_environment.evaluate(
                        actual_base_pose, arm, required_clearance=0.0
                    )
                    nonhand_environment = static_nonhand_environment.evaluate(
                        actual_base_pose,
                        arm,
                        required_clearance=args.required_environment_clearance,
                    )
                    path_finger_environment.append(finger_environment.minimum_clearance)
                    path_nonhand_environment.append(nonhand_environment.minimum_clearance)
                    if finger_environment.minimum_clearance < args.required_environment_clearance:
                        contact_geometry = _contact_geometry_at_configuration(
                            oracle, query, arm, static_contact_geometry
                        )
                        path_designated_face_ready.append(bool(contact_geometry["fingers"]) and all(
                            finger["separated_witnesses_valid"]
                            and finger["box_point_in_front_region"]
                            for finger in contact_geometry["fingers"]
                        ) and not contact_geometry["contact_samples"])
                    else:
                        path_designated_face_ready.append(True)
                path_support.append(
                    static_support.evaluate_configuration(
                        actual_base_pose,
                        arm,
                        required_margin=args.required_support_margin,
                    ).support_margin
                )
            minimum_self_index = int(np.argmin(path_self))
            minimum_environment_index = int(np.argmin(path_environment))
            self_motion_bound = static_self.linear_path_sampling_motion_bound(
                starting_arm, candidate.joint_solution, samples=args.path_samples
            )
            environment_motion_bound = static_environment.linear_path_sampling_motion_bound(
                starting_arm, candidate.joint_solution, samples=args.path_samples
            )
            continuous_self_lower_bound = min(path_self) - self_motion_bound
            continuous_environment_lower_bound = min(path_environment) - environment_motion_bound
            if args.diagnose_designated_hand_approach:
                finger_motion_bound = static_finger_environment.linear_path_sampling_motion_bound(
                    starting_arm, candidate.joint_solution, samples=args.path_samples
                )
                nonhand_motion_bound = static_nonhand_environment.linear_path_sampling_motion_bound(
                    starting_arm, candidate.joint_solution, samples=args.path_samples
                )
                continuous_finger_lower_bound = min(path_finger_environment) - finger_motion_bound
                continuous_nonhand_lower_bound = min(path_nonhand_environment) - nonhand_motion_bound
                continuous_clearance_passed = bool(
                    continuous_self_lower_bound >= args.required_self_clearance
                    and continuous_finger_lower_bound >= 0.0
                    and continuous_nonhand_lower_bound >= args.required_environment_clearance
                )
                designated_static_path = {
                    "scope": (
                        "Fixed-state joint-linear finger/nonhand clearance diagnosis; sampled face labels "
                        "are diagnostic because this is not the WBC trajectory"
                    ),
                    "contact_execution_enabled": False,
                    "minimum_finger_clearance": min(path_finger_environment),
                    "minimum_nonhand_environment_clearance": min(path_nonhand_environment),
                    "finger_sample_motion_bound": finger_motion_bound,
                    "nonhand_sample_motion_bound": nonhand_motion_bound,
                    "continuous_finger_clearance_lower_bound": continuous_finger_lower_bound,
                    "continuous_nonhand_environment_clearance_lower_bound": continuous_nonhand_lower_bound,
                    "sampled_designated_face_ready": all(path_designated_face_ready),
                    "sampled_designated_face_required": False,
                    "passed": bool(
                        min(path_finger_environment) >= 0.0
                        and min(path_nonhand_environment) >= args.required_environment_clearance
                    ),
                }
            else:
                continuous_clearance_passed = bool(
                    continuous_self_lower_bound >= args.required_self_clearance
                    and continuous_environment_lower_bound >= args.required_environment_clearance
                )
                designated_static_path = None
            static_path = {
                "samples": args.path_samples,
                "minimum_self_clearance": min(path_self),
                "minimum_self_clearance_fraction": minimum_self_index
                / (args.path_samples - 1),
                "minimum_self_clearance_bodies": path_self_bodies[minimum_self_index],
                "minimum_environment_clearance": min(path_environment),
                "minimum_environment_clearance_fraction": minimum_environment_index
                / (args.path_samples - 1),
                "minimum_environment_clearance_bodies": path_environment_bodies[
                    minimum_environment_index
                ],
                "minimum_support_margin": min(path_support),
                "designated_hand_approach": designated_static_path,
                "continuous_clearance": {
                    "scope": "Linear arm joint path only; fixed base, legs and scene; not WBC motion",
                    "selected_constraint_set": (
                        "finger_noncontact_and_nonhand_environment_clearance"
                        if args.diagnose_designated_hand_approach else
                        "unified_arm_environment_clearance"
                    ),
                    "self_sample_motion_bound": self_motion_bound,
                    "environment_sample_motion_bound": environment_motion_bound,
                    "self_clearance_lower_bound": continuous_self_lower_bound,
                    "environment_clearance_lower_bound": continuous_environment_lower_bound,
                    "unified_environment_clearance_enforced": not args.diagnose_designated_hand_approach,
                    "passed": continuous_clearance_passed,
                    "required": args.require_static_path_certificate,
                },
                "passed": bool(
                    min(path_self) >= args.required_self_clearance
                    and (
                        designated_static_path["passed"]
                        if args.diagnose_designated_hand_approach
                        else min(path_environment) >= args.required_environment_clearance
                    )
                    and min(path_support) >= args.required_support_margin
                ),
            }
            if not endpoint_passed:
                raise RolloutFailure("candidate_endpoint_precondition")
            if not static_path["passed"]:
                raise RolloutFailure("candidate_path_precondition")
            if args.require_static_path_certificate and not continuous_clearance_passed:
                raise RolloutFailure("candidate_path_continuous_clearance")

            (
                end_effector_target_position,
                end_effector_target_quaternion,
            ) = _candidate_end_effector_world_pose(runtime, candidate.joint_solution)
            if target_orientation_world is not None:
                end_effector_target_quaternion = target_orientation_world.copy()
            end_effector = runtime.model.body("end_effector").id
            end_effector_start_position = runtime.data.xpos[end_effector].copy()
            end_effector_start_quaternion = runtime.data.xquat[end_effector].copy()
            hand_start_position = _hand_position(runtime, args.hand_point)
            hand_feedback_integral = np.zeros(3, dtype=np.float64)
            orientation_feedback_integral = np.zeros(3, dtype=np.float64)
            reference = starting_arm.copy()
            gravity_data = mujoco.MjData(runtime.model)
            monitor.begin_arm_motion()
            monitor.track_reference = args.arm_controller == "joint-pd"
            arm_motion_start_base_position = runtime.data.qpos[
                runtime.env.robot_qpos_adr : runtime.env.robot_qpos_adr + 3
            ].copy()
            arm_motion_start_base_pose = _base_pose(runtime, planned_base_pose)
        else:
            state = cold_context["closed_loop_state_v2"]
            if cold_hold_entry_not_before_control_step is not None and (
                not isinstance(cold_hold_entry_not_before_control_step, int)
                or cold_hold_entry_not_before_control_step <= state["motion_step_index"] + 1
            ):
                raise ValueError("Diagnostic hold-entry step must be after the held boundary")
            for name, original in cold_context["arguments"].items():
                if name not in ("hold_target_step_local", "hold_target_step_probe", "output_json"):
                    if getattr(args, name) != original:
                        raise ValueError(f"Cold continuation argument changed: {name}")
            if (cold_context["schema_version"] != 1
                    or cold_context["seed"] != args.seed
                    or args.arm_controller != "unified-wbc"
                    or not target_step_enabled
                    or not args.wbc_hold_on_gate):
                raise ValueError("Invalid cold held-step continuation request")
            if (sha256(runtime.policy_path) != cold_context["artifact_sha256"]["policy"]
                    or sha256(runtime.config_path) != cold_context["artifact_sha256"]["config"]
                    or sha256(PROFILE_PATH) != cold_context["artifact_sha256"]["profile"]):
                raise ValueError("Cold continuation policy/config/profile mismatch")
            from audit_piper_held_cold_snapshot import _compiled_model_sha256
            if (_compiled_model_sha256(runtime.model) != cold_context["artifact_sha256"]["compiled_model"]
                    or sha256(runtime.scene_path) != cold_context["artifact_sha256"]["scene_xml"]):
                raise ValueError("Cold continuation model/scene mismatch")
            _restore_held_step_state_v2(runtime, monitor, state, fresh_data=True)
            candidate = SimpleNamespace(
                joint_solution=np.asarray(cold_context["candidate_joint_solution"], dtype=np.float64),
                kinematic_feasible=True,
            )
            planned_base_pose = np.asarray(cold_context["planned_base_pose"], dtype=np.float64)
            target_world = np.asarray(state["target_world"], dtype=np.float64)
            box_reference = cold_context["arm_target_box_snapshot"]
            if box_reference is None or monitor.box_reader is None:
                raise ValueError("Cold continuation requires a movable box reference")
            box_reference_state = BoxState(
                box_reference["time"], box_reference["position"], box_reference["quaternion"],
                box_reference["linear_velocity_world"], box_reference["angular_velocity_world"],
            )
            box_position = box_reference_state.position.copy()
            box_rotation = box_reference_state.rotation
            cosine, sine = box_rotation[0, 0], box_rotation[1, 0]
            monitor.box_state = monitor.box_reader.read()
            monitor.box_guard = BoxSnapshotGuard(
                box_reference_state, geometry_radius=monitor.box_reader.radius,
                **monitor.box_validity_limits,
            )
            monitor.box_guard_result = monitor.box_guard.evaluate(monitor.box_state)
            if not monitor.box_guard_result["valid"]:
                raise ValueError("Cold continuation box guard is invalid at the boundary")
            monitor.box_snapshots = cold_context["prefix_report"].get("box_snapshots", [])
            monitor.stage = "arm_motion"
            monitor.track_reference = False
            monitor._refresh_clearance_geometry()
            monitor.current_self_clearance = monitor.self_clearance.evaluate_current_configuration(
                required_clearance=args.required_self_clearance
            )
            monitor.current_environment_clearance = monitor.environment_clearance.evaluate_current_configuration(
                required_clearance=args.required_environment_clearance
            )
            if args.diagnose_designated_hand_approach:
                monitor.current_finger_environment_clearance = (
                    monitor.finger_environment_clearance.evaluate_current_configuration(required_clearance=0.0)
                )
                monitor.current_nonhand_environment_clearance = (
                    monitor.nonhand_environment_clearance.evaluate_current_configuration(
                        required_clearance=args.required_environment_clearance
                    )
                )
                geometry = monitor.contact_geometry_reader.read()
                monitor.current_designated_face_ready = bool(geometry["fingers"]) and all(
                    item["separated_witnesses_valid"] and item["box_point_in_front_region"]
                    for item in geometry["fingers"]
                )
            hand_feedback_integral = np.asarray(state["hand_feedback_integral"], dtype=np.float64)
            orientation_feedback_integral = np.asarray(state["orientation_feedback_integral"], dtype=np.float64)
            held_wbc_pose = tuple(np.asarray(part, dtype=np.float64) for part in state["held_wbc_pose"])
            hold_entry_wait_steps = state["hold_entry_wait_steps"]
            stable_steps = state["stable_steps"]
            wbc_hold_entries = state["wbc_hold_entries"]
            wbc_command_hold_steps = state["wbc_command_hold_steps"]
            end_effector_start_position = np.asarray(state["end_effector_start_position"], dtype=np.float64)
            end_effector_start_quaternion = np.asarray(state["end_effector_start_quaternion"], dtype=np.float64)
            end_effector_target_position = np.asarray(state["end_effector_target_position"], dtype=np.float64)
            end_effector_target_quaternion = np.asarray(state["end_effector_target_quaternion"], dtype=np.float64)
            hand_start_position = np.asarray(state["hand_start_position"], dtype=np.float64)
            arm_motion_start_base_position = np.asarray(state["arm_motion_start_base_position"], dtype=np.float64)
            arm_motion_start_base_pose = np.asarray(state["arm_motion_start_base_pose"], dtype=np.float64)
            end_effector = runtime.model.body("end_effector").id
            reference = runtime.data.qpos[runtime.joint_qpos_adr[12:]].copy()
            gravity_data = mujoco.MjData(runtime.model)
            wbc_hold_events = list(cold_context["prefix_report"]["hold_events_before_boundary"])
            episode_keys = (
                "target_world", "hand_feedback_integral", "orientation_feedback_integral",
                "held_wbc_pose", "hold_entry_wait_steps", "stable_steps", "wbc_hold_entries",
                "wbc_command_hold_steps", "motion_step_index", "end_effector_start_position",
                "end_effector_start_quaternion", "end_effector_target_position",
                "end_effector_target_quaternion", "hand_start_position",
                "arm_motion_start_base_position", "arm_motion_start_base_pose",
            )
            if _capture_held_step_state_v2(runtime, monitor, {key: state[key] for key in episode_keys}) != state:
                raise ValueError("Cold held-step state differs after full monitor reconstruction")
        step_start = state["motion_step_index"] if cold_context is not None else 0
        for step in range(step_start, round(args.motion_timeout_seconds / runtime.control_dt)):
            if ((target_step_enabled or target_step_probe) and target_step_event is None
                    and held_wbc_pose is not None
                    and stable_steps * runtime.control_dt >= target_step_after_seconds):
                previous_target = target_world.copy()
                hand_before_step = _hand_position(runtime, args.hand_point)
                pre_step_state = {
                    "qpos": runtime.data.qpos.tolist(),
                    "qvel": runtime.data.qvel.tolist(),
                    "ctrl": runtime.data.ctrl.tolist(),
                    "hand_feedback_integral": hand_feedback_integral.tolist(),
                    "orientation_feedback_integral": orientation_feedback_integral.tolist(),
                    "held_wbc_pose": [held_wbc_pose[0].tolist(), held_wbc_pose[1].tolist()],
                    "stable_steps": stable_steps,
                }
                episode_state = {
                    "target_world": previous_target.tolist(),
                    "hand_feedback_integral": hand_feedback_integral.tolist(),
                    "orientation_feedback_integral": orientation_feedback_integral.tolist(),
                    "held_wbc_pose": [held_wbc_pose[0].tolist(), held_wbc_pose[1].tolist()],
                    "hold_entry_wait_steps": hold_entry_wait_steps,
                    "stable_steps": stable_steps,
                    "wbc_hold_entries": wbc_hold_entries,
                    "wbc_command_hold_steps": wbc_command_hold_steps,
                    "motion_step_index": step,
                    "end_effector_start_position": end_effector_start_position.tolist(),
                    "end_effector_start_quaternion": end_effector_start_quaternion.tolist(),
                    "end_effector_target_position": end_effector_target_position.tolist(),
                    "end_effector_target_quaternion": end_effector_target_quaternion.tolist(),
                    "hand_start_position": hand_start_position.tolist(),
                    "arm_motion_start_base_position": arm_motion_start_base_position.tolist(),
                    "arm_motion_start_base_pose": arm_motion_start_base_pose.tolist(),
                }
                closed_loop_state_v2 = _capture_held_step_state_v2(
                    runtime, monitor, episode_state
                )
                if restore_state is not None:
                    if closed_loop_state_v2 != restore_state:
                        raise ValueError("Candidate and baseline held-step states differ before restore")
                    runtime.data.qpos[0] += 0.001
                    runtime.history[0][0] += 0.001
                    runtime.last_action[0] += 0.001
                    runtime.velocity_command[0] += 0.001
                    runtime.ee_command[0] += 0.001
                    monitor.support_violation_steps += 1
                    if monitor.sweep_previous_qpos is not None:
                        monitor.sweep_previous_qpos[0] += 0.001
                    monitor.physics.last_time += 0.001
                    hand_feedback_integral[0] += 0.001
                    held_wbc_pose = None
                    stable_steps += 1
                    _restore_held_step_state_v2(
                        runtime, monitor, restore_state,
                        fresh_data=restore_mode == "fresh-data",
                    )
                    target_world = np.asarray(restore_state["target_world"], dtype=np.float64)
                    hand_feedback_integral = np.asarray(
                        restore_state["hand_feedback_integral"], dtype=np.float64
                    )
                    orientation_feedback_integral = np.asarray(
                        restore_state["orientation_feedback_integral"], dtype=np.float64
                    )
                    held_wbc_pose = tuple(
                        np.asarray(part, dtype=np.float64)
                        for part in restore_state["held_wbc_pose"]
                    )
                    hold_entry_wait_steps = restore_state["hold_entry_wait_steps"]
                    stable_steps = restore_state["stable_steps"]
                    wbc_hold_entries = restore_state["wbc_hold_entries"]
                    wbc_command_hold_steps = restore_state["wbc_command_hold_steps"]
                    end_effector_start_position = np.asarray(
                        restore_state["end_effector_start_position"], dtype=np.float64
                    )
                    end_effector_start_quaternion = np.asarray(
                        restore_state["end_effector_start_quaternion"], dtype=np.float64
                    )
                    end_effector_target_position = np.asarray(
                        restore_state["end_effector_target_position"], dtype=np.float64
                    )
                    end_effector_target_quaternion = np.asarray(
                        restore_state["end_effector_target_quaternion"], dtype=np.float64
                    )
                    hand_start_position = np.asarray(
                        restore_state["hand_start_position"], dtype=np.float64
                    )
                    arm_motion_start_base_position = np.asarray(
                        restore_state["arm_motion_start_base_position"], dtype=np.float64
                    )
                    arm_motion_start_base_pose = np.asarray(
                        restore_state["arm_motion_start_base_pose"], dtype=np.float64
                    )
                    restored_episode_state = {
                        "target_world": target_world.tolist(),
                        "hand_feedback_integral": hand_feedback_integral.tolist(),
                        "orientation_feedback_integral": orientation_feedback_integral.tolist(),
                        "held_wbc_pose": [part.tolist() for part in held_wbc_pose],
                        "hold_entry_wait_steps": hold_entry_wait_steps,
                        "stable_steps": stable_steps,
                        "wbc_hold_entries": wbc_hold_entries,
                        "wbc_command_hold_steps": wbc_command_hold_steps,
                        "motion_step_index": step,
                        "end_effector_start_position": end_effector_start_position.tolist(),
                        "end_effector_start_quaternion": end_effector_start_quaternion.tolist(),
                        "end_effector_target_position": end_effector_target_position.tolist(),
                        "end_effector_target_quaternion": end_effector_target_quaternion.tolist(),
                        "hand_start_position": hand_start_position.tolist(),
                        "arm_motion_start_base_position": arm_motion_start_base_position.tolist(),
                        "arm_motion_start_base_pose": arm_motion_start_base_pose.tolist(),
                    }
                    if _capture_held_step_state_v2(runtime, monitor, restored_episode_state) != restore_state:
                        raise ValueError("Held-step state differs after restore")
                if target_step_enabled:
                    target_world = target_world + box_rotation @ target_step_local
                    monitor.target_world = target_world.copy()
                    held_wbc_pose = None
                    hold_entry_wait_steps = 0
                    stable_steps = 0
                target_step_event = {
                    "time": float(runtime.data.time),
                    "control_step": step + 1,
                    "applied": target_step_enabled,
                    "offset_local_m": target_step_local.tolist(),
                    "previous_target_world": previous_target.tolist(),
                    "new_target_world": target_world.tolist(),
                    "pre_step_hand_error_m": float(np.linalg.norm(hand_before_step - previous_target)),
                    "instantaneous_hand_error_m": float(np.linalg.norm(hand_before_step - target_world)),
                    "hold_entries_before_step": wbc_hold_entries,
                    "pre_step_state": pre_step_state,
                    "closed_loop_state_v2": closed_loop_state_v2,
                }
                if restore_state is not None:
                    target_step_event["restore_roundtrip_verified"] = True
                    target_step_event["restore_mode"] = restore_mode
            if args.arm_controller == "joint-pd":
                reference = CONTROL["coordinated_joint_target"](
                    batch(reference),
                    batch(candidate.joint_solution),
                    runtime.control_dt * args.arm_joint_speed,
                )[0].numpy()
                monitor.reference = reference.copy()
                gravity_data.qpos[:] = runtime.data.qpos
                gravity_data.qvel.fill(0.0)
                mujoco.mj_forward(runtime.model, gravity_data)
                gravity_compensation = (
                    gravity_data.qfrc_bias[runtime.joint_dof_adr[12:]]
                    / runtime.kp[12:]
                )
                maximum_gravity_compensation = max(
                    maximum_gravity_compensation,
                    float(np.max(np.abs(gravity_compensation))),
                )
                raw_arm_target = reference + gravity_compensation
                clipped_arm_target = np.clip(
                    raw_arm_target, runtime.joint_low[12:], runtime.joint_high[12:]
                )
                maximum_target_clipping = max(
                    maximum_target_clipping,
                    float(np.max(np.abs(raw_arm_target - clipped_arm_target))),
                )
                target = _policy_joint_target(runtime)
                target[12:] = clipped_arm_target
                runtime._simulate_target(target)
                runtime.last_action = (
                    (target - runtime.default_qpos) / runtime.action_scale
                )[MJ_POLICY_INDICES]
                runtime.history.append(runtime._single_observation())
            else:
                command_was_held = held_wbc_pose is not None
                ramp_fraction = min(
                    1.0,
                    (step + 1) * runtime.control_dt
                    / max(args.wbc_command_ramp_seconds, runtime.control_dt),
                )
                commanded_position = (
                    end_effector_start_position
                    + ramp_fraction
                    * (end_effector_target_position - end_effector_start_position)
                )
                midpoint_profile = (
                    ramp_fraction
                    * (1.0 - ramp_fraction)
                    * (4.0 + 2.0 * ramp_fraction)
                )
                commanded_position[:2] += (
                    args.wbc_midpoint_lateral_meters
                    * midpoint_profile
                    * np.array([-sine, cosine])
                )
                commanded_position[2] += (
                    args.wbc_midpoint_lift_meters * midpoint_profile
                )
                desired_hand_position = (
                    hand_start_position
                    + ramp_fraction * (target_world - hand_start_position)
                )
                desired_hand_position[:2] += (
                    args.wbc_midpoint_lateral_meters
                    * midpoint_profile
                    * np.array([-sine, cosine])
                )
                desired_hand_position[2] += (
                    args.wbc_midpoint_lift_meters * midpoint_profile
                )
                commanded_quaternion = _slerp_quaternion(
                    end_effector_start_quaternion,
                    end_effector_target_quaternion,
                    ramp_fraction,
                )
                current_hand = _hand_position(runtime, args.hand_point)
                hand_feedback_correction = args.wbc_hand_feedback_gain * (
                    desired_hand_position - current_hand
                )
                current_hand_local = _box_local_position(current_hand, monitor, box_position, box_rotation)
                current_hand_gate = bool(
                    bool(
                        CONTROL["side_approach_ready"](
                            batch(current_hand_local),
                            box_size[0] / 2.0,
                            args.push_approach_distance,
                        )[0]
                    )
                    and abs(current_hand_local[2]) < 0.06
                )
                feedback_gate_lower_x = (
                    -box_size[0] / 2.0
                    - args.push_approach_distance
                    - 0.06
                    + args.wbc_hand_feedback_gate_margin
                )
                feedback_gate_reached = bool(
                    current_hand_gate
                    and current_hand_local[0] >= feedback_gate_lower_x
                )
                feedback_target_reached = (
                    float(np.linalg.norm(target_world - current_hand))
                    <= args.hand_tracking_tolerance
                    if args.diagnose_designated_hand_approach
                    else feedback_gate_reached
                )
                if ramp_fraction >= 1.0 and not feedback_target_reached and not command_was_held:
                    hand_feedback_integral += (
                        args.wbc_hand_feedback_integral_gain
                        * runtime.control_dt
                        * (target_world - current_hand)
                    )
                    integral_norm = float(np.linalg.norm(hand_feedback_integral))
                    if integral_norm > args.wbc_hand_feedback_max_meters:
                        hand_feedback_integral *= (
                            args.wbc_hand_feedback_max_meters / integral_norm
                        )
                hand_feedback_correction += hand_feedback_integral
                correction_norm = float(np.linalg.norm(hand_feedback_correction))
                if correction_norm > args.wbc_hand_feedback_max_meters:
                    hand_feedback_correction *= (
                        args.wbc_hand_feedback_max_meters / correction_norm
                    )
                    correction_norm = args.wbc_hand_feedback_max_meters
                if not command_was_held:
                    maximum_hand_feedback_correction = max(
                        maximum_hand_feedback_correction,
                        correction_norm,
                    )
                commanded_position += hand_feedback_correction
                reference_quaternion = commanded_quaternion.copy()
                if ramp_fraction >= 1.0 and not command_was_held:
                    commanded_quaternion, orientation_feedback_integral = (
                        _orientation_feedback(
                            runtime.data.xquat[end_effector],
                            commanded_quaternion,
                            orientation_feedback_integral,
                            gain=args.wbc_orientation_feedback_integral_gain,
                            control_dt=runtime.control_dt,
                            maximum_radians=args.wbc_orientation_feedback_max_radians,
                        )
                    )
                    maximum_orientation_feedback_correction = max(
                        maximum_orientation_feedback_correction,
                        float(np.linalg.norm(orientation_feedback_integral)),
                    )
                if command_was_held:
                    commanded_position = held_wbc_pose[0].copy()
                    commanded_quaternion = held_wbc_pose[1].copy()
                    wbc_command_hold_steps += 1
                wbc_command = _world_pose_to_wbc_command(
                    runtime,
                    commanded_position,
                    commanded_quaternion,
                )
                if initial_wbc_command is None:
                    initial_wbc_command = wbc_command.copy()
                final_wbc_command = wbc_command.copy()
                base_velocity_command = (
                    _base_hold_velocity(
                        arm_motion_start_base_pose,
                        _base_pose(runtime, arm_motion_start_base_pose),
                        position_gain=args.wbc_base_hold_position_gain,
                        yaw_gain=args.wbc_base_hold_yaw_gain,
                        maximum_linear_speed=args.wbc_base_hold_max_linear_speed,
                        maximum_yaw_rate=args.wbc_base_hold_max_yaw_rate,
                    )
                    if args.wbc_base_hold else np.zeros(3)
                )
                maximum_base_hold_linear_command = max(
                    maximum_base_hold_linear_command,
                    float(np.linalg.norm(base_velocity_command[:2])),
                )
                maximum_base_hold_yaw_command = max(
                    maximum_base_hold_yaw_command, abs(float(base_velocity_command[2]))
                )
                runtime.step(base_velocity_command, wbc_command)
            motion_steps = step + 1
            actual_arm = runtime.data.qpos[runtime.joint_qpos_adr[12:]].copy()
            joint_error = float(np.max(np.abs(actual_arm - candidate.joint_solution)))
            current_hand = _hand_position(runtime, args.hand_point)
            current_hand_local = _box_local_position(current_hand, monitor, box_position, box_rotation)
            hand_gate = bool(
                bool(
                    CONTROL["side_approach_ready"](
                        batch(current_hand_local),
                        box_size[0] / 2.0,
                        args.push_approach_distance,
                    )[0]
                )
                and abs(current_hand_local[2]) < 0.06
            )
            hand_error = float(np.linalg.norm(current_hand - target_world))
            arm_speed = float(
                np.max(np.abs(runtime.data.qvel[runtime.joint_dof_adr[12:]]))
            )
            maximum_arm_speed = max(maximum_arm_speed, arm_speed)
            orientation_error = _quaternion_error(
                runtime.data.xquat[end_effector],
                (
                    reference_quaternion
                    if args.arm_controller == "unified-wbc"
                    else end_effector_target_quaternion
                ),
            )
            maximum_end_effector_orientation_error = max(
                maximum_end_effector_orientation_error, orientation_error
            )
            settled = bool(
                (
                    args.arm_controller == "unified-wbc"
                    or np.max(np.abs(reference - candidate.joint_solution)) <= 1.0e-9
                )
                and (
                    args.arm_controller == "unified-wbc"
                    or joint_error <= args.joint_tracking_tolerance
                )
                and (
                    args.arm_controller == "joint-pd" or ramp_fraction >= 1.0
                )
                and (
                    hand_gate
                    if args.arm_controller == "unified-wbc"
                    else hand_error <= args.hand_tracking_tolerance
                )
                and (
                    not args.diagnose_designated_hand_approach
                    or hand_error <= args.hand_tracking_tolerance
                )
                and orientation_error <= args.orientation_tracking_tolerance
                and arm_speed <= args.arm_velocity_tolerance
            )
            if (target_step_enabled and target_step_event is not None
                    and target_step_first_settled_time is None
                    and settled):
                target_step_first_settled_time = float(runtime.data.time)
            if args.wbc_hold_on_gate and args.arm_controller == "unified-wbc":
                if held_wbc_pose is None:
                    if (cold_hold_entry_not_before_control_step is not None
                            and step + 1 < cold_hold_entry_not_before_control_step):
                        settled = False
                    hold_entry_wait_steps = hold_entry_wait_steps + 1 if settled else 0
                    gate_dwell_met = hold_entry_wait_steps * runtime.control_dt >= args.hold_seconds
                    entry_front_margin = args.wbc_hold_front_margin
                    hold_clearance = (
                        monitor.current_nonhand_environment_clearance
                        if args.diagnose_designated_hand_approach
                        else monitor.current_environment_clearance
                    )
                    environment_clearance = hold_clearance.minimum_clearance
                    if environment_clearance < (
                        args.required_environment_clearance + args.wbc_hold_clearance_reserve
                    ):
                        entry_front_margin = 0.0
                    front_ready = current_hand_local[0] >= (
                        -box_size[0] / 2.0 - args.push_approach_distance - 0.06
                        + entry_front_margin
                    )
                    settled = bool(
                        settled and (front_ready or gate_dwell_met)
                    )
                if settled and held_wbc_pose is None:
                    held_wbc_pose = (
                        commanded_position.copy(), commanded_quaternion.copy()
                    )
                    wbc_hold_entries += 1
                    wbc_hold_events.append({
                        "time": float(runtime.data.time),
                        "hand_local": current_hand_local.tolist(),
                        "environment_clearance": environment_clearance,
                        "environment_clearance_scope": (
                            "nonhand_arm_to_box"
                            if args.diagnose_designated_hand_approach else
                            "unified_arm_to_box"
                        ),
                        "entry_front_margin": entry_front_margin,
                        "gate_settle_seconds": hold_entry_wait_steps * runtime.control_dt,
                        "entry_reason": (
                            "stable_gate" if not front_ready
                            else "clearance_reserve" if entry_front_margin < args.wbc_hold_front_margin
                            else "front_margin"
                        ),
                    })
                    hold_entry_wait_steps = 0
                elif not settled:
                    held_wbc_pose = None
            stable_steps = stable_steps + 1 if settled else 0
            if cold_context is not None:
                cold_control_history.append({
                    "time": float(runtime.data.time),
                    "control_step": step + 1,
                    "settled": settled,
                    "stable_steps": stable_steps,
                    "command_was_held": command_was_held,
                    "hold_entry_count": wbc_hold_entries,
                    "hand_gate_passed": hand_gate,
                    "hand_position_error": hand_error,
                    "arm_speed": arm_speed,
                })
            if step % max(1, round(0.1 / runtime.control_dt)) == 0:
                trace.append(
                    {
                        "time": float(runtime.data.time),
                        "joint_error": joint_error,
                        "hand_position_error": hand_error,
                        "hand_gate_passed": hand_gate,
                        "hand_local": current_hand_local.tolist(),
                        "wbc_command_held": (
                            command_was_held if args.arm_controller == "unified-wbc" else False
                        ),
                        "wbc_hold_entry": wbc_hold_entries,
                        "commanded_world_pose": (
                            [*commanded_position.tolist(), *commanded_quaternion.tolist()]
                            if args.arm_controller == "unified-wbc" else None
                        ),
                        "end_effector_orientation_error": orientation_error,
                        "command_orientation_error": (
                            _quaternion_error(
                                runtime.data.xquat[end_effector], commanded_quaternion
                            )
                            if args.arm_controller == "unified-wbc"
                            else None
                        ),
                        "arm_speed": arm_speed,
                        "self_clearance": monitor.current_self_clearance.minimum_clearance,
                        "self_clearance_bodies": [
                            monitor.current_self_clearance.arm_body,
                            monitor.current_self_clearance.protected_body,
                        ],
                        "environment_clearance": monitor.current_environment_clearance.minimum_clearance,
                        "base_velocity_command": (
                            base_velocity_command.tolist()
                            if args.arm_controller == "unified-wbc" else None
                        ),
                        "finger_environment_clearance": (
                            monitor.current_finger_environment_clearance.minimum_clearance
                            if monitor.current_finger_environment_clearance is not None else None
                        ),
                        "nonhand_environment_clearance": (
                            monitor.current_nonhand_environment_clearance.minimum_clearance
                            if monitor.current_nonhand_environment_clearance is not None else None
                        ),
                        "designated_face_ready": monitor.current_designated_face_ready,
                        "wbc_command_ramp_fraction": (
                            ramp_fraction
                            if args.arm_controller == "unified-wbc"
                            else None
                        ),
                        "base_position": runtime.data.qpos[
                            runtime.env.robot_qpos_adr : runtime.env.robot_qpos_adr + 3
                        ].tolist(),
                    }
                )
            if stable_steps * runtime.control_dt >= args.hold_seconds:
                break
        else:
            raise RolloutFailure("arm_tracking_timeout")
    except RolloutFailure as error:
        reason = str(error)

    if cold_context is not None:
        final_hold_entries = [
            item for item in wbc_hold_events
            if target_step_event is not None and item["time"] > target_step_event["time"]
        ]
        return {
            "schema_version": 1,
            "scope": "Prefix-free, no-contact WBC suffix only; prefix extrema are unavailable",
            "seed": args.seed,
            "reason": reason,
            "passed": reason == "completed",
            "complete_prefix_accumulators_available": False,
            "diagnostic_hold_entry_not_before_control_step": (
                cold_hold_entry_not_before_control_step
            ),
            "start_control_step": state["motion_step_index"] + 1,
            "last_control_step": motion_steps,
            "target_step_event": target_step_event,
            "target_step_first_settled_time": target_step_first_settled_time,
            "stable_seconds": stable_steps * runtime.control_dt,
            "hold_events": wbc_hold_events,
            "prefix_hold_event_count": len(cold_context["prefix_report"]["hold_events_before_boundary"]),
            "ten_second_acceptance": bool(
                reason == "completed" and target_step_event is not None
                and final_hold_entries
                and final_hold_entries[-1]["time"] - target_step_event["time"] <= 10.0
            ),
            "trace": trace,
            "control_history": cold_control_history,
            "final_state": {
                "time": float(runtime.data.time),
                "qpos": runtime.data.qpos.tolist(),
                "qvel": runtime.data.qvel.tolist(),
                "ctrl": runtime.data.ctrl.tolist(),
            },
            "suffix_safety": {
                "physics_steps": monitor.physics.physics_steps,
                "dynamic_physics_samples": monitor.dynamic_samples,
                "minimum_self_clearance": monitor.finite_minimum(monitor.minimum_self_clearance),
                "minimum_environment_clearance": monitor.finite_minimum(monitor.minimum_environment_clearance),
                "minimum_nonhand_environment_clearance": monitor.finite_minimum(
                    monitor.minimum_nonhand_environment_clearance
                ),
                "minimum_swept_self_lower_bound": monitor.finite_minimum(
                    monitor.minimum_swept_self_clearance
                ),
                "minimum_swept_environment_lower_bound": monitor.finite_minimum(
                    monitor.minimum_swept_environment_clearance
                ),
                "minimum_swept_nonhand_lower_bound": monitor.finite_minimum(
                    monitor.minimum_swept_nonhand_environment_clearance
                ),
                "sweep_intervals": monitor.sweep_intervals,
                "minimum_support_margin": monitor.finite_minimum(monitor.minimum_support_margin),
                "minimum_supporting_feet": monitor.minimum_supporting_feet,
                "maximum_support_violation_seconds": (
                    monitor.maximum_support_violation_steps * runtime.sim_dt
                ),
                "minimum_base_height": monitor.finite_minimum(monitor.physics.min_height),
                "maximum_tilt_rad": monitor.physics.max_tilt,
                "first_nonfoot_ground_contact": monitor.physics.first_illegal_contact,
                "first_box_contact": monitor.first_box_contact,
                "box_stop_event": monitor.box_stop_event,
                "failure_snapshot": monitor.failure_snapshot,
            },
        }

    final_arm = runtime.data.qpos[runtime.joint_qpos_adr[12:]].copy()
    final_hand = _hand_position(runtime, args.hand_point)
    if monitor.box_reader is not None:
        monitor.box_state = monitor.box_reader.read()
    final_hand_local = _box_local_position(final_hand, monitor, box_position, box_rotation)
    final_gate = bool(
        bool(
            CONTROL["side_approach_ready"](
                batch(final_hand_local), box_size[0] / 2.0, args.push_approach_distance
            )[0]
        )
        and abs(final_hand_local[2]) < 0.06
    )
    return {
        "seed": args.seed,
        "passed": reason == "completed",
        "reason": reason,
        "scope": (
            f"single {args.box_mode}-box NAV arrival followed by {args.locomotion_policy} locomotion policy and "
            f"{args.arm_controller} motion to one {'pose' if args.native_push_pose else 'position'}-IK precontact candidate "
            f"using the {args.hand_point} hand reference; "
            "no PUSH actor, contact, continuous physical-dynamics certificate, "
            "or deployment approval"
        ),
        "locomotion_policy": args.locomotion_policy,
        "arm_controller": args.arm_controller,
        "contact_shadow": (
            PiperContactGeometryReader(runtime, proxy_offset=HAND_OFFSET).read()
            if args.contact_shadow else None
        ),
        "simulation": {
            "physics_substeps": runtime.physics_substeps,
            "physics_dt": runtime.sim_dt,
            "pd_dt": runtime.pd_dt,
            "policy_dt": runtime.control_dt,
            "pd_updates_per_policy_step": runtime.decimation,
            "integrator": int(runtime.model.opt.integrator),
        },
        "scene": {
            "box_mode": args.box_mode,
            "box_mass": args.box_mass if args.box_mode == "movable" else None,
            "box_position": box_position.tolist(),
            "box_size": box_size.tolist(),
            "box_yaw": float(np.arctan2(box_rotation[1, 0], box_rotation[0, 0])) if args.box_mode == "movable" else args.static_box_yaw,
            "requested_box_position": list(args.static_box_position),
            "requested_box_yaw": args.static_box_yaw,
        },
        "box_runtime": {
            "scope": "Live box state with bounded snapshot validity; abort requires re-observation and re-planning",
            "snapshots": monitor.box_snapshots,
            "final_state": monitor.box_state.as_dict() if monitor.box_state is not None else None,
            "last_validity": monitor.box_guard_result,
            "maximum_geometry_displacement": monitor.maximum_box_displacement,
            "maximum_linear_speed": monitor.maximum_box_linear_speed,
            "maximum_angular_speed": monitor.maximum_box_angular_speed,
            "floor_contact_samples": monitor.box_floor_contact_samples,
            "contact_region": monitor.box_contact_region.as_dict() if monitor.box_contact_region is not None else None,
            "stop_event": monitor.box_stop_event,
        },
        "nav": {
            "front_standoff": args.nav_front_standoff,
            "lateral_offset": args.nav_lateral_offset,
            "yaw_gain": args.nav_yaw_gain,
            "planned_base_pose": planned_base_pose.tolist(),
            "actual_base_pose": actual_base_pose.tolist(),
            "trace": nav_trace,
        },
        "candidate": {
            "hand_point": {
                "mode": args.hand_point, "body": hand_body_name, "offset": list(hand_offset),
                "matches_native_piper_frame": args.hand_point == "piper",
            },
            "target_local": target_local.tolist(),
            "active_target_local": (
                target_local + target_step_local
                if target_step_event is not None else target_local
            ).tolist(),
            "target_world": target_world.tolist(),
            "ik_initial": ik_initial.tolist(),
            "precontact_state": precontact_state,
            "kinematic_feasible": bool(
                candidate is not None and candidate.kinematic_feasible
            ),
            "position_error": candidate.position_error if candidate is not None else None,
            "orientation_error": candidate.orientation_error if candidate is not None else None,
            "target_orientation_world": target_orientation_world.tolist() if target_orientation_world is not None else None,
            "ik_orientation_tolerance": oracle.orientation_tolerance if args.native_push_pose else None,
            "ik_orientation_weight": oracle.orientation_weight if args.native_push_pose else None,
            "joint_limit_margin": (
                candidate.joint_limit_margin if candidate is not None else None
            ),
            "joint_solution": (
                candidate.joint_solution.tolist() if candidate is not None else None
            ),
            "end_effector_target_world_pose": (
                [
                    *end_effector_target_position,
                    *end_effector_target_quaternion,
                ]
                if end_effector_target_position is not None
                and end_effector_target_quaternion is not None
                else None
            ),
            "endpoint": (
                {
                    "self_clearance": endpoint_self.minimum_clearance,
                    "self_clearance_bodies": [
                        endpoint_self.arm_body,
                        endpoint_self.protected_body,
                    ],
                    "environment_clearance": endpoint_environment.minimum_clearance,
                    "environment_clearance_bodies": [
                        endpoint_environment.arm_body,
                        endpoint_environment.protected_body,
                    ],
                    "designated_hand_approach": endpoint_designated_hand_approach,
                    "support_margin": endpoint_support.support_margin,
                    "hand_local": hand_local.tolist(),
                    "hand_gate_passed": endpoint_hand_gate,
                    "passed": endpoint_passed,
                }
                if candidate is not None and candidate.kinematic_feasible
                else None
            ),
            "static_path": static_path,
        },
        "motion": {
            "control_steps": motion_steps,
            "dynamic_physics_samples": monitor.dynamic_samples,
            "clearance_state": "post-integration qpos, independently recomputed geometry",
            "swept_clearance": {
                "scope": (
                    "Euler numerical position-update segments with explicitly tracked free box; not physical ODE trajectories"
                    if monitor.box_is_movable else
                    "Euler numerical position-update segments only; static external scene; not physical ODE trajectories"
                ),
                "selected_constraint_set": (
                    "finger_noncontact_and_nonhand_environment_clearance"
                    if args.diagnose_designated_hand_approach else
                    "unified_arm_environment_clearance"
                ),
                "required": monitor.require_motion_sweep_certificate,
                "checked_intervals": monitor.sweep_intervals,
                "minimum_self_lower_bound": monitor.finite_minimum(monitor.minimum_swept_self_clearance),
                "minimum_environment_lower_bound": monitor.finite_minimum(monitor.minimum_swept_environment_clearance),
                "unified_environment_clearance_enforced": not args.diagnose_designated_hand_approach,
                "minimum_finger_environment_lower_bound": monitor.finite_minimum(
                    monitor.minimum_swept_finger_environment_clearance
                ),
                "minimum_nonhand_environment_lower_bound": monitor.finite_minimum(
                    monitor.minimum_swept_nonhand_environment_clearance
                ),
                "maximum_integration_residual": monitor.maximum_integration_residual,
                "passed": (
                    bool(
                        monitor.sweep_intervals == monitor.dynamic_samples
                        and monitor.sweep_intervals > 0
                        and monitor.minimum_swept_self_clearance >= args.required_self_clearance
                        and (
                            (
                                monitor.minimum_swept_finger_environment_clearance >= 0.0
                                and monitor.minimum_swept_nonhand_environment_clearance
                                >= args.required_environment_clearance
                            )
                            if args.diagnose_designated_hand_approach else
                            monitor.minimum_swept_environment_clearance
                            >= args.required_environment_clearance
                        )
                        and monitor.maximum_integration_residual <= 1.0e-12
                        and reason not in ("motion_sweep_unsupported_integrator", "motion_sweep_integration_mismatch")
                    )
                    if monitor.require_motion_sweep_certificate else None
                ),
            },
            "stable_seconds": stable_steps * runtime.control_dt,
            "wbc_hold_entries": wbc_hold_entries,
            "wbc_hold_events": wbc_hold_events,
            "target_step_event": target_step_event,
            "target_step_first_settled_time": target_step_first_settled_time,
            "wbc_command_hold_seconds": wbc_command_hold_steps * runtime.control_dt,
            "minimum_self_clearance": monitor.finite_minimum(
                monitor.minimum_self_clearance
            ),
            "minimum_environment_clearance": monitor.finite_minimum(
                monitor.minimum_environment_clearance
            ),
            "minimum_finger_environment_clearance": monitor.finite_minimum(
                monitor.minimum_finger_environment_clearance
            ),
            "minimum_nonhand_environment_clearance": monitor.finite_minimum(
                monitor.minimum_nonhand_environment_clearance
            ),
            "minimum_support_margin": monitor.finite_minimum(
                monitor.minimum_support_margin
            ),
            "minimum_supporting_feet": monitor.minimum_supporting_feet,
            "maximum_support_violation_seconds": (
                monitor.maximum_support_violation_steps * runtime.sim_dt
            ),
            "maximum_reference_tracking_error": monitor.maximum_reference_tracking_error,
            "maximum_hand_position_error": monitor.maximum_hand_position_error,
            "maximum_end_effector_orientation_error": maximum_end_effector_orientation_error,
            "maximum_arm_speed": maximum_arm_speed,
            "maximum_gravity_compensation": maximum_gravity_compensation,
            "maximum_target_clipping": maximum_target_clipping,
            "maximum_hand_feedback_correction": maximum_hand_feedback_correction,
            "maximum_orientation_feedback_correction": maximum_orientation_feedback_correction,
            "maximum_base_hold_linear_command": maximum_base_hold_linear_command,
            "maximum_base_hold_yaw_command": maximum_base_hold_yaw_command,
            "initial_wbc_command": (
                initial_wbc_command.tolist() if initial_wbc_command is not None else None
            ),
            "final_wbc_command": (
                final_wbc_command.tolist() if final_wbc_command is not None else None
            ),
            "base_displacement_during_motion": (
                (
                    runtime.data.qpos[
                        runtime.env.robot_qpos_adr : runtime.env.robot_qpos_adr + 3
                    ]
                    - arm_motion_start_base_position
                ).tolist()
                if arm_motion_start_base_position is not None
                else None
            ),
            "failure_snapshot": monitor.failure_snapshot,
            "final_joint_position": final_arm.tolist(),
            "final_state": {
                "time": float(runtime.data.time),
                "qpos": runtime.data.qpos.tolist(),
                "qvel": runtime.data.qvel.tolist(),
                "ctrl": runtime.data.ctrl.tolist(),
            },
            "final_joint_error": (
                float(np.max(np.abs(final_arm - candidate.joint_solution)))
                if candidate is not None and candidate.kinematic_feasible
                else None
            ),
            "final_hand_position": final_hand.tolist(),
            "final_hand_local": final_hand_local.tolist(),
            "final_end_effector_world_pose": [
                *runtime.data.xpos[runtime.model.body("end_effector").id].tolist(),
                *runtime.data.xquat[runtime.model.body("end_effector").id].tolist(),
            ],
            "final_hand_position_error": float(np.linalg.norm(final_hand - target_world)),
            "final_hand_gate_passed": final_gate,
            "final_end_effector_orientation_error": (
                _quaternion_error(
                    runtime.data.xquat[runtime.model.body("end_effector").id],
                    end_effector_target_quaternion,
                )
                if end_effector_target_quaternion is not None
                else None
            ),
            "trace": trace,
        },
        "safety": {
            "minimum_base_height": monitor.physics.min_height,
            "maximum_tilt_rad": monitor.physics.max_tilt,
            "maximum_torque_fraction": monitor.physics.max_torque_fraction,
            "first_nonfoot_ground_contact": monitor.physics.first_illegal_contact,
            "first_box_contact": monitor.first_box_contact,
            "contact_execution_enabled": False,
        },
        "thresholds": {
            "push_approach_distance": args.push_approach_distance,
            "joint_limit_margin": args.required_joint_limit_margin,
            "self_clearance": args.required_self_clearance,
            "environment_clearance": args.required_environment_clearance,
            "quasistatic_support_margin": args.required_support_margin,
            "support_violation_grace_seconds": args.support_violation_grace_seconds,
            "joint_tracking_tolerance": args.joint_tracking_tolerance,
            "hand_tracking_tolerance": args.hand_tracking_tolerance,
            "arm_velocity_tolerance": args.arm_velocity_tolerance,
            "orientation_tracking_tolerance": args.orientation_tracking_tolerance,
            "wbc_command_ramp_seconds": args.wbc_command_ramp_seconds,
            "wbc_hold_on_gate": args.wbc_hold_on_gate,
            "wbc_base_hold": args.wbc_base_hold,
            "wbc_base_hold_position_gain": args.wbc_base_hold_position_gain,
            "wbc_base_hold_yaw_gain": args.wbc_base_hold_yaw_gain,
            "wbc_base_hold_max_linear_speed": args.wbc_base_hold_max_linear_speed,
            "wbc_base_hold_max_yaw_rate": args.wbc_base_hold_max_yaw_rate,
            "wbc_hold_front_margin": args.wbc_hold_front_margin,
            "wbc_hold_clearance_reserve": args.wbc_hold_clearance_reserve,
            "wbc_hand_feedback_gain": args.wbc_hand_feedback_gain,
            "wbc_hand_feedback_integral_gain": (
                args.wbc_hand_feedback_integral_gain
            ),
            "wbc_hand_feedback_gate_margin": args.wbc_hand_feedback_gate_margin,
            "wbc_hand_feedback_max_meters": args.wbc_hand_feedback_max_meters,
            "wbc_orientation_feedback_integral_gain": args.wbc_orientation_feedback_integral_gain,
            "wbc_orientation_feedback_max_radians": args.wbc_orientation_feedback_max_radians,
            "wbc_midpoint_lateral_meters": args.wbc_midpoint_lateral_meters,
            "wbc_midpoint_lift_meters": args.wbc_midpoint_lift_meters,
            "hold_seconds": args.hold_seconds,
            "arm_joint_speed": args.arm_joint_speed,
        },
        "elapsed_sim_time": float(runtime.data.time),
        "physical_initializations": 1,
        "policy_sha256": sha256(runtime.policy_path),
        "config_sha256": sha256(runtime.config_path),
        "profile_sha256": sha256(PROFILE_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--locomotion-policy", choices=("flat", "wbc"), default="flat")
    parser.add_argument("--physics-substeps", type=int, choices=(1, 2, 4), default=1)
    parser.add_argument(
        "--arm-controller", choices=("joint-pd", "unified-wbc"), default="joint-pd"
    )
    parser.add_argument("--seed", type=int, default=435)
    parser.add_argument("--box-mode", choices=("static", "movable"), default="static")
    parser.add_argument("--contact-shadow", action="store_true")
    parser.add_argument("--hand-point", choices=("piper", "legacy-proxy"), default="piper")
    parser.add_argument("--native-push-pose", action="store_true")
    parser.add_argument("--diagnose-designated-hand-approach", action="store_true")
    parser.add_argument("--box-mass", type=float, default=1.0)
    parser.add_argument("--box-max-displacement", type=float, default=0.001)
    parser.add_argument("--box-max-linear-speed", type=float, default=0.005)
    parser.add_argument("--box-max-angular-speed", type=float, default=0.02)
    parser.add_argument("--static-box-position", "--box-position", type=float, nargs=3, default=(0.9, 0.0, 0.1))
    parser.add_argument("--static-box-size", "--box-size", type=float, nargs=3, default=(0.2, 0.2, 0.2))
    parser.add_argument("--static-box-yaw", "--box-yaw", type=float, default=0.0)
    parser.add_argument("--nav-front-standoff", type=float, default=0.51)
    parser.add_argument("--nav-lateral-offset", type=float, default=0.08)
    parser.add_argument("--nav-yaw-gain", type=float, default=NavigateConfig().yaw_gain)
    parser.add_argument("--hand-target-local", type=float, nargs=3, default=(-0.25, -0.06, 0.02))
    parser.add_argument("--ik-initial", type=float, nargs=6, default=(0.0, 0.6, -0.6, 0.0, 0.0, 0.0))
    parser.add_argument("--push-approach-distance", type=float, default=None)
    parser.add_argument("--initial-settle-seconds", type=float, default=2.0)
    parser.add_argument("--post-nav-settle-seconds", type=float, default=1.0)
    parser.add_argument("--motion-timeout-seconds", type=float, default=6.0)
    parser.add_argument("--hold-seconds", type=float, default=0.5)
    parser.add_argument("--path-samples", type=int, default=101)
    parser.add_argument("--require-static-path-certificate", action="store_true")
    parser.add_argument("--require-motion-sweep-certificate", action="store_true")
    parser.add_argument("--required-joint-limit-margin", type=float, default=0.05)
    parser.add_argument("--required-self-clearance", type=float, default=0.05)
    parser.add_argument("--required-environment-clearance", type=float, default=0.05)
    parser.add_argument("--required-support-margin", type=float, default=0.02)
    parser.add_argument("--support-violation-grace-seconds", type=float, default=0.2)
    parser.add_argument("--joint-tracking-tolerance", type=float, default=0.08)
    parser.add_argument("--hand-tracking-tolerance", type=float, default=0.02)
    parser.add_argument("--arm-velocity-tolerance", type=float, default=0.15)
    parser.add_argument("--orientation-tracking-tolerance", type=float, default=0.15)
    parser.add_argument("--wbc-command-ramp-seconds", type=float, default=2.0)
    parser.add_argument("--wbc-hold-on-gate", "--wbc-hold-command-on-gate", action="store_true")
    parser.add_argument("--wbc-base-hold", action="store_true")
    parser.add_argument("--wbc-base-hold-position-gain", type=float, default=1.0)
    parser.add_argument("--wbc-base-hold-yaw-gain", type=float, default=1.0)
    parser.add_argument("--wbc-base-hold-max-linear-speed", type=float, default=0.05)
    parser.add_argument("--wbc-base-hold-max-yaw-rate", type=float, default=0.10)
    parser.add_argument("--wbc-hold-front-margin", type=float, default=0.005)
    parser.add_argument("--wbc-hold-clearance-reserve", type=float, default=0.008)
    parser.add_argument("--wbc-hand-feedback-gain", type=float, default=0.0)
    parser.add_argument("--wbc-hand-feedback-integral-gain", type=float, default=0.0)
    parser.add_argument("--wbc-hand-feedback-gate-margin", type=float, default=0.0)
    parser.add_argument("--wbc-hand-feedback-max-meters", type=float, default=0.03)
    parser.add_argument("--wbc-orientation-feedback-integral-gain", type=float, default=0.0)
    parser.add_argument("--wbc-orientation-feedback-max-radians", type=float, default=0.2)
    parser.add_argument("--wbc-midpoint-lateral-meters", type=float, default=0.0)
    parser.add_argument("--wbc-midpoint-lift-meters", type=float, default=0.0)
    parser.add_argument("--arm-joint-speed", type=float, default=1.0)
    args = parser.parse_args()
    if args.push_approach_distance is None:
        args.push_approach_distance = NATIVE_PUSH_APPROACH_DISTANCE if args.native_push_pose else 0.10
    if args.native_push_pose and (
        args.hand_point != "piper"
        or not np.isclose(args.push_approach_distance, NATIVE_PUSH_APPROACH_DISTANCE, rtol=0.0, atol=1e-12)
    ):
        parser.error("Native PUSH pose requires the piper hand point and 0.03 m approach distance")
    if args.diagnose_designated_hand_approach and not args.native_push_pose:
        parser.error("Designated hand approach diagnosis requires the native PUSH pose")
    if args.output_json.exists():
        parser.error(f"Refusing to overwrite {args.output_json}")
    finite_values = (
        *args.static_box_position,
        args.box_mass,
        args.box_max_displacement,
        args.box_max_linear_speed,
        args.box_max_angular_speed,
        *args.static_box_size,
        args.static_box_yaw,
        args.nav_front_standoff,
        args.nav_lateral_offset,
        args.nav_yaw_gain,
        *args.hand_target_local,
        *args.ik_initial,
        args.push_approach_distance,
        args.initial_settle_seconds,
        args.post_nav_settle_seconds,
        args.motion_timeout_seconds,
        args.hold_seconds,
        args.required_joint_limit_margin,
        args.required_self_clearance,
        args.required_environment_clearance,
        args.required_support_margin,
        args.support_violation_grace_seconds,
        args.joint_tracking_tolerance,
        args.hand_tracking_tolerance,
        args.arm_velocity_tolerance,
        args.orientation_tracking_tolerance,
        args.wbc_command_ramp_seconds,
        args.wbc_hold_front_margin,
        args.wbc_hold_clearance_reserve,
        args.wbc_base_hold_position_gain,
        args.wbc_base_hold_yaw_gain,
        args.wbc_base_hold_max_linear_speed,
        args.wbc_base_hold_max_yaw_rate,
        args.wbc_hand_feedback_gain,
        args.wbc_hand_feedback_integral_gain,
        args.wbc_hand_feedback_gate_margin,
        args.wbc_hand_feedback_max_meters,
        args.wbc_orientation_feedback_integral_gain,
        args.wbc_orientation_feedback_max_radians,
        args.wbc_midpoint_lateral_meters,
        args.wbc_midpoint_lift_meters,
        args.arm_joint_speed,
    )
    if not np.isfinite(finite_values).all():
        parser.error("All numeric arguments must be finite")
    if args.arm_controller == "unified-wbc" and args.locomotion_policy != "wbc":
        parser.error("Unified WBC arm control requires the WBC locomotion policy")
    if args.wbc_hold_on_gate and args.arm_controller != "unified-wbc":
        parser.error("WBC holding requires unified WBC arm control")
    if args.wbc_base_hold and args.arm_controller != "unified-wbc":
        parser.error("WBC base holding requires unified WBC arm control")
    if (
        args.seed < 0
        or args.box_mass <= 0.0
        or args.path_samples < 2
        or min(args.static_box_size) <= 0.0
        or min(
            args.nav_front_standoff,
            args.nav_yaw_gain,
            args.box_max_displacement,
            args.box_max_linear_speed,
            args.box_max_angular_speed,
            args.push_approach_distance,
            args.initial_settle_seconds,
            args.post_nav_settle_seconds,
            args.motion_timeout_seconds,
            args.hold_seconds,
            args.required_joint_limit_margin,
            args.required_self_clearance,
            args.required_environment_clearance,
            args.required_support_margin,
            args.support_violation_grace_seconds,
            args.joint_tracking_tolerance,
            args.hand_tracking_tolerance,
            args.arm_velocity_tolerance,
            args.orientation_tracking_tolerance,
            args.wbc_command_ramp_seconds,
            args.wbc_hold_front_margin,
            args.wbc_hold_clearance_reserve,
            args.wbc_base_hold_position_gain,
            args.wbc_base_hold_yaw_gain,
            args.wbc_base_hold_max_linear_speed,
            args.wbc_base_hold_max_yaw_rate,
            args.wbc_hand_feedback_gain,
            args.wbc_hand_feedback_integral_gain,
            args.wbc_hand_feedback_gate_margin,
            args.wbc_hand_feedback_max_meters,
            args.wbc_orientation_feedback_integral_gain,
            args.wbc_orientation_feedback_max_radians,
            args.arm_joint_speed,
        )
        < 0.0
    ):
        parser.error("Sizes, durations, thresholds, and seed must be non-negative")
    torch.set_num_threads(1)
    result = run_episode(args)
    root = Path(__file__).resolve().parent
    source_paths = (
        Path(__file__),
        root / "check_piper_locomotion.py",
        root / "check_piper_navigation.py",
        root / "reconfigurable_navigation/box_push_runtime.py",
        root / "reconfigurable_navigation/piper_box_runtime.py",
        root / "reconfigurable_navigation/locomotion_runtime.py",
        root / "reconfigurable_navigation/reachability/oracle.py",
        root / "reconfigurable_navigation/reachability/schema.py",
        root / "reconfigurable_navigation/reachability/clearance.py",
        root / "reconfigurable_navigation/reachability/sweep.py",
        root / "reconfigurable_navigation/reachability/support.py",
        root / "reconfigurable_navigation/reachability/scenes.py",
        root / "reconfigurable_navigation/reachability/box_state.py",
        root / "reconfigurable_navigation/reachability/contact_geometry.py",
        root / "reconfigurable_navigation/reachability/contact_limits.py",
        CONTROL_PATH,
    )
    report = {
        "schema_version": 1,
        "arguments": {
            name: str(value) if isinstance(value, Path) else value
            for name, value in vars(args).items()
        },
        "source_sha256": {str(path): sha256(path) for path in source_paths},
        "result": result,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as destination:
        json.dump(report, destination, indent=2, allow_nan=False)
        destination.write("\n")
    print(json.dumps({"passed": result["passed"], "reason": result["reason"]}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
