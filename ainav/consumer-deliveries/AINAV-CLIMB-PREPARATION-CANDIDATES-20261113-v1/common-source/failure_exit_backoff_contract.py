"""Measured pre-stow retreat protocol, no simulator/actor dependencies."""
from dataclasses import dataclass
import math
from contact_failure_exit_contract import FailureExitRefused


@dataclass(frozen=True)
class BackoffConfig:
    target_standoff_m: float = .63
    request_speed_m_s: float = .05
    maximum_speed_m_s: float = .15
    maximum_distance_m: float = .18
    maximum_seconds: float = 8.

    def __post_init__(self):
        exact=(.63,.05,.15,.18,8.)
        if tuple(vars(self).values())!=exact:
            raise ValueError('Only the registered backoff geometry and motion domain')


class MeasuredBackoff:
    def __init__(self, config=BackoffConfig()):
        self.cfg=config; self.phase='INITIAL_UNLOAD'; self.start=None
        self.origin=None; self.target_x=None; self.last=None

    def begin(self, now, position, standoff, *, original_stable):
        self._finite(now,position,standoff,0.)
        if self.phase!='INITIAL_UNLOAD' or original_stable is not True:
            raise FailureExitRefused('Unique actually supported stable start required')
        needed=self.cfg.target_standoff_m-standoff
        if not 0.<needed<self.cfg.maximum_distance_m:
            raise FailureExitRefused('Actual retreat target outside registered backward distance')
        self.start=now;self.origin=list(position);self.target_x=position[0]-needed
        self.phase='BACKOFF';self.last=now
        return dict(phase=self.phase,start_s=now,actual_origin=list(position),
                    phase_target_world_x_m=self.target_x,needed_backward_m=needed,
                    original_box_goal_modified=False)

    @staticmethod
    def _finite(now,position,standoff,speed):
        if len(position)!=3 or not all(type(x) in (int,float) and math.isfinite(x) for x in (now,*position,standoff,speed)):
            raise FailureExitRefused('Finite synchronized actual backoff measurements required')

    def observe(self, now, position, standoff, speed):
        self._finite(now,position,standoff,speed)
        if self.start is None:return self.receipt(now,position,standoff)
        if now<self.last-1e-9:raise FailureExitRefused('Backoff clock moved backwards')
        self.last=now
        displacement=math.dist(position[:2],self.origin[:2])
        if displacement>self.cfg.maximum_distance_m+1e-7:
            raise FailureExitRefused('Actual backoff exceeded registered distance')
        if abs(position[1]-self.origin[1])>.05 or abs(position[2]-self.origin[2])>.03:
            raise FailureExitRefused('Actual backoff left lateral/height corridor')
        if position[0]-self.origin[0]>.02:
            raise FailureExitRefused('Actual backoff moved forward instead')
        if speed>self.cfg.maximum_speed_m_s+1e-7:
            raise FailureExitRefused('Actual backoff exceeded original dynamic speed domain')
        if self.phase in ('BACKOFF','BRAKE_AFTER_BACKOFF') and now-self.start>self.cfg.maximum_seconds+1e-9:
            raise FailureExitRefused('Actual backoff/recapture exceeded eight-second bound')
        if self.phase=='BACKOFF' and standoff>=self.cfg.target_standoff_m and position[0]<self.origin[0]-.01:
            self.phase='BRAKE_AFTER_BACKOFF'
        return self.receipt(now,position,standoff)

    def request(self):
        return [-self.cfg.request_speed_m_s,0.,0.] if self.phase=='BACKOFF' else [0.,0.,0.]

    def capture_allowed(self, *, zero_interval_actually_issued):
        return self.phase!='BACKOFF' and (self.phase=='INITIAL_UNLOAD' or zero_interval_actually_issued is True)

    def allow_stow(self, *, original_stable, actual_standoff, swept_path_passed):
        if (self.phase!='BRAKE_AFTER_BACKOFF' or original_stable is not True
            or actual_standoff<self.cfg.target_standoff_m or swept_path_passed is not True):
            raise FailureExitRefused('Actual recapture/stability/clearance and fresh full sweep required before stow')
        self.phase='STOW'

    def receipt(self, now, position, standoff):
        return dict(phase=self.phase,actual_time_s=now,actual_position=list(position),
                    actual_AABB_standoff_m=standoff,
                    actual_backward_m=None if self.origin is None else self.origin[0]-position[0],
                    seconds_since_backoff=None if self.start is None else now-self.start,
                    next_requested_velocity=self.request())


def validate_registered_backoff(plan):
    versions={'native-pre-stow-clearance-backoff-g1c2-v1':'249a27f95e3613e2746adec0a83fd2bcebdec885',
              'native-pre-stow-directional-forecast-transfer-g1c2-v1':'b1ff2e9464e9ef34e99dee94568d92baca98ff17'}
    if (plan.get('schema')!='native-pre-stow-clearance-backoff-protocol-v1'
        or plan.get('protocol_id') not in versions
        or plan.get('reference_source_commit')!=versions.get(plan.get('protocol_id'))):
        raise ValueError('Exact source-matched one-shot registered backoff required')
    roots={'native-pre-stow-clearance-backoff-g1c2-v1':'/mnt/yuanyue/data/go2-piper-world-model/compliant-zero-recovery-20261024-v1',
           'native-pre-stow-directional-forecast-transfer-g1c2-v1':'/mnt/yuanyue/data/go2-piper-world-model/clearance-backoff-recovery-20261024-v1'}
    if plan.get('reference_closed_root')!=roots[plan['protocol_id']]:raise ValueError('Exact registered reference root required')
    required={'max_new_physics_starts':1,'max_sim_seconds':96,'max_wall_seconds':1800,
              'grace_seconds':10,'max_same_root_launches':1,'automatic_retry':False,
              'physical_resets_after_initial_allowed':0,'training_runs':0,'world_model_forwards_or_control':False}
    budget=plan.get('execution_budget',{})
    if set(required)!=set(budget) or any(type(budget[k]) is not type(v) or budget[k]!=v for k,v in required.items()):
        raise ValueError('Exact registered no-retry/reset/training single-start budget required')
    c=plan.get('candidate',{})
    limits={'maximum_backward_request_m_s':.05,'maximum_actual_motion_speed_m_s':.15,
            'target_conservative_course_AABB_box_front_standoff_m':.63,
            'maximum_measured_backward_distance_m':.18,'maximum_backoff_seconds':8.,
            'original_capture_requires_four_actual_foot_loads_N':12.}
    if any(type(c.get(k)) not in (int,float) or c[k]!=v for k,v in limits.items()):
        raise ValueError('Exact registered backoff limits and support load required')
    for k in ('original_box_PUSH_goal_unchanged','robot_backoff_phase_anchor_is_not_box_goal',
              'arm_stow_after_actual_clearance_and_recapture_only','hard_physics_and_contact_protection_unchanged'):
        if c.get(k) is not True:raise ValueError('Original goal/safety/ownership contracts required')
    if plan.get('training_authorized') is not False or plan.get('reference_replay_or_restart') is not False:
        raise ValueError('No training or old-root replay authorization')
    if plan['protocol_id']=='native-pre-stow-clearance-backoff-g1c2-v1':
        if c.get('box_clearance_forecast_mode','omnidirectional_angular_ball_40ms')!='omnidirectional_angular_ball_40ms' or c.get('leg_transfer_seconds',0.)!=0.:
            raise ValueError('Do not reuse old protocol budget for a new forecast or PD transfer')
    if plan['protocol_id']=='native-pre-stow-directional-forecast-transfer-g1c2-v1':
        exact={'box_clearance_forecast_mode':'measured_world_twist_sweep_40ms','forecast_horizon_s':.04,
               'forecast_time_intervals':8,'leg_transfer_seconds':.4,'leg_transfer':'quintic_from_last_issued_supported_PD'}
        if any(type(c.get(k)) is not type(v) or c[k]!=v for k,v in exact.items()):
            raise ValueError('Exact new directional40ms/8-interval/400ms-transfer protocol required')
        for k in ('last_issued_PD_seed_not_measured_pose_or_actuator_reset','box_clearance_margin_unchanged','original_native_substep_guards_unchanged'):
            if c.get(k) is not True:raise ValueError('New forecast/PD transfer must preserve native physics and margins')
    return .06
