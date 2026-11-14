"""Read physical PIPER finger geometry without granting contact permission."""

from __future__ import annotations

import mujoco
import numpy as np

from .box_state import BoxFrontContactRegion, BoxStateReader
from .contact_limits import ContactHandoffGuard, ContactLimitMonitor


NATIVE_PUSH_HAND_PITCH = 0.8
NATIVE_PUSH_APPROACH_DISTANCE = 0.03


def native_push_orientation(box_quaternion: np.ndarray) -> np.ndarray:
    desired = np.empty(4)
    mujoco.mju_mulQuat(
        desired, box_quaternion,
        np.array([np.cos(NATIVE_PUSH_HAND_PITCH / 2.0), 0.0, np.sin(NATIVE_PUSH_HAND_PITCH / 2.0), 0.0]),
    )
    return desired


def read_box_contact_sample(runtime, contact, wrench, *, box_geometry: int, region: BoxFrontContactRegion):
    """Measure force on the box and relative point velocity in the contact-generation frame."""
    model, data = runtime.model, runtime.data
    if box_geometry not in (contact.geom1, contact.geom2):
        raise ValueError("Contact must include the box geometry")
    other = contact.geom2 if contact.geom1 == box_geometry else contact.geom1
    body = model.body(int(model.geom_bodyid[other])).name
    wrench = np.asarray(wrench, dtype=np.float64)
    if wrench.shape != (6,) or not np.isfinite(wrench).all():
        return {"measurement_valid": False, "body": body, "reason": "invalid_contact_wrench"}
    rotation = data.geom_xmat[box_geometry].reshape(3, 3)
    force_world = contact.frame.reshape(3, 3).T @ wrench[:3]
    if contact.geom1 == box_geometry:
        force_world *= -1.0
    force_box = rotation.T @ force_world
    local_point = rotation.T @ (contact.pos - data.geom_xpos[box_geometry])
    velocities = []
    for geometry in (other, box_geometry):
        velocity = np.zeros(6)
        mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_GEOM, geometry, velocity, 0)
        velocities.append(velocity[3:] + np.cross(velocity[:3], contact.pos - data.geom_xpos[geometry]))
    relative = rotation.T @ (velocities[0] - velocities[1])
    end_effector = model.body("end_effector").id
    box_quaternion = np.empty(4)
    mujoco.mju_mat2Quat(box_quaternion, data.geom_xmat[box_geometry])
    desired = native_push_orientation(box_quaternion)
    orientation_error = float(2.0 * np.arccos(np.clip(abs(float(desired @ data.xquat[end_effector])), 0.0, 1.0)))
    sample = {
        "measurement_valid": True, "body": body,
        "frame": "contact_generation_cache", "force_on": "box",
        "force_box_frame": force_box.tolist(), "position_box_frame": local_point.tolist(),
        "normal_force": float(force_box[0]),
        "tangential_force": float(np.linalg.norm(force_box[1:])),
        "normal_speed": float(relative[0]),
        "tangential_speed": float(np.linalg.norm(relative[1:])),
        "tip_distance": float(np.linalg.norm(contact.pos - data.xpos[end_effector])),
        "orientation_error": orientation_error,
        "region_matched": region.contains_local(local_point, body),
    }
    if not np.isfinite([sample[name] for name in (
        "normal_force", "tangential_force", "normal_speed", "tangential_speed", "tip_distance", "orientation_error"
    )]).all():
        return {"measurement_valid": False, "body": body, "reason": "nonfinite_contact_measurement"}
    return sample


class PiperContactGeometryReader:
    """Compare the legacy proxy with measured collision geometry and motion."""

    def __init__(self, runtime, *, proxy_offset=(0.15, 0.0, 0.0)) -> None:
        self.runtime = runtime
        self.model = runtime.model
        self.box_reader = BoxStateReader(runtime)
        self.region = BoxFrontContactRegion(self.box_reader.size)
        self.wrist = self.model.body("link6").id
        self.end_effector = self.model.body("end_effector").id
        self.proxy_offset = np.asarray(proxy_offset, dtype=np.float64)
        if self.proxy_offset.shape != (3,) or not np.isfinite(self.proxy_offset).all():
            raise ValueError("Proxy offset must contain three finite values")
        self.proxy_offset = self.proxy_offset.copy()
        self.finger_geometries = tuple(
            geometry for geometry in range(self.model.ngeom)
            if self.model.body(int(self.model.geom_bodyid[geometry])).name in self.region.hand_bodies
            and (self.model.geom_contype[geometry] or self.model.geom_conaffinity[geometry])
        )
        if not self.finger_geometries:
            raise ValueError("Missing active finger collision geometry")

    @staticmethod
    def _angle(first: np.ndarray, second: np.ndarray) -> float:
        return float(np.arccos(np.clip(float(first @ second), -1.0, 1.0)))

    def read(
        self, *, limit_monitor: ContactLimitMonitor | None = None,
        handoff_guard: ContactHandoffGuard | None = None,
        snapshot_valid: bool = False, support_valid: bool = False,
        nonhand_clearance_valid: bool = False,
        native_orientation_valid: bool = False,
    ) -> dict[str, object]:
        box = self.box_reader.read()
        data = self.box_reader.data
        wrist_rotation = data.xmat[self.wrist].reshape(3, 3)
        end_rotation = data.xmat[self.end_effector].reshape(3, 3)
        proxy_world = data.xpos[self.wrist] + wrist_rotation @ self.proxy_offset
        end_world = data.xpos[self.end_effector].copy()
        inward = box.rotation[:, 0]
        desired_orientation = native_push_orientation(box.quaternion)
        actual_orientation = data.xquat[self.end_effector].copy()
        orientation_error = float(2.0 * np.arccos(np.clip(abs(float(
            desired_orientation @ actual_orientation
        )), 0.0, 1.0)))
        fingers = []
        for geometry in self.finger_geometries:
            witnesses = np.zeros(6)
            distance = float(mujoco.mj_geomDistance(
                self.model, data, geometry, self.box_reader.geometry, float("inf"), witnesses
            ))
            separated = bool(distance > 1e-8 and np.isfinite(distance) and np.isfinite(witnesses).all())
            body_name = self.model.body(int(self.model.geom_bodyid[geometry])).name
            row = {
                "body": body_name, "geometry_id": geometry,
                "clearance": distance,
                "center_world": data.geom_xpos[geometry].tolist(),
                "separated_witnesses_valid": separated,
            }
            if separated:
                finger_point, box_point = witnesses[:3], witnesses[3:]
                velocity = np.empty(6)
                mujoco.mj_objectVelocity(
                    self.model, data, mujoco.mjtObj.mjOBJ_GEOM, geometry, velocity, 0
                )
                finger_velocity = velocity[3:] + np.cross(
                    velocity[:3], finger_point - data.geom_xpos[geometry]
                )
                box_velocity = box.linear_velocity + np.cross(
                    box.angular_velocity, box_point - box.position
                )
                relative_velocity = finger_velocity - box_velocity
                closing_speed = float(relative_velocity @ inward)
                separation = box_point - finger_point
                separation /= np.linalg.norm(separation)
                row.update(
                    finger_point_world=finger_point.tolist(),
                    finger_point_box_frame=box.point_local(finger_point).tolist(),
                    box_point_world=box_point.tolist(),
                    box_point_box_frame=box.point_local(box_point).tolist(),
                    box_point_in_front_region=self.region.contains(box, box_point, body_name),
                    separation_to_inward_angle=self._angle(separation, inward),
                    closing_speed=closing_speed,
                    tangential_speed=float(np.linalg.norm(relative_velocity - closing_speed * inward)),
                )
            fingers.append(row)
        contacts = []
        floor = self.model.geom("floor").id
        for index, contact in enumerate(self.runtime.data.contact):
            if self.box_reader.geometry not in (contact.geom1, contact.geom2) or contact.dist > 0.0:
                continue
            other = contact.geom2 if contact.geom1 == self.box_reader.geometry else contact.geom1
            if other == floor:
                continue
            wrench = np.zeros(6)
            mujoco.mj_contactForce(self.model, self.runtime.data, index, wrench)
            contacts.append(read_box_contact_sample(
                self.runtime, contact, wrench, box_geometry=self.box_reader.geometry, region=self.region
            ))
        limits_result = (
            limit_monitor.observe(
                contacts, time=float(self.runtime.data.time), snapshot_valid=snapshot_valid,
                support_valid=support_valid, nonhand_clearance_valid=nonhand_clearance_valid,
            )
            if limit_monitor is not None else None
        )
        designated_face_ready = bool(fingers) and all(
            row["separated_witnesses_valid"]
            and row.get("box_point_in_front_region", False)
            for row in fingers
        )
        handoff_result = (
            handoff_guard.check_precontact(
                time=float(box.time), snapshot_valid=snapshot_valid,
                support_valid=support_valid,
                nonhand_clearance_valid=nonhand_clearance_valid,
                designated_face_ready=designated_face_ready,
                native_orientation_valid=native_orientation_valid,
                contact_free=not contacts,
            )
            if handoff_guard is not None else None
        )
        return {
            "scope": "Physical finger collision geometry only; not contact execution or a force certificate",
            "time": box.time,
            "box_state": box.as_dict(),
            "proxy_offset_in_link6": self.proxy_offset.tolist(),
            "proxy_world": proxy_world.tolist(),
            "proxy_box_frame": box.point_local(proxy_world).tolist(),
            "end_effector_world": end_world.tolist(),
            "end_effector_quaternion_world": actual_orientation.tolist(),
            "native_push_orientation_world": desired_orientation.tolist(),
            "native_push_orientation_error": orientation_error,
            "native_push_approach_distance": NATIVE_PUSH_APPROACH_DISTANCE,
            "end_effector_box_frame": box.point_local(end_world).tolist(),
            "proxy_to_end_effector_distance": float(np.linalg.norm(proxy_world - end_world)),
            "wrist_x_to_box_inward_angle": self._angle(wrist_rotation[:, 0], inward),
            "wrist_z_to_box_inward_angle": self._angle(wrist_rotation[:, 2], inward),
            "end_effector_x_to_box_inward_angle": self._angle(end_rotation[:, 0], inward),
            "minimum_finger_clearance": min(row["clearance"] for row in fingers),
            "fingers": fingers,
            "contact_samples": contacts,
            "contact_limits_status": "not_configured" if limits_result is None else limits_result["state"],
            "contact_limits_assessment": limits_result,
            "contact_handoff": handoff_result,
            "contact_region": self.region.as_dict(),
            "contact_execution_enabled": False,
        }