"""Exact binomial bounds for a fixed, independently evaluated skill contract."""

import math
import re
from dataclasses import dataclass
from typing import Sequence

from scipy.stats import beta


def lower_success_probability(successes: int, trials: int, alpha: float = 0.05) -> float:
    """One-sided Clopper-Pearson lower bound, conditional on iid Bernoulli trials."""
    if not isinstance(successes, int) or not isinstance(trials, int) or not 0 <= successes <= trials or trials < 1:
        raise ValueError("Require integer 0 <= successes <= trials and trials >= 1")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between 0 and 1")
    if successes == 0:
        return 0.0
    return float(beta.ppf(alpha, successes, trials - successes + 1))


def minimum_all_successes(target_probability: float, alpha: float = 0.05) -> int:
    """Trials needed with zero failures for the lower bound to reach target."""
    if not 0 < target_probability < 1 or not 0 < alpha < 1:
        raise ValueError("target_probability and alpha must lie strictly between 0 and 1")
    estimate = math.ceil(math.log(alpha) / math.log(target_probability))
    while alpha ** (1 / estimate) < target_probability:
        estimate += 1
    return estimate


def minimum_all_successes_for_union(
    target_joint_probability: float, components: int, alpha: float = 0.05,
) -> int:
    """Zero-failure trials per predeclared component under equal Bonferroni budgets.

    A union bound allocates (1 - target_joint_probability) / components
    failure probability and alpha / components confidence error to each
    component. This is a sample-size diagnostic, not proof of its event labels.
    """
    if not isinstance(components, int) or components < 1:
        raise ValueError("components must be a positive integer")
    if not 0.0 < target_joint_probability < 1.0 or not 0.0 < alpha < 1.0:
        raise ValueError("joint target and alpha must lie strictly between 0 and 1")
    per_component_target = 1.0 - (1.0 - target_joint_probability) / components
    return minimum_all_successes(per_component_target, alpha / components)


@dataclass(frozen=True)
class FullRolloutCoverageRecord:
    rollout_id: str
    contract_sha256: str
    coverage_unit: str
    joint_enclosure_satisfied: bool


@dataclass(frozen=True)
class FullRolloutCoverageSummary:
    contract_sha256: str
    successes: int
    trials: int
    confidence_level: float
    joint_coverage_lower_bound: float


def calibrate_full_rollout_coverage(
    records: Sequence[FullRolloutCoverageRecord],
    *,
    expected_contract_sha256: str,
    alpha: float = 0.05,
) -> FullRolloutCoverageSummary:
    """Compute an exact bound from externally verified, independent rollout events.

    The caller must audit the joint event, frozen contract and iid sampling. A
    per-step event or historical partial-state log is not a valid input.
    """
    if not re.fullmatch(r"[0-9a-f]{64}", expected_contract_sha256):
        raise ValueError("expected_contract_sha256 must be a lowercase SHA-256")
    if not records:
        raise ValueError("At least one full rollout is required")
    seen: set[str] = set()
    successes = 0
    for record in records:
        if not record.rollout_id or record.rollout_id in seen:
            raise ValueError("Rollout IDs must be nonempty and unique")
        seen.add(record.rollout_id)
        if record.contract_sha256 != expected_contract_sha256:
            raise ValueError("Coverage records must share the frozen contract")
        if record.coverage_unit != "full_rollout":
            raise ValueError("Coverage records must represent full rollout events")
        if type(record.joint_enclosure_satisfied) is not bool:
            raise ValueError("Joint enclosure outcomes must be Boolean")
        successes += record.joint_enclosure_satisfied
    return FullRolloutCoverageSummary(
        expected_contract_sha256, successes, len(records), 1.0 - alpha,
        lower_success_probability(successes, len(records), alpha),
    )
