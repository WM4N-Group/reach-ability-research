"""Conditional clearance bounds for bounded whole-robot tracking errors.

Budgets are caller assumptions, not estimates of a policy's tracking ability.
The geometry pairs are exactly those selected by the supplied checker.
"""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np

from .sweep import PiperConfigurationSweep


@dataclass(frozen=True)
class TrackingClearanceResult:
    nominal_clearance: float
    clearance_lower_bound: float
    required_clearance: float
    joint_limit_margin_lower_bound: float
    required_joint_margin: float
    limiting_geometry_pair: tuple[int, int]
    checked_pairs: int
    common_base_motion_cancels: bool

    @property
    def conditional_clearance_safe(self) -> bool:
        return bool(
            self.clearance_lower_bound >= self.required_clearance
            and self.joint_limit_margin_lower_bound >= self.required_joint_margin
        )


class PiperTrackingClearance:
    """Translate joint/base/object error budgets into clearance lower bounds.

    Joint radii use runtime.joint_qpos_adr order (not policy action order).
    All 18 leg and arm hinges may vary. Base translation is a 3D Euclidean
    radius and base rotation is an SO(3) geodesic radius. External uncertainty
    bounds the displacement of every point of the selected protected geometry.
    Other model coordinates and geometry must stay fixed. No step is executed.
    """

    def __init__(self, checker, *, moving_body_names=frozenset()):
        self.checker = checker
        self.model = checker.model
        self.sweep = PiperConfigurationSweep(checker, moving_body_names=moving_body_names)
        self.joint_addresses = self.sweep.joint_addresses.copy()
        if len(self.joint_addresses) != 18:
            raise ValueError("Expected 18 PIPER leg and arm joints")
        ids = self.sweep.joint_ids
        if not np.all(self.model.jnt_limited[ids]):
            raise ValueError("Tracking region requires limited robot joints")
        self.joint_low = self.model.jnt_range[ids, 0].copy()
        self.joint_high = self.model.jnt_range[ids, 1].copy()
        geometries = set(checker.arm_geometries) | set(checker.protected_geometries)
        bounds = {geometry: self.sweep._geometry_bounds(geometry) for geometry in geometries}
        if not all(bounds[g][2] for g in checker.arm_geometries):
            raise ValueError("Moving geometry must belong to the robot")
        protected_is_robot = {bounds[g][2] for g in checker.protected_geometries}
        if len(protected_is_robot) != 1:
            raise ValueError("Separate robot and external protected geometry into different checkers")
        self.common_base_motion_cancels = protected_is_robot.pop()
        self.pairs = [(a, b) for a in checker.arm_geometries for b in checker.protected_geometries]
        self.pair_joint_radii = np.stack([bounds[a][0] + bounds[b][0] for a, b in self.pairs])
        # A common base rigid transform preserves all self distances exactly.
        self.pair_base_radii = np.array([
            0.0 if self.common_base_motion_cancels else bounds[a][1]
            for a, _ in self.pairs
        ])

    def _terms(self, nominal_qpos, joint_error_radii, base_translation_radius,
               base_rotation_radius, external_point_error_radius, required_clearance,
               required_joint_margin):
        qpos = np.asarray(nominal_qpos, dtype=np.float64)
        radii = np.asarray(joint_error_radii, dtype=np.float64)
        if qpos.shape != (self.model.nq,) or not np.isfinite(qpos).all():
            raise ValueError("nominal_qpos must be a finite full qpos vector")
        if radii.shape != (18,) or not np.isfinite(radii).all() or np.any(radii < 0):
            raise ValueError("joint_error_radii must contain 18 finite nonnegative radii")
        scalars = [base_translation_radius, base_rotation_radius, external_point_error_radius,
                   required_clearance, required_joint_margin]
        if not np.isfinite(scalars).all() or min(scalars) < 0 or base_rotation_radius > np.pi:
            raise ValueError("Budgets and requirements must be finite nonnegative; rotation <= pi")
        if self.common_base_motion_cancels and external_point_error_radius != 0:
            raise ValueError("External geometry error does not apply to a self-clearance checker")
        for joint in range(self.model.njnt):
            kind = int(self.model.jnt_type[joint])
            if kind in (int(mujoco.mjtJoint.mjJNT_FREE), int(mujoco.mjtJoint.mjJNT_BALL)):
                address = int(self.model.jnt_qposadr[joint])
                if kind == mujoco.mjtJoint.mjJNT_FREE:
                    address += 3
                if not np.isclose(np.linalg.norm(qpos[address:address + 4]), 1.0, rtol=0, atol=1e-10):
                    raise ValueError("Nominal quaternions must be normalized")
        joints = qpos[self.joint_addresses]
        margins = np.minimum(joints - self.joint_low, self.joint_high - joints)
        if np.any(margins < 0):
            raise ValueError("Nominal robot joints must satisfy joint limits")
        scratch = mujoco.MjData(self.model)
        scratch.qpos[:] = qpos
        mujoco.mj_forward(self.model, scratch)
        distances = np.array([
            mujoco.mj_geomDistance(self.model, scratch, a, b, float("inf"), None)
            for a, b in self.pairs
        ])
        if not np.isfinite(distances).all():
            raise ValueError("Geometry distances must be finite")
        rigid_loss = np.zeros(len(self.pairs))
        if not self.common_base_motion_cancels:
            rigid_loss = (base_translation_radius + external_point_error_radius
                          + 2 * self.pair_base_radii * np.sin(base_rotation_radius / 2))
        lower = distances - self.pair_joint_radii @ radii - rigid_loss
        return distances, lower, margins - radii

    def evaluate(self, nominal_qpos, *, joint_error_radii,
                 base_translation_radius=0.0, base_rotation_radius=0.0,
                 external_point_error_radius=0.0, required_clearance=0.05,
                 required_joint_margin=0.0) -> TrackingClearanceResult:
        """Sufficient clearance/limit check for every state within the budgets.

        For each pair (a,b), subtract sum_j (R_aj+R_bj)*epsilon_j
        from the nominal distance. External pairs also lose base translation,
        bounded base rotation and object point motion. The minimum of these
        pair-specific lower bounds is stronger than subtracting the worst
        displacement over all geometry from the minimum nominal distance.
        """
        distances, lower, margins = self._terms(
            nominal_qpos, joint_error_radii, base_translation_radius,
            base_rotation_radius, external_point_error_radius,
            required_clearance, required_joint_margin,
        )
        limiting = int(np.argmin(lower))
        return TrackingClearanceResult(
            nominal_clearance=float(np.min(distances)),
            clearance_lower_bound=float(lower[limiting]),
            required_clearance=required_clearance,
            joint_limit_margin_lower_bound=float(np.min(margins)),
            required_joint_margin=required_joint_margin,
            limiting_geometry_pair=self.pairs[limiting],
            checked_pairs=len(self.pairs),
            common_base_motion_cancels=self.common_base_motion_cancels,
        )

    def maximum_uniform_arm_error(self, nominal_qpos, *, leg_error_radii,
                                  base_translation_radius=0.0, base_rotation_radius=0.0,
                                  external_point_error_radius=0.0, required_clearance=0.05,
                                  required_joint_margin=0.0) -> float | None:
        """Largest common six-arm-joint radius admitted by these sufficient bounds.

        None means the fixed leg/base/object budgets already fail, even for
        zero arm error. This is not the true maximal collision-free radius.
        """
        legs = np.asarray(leg_error_radii, dtype=np.float64)
        if legs.shape != (12,):
            raise ValueError("leg_error_radii must contain 12 values")
        _, lower, margins = self._terms(
            nominal_qpos, np.concatenate([legs, np.zeros(6)]),
            base_translation_radius, base_rotation_radius, external_point_error_radius,
            required_clearance, required_joint_margin,
        )
        return self._inverse_arm_radius(lower, margins, required_clearance, required_joint_margin)

    def _inverse_arm_radius(self, lower, margins, required_clearance, required_joint_margin):
        if np.min(lower) < required_clearance or np.min(margins) < required_joint_margin:
            return None
        slopes = np.sum(self.pair_joint_radii[:, 12:], axis=1)
        positive = slopes > 0
        limits = list((lower[positive] - required_clearance) / slopes[positive])
        limits.extend(margins[12:] - required_joint_margin)
        return float(min(limits))

    def _path_terms(self, start_qpos, target_qpos, samples, joint_error_radii,
                    base_translation_radius, base_rotation_radius,
                    external_point_error_radius, required_clearance, required_joint_margin):
        start = np.asarray(start_qpos, dtype=float)
        target = np.asarray(target_qpos, dtype=float)
        if (start.shape != (self.model.nq,) or target.shape != start.shape
                or not np.isfinite(start).all() or not np.isfinite(target).all()):
            raise ValueError("Path endpoints must be finite full qpos vectors")
        if isinstance(samples, bool) or not isinstance(samples, (int, np.integer)) or samples < 2:
            raise ValueError("Path samples must be an integer >= 2")
        fixed = np.ones(self.model.nq, dtype=bool)
        fixed[self.joint_addresses] = False
        if not np.array_equal(start[fixed], target[fixed]):
            raise ValueError("Nominal path may change robot hinges only")
        delta = np.abs(target[self.joint_addresses] - start[self.joint_addresses])
        # Every reference point is within half a grid interval of a sample.
        between_sample_loss = self.pair_joint_radii @ delta / (2 * (samples - 1))
        terms = [self._terms(
            start + fraction * (target - start), joint_error_radii,
            base_translation_radius, base_rotation_radius, external_point_error_radius,
            required_clearance, required_joint_margin,
        ) for fraction in np.linspace(0, 1, samples)]
        nominal = np.min([item[0] for item in terms], axis=0)
        lower = np.min([item[1] for item in terms], axis=0) - between_sample_loss
        # Joint intervals are convex: their smallest margin is at an endpoint.
        margins = np.minimum(terms[0][2], terms[-1][2])
        return nominal, lower, margins

    def evaluate_joint_path(self, start_qpos, target_qpos, *, samples=51,
                            joint_error_radii, base_translation_radius=0.0,
                            base_rotation_radius=0.0, external_point_error_radius=0.0,
                            required_clearance=0.05, required_joint_margin=0.0):
        """Bound the continuous hinge-linear reference path plus tracking errors.

        The controller must stay within the stated errors of some reference
        phase at every time. This checks geometry and limits, not the ability
        to track the path, finish on time, or keep the supporting feet active.
        nominal_clearance is the minimum over samples; the lower bound also
        includes the rigorously bounded gaps between samples.
        """
        nominal, lower, margins = self._path_terms(
            start_qpos, target_qpos, samples, joint_error_radii,
            base_translation_radius, base_rotation_radius, external_point_error_radius,
            required_clearance, required_joint_margin,
        )
        return TrackingClearanceResult(
            nominal_clearance=float(np.min(nominal)),
            clearance_lower_bound=float(np.min(lower)), required_clearance=required_clearance,
            joint_limit_margin_lower_bound=float(np.min(margins)),
            required_joint_margin=required_joint_margin,
            limiting_geometry_pair=self.pairs[int(np.argmin(lower))],
            checked_pairs=len(self.pairs), common_base_motion_cancels=self.common_base_motion_cancels,
        )

    def maximum_uniform_arm_error_on_joint_path(
        self, start_qpos, target_qpos, *, leg_error_radii, samples=51,
        base_translation_radius=0.0, base_rotation_radius=0.0,
        external_point_error_radius=0.0, required_clearance=0.05, required_joint_margin=0.0,
    ):
        """Invert the continuous reference-path bound, including joint limits."""
        legs = np.asarray(leg_error_radii, dtype=float)
        if legs.shape != (12,):
            raise ValueError("leg_error_radii must contain 12 values")
        _, lower, margins = self._path_terms(
            start_qpos, target_qpos, samples, np.r_[legs, np.zeros(6)],
            base_translation_radius, base_rotation_radius, external_point_error_radius,
            required_clearance, required_joint_margin,
        )
        return self._inverse_arm_radius(lower, margins, required_clearance, required_joint_margin)
