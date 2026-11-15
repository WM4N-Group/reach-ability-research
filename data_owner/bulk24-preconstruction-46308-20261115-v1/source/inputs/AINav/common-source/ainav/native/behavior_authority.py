"""Shared option/receipt data contracts, AST-extracted; NO world-model authority."""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from types import MappingProxyType
SKILLS = frozenset(('NAV', 'PUSH', 'CLIMB', 'EXIT_PUSH', 'RECOVER', 'HOLD'))
TERMINAL = frozenset(('succeeded', 'failed', 'protected_exit_complete'))

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()

def finite(value):
    return type(value) in (int, float) and math.isfinite(value)

@dataclass(frozen=True)
class BehaviorOption:
    token: str
    skill: str
    target_ref: str
    parameters: tuple
    budget_s: float
    native_preconditions_receipt: str
    attempt_id: str = ''
    original_push_goal_sha256: str = ''
    mandatory_protection: bool = False

    def __post_init__(self):
        if not self.token or self.skill not in SKILLS or (not self.target_ref):
            raise ValueError('Opaque option, registered skill and observed target required')
        if not finite(self.budget_s) or not 0 < self.budget_s <= 60:
            raise ValueError('Positive bounded option execution interval required')
        if not isinstance(self.parameters, tuple) or any((not isinstance(x, tuple) or len(x) != 2 for x in self.parameters)):
            raise ValueError('Immutable declared parameter pairs required')
        keys = [x[0] for x in self.parameters]
        allowed = {'goal_world_x_m', 'goal_world_y_m', 'surface_height_m', 'push_distance_m', 'requested_interval_s'}
        if keys != sorted(set(keys)) or not set(keys) <= allowed:
            raise ValueError('Unique sorted public skill parameters required')
        if any((not finite(v) for _, v in self.parameters)):
            raise ValueError('Finite declared skill parameters required')
        if any((k in ('push_distance_m', 'requested_interval_s') and v <= 0 for k, v in self.parameters)):
            raise ValueError('Positive push distance and requested interval required')
        if not self.native_preconditions_receipt:
            raise ValueError('Executor must witness actual native entry preconditions')
        if self.skill in ('PUSH', 'EXIT_PUSH'):
            if not self.attempt_id or len(self.original_push_goal_sha256) != 64:
                raise ValueError('PUSH must bind its original goal to an attempt')
        if self.mandatory_protection and self.skill not in ('EXIT_PUSH', 'RECOVER', 'HOLD'):
            raise ValueError('Safety authority cannot choose a task-progress action')

    @property
    def sha256(self):
        return digest(asdict(self))

@dataclass(frozen=True)
class NativeReceipt:
    option_sha256: str
    time_s: float
    status: str
    issued_command_sha256: str
    evidence_ref: str

    def __post_init__(self):
        if self.status not in TERMINAL | {'admitted', 'running', 'started', 'budget_expired', 'hard_stop'} or not finite(self.time_s) or self.time_s < 0 or (len(self.option_sha256) != 64) or (len(self.issued_command_sha256) != 64) or (not self.evidence_ref):
            raise ValueError('Actual native option/command/evidence receipt required')
