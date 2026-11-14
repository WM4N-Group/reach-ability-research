"""Conditional finite-horizon viability on observation-history classes.

The graph and its joint error bound are external proof obligations. This module
checks their contract and quantifier order; it does not calibrate a physics model
or authorize contact execution.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Mapping


SAFETY_TERMS = frozenset({
    "base_contact", "invalid_hand_contact", "bad_orientation", "low_posture",
    "arm_body_clearance", "self_collision", "box_tipped", "box_contact",
    "joint_limit", "actuator_limit",
})
FAILURE_TERMS = SAFETY_TERMS | {"time_out", "push_budget_exhausted"}


def _sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))


@dataclass(frozen=True)
class BeliefTransition:
    """Action edge with safety lower bounds over its entire physical interval."""

    action_id: str
    successor_ids: tuple[str, ...]
    interval_safety_margin_lower_bounds: Mapping[str, float]


@dataclass(frozen=True)
class BeliefNode:
    node_id: str
    step: int
    safety_margin_lower_bounds: Mapping[str, float]
    task_reached_for_all_states: bool
    transitions: tuple[BeliefTransition, ...] = ()
    observation_history_id: str = ""


@dataclass(frozen=True)
class JointBoundEvidence:
    model_sha256: str
    calibration_manifest_sha256: str
    policy_sha256: str
    control_sha256: str
    scene_case: str
    scene_contract_sha256: str
    entry_distribution_sha256: str
    entry_observation_history_id: str
    joint_coverage_lower_bound: float | None
    coverage_confidence_level: float | None
    coverage_unit: str
    coverage_action_scope: str
    coverage_horizon_steps: int | None
    coverage_step_dt_s: float | None
    state_enclosure_validated: bool
    transition_enclosure_validated: bool
    command_realization_enclosure_validated: bool
    observation_partition_validated: bool
    max_control_delay_steps: int | None
    modelled_delay_steps: int | None
    validated_action_ids: frozenset[str]

    def __post_init__(self) -> None:
        for name in ("model_sha256", "calibration_manifest_sha256", "policy_sha256",
                     "control_sha256", "scene_contract_sha256", "entry_distribution_sha256"):
            if not _sha256(getattr(self, name)):
                raise ValueError(f"{name} must be a lowercase SHA-256")
        if not self.scene_case:
            raise ValueError("scene_case must name the calibrated layout family")
        if not self.entry_observation_history_id:
            raise ValueError("entry_observation_history_id must identify the calibrated root group")
        coverage = self.joint_coverage_lower_bound
        if coverage is not None and (not math.isfinite(coverage) or not 0.0 <= coverage <= 1.0):
            raise ValueError("joint_coverage_lower_bound must lie in [0, 1]")
        confidence = self.coverage_confidence_level
        if confidence is not None and (not math.isfinite(confidence) or not 0.0 < confidence <= 1.0):
            raise ValueError("coverage_confidence_level must lie in (0, 1]")
        if self.coverage_horizon_steps is not None and (
                not isinstance(self.coverage_horizon_steps, int) or self.coverage_horizon_steps < 0):
            raise ValueError("coverage_horizon_steps must be a nonnegative integer or unknown")
        if self.coverage_step_dt_s is not None and (
                not math.isfinite(self.coverage_step_dt_s) or self.coverage_step_dt_s <= 0.0):
            raise ValueError("coverage_step_dt_s must be positive and finite or unknown")
        for name in ("state_enclosure_validated", "transition_enclosure_validated",
                     "command_realization_enclosure_validated", "observation_partition_validated"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be Boolean")
        for name in ("max_control_delay_steps", "modelled_delay_steps"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"{name} must be a nonnegative integer or unknown")
        if any(not action_id for action_id in self.validated_action_ids):
            raise ValueError("validated action IDs must be nonempty")


@dataclass(frozen=True)
class HandoffViabilityDecision:
    verdict: str
    reason: str
    causal_policy: Mapping[str, str]
    joint_coverage_lower_bound: float | None
    contact_authorized: bool = False


def _validate_graph(nodes: Mapping[str, BeliefNode], root_id: str, horizon_steps: int) -> None:
    if root_id not in nodes or nodes[root_id].step != 0:
        raise ValueError("root must be a step-zero belief node")
    history_steps: dict[str, int] = {}
    for key, node in nodes.items():
        if node.node_id != key or not 0 <= node.step <= horizon_steps:
            raise ValueError(f"Invalid belief node: {key}")
        if not node.observation_history_id:
            raise ValueError(f"Missing observation history identity: {key}")
        previous_step = history_steps.setdefault(node.observation_history_id, node.step)
        if previous_step != node.step:
            raise ValueError("An observation history cannot appear at different steps")
        if not isinstance(node.task_reached_for_all_states, bool):
            raise ValueError(f"Goal guarantee must be Boolean: {key}")
        if any(not math.isfinite(value) for value in node.safety_margin_lower_bounds.values()):
            raise ValueError(f"Nonfinite safety margin: {key}")
        actions = [transition.action_id for transition in node.transitions]
        if len(actions) != len(set(actions)) or any(not action for action in actions):
            raise ValueError(f"Duplicate or empty action at {key}")
        for transition in node.transitions:
            if not transition.successor_ids or node.step == horizon_steps:
                raise ValueError(f"Empty or late transition at {key}")
            if any(not math.isfinite(value)
                   for value in transition.interval_safety_margin_lower_bounds.values()):
                raise ValueError(f"Nonfinite interval safety margin: {key}")
            for successor_id in transition.successor_ids:
                if successor_id not in nodes or nodes[successor_id].step != node.step + 1:
                    raise ValueError(f"Transition from {key} must advance exactly one step")


def evaluate_bounded_handoff(
    nodes: Mapping[str, BeliefNode],
    root_id: str,
    *,
    horizon_steps: int,
    step_dt_s: float,
    remaining_push_budget_s: float,
    expected_policy_sha256: str,
    expected_control_sha256: str,
    expected_model_sha256: str,
    expected_calibration_manifest_sha256: str,
    expected_scene_case: str,
    expected_scene_contract_sha256: str,
    expected_entry_distribution_sha256: str,
    required_joint_coverage: float,
    required_coverage_confidence: float,
    evidence: JointBoundEvidence | None,
) -> HandoffViabilityDecision:
    """Find one causal action per observation history that wins for every successor.

    A positive result is conditional on the supplied validated overapproximation
    and its *joint* coverage. It is never an Isaac/MuJoCo or real-contact gate.
    """
    if (not isinstance(horizon_steps, int) or horizon_steps < 0
            or not math.isfinite(step_dt_s) or step_dt_s <= 0.0
            or not math.isfinite(remaining_push_budget_s) or remaining_push_budget_s <= 0.0
            or not 0.0 < required_joint_coverage <= 1.0
            or not 0.0 < required_coverage_confidence <= 1.0):
        raise ValueError("Require a finite positive budget, step duration, coverage and confidence target")
    if not all(_sha256(value) for value in (
            expected_policy_sha256, expected_control_sha256,
            expected_model_sha256, expected_calibration_manifest_sha256,
            expected_scene_contract_sha256, expected_entry_distribution_sha256)):
        raise ValueError("Expected policy, control, model, calibration, scene and entry distribution must be SHA-256 pinned")
    if not expected_scene_case:
        raise ValueError("Expected scene case must be named")
    _validate_graph(nodes, root_id, horizon_steps)

    def abstain(reason: str) -> HandoffViabilityDecision:
        return HandoffViabilityDecision("abstain", reason, {}, None)

    if evidence is None:
        return abstain("missing_joint_bound_evidence")
    if (evidence.policy_sha256 != expected_policy_sha256
            or evidence.control_sha256 != expected_control_sha256
            or evidence.model_sha256 != expected_model_sha256
            or evidence.calibration_manifest_sha256 != expected_calibration_manifest_sha256
            or evidence.scene_case != expected_scene_case
            or evidence.scene_contract_sha256 != expected_scene_contract_sha256):
        return abstain("source_or_scene_outside_calibration")
    if (evidence.entry_distribution_sha256 != expected_entry_distribution_sha256
            or evidence.entry_observation_history_id != nodes[root_id].observation_history_id):
        return abstain("entry_distribution_or_history_outside_calibration")
    if not evidence.command_realization_enclosure_validated:
        return abstain("unvalidated_command_realization")
    if (not evidence.state_enclosure_validated or not evidence.transition_enclosure_validated
            or not evidence.observation_partition_validated):
        return abstain("unvalidated_state_transition_or_observation_cover")
    if (evidence.joint_coverage_lower_bound is None
            or evidence.joint_coverage_lower_bound < required_joint_coverage):
        return abstain("insufficient_joint_coverage")
    if evidence.coverage_unit != "full_rollout":
        return abstain("coverage_not_full_rollout")
    if evidence.coverage_action_scope != "all_graph_actions_and_branches":
        return abstain("coverage_not_action_uniform")
    if (evidence.coverage_confidence_level is None
            or evidence.coverage_confidence_level < required_coverage_confidence):
        return abstain("insufficient_coverage_confidence")
    if (evidence.coverage_horizon_steps != horizon_steps
            or evidence.coverage_step_dt_s != step_dt_s):
        return abstain("coverage_horizon_mismatch")
    if (evidence.max_control_delay_steps is None or evidence.modelled_delay_steps is None
            or evidence.modelled_delay_steps < evidence.max_control_delay_steps):
        return abstain("unbounded_or_unmodelled_control_delay")
    if horizon_steps * step_dt_s > remaining_push_budget_s + 1e-12:
        return abstain("horizon_exceeds_push_budget")

    groups: dict[str, list[BeliefNode]] = {}
    for node in nodes.values():
        groups.setdefault(node.observation_history_id, []).append(node)
    choices: dict[str, tuple[str, tuple[str, ...]]] = {}
    winning: dict[str, bool] = {}
    histories_by_step: list[list[str]] = [[] for _ in range(horizon_steps + 1)]
    for history_id, group in groups.items():
        histories_by_step[group[0].step].append(history_id)
    for step in range(horizon_steps, -1, -1):
        for history_id in histories_by_step[step]:
            group = groups[history_id]
            if any(node.safety_margin_lower_bounds.get(term, -math.inf) <= 0.0
                   for node in group for term in SAFETY_TERMS):
                winning[history_id] = False
                continue
            if all(node.task_reached_for_all_states for node in group):
                winning[history_id] = True
                continue
            winning[history_id] = False
            if step == horizon_steps:
                continue
            common_actions = set.intersection(*(
                {transition.action_id for transition in node.transitions} for node in group
            ))
            for action_id in sorted(common_actions & evidence.validated_action_ids):
                if any(transition.interval_safety_margin_lower_bounds.get(term, -math.inf) <= 0.0
                       for node in group for transition in node.transitions
                       if transition.action_id == action_id for term in SAFETY_TERMS):
                    continue
                successors = {
                    nodes[successor_id].observation_history_id
                    for node in group for transition in node.transitions
                    if transition.action_id == action_id
                    for successor_id in transition.successor_ids
                }
                if all(winning[successor] for successor in successors):
                    choices[history_id] = (action_id, tuple(sorted(successors)))
                    winning[history_id] = True
                    break

    root_history_id = nodes[root_id].observation_history_id
    if not winning[root_history_id]:
        return abstain("no_inner_policy_proved_by_supplied_bounds")
    policy: dict[str, str] = {}
    pending = [root_history_id]
    while pending:
        history_id = pending.pop()
        if history_id in choices and history_id not in policy:
            action_id, successors = choices[history_id]
            policy[history_id] = action_id
            pending.extend(reversed(successors))
    return HandoffViabilityDecision("model_conditional_inner_set", "all_branches_safe_and_reach_goal",
                                    policy, evidence.joint_coverage_lower_bound)


@dataclass(frozen=True)
class MatchedActionWitness:
    matching_audit_sha256: str
    candidate_report_sha256: str
    action_id: str
    pre_action_trace_equal: bool
    terminal_reason: str


def classify_matched_action_witness(witness: MatchedActionWitness) -> str:
    """Falsify only a frozen action at one matched state, never a whole action class."""
    if (not _sha256(witness.matching_audit_sha256)
            or not _sha256(witness.candidate_report_sha256)
            or not witness.action_id):
        raise ValueError("A witness needs pinned matching audit, candidate and action identity")
    if not witness.pre_action_trace_equal:
        return "abstain_unmatched_rollout"
    if witness.terminal_reason in FAILURE_TERMS:
        return "refuted_at_observed_state"
    if witness.terminal_reason == "box_settled":
        return "observed_success_only"
    return "abstain_unknown_terminal_reason"
