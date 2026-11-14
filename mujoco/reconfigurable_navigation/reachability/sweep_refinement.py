"""Adaptive clearance bounds along one recorded Euler position-update curve."""

from __future__ import annotations

from dataclasses import dataclass

import mujoco
import numpy as np

from .sweep import PiperConfigurationSweep


@dataclass(frozen=True)
class RefinedSweepResult:
    passed: bool
    lower_bound: float
    geometry_evaluations: int
    leaf_intervals: int
    maximum_depth_used: int


def refine_euler_clearance(
    checker,
    sweep: PiperConfigurationSweep,
    start_qpos: np.ndarray,
    velocity: np.ndarray,
    duration: float,
    start_clearance: float,
    end_clearance: float,
    required_clearance: float,
    *,
    max_depth: int,
) -> RefinedSweepResult:
    """Bound the Euler curve, refining only intervals rejected by the current bound.

    The caller must verify that integrating ``start_qpos`` by ``velocity`` for
    ``duration`` reproduces the recorded endpoint. The checker must use its own
    scratch MjData, since midpoint evaluation overwrites its geometry cache.
    """
    model = sweep.model
    start = np.asarray(start_qpos, dtype=float)
    velocity = np.asarray(velocity, dtype=float)
    if (checker.model is not model or checker.data is checker.runtime.data
            or start.shape != (model.nq,) or velocity.shape != (model.nv,)
            or not np.isfinite(start).all() or not np.isfinite(velocity).all()
            or not np.isfinite(duration) or duration <= 0
            or not isinstance(max_depth, int) or max_depth < 0
            or not all(np.isfinite(value) for value in (
                start_clearance, end_clearance, required_clearance))
            or required_clearance < 0):
        raise ValueError("Invalid sweep refinement inputs or shared checker data")
    for joint in np.flatnonzero(model.jnt_type == mujoco.mjtJoint.mjJNT_FREE):
        angular_dof = int(model.jnt_dofadr[joint]) + 3
        if np.linalg.norm(velocity[angular_dof:angular_dof + 3]) * duration >= np.pi:
            raise ValueError("Free-joint Euler rotation must be shorter than pi")
    endpoint = start.copy()
    mujoco.mj_integratePos(model, endpoint, velocity, duration)
    evaluations = 0
    deepest = 0

    def visit(left_fraction, right_fraction, left, right, left_clearance, right_clearance, depth):
        nonlocal evaluations, deepest
        deepest = max(deepest, depth)
        lower = (min(left_clearance, right_clearance)
                 - sweep.nearest_endpoint_motion_bound(left, right))
        if lower >= required_clearance:
            return True, lower, 1
        if (depth == max_depth or left_clearance < required_clearance
                or right_clearance < required_clearance):
            return False, lower, 1
        middle_fraction = (left_fraction + right_fraction) / 2.0
        middle = start.copy()
        mujoco.mj_integratePos(model, middle, velocity, duration * middle_fraction)
        checker.data.qpos[:] = middle
        mujoco.mj_kinematics(model, checker.data)
        middle_clearance = checker.evaluate_current_configuration(
            required_clearance=0.0).minimum_clearance
        evaluations += 1
        left_pass, left_lower, left_leaves = visit(
            left_fraction, middle_fraction, left, middle,
            left_clearance, middle_clearance, depth + 1)
        right_pass, right_lower, right_leaves = visit(
            middle_fraction, right_fraction, middle, right,
            middle_clearance, right_clearance, depth + 1)
        return left_pass and right_pass, min(left_lower, right_lower), left_leaves + right_leaves

    passed, lower, leaves = visit(
        0.0, 1.0, start, endpoint, start_clearance, end_clearance, 0)
    return RefinedSweepResult(passed, float(lower), evaluations, leaves, deepest)
