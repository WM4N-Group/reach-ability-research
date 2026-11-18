"""Reward only from a *new* declared training collector's closed native attempt.

No task-success inference from pose, local NN, partial receipts, or bad engineering.
This module does not grant training use; a future collector must prove pins/lease.
"""
from dataclasses import dataclass
from terminal_action import BrakeAction


def _sha(value):
    return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


@dataclass(frozen=True)
class TrainAttempt:
    rollout_id: str
    used_action: BrakeAction
    purpose: str
    ancestor_id: str
    actual_admit: bool
    actual_task_progress_after_admit: bool
    outcome: str
    full_native_terminal_succeeded: bool
    original_placement_verified_at_terminal: bool
    original_stow_verified_at_terminal: bool
    exact_guard_rejection_stage: str | None
    resource_or_engineering_failure: bool
    real_closed_result_sha256: str
    active_program_freeze_sha256: str
    behavior_policy_sha256: str


def reward(attempt, *, registered_program, allocated_ancestors):
    """Return None for a non-learning censor, else the binary guarded reward.

    `registered_program` and `allocated_ancestors` are external verified inputs
    from the future trainer's purpose/owner registry, never the row's authority.
    """
    if type(attempt) is not TrainAttempt or type(attempt.used_action) is not BrakeAction:
        raise TypeError('Explicit typed native train handoff')
    if not (_sha(registered_program) and _sha(attempt.real_closed_result_sha256)
            and registered_program == attempt.active_program_freeze_sha256):
        raise ValueError('Exact new train program/result pins required')
    if attempt.purpose != 'PUSH_TERMINAL_ONLINE_TRAIN_ONLY' or attempt.ancestor_id not in allocated_ancestors:
        raise ValueError('Not preregistered purpose/ancestor; DEV/EVAL cannot enter fit')
    if not attempt.rollout_id:
        raise ValueError('Unique rollout identity required')
    if any(type(x) is not bool for x in (attempt.actual_admit, attempt.actual_task_progress_after_admit,
            attempt.full_native_terminal_succeeded, attempt.original_placement_verified_at_terminal,
            attempt.original_stow_verified_at_terminal, attempt.resource_or_engineering_failure)):
        raise TypeError('No coerced facts or UNKNOWN-as-false')
    if attempt.resource_or_engineering_failure or not (attempt.actual_admit and attempt.actual_task_progress_after_admit):
        return None
    if attempt.outcome == 'ORIGINAL_FULL_PUSH_SUCCESS':
        if not (attempt.full_native_terminal_succeeded and attempt.original_placement_verified_at_terminal
                and attempt.original_stow_verified_at_terminal and attempt.exact_guard_rejection_stage is None):
            raise ValueError('Incomplete or inconsistent original success receipt')
        return 1.
    if attempt.outcome == 'ORIGINAL_PHYSICAL_TERMINAL_REJECTION':
        if not attempt.full_native_terminal_succeeded and attempt.exact_guard_rejection_stage in (
                'IMMUTABLE_PLACEMENT_LOST_AFTER_STOW', 'NATIVE_SETTLED_CONFIRMATION_LOST_DURING_BRAKE'):
            return 0.
        return None  # UNKNOWN guard or missing selected actual proof is not a training label
    return None
