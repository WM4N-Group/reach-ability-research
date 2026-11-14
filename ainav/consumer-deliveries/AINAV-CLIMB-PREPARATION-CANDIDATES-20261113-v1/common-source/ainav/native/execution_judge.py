"""Pure necessary-entry checks, not learned dynamics or task successor policy.

The .16m/.25rad pose envelope is Machine.activate's original contract. Native
ClimbEntry is IN PLACE and does not repair XY; NAV may establish that reference.
Original posture/settling/contact checks still run inside each native skill.
"""
from dataclasses import dataclass,asdict
import math
from ..contracts import sha,finite,text


@dataclass(frozen=True)
class EntrySpec:
    skill: str
    target_ref: str
    approach_xy: tuple
    source_height_m: float
    target_ready: bool = True
    geometry_compatible: bool = True

    def __post_init__(self):
        if self.skill not in ('PUSH','CLIMB'):raise ValueError('Interaction entry spec required')
        text(self.target_ref,'entry target')
        if len(self.approach_xy)!=2 or not all(finite(x) for x in (*self.approach_xy,self.source_height_m)):
            raise ValueError('Finite original entry reference required')
        if type(self.target_ready) is not bool or type(self.geometry_compatible) is not bool:raise ValueError('Measured predicates required')


@dataclass(frozen=True)
class EntryState:
    time_s: float
    world_sha256: str
    base_xy: tuple
    yaw_rad: float
    source_supported: bool
    push_four_foot_supported: bool
    native_hard_stop: bool = False

    def __post_init__(self):
        if not finite(self.time_s) or self.time_s<0 or len(self.world_sha256)!=64 or len(self.base_xy)!=2 or not all(finite(x) for x in (*self.base_xy,self.yaw_rad)):
            raise ValueError('Actual finite current entry state required')
        if any(type(x) is not bool for x in (self.source_supported,self.push_four_foot_supported,self.native_hard_stop)):
            raise ValueError('Actual typed entry predicates required')


@dataclass(frozen=True)
class EntryJudgment:
    status: str
    reasons: tuple
    spec: EntrySpec
    state: EntryState
    xy_error_m: float
    yaw_error_rad: float

    @property
    def sha256(self):return sha(asdict(self))

    def private_record(self):return dict(schema='ainav-independent-entry-judgment-v1',**asdict(self),
        original_pose_tolerance_m=.16,original_yaw_tolerance_rad=.25,model_input=False,physical_success_claimed=False)


def judge_entry(spec,state):
    if not isinstance(spec,EntrySpec) or not isinstance(state,EntryState):raise ValueError('Typed entry spec/state required')
    xy=math.hypot(*(a-b for a,b in zip(state.base_xy,spec.approach_xy)))
    yaw=abs(math.atan2(math.sin(state.yaw_rad),math.cos(state.yaw_rad)))
    blocked=[]
    if state.native_hard_stop:blocked.append('native_safety_revoked')
    if not spec.geometry_compatible:blocked.append('outside_original_interaction_geometry')
    if not state.source_supported:blocked.append('different_or_unverified_source_support; same-level_NAV_cannot_change_support')
    if not spec.target_ready:blocked.append('required_target_relation_not_established')
    if blocked:return EntryJudgment('BLOCKED',tuple(blocked),spec,state,xy,yaw)
    need=[]
    if xy>.16:need.append('outside_original_approach_pose')
    if yaw>.25:need.append('outside_original_approach_yaw')
    if spec.skill=='PUSH' and not state.push_four_foot_supported:need.append('original_PUSH_four_foot_support_not_ready')
    return EntryJudgment('PREPARE' if need else 'READY',tuple(need),spec,state,xy,yaw)
