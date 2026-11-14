"""Finite nominal path ranking, not a controller or physical safety certificate.

OmniNav v1 equations 33--42: dual-ellipsoid target/shell cost plus alignment and
chassis softplus cost. Parameters MUST be supplied; no ARX-to-Piper fit is implied.
P1: max_path min_sample,constraint signed_margin / declared_positive_scale.
None means missing, never zero/feasible. No SDK, learning, FK or physics imports.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence


def finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def vector(value: Sequence[float], size: int, name: str) -> tuple[float, ...]:
    if len(value) != size:
        raise ValueError(f"{name} needs {size} entries")
    return tuple(finite(x, name) for x in value)


def positive(value: float, name: str) -> float:
    value = finite(value, name)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x)) if x >= 0 else math.exp(x) / (1 + math.exp(x))


def softplus(x: float) -> float:
    return max(x, 0.0) + math.log1p(math.exp(-abs(x)))


@dataclass(frozen=True)
class Ellipsoid:
    center: tuple[float, float, float]
    metric: tuple[tuple[float, float, float], ...]

    def __post_init__(self):
        center = vector(self.center, 3, "ellipsoid center")
        if len(self.metric) != 3:
            raise ValueError("ellipsoid metric needs 3 rows")
        metric = tuple(vector(row, 3, "ellipsoid metric") for row in self.metric)
        if any(abs(metric[i][j] - metric[j][i]) > 1e-12 for i in range(3) for j in range(3)):
            raise ValueError("ellipsoid metric must be symmetric")
        # Positive definiteness via Cholesky, not clipping an indefinite metric.
        lower = [[0.0] * 3 for _ in range(3)]
        for i in range(3):
            for j in range(i + 1):
                residual = metric[i][j] - sum(lower[i][k] * lower[j][k] for k in range(j))
                if i == j:
                    if residual <= 0:
                        raise ValueError("ellipsoid metric must be positive definite")
                    lower[i][j] = math.sqrt(residual)
                else:
                    lower[i][j] = residual / lower[j][j]
        object.__setattr__(self, "center", center)
        object.__setattr__(self, "metric", metric)

    def distance_squared(self, point: Sequence[float]) -> float:
        p = vector(point, 3, "point")
        delta = tuple(x - y for x, y in zip(p, self.center))
        result = sum(delta[i] * self.metric[i][j] * delta[j] for i in range(3) for j in range(3))
        return finite(result, "ellipsoid quadratic form")


@dataclass(frozen=True)
class BasePose:
    """Rigid pose: actual rotation, not yaw-flattened tilted body observations."""
    position: tuple[float, float, float]
    rotation: tuple[tuple[float, float, float], ...]  # R_world_from_base

    def __post_init__(self):
        position = vector(self.position, 3, "base position")
        if len(self.rotation) != 3:
            raise ValueError("rotation needs 3 rows")
        r = tuple(vector(row, 3, "rotation") for row in self.rotation)
        for i in range(3):
            for j in range(3):
                if abs(sum(r[k][i] * r[k][j] for k in range(3)) - float(i == j)) > 1e-9:
                    raise ValueError("rotation must be orthonormal")
        det = sum(r[0][i] * (r[1][(i + 1) % 3] * r[2][(i + 2) % 3]
                            - r[1][(i + 2) % 3] * r[2][(i + 1) % 3]) for i in range(3))
        if abs(det - 1) > 1e-9:
            raise ValueError("rotation must have determinant +1")
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "rotation", r)

    @classmethod
    def planar(cls, x: float, y: float, yaw: float, height: float) -> BasePose:
        yaw = finite(yaw, "yaw")
        c, s = math.cos(yaw), math.sin(yaw)
        return cls((x, y, height), ((c, -s, 0), (s, c, 0), (0, 0, 1)))

    def to_base(self, point_world: Sequence[float]) -> tuple[float, ...]:
        p = vector(point_world, 3, "world point")
        delta = tuple(x - y for x, y in zip(p, self.position))
        return tuple(sum(self.rotation[j][i] * delta[j] for j in range(3)) for i in range(3))


@dataclass(frozen=True)
class OmniNavParameters:
    outer: Ellipsoid
    inner: Ellipsoid
    alignment_weight: float
    reach_weight: float
    collision_weight: float
    shell_weight: float
    chassis_radius_m: float
    chassis_safety_margin_m: float

    def __post_init__(self):
        for name in ("alignment_weight", "reach_weight", "collision_weight", "shell_weight",
                     "chassis_safety_margin_m"):
            if finite(getattr(self, name), name) < 0:
                raise ValueError(f"{name} must be nonnegative")
        if abs(self.alignment_weight + self.reach_weight + self.collision_weight - 1) > 1e-9:
            raise ValueError("paper objective weights must sum to one")
        positive(self.chassis_radius_m, "chassis_radius_m")


def omninav_cost(pose: BasePose, target_world: Sequence[float],
                 obstacle_points_world: Sequence[Sequence[float]], p: OmniNavParameters) -> dict:
    """Paper-form objective only; supplied ellipsoids, fixed point-cloud stencil.

    No ellipsoid fit, IK map, perception, PSO or navigation is implemented here.
    Empty obstacles explicitly means a known-empty stencil, NOT missing geometry.
    """
    target = vector(target_world, 3, "target")
    delta = (target[0] - pose.position[0], target[1] - pose.position[1])
    heading = (pose.rotation[0][0], pose.rotation[1][0])
    norm = math.hypot(*delta) * math.hypot(*heading)
    if norm <= 1e-12:
        raise ValueError("alignment has undefined planar target/heading direction")
    alignment = 1 - max(-1.0, min(1.0, sum(x * y for x, y in zip(delta, heading)) / norm))
    target_base = pose.to_base(target)
    target_cost = (max(p.outer.distance_squared(target_base) - 1, 0) ** 2
                   + max(1 - p.inner.distance_squared(target_base), 0) ** 2)
    obstacles = [pose.to_base(point) for point in obstacle_points_world]
    shell = (sum(max(1 - p.outer.distance_squared(point), 0)
                 * sigmoid(p.inner.distance_squared(point) - 1) for point in obstacles) / len(obstacles)
             if obstacles else 0.0)
    collision = (sum(softplus(p.chassis_radius_m + p.chassis_safety_margin_m - math.hypot(*point[:2]))
                     for point in obstacles) / len(obstacles) if obstacles else 0.0)
    reach = target_cost + p.shell_weight * shell
    total = p.alignment_weight * alignment + p.reach_weight * reach + p.collision_weight * collision
    finite(total, "OmniNav objective")
    return dict(alignment=alignment, target=target_cost, shell=shell, reach=reach,
                collision=collision, total=total,
                scope="paper_form_only_no_Piper_fit_or_full_OmniNav_reproduction")


@dataclass(frozen=True)
class Constraint:
    name: str
    unit: str
    scale: float  # signed g/scale; original physical threshold already in g

    def __post_init__(self):
        if not self.name or not self.unit:
            raise ValueError("constraint needs name and physical unit")
        positive(self.scale, "normalization scale")


@dataclass(frozen=True)
class Sample:
    time_s: float
    margins: Mapping[str, float | None]


@dataclass(frozen=True)
class PhaseSample:
    """Dimensionless path phase; explicitly not a physical timestamp."""
    phase: float
    margins: Mapping[str, float | None]


@dataclass(frozen=True)
class NominalPath:
    path_id: str
    samples: tuple[Sample | PhaseSample, ...]
    supported_model_domain: bool | None = True
    sample_axis: str = "time_s"


@dataclass(frozen=True)
class PathScore:
    path_id: str
    status: str  # feasible / infeasible / unknown
    lower: float  # exact or -inf with missing values
    upper: float  # min known margins, +inf if none; never fill missing with zero
    rho: float | None
    witness: tuple[int, str] | None
    missing: tuple[tuple[int, str], ...]


def path_score(path: NominalPath, constraints: Sequence[Constraint], *, endpoint_only: bool = False) -> PathScore:
    if not constraints or len({c.name for c in constraints}) != len(constraints):
        raise ValueError("need unique declared constraints")
    if not path.path_id or not path.samples:
        raise ValueError("path needs id and at least one sample")
    if path.supported_model_domain is not None and type(path.supported_model_domain) is not bool:
        raise ValueError("model-domain flag must be bool or None")
    if path.sample_axis == "time_s" and all(isinstance(s, Sample) for s in path.samples):
        times = [finite(s.time_s, "sample time") for s in path.samples]
    elif path.sample_axis == "normalized_phase" and all(isinstance(s, PhaseSample) for s in path.samples):
        times = [finite(s.phase, "sample phase") for s in path.samples]
        if times[-1] > 1:
            raise ValueError("normalized phase must be in [0,1]")
    else:
        raise ValueError("path sample type and axis must agree")
    if times[0] < 0 or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("path times/phases must be nonnegative and strictly increasing")
    names = {c.name for c in constraints}
    # Reject typos even if using only the endpoint; still no margin imputation.
    if any(set(s.margins) - names for s in path.samples):
        raise ValueError("undeclared constraint in path")
    if path.supported_model_domain is not True:
        return PathScore(path.path_id, "unknown", -math.inf, math.inf, None, None, ())
    values, missing = [], []
    indices = [len(path.samples) - 1] if endpoint_only else range(len(path.samples))
    for k in indices:
        for c in constraints:
            value = path.samples[k].margins.get(c.name)
            if value is None:
                missing.append((k, c.name))
            else:
                values.append((finite(finite(value, c.name) / c.scale, "normalized margin"), k, c.name))
    upper, witness = (math.inf, None) if not values else (min(values)[0], min(values)[1:])
    lower = upper if not missing else -math.inf
    rho = upper if not missing else None
    status = "infeasible" if upper < 0 else "feasible" if lower >= 0 else "unknown"
    return PathScore(path.path_id, status, lower, upper, rho, witness, tuple(missing))


@dataclass(frozen=True)
class CandidateScore:
    status: str
    lower: float
    upper: float
    rho: float | None
    best_known_path_id: str | None
    paths: tuple[PathScore, ...]


def candidate_score(paths: Sequence[NominalPath], constraints: Sequence[Constraint], *,
                    endpoint_only: bool = False) -> CandidateScore:
    """Bounds for max of path bottlenecks, preserving incomplete alternatives.

    Empty/unavailable path set is UNKNOWN, not proof that the robot is infeasible.
    Exact max is possible with incomplete paths only if their known upper bounds
    cannot beat the best complete path. Unsupported model domains stay UNKNOWN.
    """
    if len({p.path_id for p in paths}) != len(paths):
        raise ValueError("duplicate path ids")
    if not paths:
        # Validate even on empty path sets.
        if not constraints or len({c.name for c in constraints}) != len(constraints):
            raise ValueError("need unique declared constraints")
        return CandidateScore("unknown", -math.inf, math.inf, None, None, ())
    results = tuple(path_score(p, constraints, endpoint_only=endpoint_only) for p in paths)
    lower, upper = max(p.lower for p in results), max(p.upper for p in results)
    exact = lower == upper and math.isfinite(lower)
    status = "feasible" if lower >= 0 else "infeasible" if upper < 0 else "unknown"
    best = next((p.path_id for p in results if p.rho is not None and p.rho == lower), None)
    return CandidateScore(status, lower, upper, lower if exact else None, best, results)


def select_exact_candidate(base_costs: Mapping[str, float], scores: Mapping[str, CandidateScore],
                           margin_weight: float) -> dict:
    """P2 on the completely evaluable finite set; incomplete contenders abstain.

    This conservative first implementation does not silently delete UNKNOWN
    contenders and report the result as the global maximizer/minimizer.
    """
    weight = finite(margin_weight, "margin_weight")
    if weight < 0 or set(base_costs) != set(scores):
        raise ValueError("need nonnegative weight and same candidate ids")
    for cost in base_costs.values():
        finite(cost, "base cost")
    incomplete = [cid for cid, s in scores.items() if s.status != "infeasible" and s.rho is None]
    if incomplete:
        return dict(status="unknown", candidate_id=None, incomplete_candidates=sorted(incomplete))
    feasible = [(base_costs[cid] - weight * s.rho, cid) for cid, s in scores.items()
                if s.status == "feasible" and s.rho is not None]
    if not feasible:
        return dict(status="abstain", candidate_id=None, incomplete_candidates=[])
    objective, cid = min(feasible)  # deterministic tie by id, not seed search
    return dict(status="selected_nominal", candidate_id=cid, objective=objective,
                path_id=scores[cid].best_known_path_id, incomplete_candidates=[])


def quasi_static_torque(gravity_compensation: Sequence[float], jacobian: Sequence[Sequence[float]],
                        external_wrench: Sequence[float]) -> tuple[float, ...]:
    """tau = tau_g - J^T w_ext at STATIC equilibrium, not actuator prediction.

    w_ext is force/moment applied BY environment TO robot, [Fx,Fy,Fz,Mx,My,Mz].
    J spatial rows use that SAME expressed frame and contact point. tau_g is the
    modeled compensation joint torque. Neither future measured force nor current
    gravity copied along a moving path is justified by this algebra.
    """
    g = vector(gravity_compensation, len(gravity_compensation), "gravity compensation")
    if not g or len(jacobian) != 6:
        raise ValueError("need nonempty joints and six-row spatial Jacobian")
    j = tuple(vector(row, len(g), "Jacobian row") for row in jacobian)
    w = vector(external_wrench, 6, "external wrench")
    return tuple(finite(g[i] - sum(j[k][i] * w[k] for k in range(6)), "static torque") for i in range(len(g)))
