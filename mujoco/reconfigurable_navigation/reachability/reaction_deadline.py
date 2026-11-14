"""Necessary timing condition for a loaded-contact-triggered intervention."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ReactionDeadlineAssessment:
    state: str
    available_substeps: int | None
    contact_authorized: bool = False


@dataclass(frozen=True)
class LoadedReactionActionEvidence:
    action_id: str
    earliest_effect_delay_lower_bound_substeps: int | None
    counterfactual_prefix_certified: bool


def assess_loaded_contact_reaction_deadline(
    *,
    first_illegal_substep: int,
    prior_legal_loaded_control_end_substep: int | None,
    earliest_effect_delay_lower_bound_substeps: int | None,
) -> ReactionDeadlineAssessment:
    """Refute a reaction from one observed loaded-contact control-step end.

    Substeps are one-based end-of-physics-step ticks on the same clock. The
    caller must prove that the observation can be consumed no earlier than its
    stated tick, that the effect-delay lower bound includes acquisition and
    actuation, and that the counterfactual trajectory agrees with the recorded
    one until the new action can first take effect. A later effect cannot avert
    the recorded event. An earlier possible effect proves no safety or success.
    This says nothing about actions chosen from precontact or earlier history.
    """
    if isinstance(first_illegal_substep, bool) or not isinstance(first_illegal_substep, int) \
            or first_illegal_substep < 1:
        raise ValueError("First illegal tick must be a positive integer")
    if prior_legal_loaded_control_end_substep is not None:
        if (isinstance(prior_legal_loaded_control_end_substep, bool)
                or not isinstance(prior_legal_loaded_control_end_substep, int)
                or not 1 <= prior_legal_loaded_control_end_substep < first_illegal_substep):
            raise ValueError("Prior legal loaded tick must precede the event")
    if earliest_effect_delay_lower_bound_substeps is not None:
        if (isinstance(earliest_effect_delay_lower_bound_substeps, bool)
                or not isinstance(earliest_effect_delay_lower_bound_substeps, int)
                or earliest_effect_delay_lower_bound_substeps < 0):
            raise ValueError("Effect-delay lower bound must be nonnegative ticks")
    if prior_legal_loaded_control_end_substep is None:
        return ReactionDeadlineAssessment("conditional_no_prior_loaded_anchor", None)
    available = first_illegal_substep - prior_legal_loaded_control_end_substep
    if earliest_effect_delay_lower_bound_substeps is None:
        state = "abstain_missing_effect_delay_lower_bound"
    elif earliest_effect_delay_lower_bound_substeps >= available:
        state = "conditional_reaction_too_late"
    else:
        state = "undetermined"
    return ReactionDeadlineAssessment(state, available)


def assess_allowed_loaded_reaction_deadline(
    *,
    first_illegal_substep: int,
    prior_legal_loaded_control_end_substep: int | None,
    allowed_actions: Sequence[LoadedReactionActionEvidence],
    allowed_action_set_complete: bool,
) -> ReactionDeadlineAssessment:
    """Refute every permitted reaction initiated after one loaded observation.

    Each ID must cover an entire permitted causal response class, including
    combinations and schedules if those are allowed. The caller must establish
    that this finite list exhausts that class, and certify each action's
    same-initial-state, same-disturbance prefix through its earliest effect.
    This cannot refute actions already initiated before the observation.
    """
    if not isinstance(allowed_action_set_complete, bool):
        raise ValueError("Action-set completeness must be a boolean")
    if not allowed_actions:
        raise ValueError("Allowed action set must be nonempty")
    if any(not isinstance(action, LoadedReactionActionEvidence) for action in allowed_actions):
        raise ValueError("Every allowed action needs evidence")
    action_ids = [action.action_id for action in allowed_actions]
    if any(not isinstance(action_id, str) or not action_id
           or action_id != action_id.strip() for action_id in action_ids):
        raise ValueError("Action IDs must be nonempty canonical strings")
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("Allowed action IDs must be unique")
    if any(not isinstance(action.counterfactual_prefix_certified, bool)
           for action in allowed_actions):
        raise ValueError("Prefix certification must be a boolean")

    per_action = [assess_loaded_contact_reaction_deadline(
        first_illegal_substep=first_illegal_substep,
        prior_legal_loaded_control_end_substep=prior_legal_loaded_control_end_substep,
        earliest_effect_delay_lower_bound_substeps=action.earliest_effect_delay_lower_bound_substeps,
    ) for action in allowed_actions]
    available = per_action[0].available_substeps
    if available is None:
        return ReactionDeadlineAssessment("conditional_no_prior_loaded_anchor", None)
    if not allowed_action_set_complete:
        return ReactionDeadlineAssessment("abstain_incomplete_action_set", available)
    if any(not action.counterfactual_prefix_certified for action in allowed_actions):
        return ReactionDeadlineAssessment("abstain_missing_counterfactual_prefix", available)
    if any(result.state == "abstain_missing_effect_delay_lower_bound" for result in per_action):
        return ReactionDeadlineAssessment("abstain_missing_effect_delay_lower_bound", available)
    if any(result.state == "undetermined" for result in per_action):
        return ReactionDeadlineAssessment("undetermined", available)
    return ReactionDeadlineAssessment("conditional_all_allowed_reactions_too_late", available)
