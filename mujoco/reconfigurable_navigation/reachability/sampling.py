"""Deterministic fixed-base sampling records for PIPER reachability maps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .schema import ReachabilityQuery, ReachabilityResult


@dataclass(frozen=True)
class ReachabilitySample:
    """One target query and its P0 kinematic-oracle label."""

    query: ReachabilityQuery
    result: ReachabilityResult
    self_clearance: object | None = None
    environment_clearance: object | None = None
    support: object | None = None
    required_joint_limit_margin: float = 0.0

    def __post_init__(self) -> None:
        if (
            not np.isfinite(self.required_joint_limit_margin)
            or self.required_joint_limit_margin < 0.0
        ):
            raise ValueError(
                "required_joint_limit_margin must be finite and non-negative"
            )

    def record(self) -> dict[str, object]:
        record = {
            "base_pose": self.query.base_pose.tolist(),
            "target_position": self.query.target_position.tolist(),
            "kinematic_feasible": self.result.kinematic_feasible,
            "joint_solution": self.result.joint_solution.tolist(),
            "position_error": self.result.position_error,
            "joint_limit_margin": self.result.joint_limit_margin,
            "required_joint_limit_margin": self.required_joint_limit_margin,
            "joint_limit_safe": bool(
                self.result.kinematic_feasible
                and self.result.joint_limit_margin >= self.required_joint_limit_margin
            ),
            "iterations": self.result.iterations,
            "failure_reason": self.result.failure_reason,
            "collision_checked": self.result.collision_checked,
            "support_checked": self.result.support_checked,
            "handoff_checked": self.result.handoff_checked,
        }
        if self.self_clearance is None:
            record.update(
                {
                    "self_clearance_checked": False,
                    "minimum_self_clearance": None,
                    "required_self_clearance": None,
                    "self_clearance_safe": None,
                    "self_clearance_pair": None,
                }
            )
        else:
            record.update(
                {
                    "self_clearance_checked": True,
                    "minimum_self_clearance": self.self_clearance.minimum_clearance,
                    "required_self_clearance": self.self_clearance.required_clearance,
                    "self_clearance_safe": self.self_clearance.safe,
                    "self_clearance_pair": {
                        "arm_body": self.self_clearance.arm_body,
                        "protected_body": self.self_clearance.protected_body,
                        "arm_geometry": self.self_clearance.arm_geometry,
                        "protected_geometry": self.self_clearance.protected_geometry,
                    },
                }
            )
        if self.environment_clearance is None:
            record.update(
                {
                    "environment_clearance_checked": False,
                    "minimum_environment_clearance": None,
                    "required_environment_clearance": None,
                    "environment_clearance_safe": None,
                    "environment_clearance_pair": None,
                }
            )
        else:
            record.update(
                {
                    "environment_clearance_checked": True,
                    "minimum_environment_clearance": (
                        self.environment_clearance.minimum_clearance
                    ),
                    "required_environment_clearance": (
                        self.environment_clearance.required_clearance
                    ),
                    "environment_clearance_safe": self.environment_clearance.safe,
                    "environment_clearance_pair": {
                        "arm_body": self.environment_clearance.arm_body,
                        "protected_body": self.environment_clearance.protected_body,
                        "arm_geometry": self.environment_clearance.arm_geometry,
                        "protected_geometry": (
                            self.environment_clearance.protected_geometry
                        ),
                    },
                }
            )
        if self.support is None:
            record.update(
                {
                    "support_checked": False,
                    "supporting_feet": None,
                    "support_margin": None,
                    "required_support_margin": None,
                    "support_safe": None,
                }
            )
        else:
            record.update(
                {
                    "support_checked": True,
                    "supporting_feet": list(self.support.supporting_feet),
                    "support_margin": self.support.support_margin,
                    "required_support_margin": self.support.required_margin,
                    "support_safe": self.support.safe,
                }
            )
        return record


@dataclass(frozen=True)
class ReachabilitySampleSet:
    """A fixed-base set of P0 labels with deterministic aggregate statistics."""

    base_pose: np.ndarray
    samples: tuple[ReachabilitySample, ...]

    def __post_init__(self) -> None:
        base_pose = np.asarray(self.base_pose, dtype=np.float64)
        if base_pose.shape != (3,) or not np.isfinite(base_pose).all():
            raise ValueError("base_pose must contain three finite values")
        object.__setattr__(self, "base_pose", base_pose.copy())

    def summary(self) -> dict[str, int | float]:
        total = len(self.samples)
        feasible = sum(sample.result.kinematic_feasible for sample in self.samples)
        joint_limit_safe = sum(
            sample.result.kinematic_feasible
            and sample.result.joint_limit_margin >= sample.required_joint_limit_margin
            for sample in self.samples
        )
        return {
            "total": total,
            "kinematic_feasible": feasible,
            "kinematic_unreachable": total - feasible,
            "joint_limit_safe": joint_limit_safe,
            "joint_limit_unsafe_or_unreachable": total - joint_limit_safe,
            "minimum_joint_limit_margin": min(
                (sample.result.joint_limit_margin for sample in self.samples),
                default=0.0,
            ),
        }

    def records(self) -> list[dict[str, object]]:
        return [sample.record() for sample in self.samples]


@dataclass(frozen=True)
class BasePosePerturbationSample:
    """One fixed target evaluated after a deterministic base-pose offset."""

    base_pose_offset: np.ndarray
    sample: ReachabilitySample

    def __post_init__(self) -> None:
        offset = np.asarray(self.base_pose_offset, dtype=np.float64)
        if offset.shape != (3,) or not np.isfinite(offset).all():
            raise ValueError("base_pose_offset must contain three finite values")
        object.__setattr__(self, "base_pose_offset", offset.copy())

    def record(self) -> dict[str, object]:
        record = self.sample.record()
        record["base_pose_offset"] = self.base_pose_offset.tolist()
        return record


@dataclass(frozen=True)
class BasePosePerturbationSet:
    """One scene-case target under a controlled set of NAV arrival offsets."""

    scene_case: str
    split: str
    nominal_base_pose: np.ndarray
    target_position: np.ndarray
    samples: tuple[BasePosePerturbationSample, ...]

    def __post_init__(self) -> None:
        if not self.scene_case:
            raise ValueError("scene_case must not be empty")
        if self.split not in ("calibration", "test"):
            raise ValueError("split must be calibration or test")
        for name in ("nominal_base_pose", "target_position"):
            vector = np.asarray(getattr(self, name), dtype=np.float64)
            if vector.shape != (3,) or not np.isfinite(vector).all():
                raise ValueError(f"{name} must contain three finite values")
            object.__setattr__(self, name, vector.copy())

    def summary(self) -> dict[str, int | float | str]:
        feasible = sum(sample.sample.result.kinematic_feasible for sample in self.samples)
        joint_limit_safe = sum(
            sample.sample.result.kinematic_feasible
            and (
                sample.sample.result.joint_limit_margin
                >= sample.sample.required_joint_limit_margin
            )
            for sample in self.samples
        )
        return {
            "scene_case": self.scene_case,
            "split": self.split,
            "total": len(self.samples),
            "kinematic_feasible": feasible,
            "kinematic_unreachable": len(self.samples) - feasible,
            "joint_limit_safe": joint_limit_safe,
            "joint_limit_unsafe_or_unreachable": len(self.samples) - joint_limit_safe,
            "minimum_joint_limit_margin": min(
                (sample.sample.result.joint_limit_margin for sample in self.samples),
                default=0.0,
            ),
        }

    def records(self) -> list[dict[str, object]]:
        return [
            {
                "scene_case": self.scene_case,
                "split": self.split,
                "nominal_base_pose": self.nominal_base_pose.tolist(),
                **sample.record(),
            }
            for sample in self.samples
        ]


def sample_fixed_base(
    oracle,
    base_pose: np.ndarray,
    target_positions: Iterable[np.ndarray],
    *,
    clearance_checker=None,
    required_self_clearance: float = 0.0,
    environment_clearance_checker=None,
    required_environment_clearance: float = 0.0,
    support_checker=None,
    required_support_margin: float = 0.0,
    required_joint_limit_margin: float = 0.0,
) -> ReachabilitySampleSet:
    """Evaluate target positions with one immutable base pose and one Oracle."""
    base = np.asarray(base_pose, dtype=np.float64)
    if base.shape != (3,) or not np.isfinite(base).all():
        raise ValueError("base_pose must contain three finite values")
    samples = tuple(
        _sample(
            oracle,
            ReachabilityQuery(base, target_position),
            clearance_checker=clearance_checker,
            required_self_clearance=required_self_clearance,
            environment_clearance_checker=environment_clearance_checker,
            required_environment_clearance=required_environment_clearance,
            support_checker=support_checker,
            required_support_margin=required_support_margin,
            required_joint_limit_margin=required_joint_limit_margin,
        )
        for target_position in target_positions
    )
    return ReachabilitySampleSet(base, samples)


def sample_base_pose_perturbations(
    oracle,
    nominal_base_pose: np.ndarray,
    target_position: np.ndarray,
    base_pose_offsets: Iterable[np.ndarray],
    *,
    scene_case: str,
    split: str,
    clearance_checker=None,
    required_self_clearance: float = 0.0,
    environment_clearance_checker=None,
    required_environment_clearance: float = 0.0,
    support_checker=None,
    required_support_margin: float = 0.0,
    required_joint_limit_margin: float = 0.0,
) -> BasePosePerturbationSet:
    """Label one target under deterministic position and yaw arrival errors."""
    nominal = np.asarray(nominal_base_pose, dtype=np.float64)
    target = np.asarray(target_position, dtype=np.float64)
    if nominal.shape != (3,) or not np.isfinite(nominal).all():
        raise ValueError("nominal_base_pose must contain three finite values")
    if target.shape != (3,) or not np.isfinite(target).all():
        raise ValueError("target_position must contain three finite values")
    samples = []
    for base_pose_offset in base_pose_offsets:
        offset = np.asarray(base_pose_offset, dtype=np.float64)
        if offset.shape != (3,) or not np.isfinite(offset).all():
            raise ValueError("base_pose_offset must contain three finite values")
        query = ReachabilityQuery(nominal + offset, target)
        samples.append(
            BasePosePerturbationSample(
                offset,
                _sample(
                    oracle,
                    query,
                    clearance_checker=clearance_checker,
                    required_self_clearance=required_self_clearance,
                    environment_clearance_checker=environment_clearance_checker,
                    required_environment_clearance=required_environment_clearance,
                    support_checker=support_checker,
                    required_support_margin=required_support_margin,
                    required_joint_limit_margin=required_joint_limit_margin,
                ),
            )
        )
    return BasePosePerturbationSet(
        scene_case=scene_case,
        split=split,
        nominal_base_pose=nominal,
        target_position=target,
        samples=tuple(samples),
    )


def _sample(
    oracle,
    query: ReachabilityQuery,
    *,
    clearance_checker,
    required_self_clearance: float,
    environment_clearance_checker,
    required_environment_clearance: float,
    support_checker,
    required_support_margin: float,
    required_joint_limit_margin: float,
) -> ReachabilitySample:
    if required_self_clearance < 0.0 or not np.isfinite(required_self_clearance):
        raise ValueError("required_self_clearance must be finite and non-negative")
    if (
        required_environment_clearance < 0.0
        or not np.isfinite(required_environment_clearance)
    ):
        raise ValueError(
            "required_environment_clearance must be finite and non-negative"
        )
    if (
        required_joint_limit_margin < 0.0
        or not np.isfinite(required_joint_limit_margin)
    ):
        raise ValueError(
            "required_joint_limit_margin must be finite and non-negative"
        )
    if required_support_margin < 0.0 or not np.isfinite(required_support_margin):
        raise ValueError("required_support_margin must be finite and non-negative")
    result = oracle.solve(query)
    self_clearance = None
    environment_clearance = None
    support = None
    if clearance_checker is not None and result.kinematic_feasible:
        self_clearance = clearance_checker.evaluate(
            query.base_pose,
            result.joint_solution,
            required_clearance=required_self_clearance,
        )
    if environment_clearance_checker is not None and result.kinematic_feasible:
        environment_clearance = environment_clearance_checker.evaluate(
            query.base_pose,
            result.joint_solution,
            required_clearance=required_environment_clearance,
        )
    if support_checker is not None and result.kinematic_feasible:
        support = support_checker.evaluate_configuration(
            query.base_pose,
            result.joint_solution,
            required_margin=required_support_margin,
        )
    return ReachabilitySample(
        query,
        result,
        self_clearance,
        environment_clearance,
        support,
        required_joint_limit_margin,
    )