"""Deterministic fixed-base PIPER IK with optional end-effector orientation."""

from __future__ import annotations

import mujoco
import numpy as np

from .schema import ReachabilityQuery, ReachabilityResult


class PiperPositionReachabilityOracle:
    """Solve fixed-base PIPER position or pose IK without advancing simulation."""

    def __init__(
        self,
        runtime,
        *,
        tolerance: float = 1.0e-4,
        damping: float = 1.0e-2,
        max_joint_step: float = 0.08,
        max_iterations: int = 160,
        orientation_tolerance: float = 1.0e-3,
        orientation_weight: float = 0.2,
    ) -> None:
        if tolerance <= 0.0 or damping <= 0.0 or max_joint_step <= 0.0:
            raise ValueError("tolerance, damping, and max_joint_step must be positive")
        if max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        if not np.isfinite((orientation_tolerance, orientation_weight)).all() or min(orientation_tolerance, orientation_weight) <= 0.0:
            raise ValueError("Orientation tolerance and weight must be finite and positive")
        self.runtime = runtime
        self.model = runtime.model
        self.data = runtime.data
        self.tolerance = tolerance
        self.damping = damping
        self.max_joint_step = max_joint_step
        self.max_iterations = max_iterations
        self.orientation_tolerance = orientation_tolerance
        self.orientation_weight = orientation_weight
        self.arm_qpos_adr = np.asarray(runtime.joint_qpos_adr[12:], dtype=int)
        self.arm_dof_adr = np.asarray(runtime.joint_dof_adr[12:], dtype=int)
        arm_joint_ids = self.model.dof_jntid[self.arm_dof_adr]
        self.arm_low = self.model.jnt_range[arm_joint_ids, 0].copy()
        self.arm_high = self.model.jnt_range[arm_joint_ids, 1].copy()
        self.base_qpos_adr = self._base_qpos_address()
        self.end_effector_body = self.model.body("end_effector").id

    def end_effector_position(self, query: ReachabilityQuery) -> np.ndarray:
        """Return the nominal-arm world position for a fixed base query."""
        saved_qpos, saved_qvel, saved_ctrl = self._save_state()
        try:
            self._set_query_state(query, self.runtime.default_qpos[12:])
            return self.data.xpos[self.end_effector_body].copy()
        finally:
            self._restore_state(saved_qpos, saved_qvel, saved_ctrl)

    def end_effector_pose(
        self, query: ReachabilityQuery, arm_joint_positions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return the world-frame end-effector position and wxyz quaternion."""
        arm = np.asarray(arm_joint_positions, dtype=np.float64)
        if arm.shape != (6,) or not np.isfinite(arm).all():
            raise ValueError("arm_joint_positions must contain six finite values")
        if np.any(arm < self.arm_low) or np.any(arm > self.arm_high):
            raise ValueError("arm_joint_positions must satisfy joint limits")
        saved_qpos, saved_qvel, saved_ctrl = self._save_state()
        try:
            self._set_query_state(query, arm)
            return (
                self.data.xpos[self.end_effector_body].copy(),
                self.data.xquat[self.end_effector_body].copy(),
            )
        finally:
            self._restore_state(saved_qpos, saved_qvel, saved_ctrl)

    def hand_position(
        self, query: ReachabilityQuery, arm_joint_positions: np.ndarray,
        *, body_name: str = "link6", offset: tuple[float, float, float] = (0.15, 0.0, 0.0),
    ) -> np.ndarray:
        """Return a selected body point; defaults preserve the legacy link6 proxy."""
        saved_qpos, saved_qvel, saved_ctrl = self._save_state()
        try:
            self._set_query_state(query, arm_joint_positions)
            body = self.model.body(body_name).id
            return self.data.xpos[body].copy() + self.data.xmat[body].reshape(3, 3) @ np.asarray(offset)
        finally:
            self._restore_state(saved_qpos, saved_qvel, saved_ctrl)

    def solve(
        self, query: ReachabilityQuery, *, initial_joint_positions: np.ndarray | None = None,
        hand_offset: tuple[float, float, float] | None = None,
        target_quaternion: np.ndarray | None = None,
    ) -> ReachabilityResult:
        """Solve position IK, optionally including an end-effector world orientation."""
        if target_quaternion is not None:
            target_quaternion = np.asarray(target_quaternion, dtype=np.float64)
            if (
                target_quaternion.shape != (4,) or not np.isfinite(target_quaternion).all()
                or not np.isclose(np.linalg.norm(target_quaternion), 1.0, rtol=0.0, atol=1e-10)
            ):
                raise ValueError("target_quaternion must be a normalized finite quaternion")
            if hand_offset is not None:
                raise ValueError("Pose IK requires the end_effector reference without a legacy offset")
        if hand_offset is not None and (
            np.asarray(hand_offset).shape != (3,) or not np.isfinite(hand_offset).all()
        ):
            raise ValueError("hand_offset must contain three finite values")
        hand_body = self.model.body("link6").id if hand_offset is not None else None
        initial = self.runtime.default_qpos[12:] if initial_joint_positions is None else np.asarray(
            initial_joint_positions, dtype=np.float64
        )
        if initial.shape != (6,) or not np.isfinite(initial).all():
            raise ValueError("initial_joint_positions must contain six finite values")
        if np.any(initial < self.arm_low) or np.any(initial > self.arm_high):
            raise ValueError("initial_joint_positions must satisfy joint limits")
        saved_qpos, saved_qvel, saved_ctrl = self._save_state()
        try:
            self._set_query_state(query, initial)
            solution = self.data.qpos[self.arm_qpos_adr].copy()
            error_norm = float("inf")
            orientation_error = None
            for iteration in range(self.max_iterations + 1):
                position = self.data.xpos[self.end_effector_body] if hand_body is None else (
                    self.data.xpos[hand_body]
                    + self.data.xmat[hand_body].reshape(3, 3) @ np.asarray(hand_offset)
                )
                error = query.target_position - position
                error_norm = float(np.linalg.norm(error))
                angular_error = None
                if target_quaternion is not None:
                    inverse_actual = self.data.xquat[self.end_effector_body].copy()
                    inverse_actual[1:] *= -1.0
                    difference = np.empty(4)
                    mujoco.mju_mulQuat(difference, target_quaternion, inverse_actual)
                    if difference[0] < 0.0:
                        difference *= -1.0
                    angular_error = np.empty(3)
                    mujoco.mju_quat2Vel(angular_error, difference, 1.0)
                    orientation_error = float(np.linalg.norm(angular_error))
                if error_norm <= self.tolerance and (
                    orientation_error is None or orientation_error <= self.orientation_tolerance
                ):
                    return ReachabilityResult(
                        kinematic_feasible=True,
                        joint_solution=solution,
                        position_error=error_norm,
                        iterations=iteration,
                        failure_reason=None,
                        joint_limit_margin=self._joint_limit_margin(solution),
                        orientation_error=orientation_error,
                    )
                if iteration == self.max_iterations:
                    break
                jacobian = np.zeros((3, self.model.nv))
                angular_jacobian = np.zeros_like(jacobian) if target_quaternion is not None else None
                if hand_body is None:
                    mujoco.mj_jacBody(
                        self.model, self.data, jacobian, angular_jacobian, self.end_effector_body,
                    )
                else:
                    mujoco.mj_jac(
                        self.model, self.data, jacobian, None, position, hand_body,
                    )
                arm_jacobian = jacobian[:, self.arm_dof_adr]
                if angular_jacobian is not None:
                    arm_jacobian = np.vstack((
                        arm_jacobian, self.orientation_weight * angular_jacobian[:, self.arm_dof_adr]
                    ))
                    error = np.concatenate((error, self.orientation_weight * angular_error))
                step = arm_jacobian.T @ np.linalg.solve(
                    arm_jacobian @ arm_jacobian.T
                    + self.damping**2 * np.eye(len(error)),
                    error,
                )
                step = np.clip(step, -self.max_joint_step, self.max_joint_step)
                candidate = np.clip(solution + step, self.arm_low, self.arm_high)
                if np.array_equal(candidate, solution):
                    break
                solution = candidate
                self.data.qpos[self.arm_qpos_adr] = solution
                self.data.qvel.fill(0.0)
                mujoco.mj_forward(self.model, self.data)
            return ReachabilityResult(
                kinematic_feasible=False,
                joint_solution=solution,
                position_error=error_norm,
                iterations=self.max_iterations,
                failure_reason="pose_ik_unreachable" if target_quaternion is not None else "position_ik_unreachable",
                joint_limit_margin=self._joint_limit_margin(solution),
                orientation_error=orientation_error,
            )
        finally:
            self._restore_state(saved_qpos, saved_qvel, saved_ctrl)

    def _set_query_state(
        self, query: ReachabilityQuery, arm_joint_positions: np.ndarray
    ) -> None:
        x_position, y_position, yaw = query.base_pose
        settled_quaternion = self.data.qpos[
            self.base_qpos_adr + 3 : self.base_qpos_adr + 7
        ].copy()
        settled_rotation = np.empty(9, dtype=np.float64)
        mujoco.mju_quat2Mat(settled_rotation, settled_quaternion)
        settled_rotation = settled_rotation.reshape(3, 3)
        settled_yaw = float(np.arctan2(settled_rotation[1, 0], settled_rotation[0, 0]))
        yaw_delta = yaw - settled_yaw
        yaw_quaternion = np.array(
            [np.cos(yaw_delta / 2.0), 0.0, 0.0, np.sin(yaw_delta / 2.0)],
            dtype=np.float64,
        )
        target_quaternion = np.empty(4, dtype=np.float64)
        mujoco.mju_mulQuat(target_quaternion, yaw_quaternion, settled_quaternion)
        self.data.qpos[self.base_qpos_adr : self.base_qpos_adr + 3] = (
            x_position,
            y_position,
            self.runtime.data.qpos[self.base_qpos_adr + 2],
        )
        self.data.qpos[self.base_qpos_adr + 3 : self.base_qpos_adr + 7] = target_quaternion
        self.data.qpos[self.arm_qpos_adr] = np.clip(
            arm_joint_positions,
            self.arm_low,
            self.arm_high,
        )
        self.data.qvel.fill(0.0)
        mujoco.mj_forward(self.model, self.data)

    def _save_state(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.data.qpos.copy(), self.data.qvel.copy(), self.data.ctrl.copy()

    def _joint_limit_margin(self, solution: np.ndarray) -> float:
        return float(np.min(np.minimum(solution - self.arm_low, self.arm_high - solution)))

    def _base_qpos_address(self) -> int:
        environment = getattr(self.runtime, "env", None)
        if environment is not None and hasattr(environment, "robot_qpos_adr"):
            return int(environment.robot_qpos_adr)
        base_body = self.model.body("base_link").id
        root_joint = int(self.model.body_jntadr[base_body])
        if root_joint < 0 or self.model.jnt_type[root_joint] != mujoco.mjtJoint.mjJNT_FREE:
            raise ValueError("PIPER base_link must have a free joint")
        return int(self.model.jnt_qposadr[root_joint])

    def _restore_state(
        self,
        qpos: np.ndarray,
        qvel: np.ndarray,
        ctrl: np.ndarray,
    ) -> None:
        self.data.qpos[:] = qpos
        self.data.qvel[:] = qvel
        self.data.ctrl[:] = ctrl
        mujoco.mj_forward(self.model, self.data)
