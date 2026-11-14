"""Read-only PIPER arm clearance checks against the body and front legs."""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np


ARM_BODY_NAMES = frozenset(
    {"link1", "link2", "link3", "link4", "link5", "link6", "link7", "link8"}
)
PROTECTED_BODY_NAMES = frozenset(
    {
        "base_link",
        "FL_hip",
        "FL_thigh",
        "FL_calf",
        "FR_hip",
        "FR_thigh",
        "FR_calf",
    }
)


@dataclass(frozen=True)
class ClearanceResult:
    """Minimum distance over the configured PIPER self-clearance geometry pairs."""

    minimum_clearance: float
    required_clearance: float
    arm_body: str
    protected_body: str
    arm_geometry: str
    protected_geometry: str
    checked_pairs: int

    @property
    def safe(self) -> bool:
        return self.minimum_clearance >= self.required_clearance


@dataclass(frozen=True)
class FrozenConfigurationSafetyTube:
    """Conservative external-clearance bound under a base SE(2) error.

    The arm configuration and protected geometry snapshot are fixed. This is a
    collision-safety certificate only; it does not certify end-effector target
    tracking, re-solved IK, support, or contact-skill execution.
    """

    nominal_clearance: ClearanceResult
    base_pose_offset: np.ndarray
    external_geometry_error_bound: float
    maximum_arm_rotation_radius: float
    robot_motion_bound: float
    clearance_lower_bound: float

    def __post_init__(self) -> None:
        offset = np.asarray(self.base_pose_offset, dtype=np.float64)
        if offset.shape != (3,) or not np.isfinite(offset).all():
            raise ValueError("base_pose_offset must contain three finite values")
        object.__setattr__(self, "base_pose_offset", offset.copy())
        for name in (
            "external_geometry_error_bound",
            "maximum_arm_rotation_radius",
            "robot_motion_bound",
            "clearance_lower_bound",
        ):
            value = getattr(self, name)
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if (
            self.external_geometry_error_bound < 0.0
            or self.maximum_arm_rotation_radius < 0.0
            or self.robot_motion_bound < 0.0
        ):
            raise ValueError("safety-tube bounds must be non-negative")

    @property
    def safe(self) -> bool:
        return bool(
            self.nominal_clearance.minimum_clearance >= 0.0
            and self.clearance_lower_bound
            >= self.nominal_clearance.required_clearance
        )


class PiperArmClearanceChecker:
    """Evaluate arm clearance against named active geometry without stepping."""

    def __init__(
        self,
        runtime,
        *,
        protected_body_names: frozenset[str],
        arm_body_names: frozenset[str] = ARM_BODY_NAMES,
        data=None,
    ) -> None:
        self.runtime = runtime
        self.model = runtime.model
        self.data = runtime.data if data is None else data
        if not arm_body_names or not arm_body_names <= ARM_BODY_NAMES:
            raise ValueError("arm_body_names must be a non-empty subset of the PIPER arm")
        self.arm_qpos_adr = np.asarray(runtime.joint_qpos_adr[12:], dtype=int)
        arm_dof_adr = np.asarray(runtime.joint_dof_adr[12:], dtype=int)
        arm_joint_ids = self.model.dof_jntid[arm_dof_adr]
        self.arm_low = self.model.jnt_range[arm_joint_ids, 0].copy()
        self.arm_high = self.model.jnt_range[arm_joint_ids, 1].copy()
        self.base_qpos_adr = self._base_qpos_address()
        self.arm_geometries = self._geometry_ids(arm_body_names)
        self.protected_geometries = self._geometry_ids(protected_body_names)
        if not self.arm_geometries or not self.protected_geometries:
            raise ValueError("Missing PIPER arm or protected collision geometry")

    def evaluate(
        self,
        base_pose: np.ndarray,
        arm_joint_positions: np.ndarray,
        *,
        required_clearance: float,
    ) -> ClearanceResult:
        """Return the smallest active-geometry distance for one arm configuration."""
        base = self._vector(base_pose, "base_pose")
        arm = self._vector(arm_joint_positions, "arm_joint_positions")
        if required_clearance < 0.0 or not np.isfinite(required_clearance):
            raise ValueError("required_clearance must be finite and non-negative")
        if np.any(arm < self.arm_low) or np.any(arm > self.arm_high):
            raise ValueError("arm_joint_positions must satisfy joint limits")
        saved_qpos = self.data.qpos.copy()
        saved_qvel = self.data.qvel.copy()
        saved_ctrl = self.data.ctrl.copy()
        try:
            self._set_state(base, arm)
            result = self._minimum_clearance(required_clearance)
        finally:
            self.data.qpos[:] = saved_qpos
            self.data.qvel[:] = saved_qvel
            self.data.ctrl[:] = saved_ctrl
            mujoco.mj_forward(self.model, self.data)
        return result

    def evaluate_current_configuration(
        self, *, required_clearance: float
    ) -> ClearanceResult:
        """Return clearance for the current MuJoCo state without modifying it."""
        if required_clearance < 0.0 or not np.isfinite(required_clearance):
            raise ValueError("required_clearance must be finite and non-negative")
        return self._minimum_clearance(required_clearance)

    def certify_frozen_configuration_tube(
        self,
        base_pose: np.ndarray,
        arm_joint_positions: np.ndarray,
        *,
        base_pose_offset: np.ndarray,
        required_clearance: float,
        external_geometry_error_bound: float = 0.0,
    ) -> FrozenConfigurationSafetyTube:
        """Certify a clearance lower bound for a frozen arm and scene snapshot.

        Each point of an arm geometry moves no more than its translational base
        error plus ``2 * radius * sin(abs(yaw_error) / 2)``. Geometric distance
        is one-Lipschitz under this set displacement, so subtracting this motion
        and the external-geometry error yields a conservative clearance bound.
        """
        base = self._vector(base_pose, "base_pose")
        arm = self._vector(arm_joint_positions, "arm_joint_positions")
        offset = self._vector(base_pose_offset, "base_pose")
        if abs(offset[2]) > np.pi:
            raise ValueError("base_pose_offset yaw must be within [-pi, pi]")
        if required_clearance < 0.0 or not np.isfinite(required_clearance):
            raise ValueError("required_clearance must be finite and non-negative")
        if (
            external_geometry_error_bound < 0.0
            or not np.isfinite(external_geometry_error_bound)
        ):
            raise ValueError(
                "external_geometry_error_bound must be finite and non-negative"
            )
        if np.any(arm < self.arm_low) or np.any(arm > self.arm_high):
            raise ValueError("arm_joint_positions must satisfy joint limits")
        saved_qpos = self.data.qpos.copy()
        saved_qvel = self.data.qvel.copy()
        saved_ctrl = self.data.ctrl.copy()
        try:
            self._set_state(base, arm)
            nominal = self._minimum_clearance(required_clearance)
            maximum_radius = self._maximum_arm_rotation_radius()
        finally:
            self.data.qpos[:] = saved_qpos
            self.data.qvel[:] = saved_qvel
            self.data.ctrl[:] = saved_ctrl
            mujoco.mj_forward(self.model, self.data)
        translation_bound = float(np.linalg.norm(offset[:2]))
        yaw_bound = float(
            2.0 * maximum_radius * np.sin(abs(offset[2]) / 2.0)
        )
        motion_bound = translation_bound + yaw_bound + external_geometry_error_bound
        return FrozenConfigurationSafetyTube(
            nominal_clearance=nominal,
            base_pose_offset=offset,
            external_geometry_error_bound=external_geometry_error_bound,
            maximum_arm_rotation_radius=maximum_radius,
            robot_motion_bound=motion_bound,
            clearance_lower_bound=nominal.minimum_clearance - motion_bound,
        )

    def linear_path_sampling_motion_bound(
        self, start: np.ndarray, target: np.ndarray, *, samples: int
    ) -> float:
        """Bound arm-point displacement from the nearest uniform path sample.

        Only the six arm hinges may move; base, legs and protected geometry
        remain fixed. For origin-anchored hinges, sums of descendant body
        offsets plus the geometry bounding radius bound every joint's moment
        arm for all configurations. Integrating joint motion gives a global
        point-displacement bound sum(radius * abs(delta_angle)). Any point of
        the linear path lies within half a sample interval of a sampled state.
        Subtract this bound from the sampled minimum distance to bound the
        entire path's clearance. This does not bound a controller trajectory.
        """
        start = self._vector(start, "arm_joint_positions")
        target = self._vector(target, "arm_joint_positions")
        if not isinstance(samples, (int, np.integer)) or samples < 2:
            raise ValueError("samples must be an integer of at least two")
        if (
            np.any(start < self.arm_low) or np.any(start > self.arm_high)
            or np.any(target < self.arm_low) or np.any(target > self.arm_high)
        ):
            raise ValueError("Path endpoints must satisfy joint limits")
        joint_ids = self.model.dof_jntid[
            np.asarray(self.runtime.joint_dof_adr[12:], dtype=int)
        ]
        radii = np.zeros(6, dtype=np.float64)
        for index, joint_id in enumerate(joint_ids):
            joint_body = int(self.model.jnt_bodyid[joint_id])
            for geometry_id in self.protected_geometries:
                body = int(self.model.geom_bodyid[geometry_id])
                while body != 0 and body != joint_body:
                    body = int(self.model.body_parentid[body])
                if body == joint_body:
                    raise ValueError("Protected geometry must be independent of arm joints")
            for geometry_id in self.arm_geometries:
                radius = float(
                    np.linalg.norm(self.model.geom_pos[geometry_id])
                    + self.model.geom_rbound[geometry_id]
                )
                if not np.isfinite(radius) or self.model.geom_rbound[geometry_id] <= 0.0:
                    raise ValueError("Arm geometry needs a finite positive bounding radius")
                body = int(self.model.geom_bodyid[geometry_id])
                while body != 0:
                    first_joint = int(self.model.body_jntadr[body])
                    joint_count = int(self.model.body_jntnum[body])
                    for descendant_joint in range(first_joint, first_joint + joint_count):
                        if (
                            self.model.jnt_type[descendant_joint] != mujoco.mjtJoint.mjJNT_HINGE
                            or np.any(self.model.jnt_pos[descendant_joint] != 0.0)
                        ):
                            raise ValueError("Path bound requires origin-anchored arm hinges")
                    if body == joint_body:
                        radii[index] = max(radii[index], radius)
                        break
                    radius += float(np.linalg.norm(self.model.body_pos[body]))
                    body = int(self.model.body_parentid[body])
                    if body == self.model.body("Piper").id:
                        break
        return float(radii @ np.abs(target - start) / (2.0 * (samples - 1)))

    def _geometry_ids(self, body_names: frozenset[str]) -> tuple[int, ...]:
        return tuple(
            geometry_id
            for geometry_id in range(self.model.ngeom)
            if self.model.body(int(self.model.geom_bodyid[geometry_id])).name in body_names
            and (
                self.model.geom_contype[geometry_id]
                or self.model.geom_conaffinity[geometry_id]
            )
        )

    def _minimum_clearance(self, required_clearance: float) -> ClearanceResult:
        best_distance = float("inf")
        best_arm_geometry = -1
        best_protected_geometry = -1
        checked_pairs = 0
        for arm_geometry in self.arm_geometries:
            for protected_geometry in self.protected_geometries:
                distance = mujoco.mj_geomDistance(
                    self.model,
                    self.data,
                    arm_geometry,
                    protected_geometry,
                    float("inf"),
                    None,
                )
                checked_pairs += 1
                if distance < best_distance:
                    best_distance = float(distance)
                    best_arm_geometry = arm_geometry
                    best_protected_geometry = protected_geometry
        return ClearanceResult(
            minimum_clearance=best_distance,
            required_clearance=required_clearance,
            arm_body=self.model.body(int(self.model.geom_bodyid[best_arm_geometry])).name,
            protected_body=self.model.body(
                int(self.model.geom_bodyid[best_protected_geometry])
            ).name,
            arm_geometry=self.model.geom(best_arm_geometry).name or str(best_arm_geometry),
            protected_geometry=(
                self.model.geom(best_protected_geometry).name
                or str(best_protected_geometry)
            ),
            checked_pairs=checked_pairs,
        )

    def _maximum_arm_rotation_radius(self) -> float:
        base_position = self.data.qpos[self.base_qpos_adr : self.base_qpos_adr + 2]
        return max(
            float(
                np.linalg.norm(self.data.geom_xpos[geometry_id, :2] - base_position)
                + self.model.geom_rbound[geometry_id]
            )
            for geometry_id in self.arm_geometries
        )

    def _set_state(self, base_pose: np.ndarray, arm_joint_positions: np.ndarray) -> None:
        x_position, y_position, yaw = base_pose
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
            self.data.qpos[self.base_qpos_adr + 2],
        )
        self.data.qpos[self.base_qpos_adr + 3 : self.base_qpos_adr + 7] = target_quaternion
        self.data.qpos[self.arm_qpos_adr] = arm_joint_positions
        self.data.qvel.fill(0.0)
        mujoco.mj_forward(self.model, self.data)

    def _base_qpos_address(self) -> int:
        environment = getattr(self.runtime, "env", None)
        if environment is not None and hasattr(environment, "robot_qpos_adr"):
            return int(environment.robot_qpos_adr)
        base_body = self.model.body("base_link").id
        root_joint = int(self.model.body_jntadr[base_body])
        if root_joint < 0 or self.model.jnt_type[root_joint] != mujoco.mjtJoint.mjJNT_FREE:
            raise ValueError("PIPER base_link must have a free joint")
        return int(self.model.jnt_qposadr[root_joint])

    @staticmethod
    def _vector(value: np.ndarray, name: str) -> np.ndarray:
        vector = np.asarray(value, dtype=np.float64)
        if vector.shape != (3 if name == "base_pose" else 6,) or not np.isfinite(vector).all():
            raise ValueError(f"{name} must contain finite values with the expected shape")
        return vector.copy()


class PiperSelfClearanceChecker(PiperArmClearanceChecker):
    """Evaluate PIPER arm clearance to the body and front legs."""

    def __init__(self, runtime, *, data=None) -> None:
        super().__init__(runtime, protected_body_names=PROTECTED_BODY_NAMES, data=data)
