"""Clearance bounds for interpolated PIPER configurations, not physical ODEs."""

from __future__ import annotations

import mujoco
import numpy as np


class PiperConfigurationSweep:
    """Bound selected-pair motion along joint-linear and base-SLERP segments."""

    def __init__(self, checker, *, moving_body_names: frozenset[str] = frozenset()) -> None:
        self.model = checker.model
        self.base_address = checker.base_qpos_adr
        self.joint_addresses = np.asarray(checker.runtime.joint_qpos_adr, dtype=int)
        self.joint_ids = self.model.dof_jntid[
            np.asarray(checker.runtime.joint_dof_adr, dtype=int)
        ]
        self.joint_indices = {
            int(joint_id): index for index, joint_id in enumerate(self.joint_ids)
        }
        self.base_body = self.model.body("base_link").id
        self.free_body_addresses = {}
        for name in sorted(moving_body_names):
            body = self.model.body(name).id
            joint = int(self.model.body_jntadr[body])
            if (
                body == self.base_body or self.model.body_parentid[body] != 0
                or self.model.body_jntnum[body] != 1
                or self.model.jnt_type[joint] != mujoco.mjtJoint.mjJNT_FREE
            ):
                raise ValueError("Moving scene bodies must be independent free rigid bodies")
            self.free_body_addresses[body] = int(self.model.jnt_qposadr[joint])
        self.free_body_radii = {body: 0.0 for body in self.free_body_addresses}
        self.free_body_translation_factors = {body: 0 for body in self.free_body_addresses}
        self.joint_radii = np.zeros(len(self.joint_ids))
        self.base_radius = 0.0
        self.base_translation_factor = 0
        for geometries in (checker.arm_geometries, checker.protected_geometries):
            bounds = [self._geometry_bounds(geometry) for geometry in geometries]
            self.joint_radii += np.max([bound[0] for bound in bounds], axis=0)
            self.base_radius += max(bound[1] for bound in bounds)
            self.base_translation_factor += int(any(bound[2] for bound in bounds))
            for body in self.free_body_addresses:
                self.free_body_radii[body] += max(bound[3].get(body, 0.0) for bound in bounds)
                self.free_body_translation_factors[body] += int(any(body in bound[3] for bound in bounds))
        self.other_qpos = np.ones(self.model.nq, dtype=bool)
        self.other_qpos[self.joint_addresses] = False
        self.other_qpos[self.base_address : self.base_address + 7] = False
        for address in self.free_body_addresses.values():
            self.other_qpos[address : address + 7] = False

    def _geometry_bounds(self, geometry: int) -> tuple[np.ndarray, float, bool, dict[int, float]]:
        radius = float(
            np.linalg.norm(self.model.geom_pos[geometry])
            + self.model.geom_rbound[geometry]
        )
        if not np.isfinite(radius) or self.model.geom_rbound[geometry] <= 0.0:
            raise ValueError("Sweep geometry requires a finite positive bounding radius")
        joint_radii = np.zeros(len(self.joint_ids))
        body = int(self.model.geom_bodyid[geometry])
        while body != 0:
            if self.model.body_mocapid[body] >= 0:
                raise ValueError("Sweeps do not support mocap geometry")
            if body == self.base_body:
                return joint_radii, radius, True, {}
            if body in self.free_body_addresses:
                return joint_radii, 0.0, False, {body: radius}
            first_joint = int(self.model.body_jntadr[body])
            count = int(self.model.body_jntnum[body])
            for joint in range(first_joint, first_joint + count):
                if (
                    joint not in self.joint_indices
                    or self.model.jnt_type[joint] != mujoco.mjtJoint.mjJNT_HINGE
                    or np.any(self.model.jnt_pos[joint] != 0.0)
                ):
                    raise ValueError("Sweeps require robot hinges or explicitly allowed free scene bodies")
                joint_radii[self.joint_indices[joint]] = radius
            radius += float(np.linalg.norm(self.model.body_pos[body]))
            body = int(self.model.body_parentid[body])
        return joint_radii, 0.0, False, {}

    def nearest_endpoint_motion_bound(self, start: np.ndarray, target: np.ndarray) -> float:
        """Bound pair-distance loss relative to the nearest segment endpoint.

        Triangle inequalities bound each geometry's point speed by joint
        radius times angular speed, plus base translation and rotation. The
        two selected geometry groups' bounds add; half a segment reaches the
        nearer endpoint. Explicitly allowed free scene bodies contribute their
        own translation and rotation bounds. All other coordinates must be
        fixed. Free-body rotations follow the shorter quaternion arcs.
        """
        start = np.asarray(start, dtype=np.float64)
        target = np.asarray(target, dtype=np.float64)
        if (
            start.shape != (self.model.nq,) or target.shape != start.shape
            or not np.isfinite(start).all() or not np.isfinite(target).all()
        ):
            raise ValueError("Sweep endpoints must be finite full qpos vectors")
        if not np.array_equal(start[self.other_qpos], target[self.other_qpos]):
            raise ValueError("Unmodeled coordinates must remain fixed")
        address = self.base_address
        start_quaternion = start[address + 3 : address + 7]
        target_quaternion = target[address + 3 : address + 7]
        if not all(
            np.isclose(np.linalg.norm(quaternion), 1.0, rtol=0.0, atol=1.0e-10)
            for quaternion in (start_quaternion, target_quaternion)
        ):
            raise ValueError("Base quaternions must be normalized")
        rotation_vector = np.empty(3)
        mujoco.mju_subQuat(rotation_vector, target_quaternion, start_quaternion)
        rotation_angle = float(np.linalg.norm(rotation_vector))
        translation = float(np.linalg.norm(target[address : address + 3] - start[address : address + 3]))
        joint_change = np.abs(target[self.joint_addresses] - start[self.joint_addresses])
        motion = (
            self.joint_radii @ joint_change
            + self.base_translation_factor * translation
            + self.base_radius * rotation_angle
        )
        for body, address in self.free_body_addresses.items():
            first = start[address + 3 : address + 7]
            last = target[address + 3 : address + 7]
            if not all(np.isclose(np.linalg.norm(value), 1.0, rtol=0.0, atol=1e-10) for value in (first, last)):
                raise ValueError("Scene body quaternions must be normalized")
            rotation = np.empty(3)
            mujoco.mju_subQuat(rotation, last, first)
            displacement = float(np.linalg.norm(target[address : address + 3] - start[address : address + 3]))
            motion += (
                self.free_body_translation_factors[body] * displacement
                + self.free_body_radii[body] * float(np.linalg.norm(rotation))
            )
        return float(motion / 2.0 + 1.0e-9)