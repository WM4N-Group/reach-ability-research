"""Continuous geometric bounds for a frozen PIPER precontact configuration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .clearance import (
    ClearanceResult,
    FrozenConfigurationSafetyTube,
    PiperArmClearanceChecker,
    PiperSelfClearanceChecker,
)
from .oracle import PiperPositionReachabilityOracle
from .schema import ReachabilityQuery


@dataclass(frozen=True)
class FrozenPrecontactRegion:
    """Sufficient position and clearance checks for one fixed arm/leg pose.

    Only planar base translation and yaw, target pose error, and external
    geometry displacement are bounded. Support contacts, controller tracking,
    and contact execution are outside this certificate.
    """

    translation_radius: float
    yaw_radius: float
    target_position_error_radius: float
    target_orientation_error_radius: float
    nominal_position_error: float
    nominal_orientation_error: float
    end_effector_rotation_radius: float
    position_error_upper_bound: float
    orientation_error_upper_bound: float
    required_position_tolerance: float
    required_orientation_tolerance: float
    joint_limit_margin: float
    required_joint_margin: float
    self_clearance: ClearanceResult
    environment_tube: FrozenConfigurationSafetyTube

    @property
    def geometric_precontact_safe(self) -> bool:
        return bool(
            self.position_error_upper_bound <= self.required_position_tolerance
            and self.orientation_error_upper_bound <= self.required_orientation_tolerance
            and self.joint_limit_margin >= self.required_joint_margin
            and self.self_clearance.safe
            and self.environment_tube.safe
        )


def certify_frozen_precontact_region(
    oracle: PiperPositionReachabilityOracle,
    self_checker: PiperSelfClearanceChecker,
    environment_checker: PiperArmClearanceChecker,
    query: ReachabilityQuery,
    arm_joint_positions: np.ndarray,
    *,
    target_quaternion: np.ndarray,
    translation_radius: float,
    yaw_radius: float,
    target_position_error_radius: float,
    target_orientation_error_radius: float,
    external_geometry_error_radius: float,
    required_position_tolerance: float,
    required_orientation_tolerance: float,
    required_joint_margin: float,
    required_self_clearance: float,
    required_environment_clearance: float,
) -> FrozenPrecontactRegion:
    """Bound every perturbation inside the stated radii without re-solving IK.

    The nominal end-effector point moves at most ``r_xy + 2 R sin(r_yaw/2)``.
    Triangle inequality adds nominal and target-position errors. The SO(3)
    geodesic orientation error grows by at most the base yaw and target
    orientation errors. The existing geometry safety tube applies the same
    rigid motion bound to external
    clearance; self distances and joint margins are unchanged by a rigid base
    SE(2) transform with fixed legs and arm.
    """
    if not isinstance(self_checker, PiperSelfClearanceChecker):
        raise ValueError("self_checker must check PIPER arm-to-body clearance")
    if oracle.runtime is not self_checker.runtime or oracle.runtime is not environment_checker.runtime:
        raise ValueError("oracle and clearance checkers must share one runtime")
    if (
        oracle.model is not self_checker.model
        or oracle.model is not environment_checker.model
        or oracle.data is not self_checker.data
        or oracle.data is not environment_checker.data
    ):
        raise ValueError("oracle and clearance checkers must use the same scene snapshot")
    for name, value in (
        ("translation_radius", translation_radius),
        ("yaw_radius", yaw_radius),
        ("target_position_error_radius", target_position_error_radius),
        ("target_orientation_error_radius", target_orientation_error_radius),
        ("external_geometry_error_radius", external_geometry_error_radius),
        ("required_position_tolerance", required_position_tolerance),
        ("required_orientation_tolerance", required_orientation_tolerance),
        ("required_joint_margin", required_joint_margin),
        ("required_self_clearance", required_self_clearance),
        ("required_environment_clearance", required_environment_clearance),
    ):
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be finite and non-negative")
    if yaw_radius > np.pi:
        raise ValueError("yaw_radius must not exceed pi")
    target_quaternion = np.asarray(target_quaternion, dtype=np.float64)
    if (
        target_quaternion.shape != (4,)
        or not np.isfinite(target_quaternion).all()
        or not np.isclose(np.linalg.norm(target_quaternion), 1.0, rtol=0.0, atol=1e-10)
    ):
        raise ValueError("target_quaternion must be a normalized finite wxyz quaternion")

    model = environment_checker.model
    robot_root = model.body("base_link").id
    for geometry in environment_checker.protected_geometries:
        body = int(model.geom_bodyid[geometry])
        while body != 0:
            if body == robot_root:
                raise ValueError("environment_checker must protect external geometry")
            body = int(model.body_parentid[body])

    arm = np.asarray(arm_joint_positions, dtype=np.float64)
    if arm.shape != (6,) or not np.isfinite(arm).all():
        raise ValueError("arm_joint_positions must contain six finite values")
    if np.any(arm < oracle.arm_low) or np.any(arm > oracle.arm_high):
        raise ValueError("arm_joint_positions must satisfy joint limits")

    nominal_hand, nominal_quaternion = oracle.end_effector_pose(query, arm)
    nominal_error = float(np.linalg.norm(nominal_hand - query.target_position))
    quaternion_dot = abs(float(np.dot(nominal_quaternion, target_quaternion)))
    nominal_orientation_error = float(2.0 * np.arccos(np.clip(quaternion_dot, 0.0, 1.0)))
    hand_radius = float(np.linalg.norm(nominal_hand[:2] - query.base_pose[:2]))
    position_upper_bound = (
        nominal_error + translation_radius
        + 2.0 * hand_radius * np.sin(yaw_radius / 2.0)
        + target_position_error_radius
    )
    orientation_upper_bound = (
        nominal_orientation_error + yaw_radius + target_orientation_error_radius
    )
    self_clearance = self_checker.evaluate(
        query.base_pose, arm, required_clearance=required_self_clearance
    )
    environment_tube = environment_checker.certify_frozen_configuration_tube(
        query.base_pose,
        arm,
        base_pose_offset=np.array([translation_radius, 0.0, yaw_radius]),
        required_clearance=required_environment_clearance,
        external_geometry_error_bound=external_geometry_error_radius,
    )
    margin = float(np.min(np.minimum(arm - oracle.arm_low, oracle.arm_high - arm)))
    return FrozenPrecontactRegion(
        translation_radius=translation_radius,
        yaw_radius=yaw_radius,
        target_position_error_radius=target_position_error_radius,
        target_orientation_error_radius=target_orientation_error_radius,
        nominal_position_error=nominal_error,
        nominal_orientation_error=nominal_orientation_error,
        end_effector_rotation_radius=hand_radius,
        position_error_upper_bound=position_upper_bound,
        orientation_error_upper_bound=orientation_upper_bound,
        required_position_tolerance=required_position_tolerance,
        required_orientation_tolerance=required_orientation_tolerance,
        joint_limit_margin=margin,
        required_joint_margin=required_joint_margin,
        self_clearance=self_clearance,
        environment_tube=environment_tube,
    )
