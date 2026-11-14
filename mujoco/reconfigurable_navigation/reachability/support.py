"""Read-only quasi-static support checks from PIPER foot-ground contacts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import mujoco


DEFAULT_FOOT_GEOMETRY_NAMES = ("FL", "FR", "RL", "RR")


@dataclass(frozen=True)
class QuasiStaticSupportResult:
    """Planar support-polygon margin for the current settled physical state.

    A positive margin means the robot center of mass projects inside the convex
    hull of active foot-ground contacts. It is not a dynamic-stability proof and
    does not validate contact-force feasibility or locomotion-policy behavior.
    """

    supporting_feet: tuple[str, ...]
    support_points: np.ndarray
    center_of_mass_xy: np.ndarray
    support_margin: float | None
    required_margin: float

    def __post_init__(self) -> None:
        points = np.asarray(self.support_points, dtype=np.float64)
        center = np.asarray(self.center_of_mass_xy, dtype=np.float64)
        if points.ndim != 2 or points.shape[1:] != (2,) or not np.isfinite(points).all():
            raise ValueError("support_points must have shape (N, 2) with finite values")
        if center.shape != (2,) or not np.isfinite(center).all():
            raise ValueError("center_of_mass_xy must contain two finite values")
        if self.required_margin < 0.0 or not np.isfinite(self.required_margin):
            raise ValueError("required_margin must be finite and non-negative")
        if self.support_margin is not None and not np.isfinite(self.support_margin):
            raise ValueError("support_margin must be finite when present")
        object.__setattr__(self, "support_points", points.copy())
        object.__setattr__(self, "center_of_mass_xy", center.copy())

    @property
    def safe(self) -> bool:
        return bool(
            len(self.supporting_feet) >= 3
            and self.support_margin is not None
            and self.support_margin >= self.required_margin
        )


@dataclass(frozen=True)
class FixedContactSupportRegion:
    """Support margin bound conditional on retaining the same ground contacts."""

    nominal_support: QuasiStaticSupportResult
    contact_point_error_radius: float
    center_of_mass_error_radius: float
    margin_lower_bound: float | None

    @property
    def conditional_support_safe(self) -> bool:
        return bool(
            self.margin_lower_bound is not None
            and self.margin_lower_bound >= self.nominal_support.required_margin
        )


@dataclass(frozen=True)
class RelativeContactSupportRegion:
    """Bound using correlated foot-to-COM errors under a fixed contact set."""

    nominal_support: QuasiStaticSupportResult
    relative_contact_point_error_radius: float
    margin_lower_bound: float | None

    @property
    def conditional_support_safe(self) -> bool:
        return bool(
            self.margin_lower_bound is not None
            and self.margin_lower_bound >= self.nominal_support.required_margin
        )


@dataclass(frozen=True)
class FixedContactSupportResidual:
    """Observed relative error after removing a common base SE(2) transform."""

    contact_set_preserved: bool
    maximum_contact_point_residual: float | None
    center_of_mass_residual: float | None
    maximum_relative_contact_point_residual: float | None
    observed_support_margin: float | None


def measure_fixed_contact_support_residual(
    reference: QuasiStaticSupportResult,
    reference_base_pose: np.ndarray,
    observed: QuasiStaticSupportResult,
    observed_base_pose: np.ndarray,
) -> FixedContactSupportResidual:
    """Measure point and COM residuals for a fixed contact set.

    This is retrospective measurement, not a prospective error budget. Base
    XY/yaw are world-frame values; changes in height, roll/pitch and arm pose
    appear in the residuals rather than being silently treated as common SE(2).
    """
    reference_base = np.asarray(reference_base_pose, dtype=np.float64)
    observed_base = np.asarray(observed_base_pose, dtype=np.float64)
    if (
        reference_base.shape != (3,) or observed_base.shape != (3,)
        or not np.isfinite(reference_base).all()
        or not np.isfinite(observed_base).all()
    ):
        raise ValueError("base poses must contain finite [x, y, yaw] values")
    if (
        len(set(reference.supporting_feet)) != len(reference.supporting_feet)
        or len(set(observed.supporting_feet)) != len(observed.supporting_feet)
        or len(reference.support_points) != len(reference.supporting_feet)
        or len(observed.support_points) != len(observed.supporting_feet)
    ):
        raise ValueError("supporting_feet must match distinct support_points")
    if len(reference.supporting_feet) < 3 or set(reference.supporting_feet) != set(observed.supporting_feet):
        return FixedContactSupportResidual(
            contact_set_preserved=False,
            maximum_contact_point_residual=None,
            center_of_mass_residual=None,
            maximum_relative_contact_point_residual=None,
            observed_support_margin=observed.support_margin,
        )

    yaw_delta = observed_base[2] - reference_base[2]
    cosine, sine = np.cos(yaw_delta), np.sin(yaw_delta)
    rotation = np.array([[cosine, -sine], [sine, cosine]])
    reference_points = dict(zip(reference.supporting_feet, reference.support_points))
    expected_points = np.stack([
        observed_base[:2] + rotation @ (reference_points[foot] - reference_base[:2])
        for foot in observed.supporting_feet
    ])
    expected_com = observed_base[:2] + rotation @ (
        reference.center_of_mass_xy - reference_base[:2]
    )
    relative_reference_points = np.stack([
        reference_points[foot] - reference.center_of_mass_xy
        for foot in observed.supporting_feet
    ])
    relative_observed_points = observed.support_points - observed.center_of_mass_xy
    return FixedContactSupportResidual(
        contact_set_preserved=True,
        maximum_contact_point_residual=float(np.max(np.linalg.norm(
            observed.support_points - expected_points, axis=1
        ))),
        center_of_mass_residual=float(np.linalg.norm(
            observed.center_of_mass_xy - expected_com
        )),
        maximum_relative_contact_point_residual=float(np.max(np.linalg.norm(
            relative_observed_points - relative_reference_points @ rotation.T, axis=1
        ))),
        observed_support_margin=observed.support_margin,
    )


def certify_relative_contact_support_region(
    nominal_support: QuasiStaticSupportResult,
    *,
    relative_contact_point_error_radius: float,
) -> RelativeContactSupportRegion:
    """Bound support from foot positions relative to the COM projection.

    A common planar rigid transform and a correlated foot/COM displacement
    cancel. Every named support foot must remain active. The radius must be a
    prospective bound on each transformed foot-to-COM vector, not a result
    measured from the trajectory being certified.
    """
    region = certify_fixed_contact_support_region(
        nominal_support,
        contact_point_error_radius=relative_contact_point_error_radius,
        center_of_mass_error_radius=0.0,
    )
    return RelativeContactSupportRegion(
        nominal_support=nominal_support,
        relative_contact_point_error_radius=relative_contact_point_error_radius,
        margin_lower_bound=region.margin_lower_bound,
    )


def certify_fixed_contact_support_region(
    nominal_support: QuasiStaticSupportResult,
    *,
    contact_point_error_radius: float,
    center_of_mass_error_radius: float,
) -> FixedContactSupportRegion:
    """Bound the planar support margin under relative point and COM errors.

    Every nominal support foot must retain its floor contact. Each retained
    contact point may move by at most ``contact_point_error_radius`` relative
    to a common planar rigid transform; the COM projection has an independent
    relative error bounded by ``center_of_mass_error_radius``. A common base
    translation/yaw cancels from the support-polygon margin.
    """
    for name, radius in (
        ("contact_point_error_radius", contact_point_error_radius),
        ("center_of_mass_error_radius", center_of_mass_error_radius),
    ):
        if not np.isfinite(radius) or radius < 0.0:
            raise ValueError(f"{name} must be finite and non-negative")
    if (
        len(set(nominal_support.supporting_feet)) != len(nominal_support.supporting_feet)
        or len(nominal_support.supporting_feet) != len(nominal_support.support_points)
    ):
        raise ValueError("supporting_feet must match distinct support_points")

    margin = nominal_support.support_margin
    if len(nominal_support.supporting_feet) >= 3 and margin is not None:
        measured = _convex_support_margin(
            nominal_support.support_points, nominal_support.center_of_mass_xy
        )
        if not np.isclose(margin, measured, rtol=0.0, atol=1.0e-9):
            raise ValueError("support_margin does not match the contact geometry")
    residual_bound = contact_point_error_radius + center_of_mass_error_radius
    lower_bound = (
        margin - residual_bound
        if len(nominal_support.supporting_feet) >= 3
        and margin is not None
        and margin >= residual_bound
        else None
    )
    return FixedContactSupportRegion(
        nominal_support=nominal_support,
        contact_point_error_radius=contact_point_error_radius,
        center_of_mass_error_radius=center_of_mass_error_radius,
        margin_lower_bound=lower_bound,
    )


class PiperQuasiStaticSupportChecker:
    """Measure support margin without stepping MuJoCo or modifying state."""

    def __init__(
        self,
        runtime,
        *,
        floor_geometry_name: str = "floor",
        foot_geometry_names: tuple[str, ...] = DEFAULT_FOOT_GEOMETRY_NAMES,
        data=None,
    ) -> None:
        if not foot_geometry_names or len(set(foot_geometry_names)) != len(foot_geometry_names):
            raise ValueError("foot_geometry_names must be unique and non-empty")
        self.runtime = runtime
        self.model = runtime.model
        self.data = runtime.data if data is None else data
        self.floor_geometry = self.model.geom(floor_geometry_name).id
        self.foot_geometries = {
            name: self.model.geom(name).id for name in foot_geometry_names
        }
        self.base_id = runtime.base_id
        self.base_qpos_adr = self._base_qpos_address()
        self.arm_qpos_adr = np.asarray(runtime.joint_qpos_adr[12:], dtype=int)

    def evaluate(self, *, required_margin: float) -> QuasiStaticSupportResult:
        """Evaluate planar support from the current foot-ground contacts."""
        if required_margin < 0.0 or not np.isfinite(required_margin):
            raise ValueError("required_margin must be finite and non-negative")
        contacts: dict[str, list[np.ndarray]] = {
            foot: [] for foot in self.foot_geometries
        }
        for contact_index in range(self.data.ncon):
            contact = self.data.contact[contact_index]
            if contact.dist > 0.0 or self.floor_geometry not in (
                contact.geom1,
                contact.geom2,
            ):
                continue
            for foot, geometry_id in self.foot_geometries.items():
                if geometry_id in (contact.geom1, contact.geom2):
                    contacts[foot].append(contact.pos[:2].copy())
        supporting_feet = tuple(foot for foot, points in contacts.items() if points)
        support_points = np.asarray(
            [np.mean(contacts[foot], axis=0) for foot in supporting_feet],
            dtype=np.float64,
        ).reshape(-1, 2)
        center_of_mass_xy = self.data.subtree_com[self.base_id, :2].copy()
        margin = (
            _convex_support_margin(support_points, center_of_mass_xy)
            if len(supporting_feet) >= 3
            else None
        )
        return QuasiStaticSupportResult(
            supporting_feet=supporting_feet,
            support_points=support_points,
            center_of_mass_xy=center_of_mass_xy,
            support_margin=margin,
            required_margin=required_margin,
        )

    def evaluate_configuration(
        self,
        base_pose: np.ndarray,
        arm_joint_positions: np.ndarray,
        *,
        required_margin: float,
    ) -> QuasiStaticSupportResult:
        """Evaluate support after replacing only base XY/yaw and arm joints.

        The caller is responsible for settling the leg configuration and base
        height before calling this method. It preserves the shared MuJoCo state.
        """
        base = np.asarray(base_pose, dtype=np.float64)
        arm = np.asarray(arm_joint_positions, dtype=np.float64)
        if base.shape != (3,) or not np.isfinite(base).all():
            raise ValueError("base_pose must contain three finite values")
        if arm.shape != (6,) or not np.isfinite(arm).all():
            raise ValueError("arm_joint_positions must contain six finite values")
        saved_qpos = self.data.qpos.copy()
        saved_qvel = self.data.qvel.copy()
        saved_ctrl = self.data.ctrl.copy()
        try:
            x_position, y_position, yaw = base
            settled_quaternion = self.data.qpos[
                self.base_qpos_adr + 3 : self.base_qpos_adr + 7
            ].copy()
            settled_rotation = np.empty(9, dtype=np.float64)
            mujoco.mju_quat2Mat(settled_rotation, settled_quaternion)
            settled_rotation = settled_rotation.reshape(3, 3)
            settled_yaw = float(
                np.arctan2(settled_rotation[1, 0], settled_rotation[0, 0])
            )
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
            self.data.qpos[
                self.base_qpos_adr + 3 : self.base_qpos_adr + 7
            ] = target_quaternion
            self.data.qpos[self.arm_qpos_adr] = arm
            self.data.qvel.fill(0.0)
            mujoco.mj_forward(self.model, self.data)
            result = self.evaluate(required_margin=required_margin)
        finally:
            self.data.qpos[:] = saved_qpos
            self.data.qvel[:] = saved_qvel
            self.data.ctrl[:] = saved_ctrl
            mujoco.mj_forward(self.model, self.data)
        return result

    def _base_qpos_address(self) -> int:
        environment = getattr(self.runtime, "env", None)
        if environment is not None and hasattr(environment, "robot_qpos_adr"):
            return int(environment.robot_qpos_adr)
        base_body = self.model.body("base_link").id
        root_joint = int(self.model.body_jntadr[base_body])
        if root_joint < 0 or self.model.jnt_type[root_joint] != mujoco.mjtJoint.mjJNT_FREE:
            raise ValueError("PIPER base_link must have a free joint")
        return int(self.model.jnt_qposadr[root_joint])


def _convex_support_margin(points: np.ndarray, center: np.ndarray) -> float:
    hull = _convex_hull(points)
    if len(hull) < 3:
        raise ValueError("At least three non-collinear support points are required")
    distances = []
    for index, vertex in enumerate(hull):
        edge = hull[(index + 1) % len(hull)] - vertex
        center_offset = center - vertex
        inward_distance = (
            edge[0] * center_offset[1] - edge[1] * center_offset[0]
        ) / np.linalg.norm(edge)
        distances.append(float(inward_distance))
    return min(distances)


def _convex_hull(points: np.ndarray) -> np.ndarray:
    unique = np.unique(np.asarray(points, dtype=np.float64), axis=0)
    ordered = sorted((float(point[0]), float(point[1])) for point in unique)
    if len(ordered) < 3:
        return unique

    def cross(origin, first, second) -> float:
        return (
            (first[0] - origin[0]) * (second[1] - origin[1])
            - (first[1] - origin[1]) * (second[0] - origin[0])
        )

    lower = []
    for point in ordered:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(ordered):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)
    return np.asarray(lower[:-1] + upper[:-1], dtype=np.float64)
