"""Conditional world-target error bound for a static box-local command."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class StaticBoxTargetErrorBound:
    """Target-position geometry only; no controller or skill guarantee."""

    local_target_xy_radius_m: float
    box_translation_error_bound_m: float
    box_yaw_error_bound_rad: float
    local_target_error_bound_m: float
    world_target_error_upper_bound_m: float

    @property
    def handoff_certified(self) -> bool:
        return False


@dataclass(frozen=True)
class StaticBoxPrecontactErrorBounds:
    """Paired bounds for a fixed world box and its box-local target."""

    target: StaticBoxTargetErrorBound
    box_corner_xy_radius_m: float
    external_geometry_error_upper_bound_m: float

    @property
    def target_position_error_radius(self) -> float:
        return self.target.world_target_error_upper_bound_m

    @property
    def external_geometry_error_radius(self) -> float:
        return self.external_geometry_error_upper_bound_m

    @property
    def handoff_certified(self) -> bool:
        return False


def bound_static_box_precontact_errors(
    local_target: np.ndarray,
    box_size: np.ndarray,
    *,
    box_translation_error_bound_m: float,
    box_yaw_error_bound_rad: float,
    local_target_error_bound_m: float,
) -> StaticBoxPrecontactErrorBounds:
    """Bound target and box-geometry displacement from one box pose error.

    ``box_size`` is the full xyz extent used by ``make_static_box_navigation_runtime``.
    The geometry bound covers every point on its single rigid box under planar
    translation and yaw. It applies to a synchronized static scene snapshot;
    the caller must independently justify all input error bounds.
    """
    size = np.asarray(box_size, dtype=np.float64)
    if size.shape != (3,) or not np.isfinite(size).all() or np.any(size <= 0.0):
        raise ValueError("box_size must contain three finite positive full extents")
    target = bound_static_box_target_error(
        local_target,
        box_translation_error_bound_m=box_translation_error_bound_m,
        box_yaw_error_bound_rad=box_yaw_error_bound_rad,
        local_target_error_bound_m=local_target_error_bound_m,
    )
    radius = float(np.linalg.norm(size[:2] / 2.0))
    geometry_bound = float(
        box_translation_error_bound_m
        + 2.0 * radius * np.sin(box_yaw_error_bound_rad / 2.0)
    )
    if not np.isfinite(geometry_bound) or not np.isfinite(target.world_target_error_upper_bound_m):
        raise ValueError("error bounds must produce finite displacement radii")
    return StaticBoxPrecontactErrorBounds(
        target=target,
        box_corner_xy_radius_m=radius,
        external_geometry_error_upper_bound_m=geometry_bound,
    )


def bound_static_box_target_error(
    local_target: np.ndarray,
    *,
    box_translation_error_bound_m: float,
    box_yaw_error_bound_rad: float,
    local_target_error_bound_m: float,
) -> StaticBoxTargetErrorBound:
    """Propagate validated input bounds through ``p_box + R_yaw @ local_target``.

    The caller must establish the input bounds independently. The returned
    bound applies to one synchronized static-box snapshot, not the closed-loop
    WBC trajectory or its hold, support, contact, and safety conditions.
    """
    target = np.asarray(local_target, dtype=np.float64)
    if target.shape != (3,) or not np.isfinite(target).all():
        raise ValueError("local_target must contain three finite coordinates")
    for name, value in (
        ("box_translation_error_bound_m", box_translation_error_bound_m),
        ("box_yaw_error_bound_rad", box_yaw_error_bound_rad),
        ("local_target_error_bound_m", local_target_error_bound_m),
    ):
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be finite and non-negative")
    if box_yaw_error_bound_rad > np.pi:
        raise ValueError("box_yaw_error_bound_rad must not exceed pi")
    radius = float(np.linalg.norm(target[:2]))
    bound = float(
        box_translation_error_bound_m
        + 2.0 * radius * np.sin(box_yaw_error_bound_rad / 2.0)
        + local_target_error_bound_m
    )
    return StaticBoxTargetErrorBound(
        local_target_xy_radius_m=radius,
        box_translation_error_bound_m=float(box_translation_error_bound_m),
        box_yaw_error_bound_rad=float(box_yaw_error_bound_rad),
        local_target_error_bound_m=float(local_target_error_bound_m),
        world_target_error_upper_bound_m=bound,
    )
