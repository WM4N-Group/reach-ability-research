"""Structured, unit-preserving contracts for PIPER reachability queries."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _vector(value: np.ndarray, size: int, name: str) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float64)
    if vector.shape != (size,) or not np.isfinite(vector).all():
        raise ValueError(f"{name} must contain {size} finite values")
    return vector.copy()


@dataclass(frozen=True)
class ReachabilityQuery:
    """Fixed-base, world-frame end-effector position query.

    ``base_pose`` is ``[x, y, yaw]`` in meters and radians. ``target_position``
    is a world-frame position in meters. Orientation, collision, support, and
    rollout checks are intentionally outside this P0 position-IK contract.
    """

    base_pose: np.ndarray
    target_position: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_pose", _vector(self.base_pose, 3, "base_pose"))
        object.__setattr__(
            self,
            "target_position",
            _vector(self.target_position, 3, "target_position"),
        )


@dataclass(frozen=True)
class ReachabilityResult:
    """Outcome from the P0 position-IK oracle.

    A successful result certifies only position-level kinematic feasibility at a
    fixed base pose. Later stages must add collision, support, and skill-handoff
    evidence before treating it as executable reachability.
    A non-None ``orientation_error`` records an additionally checked pose target.
    """

    kinematic_feasible: bool
    joint_solution: np.ndarray
    position_error: float
    iterations: int
    failure_reason: str | None
    joint_limit_margin: float
    collision_checked: bool = False
    support_checked: bool = False
    handoff_checked: bool = False
    orientation_error: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "joint_solution",
            _vector(self.joint_solution, 6, "joint_solution"),
        )
        if not np.isfinite(self.position_error) or self.position_error < 0.0:
            raise ValueError("position_error must be finite and non-negative")
        if not np.isfinite(self.joint_limit_margin) or self.joint_limit_margin < 0.0:
            raise ValueError("joint_limit_margin must be finite and non-negative")
        if self.iterations < 0:
            raise ValueError("iterations must be non-negative")
        if self.orientation_error is not None and (
            not np.isfinite(self.orientation_error) or self.orientation_error < 0.0
        ):
            raise ValueError("orientation_error must be finite and non-negative when checked")
        if self.kinematic_feasible != (self.failure_reason is None):
            raise ValueError("feasible results must not include a failure reason")