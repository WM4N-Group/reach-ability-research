"""Observed box state, precontact snapshot validity, and contact-region labels."""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np

from .scenes import STATIC_BOX_GEOMETRY


def _vector(value, length: int) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (length,) or not np.isfinite(result).all():
        raise ValueError(f"Expected {length} finite values")
    return result.copy()


@dataclass(frozen=True)
class BoxState:
    time: float
    position: np.ndarray
    quaternion: np.ndarray
    linear_velocity: np.ndarray
    angular_velocity: np.ndarray

    def __post_init__(self) -> None:
        if not np.isfinite(self.time):
            raise ValueError("Box state time must be finite")
        for name, length in (
            ("position", 3), ("quaternion", 4),
            ("linear_velocity", 3), ("angular_velocity", 3),
        ):
            object.__setattr__(self, name, _vector(getattr(self, name), length))
        if not np.isclose(np.linalg.norm(self.quaternion), 1.0, rtol=0.0, atol=1e-10):
            raise ValueError("Box quaternion must be normalized")

    @property
    def rotation(self) -> np.ndarray:
        rotation = np.empty(9)
        mujoco.mju_quat2Mat(rotation, self.quaternion)
        return rotation.reshape(3, 3)

    def point_local(self, world_position: np.ndarray) -> np.ndarray:
        return self.rotation.T @ (_vector(world_position, 3) - self.position)

    def point_world(self, local_position: np.ndarray) -> np.ndarray:
        return self.position + self.rotation @ _vector(local_position, 3)

    def as_dict(self) -> dict[str, object]:
        return {
            "time": float(self.time), "position": self.position.tolist(),
            "quaternion": self.quaternion.tolist(),
            "linear_velocity_world": self.linear_velocity.tolist(),
            "angular_velocity_world": self.angular_velocity.tolist(),
        }


class BoxStateReader:
    """Read post-integration geometry without changing the policy's data cache."""

    def __init__(self, runtime, *, geometry_name: str = STATIC_BOX_GEOMETRY) -> None:
        self.runtime = runtime
        self.model = runtime.model
        self.geometry = self.model.geom(geometry_name).id
        if self.model.geom_type[self.geometry] != mujoco.mjtGeom.mjGEOM_BOX:
            raise ValueError("Box state reader requires box geometry")
        self.data = mujoco.MjData(self.model)
        self.size = 2.0 * self.model.geom_size[self.geometry].copy()
        self.radius = float(self.model.geom_rbound[self.geometry])

    def read(self) -> BoxState:
        self.data.qpos[:] = self.runtime.data.qpos
        self.data.qvel[:] = self.runtime.data.qvel
        self.data.mocap_pos[:] = self.runtime.data.mocap_pos
        self.data.mocap_quat[:] = self.runtime.data.mocap_quat
        self.data.time = self.runtime.data.time
        mujoco.mj_kinematics(self.model, self.data)
        mujoco.mj_comPos(self.model, self.data)
        mujoco.mj_comVel(self.model, self.data)
        velocity = np.empty(6)
        mujoco.mj_objectVelocity(
            self.model, self.data, mujoco.mjtObj.mjOBJ_GEOM, self.geometry, velocity, 0
        )
        quaternion = np.empty(4)
        mujoco.mju_mat2Quat(quaternion, self.data.geom_xmat[self.geometry])
        return BoxState(
            float(self.data.time), self.data.geom_xpos[self.geometry], quaternion,
            velocity[3:], velocity[:3],
        )


class BoxSnapshotGuard:
    """Reject a stale target snapshot; this does not track or stop a moving box."""

    def __init__(
        self, reference: BoxState, *, geometry_radius: float,
        maximum_displacement: float = 0.001,
        maximum_linear_speed: float = 0.005,
        maximum_angular_speed: float = 0.02,
    ) -> None:
        values = (geometry_radius, maximum_displacement, maximum_linear_speed, maximum_angular_speed)
        if not np.isfinite(values).all() or min(values) < 0.0 or geometry_radius <= 0.0:
            raise ValueError("Box validity bounds must be finite and non-negative; radius must be positive")
        self.reference = reference
        self.radius = geometry_radius
        self.maximum_displacement = maximum_displacement
        self.maximum_linear_speed = maximum_linear_speed
        self.maximum_angular_speed = maximum_angular_speed

    def evaluate(self, current: BoxState) -> dict[str, object]:
        rotation = np.empty(3)
        mujoco.mju_subQuat(rotation, current.quaternion, self.reference.quaternion)
        angle = float(np.linalg.norm(rotation))
        translation = float(np.linalg.norm(current.position - self.reference.position))
        displacement = float(translation + 2.0 * self.radius * np.sin(angle / 2.0))
        linear_speed = float(np.linalg.norm(current.linear_velocity))
        angular_speed = float(np.linalg.norm(current.angular_velocity))
        return {
            "valid": bool(
                current.time >= self.reference.time
                and displacement <= self.maximum_displacement
                and linear_speed <= self.maximum_linear_speed
                and angular_speed <= self.maximum_angular_speed
            ),
            "translation": translation, "rotation_angle": angle,
            "geometry_displacement_bound": displacement,
            "linear_speed": linear_speed, "angular_speed": angular_speed,
            "maximum_displacement": self.maximum_displacement,
            "maximum_linear_speed": self.maximum_linear_speed,
            "maximum_angular_speed": self.maximum_angular_speed,
        }


class BoxFrontContactRegion:
    """Label fingertip contacts on the front-face interior, without permitting contact."""

    def __init__(
        self, size: np.ndarray, *, edge_fraction: float = 0.1,
        surface_tolerance: float = 0.005,
        hand_bodies: frozenset[str] = frozenset({"link7", "link8"}),
    ) -> None:
        self.size = _vector(size, 3)
        if (
            np.any(self.size <= 0.0)
            or not np.isfinite((edge_fraction, surface_tolerance)).all()
            or not 0.0 <= edge_fraction < 1.0 or surface_tolerance < 0.0
        ):
            raise ValueError("Contact region sizes and tolerances must be valid")
        self.edge_fraction = edge_fraction
        self.surface_tolerance = surface_tolerance
        self.hand_bodies = frozenset(hand_bodies)

    def contains(self, state: BoxState, world_position: np.ndarray, body_name: str) -> bool:
        return self.contains_local(state.point_local(world_position), body_name)

    def contains_local(self, local_position: np.ndarray, body_name: str) -> bool:
        local = _vector(local_position, 3)
        return bool(
            body_name in self.hand_bodies
            and abs(local[0] + self.size[0] / 2.0) <= self.surface_tolerance
            and np.all(np.abs(local[1:]) <= self.size[1:] / 2.0 * (1.0 - self.edge_fraction))
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "face": "negative_x", "size": self.size.tolist(),
            "edge_fraction": self.edge_fraction, "surface_tolerance": self.surface_tolerance,
            "hand_bodies": sorted(self.hand_bodies),
            "contact_enabled": False,
        }