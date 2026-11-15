"""Pure-CPU reference intersection for the new, unvalidated failure-exit adapter.

A reference is accepted only inside speed/acceleration, original soft limits and
an unchanged 90%-effort/40ms measured-velocity envelope simultaneously. No claim
of dynamic safety: original physical substep protections still own termination.
"""
from dataclasses import dataclass
import math


class FailureExitRefused(RuntimeError):
    def __init__(self, message, *, diagnostic=None):
        super().__init__(message)
        from copy import deepcopy
        self.diagnostic=deepcopy(diagnostic)


def positive_bridge_loads(normal_forces):
    """Bridge admission only, NOT the native >=12N supported-capture gate."""
    return (isinstance(normal_forces,(tuple,list)) and len(normal_forces)==4
            and all(type(x) in (float,int) and math.isfinite(x) and x>0 for x in normal_forces))


@dataclass(frozen=True)
class FailureExitConfig:
    speed_rad_s: float = .45
    acceleration_rad_s2: float = 1.
    effort_reserve: float = .90
    prediction_horizon_s: float = .04
    unloaded_force_n: float = 3.
    maximum_uncaptured_bridge_s: float = .12
    maximum_feedback_braking_s: float = 1.
    maximum_feedback_speed_m_s: float = .15
    compliant_PD_slew_rad_s: float = 2.

    def __post_init__(self):
        if any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0
               for x in vars(self).values()):
            raise ValueError('Finite positive failure-exit constants required')
        if self.effort_reserve > .90 or self.prediction_horizon_s < .04:
            raise ValueError('Do not relax the original effort prediction envelope')
        if self.speed_rad_s > .45 or self.acceleration_rad_s2 > 1.:
            raise ValueError('Do not relax original arm transition rate limits')
        if self.unloaded_force_n > 3.:
            raise ValueError('Do not relax the unloaded-force gate')
        if self.compliant_PD_slew_rad_s>2.:
            raise ValueError('Explicit compliant PD slew ceiling2rad/s required')
        if self.maximum_feedback_speed_m_s>.15:
            raise ValueError('Do not expand original dynamic-braking speed domain')
        if self.maximum_feedback_braking_s > 1.:
            raise ValueError('Explicit one-second feedback brake deadline required')
        if self.maximum_uncaptured_bridge_s > .12:
            raise ValueError('A short issued-leg-target bridge is not a stance controller')


def reference_interval(previous, previous_velocity, measured_q, measured_dq,
                       kp, kd, effort_limits, soft_lower, soft_upper, dt,
                       config=FailureExitConfig()):
    vectors=(previous,previous_velocity,measured_q,measured_dq,kp,kd,
             effort_limits,soft_lower,soft_upper)
    if any(len(v)!=6 or any(type(x) not in (int,float) or not math.isfinite(x) for x in v)
           for v in vectors):
        raise FailureExitRefused('Six explicit finite measured/reference axes required')
    if type(dt) not in (int,float) or not math.isfinite(dt) or not 0 < dt <= .020001:
        raise FailureExitRefused('Actual high-rate control dt required')
    lo,hi=[],[]
    for p,v,q,dq,k,d,e,l,u in zip(*vectors):
        if k<=0 or d<0 or e<=0 or l>=u:
            raise FailureExitRefused('Invalid actual actuator/soft-limit mapping')
        if abs(v)>config.speed_rad_s+1e-5:
            raise FailureExitRefused('Last actually issued reference rate exceeds transition domain')
        vlo=max(-config.speed_rad_s,v-config.acceleration_rad_s2*dt)
        vhi=min(config.speed_rad_s,v+config.acceleration_rad_s2*dt)
        c0=q+d/k*dq;c1=c0+config.prediction_horizon_s*dq
        radius=config.effort_reserve*e/k
        low=max(l+.01,p+vlo*dt,max(c0,c1)-radius)
        high=min(u-.01,p+vhi*dt,min(c0,c1)+radius)
        if low>high:
            raise FailureExitRefused('Empty rate/acceleration/soft-limit/effort intersection')
        lo.append(low);hi.append(high)
    return lo,hi


def failed_attempt_safe_to_leave(*, box_speed, box_angular_speed, hand_force,
                                 all_hand_force, legal_contact, config=FailureExitConfig()):
    vals=(box_speed,box_angular_speed,hand_force,all_hand_force)
    if type(legal_contact) is not bool or any(type(v) not in (float,int)
            or not math.isfinite(v) or v<0 for v in vals):
        return False
    return (not legal_contact and box_speed<.02 and box_angular_speed<.1
            and hand_force<config.unloaded_force_n and all_hand_force<config.unloaded_force_n)


def compliant_PD_interval(previous, measured_q, measured_dq, kp, kd, effort_limits,
                          soft_lower, soft_upper, dt, config=FailureExitConfig()):
    """Gravity/compliance PD tracking, NOT a planned joint-motion trajectory.

    Original hard force/soft-limit envelope is retained. Only this unload-mode
    PD reference follows measured motion with an explicit2rad/s slew ceiling;
    the original .45rad/s/1rad/s2 trajectory contract remains for actual stow.
    """
    vectors=(previous,measured_q,measured_dq,kp,kd,effort_limits,soft_lower,soft_upper)
    if any(len(v)!=6 or any(type(x) not in (float,int) or not math.isfinite(x) for x in v) for v in vectors):
        raise FailureExitRefused('Six finite axes required for compliant PD tracking')
    if type(dt) not in (float,int) or not math.isfinite(dt) or not 0<dt<=.020001:
        raise FailureExitRefused('Actual high-rate compliance dt required')
    lo,hi=[],[]
    for p,q,dq,k,d,e,l,u in zip(*vectors):
        if k<=0 or d<0 or e<=0 or l>=u:raise FailureExitRefused('Invalid actual compliant actuator/limit mapping')
        c0=q+d/k*dq;c1=c0+config.prediction_horizon_s*dq;radius=config.effort_reserve*e/k
        low=max(l+.01,p-config.compliant_PD_slew_rad_s*dt,max(c0,c1)-radius)
        high=min(u-.01,p+config.compliant_PD_slew_rad_s*dt,min(c0,c1)+radius)
        if low>high:raise FailureExitRefused('Empty original force/soft-limit/compliant-PD-slew intersection')
        lo.append(low);hi.append(high)
    return lo,hi
