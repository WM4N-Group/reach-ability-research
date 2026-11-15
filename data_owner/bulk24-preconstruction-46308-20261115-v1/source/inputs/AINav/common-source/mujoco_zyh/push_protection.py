"""Opt-in200Hz pre-queue protection; frozen actors, DIFFERENT executed option.

No state resets/queue clears/threshold relaxation. Decisions are conservative
engineering SCREENS, NOT certified future floating-base/contact bounds. An early
protective retirement is NOT a60ms no-progress failure or native PUSH success.
"""
from dataclasses import asdict,dataclass
import json
from pathlib import Path
import numpy as np

from .stall_stow import ProtectedStow,StallStowRouter
from .recovery_design import committed_queue_screen
from .failure_capsules import emit

MODE='push-prequeue-protection-v1'


@dataclass(frozen=True)
class ProtectionConfig:
    warning_base_speed_m_s:float=.08
    warning_forecast_speed_m_s:float=.11
    unchanged_recovery_speed_gate_m_s:float=.15
    warning_tilt_rad:float=.06
    warning_arm_effort_fraction:float=.70
    support_warning_foot_N:float=8.
    support_warning_speed_m_s:float=.04
    warning_loaded_feet_min:int=3
    physics_dt_s:float=.005
    measurement_reserve_s:float=.005
    native_max_command_delay_steps:int=4
    max_private_log_bytes:int=8*1024*1024


CONFIG=ProtectionConfig()


def vector(x,n,name):
    a=np.asarray(x,dtype=float)
    if a.shape!=(n,) or not np.isfinite(a).all():raise ValueError('Exact finite '+name+' required')
    return a


def screen(*,proposed,queue,delay_steps,q,dq,effort,base_velocity_world,
           measured_acceleration_world,foot_normal_N,tilt_rad,hard_flags,
           config=CONFIG,arm_warning_fraction=None):
    """Before append/step, compare REAL proposal and unavoidable old prefix.

    Acceleration is a current measurement used for EARLY WARNING ONLY. Never
    infer guaranteed safety from a green result, or use future rollout data.
    """
    if config!=CONFIG:raise ValueError('New protection margins require a separately registered version')
    arm_warning=config.warning_arm_effort_fraction if arm_warning_fraction is None else arm_warning_fraction
    if arm_warning_fraction is not None and arm_warning_fraction!=.85:
        raise ValueError('Only explicitly registered supported-PUSH .85warning accepted; native.9reserve unchanged')
    u=np.asarray(proposed,dtype=float)
    if u.shape!=(5,18) or not np.isfinite(u).all() or np.any(u[2:4]<0):raise ValueError('Finite complete5x18 nonnegative-gain proposal required')
    q=vector(q,18,'actual q');dq=vector(dq,18,'actual dq');effort=vector(effort,18,'native effort')
    v=vector(base_velocity_world,3,'world linear velocity');a=vector(measured_acceleration_world,3,'measured acceleration')
    feet=vector(foot_normal_N,4,'four measured foot loads');lag=vector(delay_steps,18,'per-axis delays')
    if np.any(effort<=0) or np.any(lag<0) or np.any(lag>4) or not np.equal(lag,np.floor(lag)).all():raise ValueError('Native effort/delay contract violated')
    if not np.isfinite(tilt_rad) or tilt_rad<0:raise ValueError('Actual nonnegative finite tilt required')
    if not isinstance(hard_flags,dict) or any(type(x) is not bool for x in hard_flags.values()):raise ValueError('Actual native hard flag booleans required')
    pending=committed_queue_screen(queue=[np.asarray(x).tolist() for x in queue],delay_steps=lag.astype(int).tolist(),
        q=q.tolist(),dq=dq.tolist(),effort=effort.tolist())
    speed=float(np.linalg.norm(v));horizon=(float(lag.max())+1)*config.physics_dt_s+config.measurement_reserve_s
    forecast=float(np.linalg.norm(v+horizon*a))
    arm_ratio=max(float(np.max(abs(u[2,12:]*(u[0,12:]-q[12:]-h*dq[12:])+u[3,12:]*(u[1,12:]-dq[12:])+u[4,12:])/effort[12:])) for h in (0.,.06))
    reasons=[]
    if speed>=config.warning_base_speed_m_s:reasons.append('base_speed_reserve')
    if forecast>=config.warning_forecast_speed_m_s:reasons.append('measured_acceleration_warning_NOT_future_bound')
    if tilt_rad>=config.warning_tilt_rad:reasons.append('tilt_reserve')
    loaded=int(np.count_nonzero(feet>=config.support_warning_foot_N))
    if loaded<config.warning_loaded_feet_min and speed>=config.support_warning_speed_m_s:reasons.append('measured_support_load_reserve')
    if arm_ratio>=arm_warning:reasons.append('arm_PD_FF_reserve')
    if not pending['screen_pass']:reasons.append('immutable_pending_torque_screen')
    hard=[name for name,value in hard_flags.items() if value]
    if speed>config.unchanged_recovery_speed_gate_m_s:hard.append('already_outside_original_recovery_speed_gate')
    action='STOP_AND_CENSOR' if hard else 'BRAKE_RETIRE_PUSH' if reasons else 'PROPOSE_UNCHANGED'
    return dict(schema=MODE,action=action,reasons=reasons,hard_flags=hard,
        measured_base_speed_m_s=speed,warning_forecast_speed_m_s=forecast,
        measured_acceleration_is_NOT_future_bound=True,warning_horizon_s=horizon,
        loaded_feet_count=loaded,foot_normal_N=feet.tolist(),maximum_arm_PD_FF_fraction=arm_ratio,
        arm_warning_fraction=arm_warning,original_arm_prediction_effort_reserve_fraction=.90,
        immutable_pending_queue_screen=pending,unchanged_recovery_speed_gate_m_s=.15,
        guaranteed_future_safety=False,physical_command_authorized=False,
        original_proposal_or_queue_or_measured_state_modified=False)


class PrequeueProtectionRouter(StallStowRouter):
    """Retire NN PUSH authority BEFORE unsafe proposal reaches delayed motors.

    Braking/retreat/stow uses existing ProtectedStow/native QP, not an untrained
    negative PUSH gait. All native hard guards/capture/stow limits retained.
    This first pilot tests early takeover only; does not claim general safety.
    """
    def __init__(self,r,native,root):
        super().__init__(r,native,root)
        self.protective_retirement=None;self.prequeue_checks=0
        self.protection_log=(Path(root)/'push-protection-prequeue-200hz.jsonl').open('x')

    def native_contact_flags(self):
        box=self.r.push['bridge'].box_push;s=self.r.sim
        return dict(box_contact=bool(box.forbidden_box_contact(s)[0]),
                    invalid_hand_contact=bool(box.invalid_hand_contact(s,s.hand_cfg)[0]),
                    box_tipped=bool(box.box_tipped(s)[0]))

    def next_command(self):
        if self.recovery is not None:return self.recovery.command()
        proposal=self.native.next_command()
        if self.kind!='push' or self.native.phase not in ('blend','run') or self.native.finish is not None:return proposal
        r,s=self.r,self.r.sim
        tilt=float(np.arccos(np.clip(s.data.xmat[s.base_id].reshape(3,3)[2,2],-1,1)))
        decision=screen(proposed=proposal.array(),queue=s.queue,delay_steps=s.delays,q=s.data.qpos[s.qids],dq=s.data.qvel[s.dids],
            effort=r.push['model'].EFFORT,base_velocity_world=s.data.qvel[:3],measured_acceleration_world=s.data.qacc[:3],
            foot_normal_N=s.forces[s.feet_ids,2],tilt_rad=tilt,hard_flags=self.native_contact_flags())
        self.prequeue_checks+=1
        self.protection_log.write(json.dumps(dict(time_s=float(s.data.time),decision=decision,unissued_frozen_NN_proposal=proposal.array().tolist()))+'\n')
        if self.protection_log.tell()>CONFIG.max_private_log_bytes:raise RuntimeError('registered_prequeue_protection_log_budget_censor')
        if decision['action']=='STOP_AND_CENSOR':
            emit(r,'prequeue_native_hard_censor',extra=dict(decision=decision),preserve_primary_failure=True)
            raise RuntimeError('prequeue_native_hard_or_domain_censor:'+str(decision['hard_flags']))
        if decision['action']=='BRAKE_RETIRE_PUSH':
            box=r.push['bridge'].box_push
            self.protective_retirement=dict(time_s=float(s.data.time),reason='protective_retirement_before_proposal_enqueue',
                decision=decision,actual_legal_hand_contact=bool(box.hand_contact(s,s.hand_cfg)[0]),
                native_motion_ready=bool(s.controller.motion_ready[0]),
                native_goal_success=False,original_60ms_progress_failure_observed=False,
                rejected_proposal_NOT_issued=proposal.array().tolist(),last_actually_issued=r.last.array().tolist())
            # Never fabricate a no-progress monitor event or put this in native Finish success.
            self.abort=dict(self.protective_retirement,original_goal=s.box_push_target.numpy().tolist(),native_PUSH_success=False)
            emit(r,'prequeue_protective_retirement',extra=self.protective_retirement)
            self.recovery=ProtectedStow(r,list(self.last_two))
            self.recovery.events.append(dict(time=float(s.data.time),event='protected_QP_takeover_before_rejected_proposal_issuance'))
            return self.recovery.command()
        return proposal

    def after_step(self):
        super().after_step()
        if self.recovery is None and self.kind=='push' and self.native.phase not in ('prepare','startup'):
            flags=self.native_contact_flags()
            if any(flags.values()):
                emit(self.r,'prequeue_actual_hard_guard',extra=dict(native_flags=flags),preserve_primary_failure=True)
                raise RuntimeError('push_protection_native_contact_guard_200Hz:'+str(flags))

    def report(self):
        out=super().report()
        out.update(push_protection=dict(mode=MODE,configuration=asdict(CONFIG),prequeue_checks=self.prequeue_checks,
            protective_retirement=self.protective_retirement,original_frozen_actors_modified=False,
            executed_option_changed=True,governor_controlling=True,WM_controlling=False,
            original_progress_failure_observed=self.protective_retirement is None and self.abort is not None,
            recovery_complete=bool(self.recovery is not None and self.recovery.complete),
            scope='Experimental early protective retirement + original protected recovery. Not calibrated reliability or original-PUSH success.'))
        if self.protective_retirement and out.get('recovery'):
            out['recovery']['native_PUSH_attempt_failed']=False
            out['recovery']['PUSH_attempt_protectively_aborted']=True
        return out

    def close(self):
        super().close();self.protection_log.close()


def arm_takeover_admission(*,last_two_issued_positions,actual_arm_q,inner_reference_limits):
    """Pure admission, not control: existing stow cannot accept every PUSH epoch.

    This must be checked BEFORE attempting direct stow. A refused direct
    handoff requires a REAL brake/capture bridge; resetting the derivative,
    clipping measured q, or advancing the FIFO is forbidden.
    """
    refs=np.asarray(last_two_issued_positions,dtype=float)
    q=vector(actual_arm_q,6,'actual six-axis arm q')
    limits=np.asarray(inner_reference_limits,dtype=float)
    if refs.shape!=(2,18) or not np.isfinite(refs).all() or limits.shape!=(6,2) or not np.isfinite(limits).all() or np.any(limits[:,0]>=limits[:,1]):
        raise ValueError('Exact measured last-two18axis commands and native inner arm limits required')
    velocity=(refs[-1,12:]-refs[-2,12:])/.005
    fast=np.flatnonzero(abs(velocity)>.45)
    outside_q=np.flatnonzero((q<limits[:,0]) | (q>limits[:,1]))
    outside_ref=np.flatnonzero((refs[-1,12:]<limits[:,0]) | (refs[-1,12:]>limits[:,1]))
    admitted=not(len(fast) or len(outside_q) or len(outside_ref))
    return dict(direct_existing_stow_handoff_admitted=admitted,
        required_next_stage='CHECK_REMAINING_ORIGINAL_QUEUE_GEOMETRY_EFFORT_GATES' if admitted else 'REAL_BRAKE_CAPTURE_BRIDGE_REQUIRED_NOT_IMPLEMENTED',
        actual_reference_velocity_rad_s=velocity.tolist(),reference_speed_violations_zero_based=fast.tolist(),
        actual_q_outside_inner_domain_zero_based=outside_q.tolist(),last_reference_outside_inner_domain_zero_based=outside_ref.tolist(),
        nominal_seed_or_measured_q_or_queue_changed=False,actual_future_brake_safety_certified=False,
        physical_control_authorized=False)


def arm_reference_rate_step(desired,reference,reference_velocity,dt=.005):
    """CPU building block for FUTURE new protocol's from-start arm protection.

    Only software targets: original .45rad/s/1rad/s2 limits, NO actuator output.
    Needs effort/geometry/soft-domain and full-body integration before use. It
    CANNOT be enabled after an already-fast actual issued seed; fail closed.
    """
    goal=vector(desired,6,'desired arm software target')
    r=vector(reference,6,'last actually issued arm position')
    v=vector(reference_velocity,6,'actual issued derivative')
    if dt!=.005 or np.any(abs(v)>.45):raise ValueError('Must protect references BEFORE original seed exceeds fold rate domain')
    wanted=np.sign(goal-r)*np.minimum.reduce([abs(goal-r)/dt,np.full(6,.4499),np.sqrt(2.*.999*abs(goal-r))])
    nv=np.clip(wanted,np.maximum(-.4499,v-.999*dt),np.minimum(.4499,v+.999*dt))
    out=r+dt*nv
    return out,nv


def protected_position_reference_step(*,desired,reference,reference_velocity,q,dq,kp,kd,feedforward,effort,inner_limits):
    """CPU-only feasible outgoing POSITION field with native ZERO PD velocity.

    Different from select_reference's nonzero motor-velocity target. Uses real
    issued seed, original rate/acceleration and .9effort at0/60ms, inner limits.
    Still NO actuator authority/geometry/COM/contact guarantee. Future from-start
    protection must use the existing compact-entry adapter to enter this domain
    by REAL motion, not transplant qpos or clip an incompatible actual seed.
    """
    goal=vector(desired,6,'desired arm reference');r=vector(reference,6,'actual last reference')
    v=vector(reference_velocity,6,'actual last reference rate');x=vector(q,6,'actual arm q');w=vector(dq,6,'actual arm dq')
    K=vector(kp,6,'native Kp');D=vector(kd,6,'native Kd');F=vector(feedforward,6,'outgoing actual FF');E=vector(effort,6,'native effort')
    limits=np.asarray(inner_limits,dtype=float)
    if limits.shape!=(6,2) or not np.isfinite(limits).all() or np.any(limits[:,0]>=limits[:,1]) or np.any(K<=0) or np.any(D<0) or np.any(E<=0):raise ValueError('Invalid original limits/gains')
    if np.any(abs(v)>.45):raise ValueError('Actual issued seed outside original fold rate domain; real from-start protection required')
    if np.any((r<limits[:,0]) | (r>limits[:,1]) | (x<limits[:,0]) | (x>limits[:,1])):
        raise ValueError('Actual state/reference outside inner domain; REAL compact-entry motion required')
    forecast=x+.06*w
    if np.any((forecast<limits[:,0]) | (forecast>limits[:,1])):raise ValueError('Measured arm-velocity forecast leaves original inner domain')
    nominal,_=arm_reference_rate_step(goal,r,v)
    rate_lo=r+.005*np.maximum(-.4499,v-.999*.005);rate_hi=r+.005*np.minimum(.4499,v+.999*.005)
    centers=np.stack([x+h*w+(D*w-F)/K for h in (0.,.06)])
    lo=np.maximum.reduce([rate_lo,limits[:,0],centers.max(0)-.90*E/K])
    hi=np.minimum.reduce([rate_hi,limits[:,1],centers.min(0)+.90*E/K])
    if np.any(lo>hi):raise RuntimeError('prequeue_position_reference_intersection_empty:'+str(np.flatnonzero(lo>hi).tolist()))
    selected=np.maximum(lo,np.minimum(hi,nominal));nv=(selected-r)/.005
    return dict(reference=selected,reference_velocity=nv,PD_velocity=np.zeros(6),feedforward=F.copy(),
        lower=lo,upper=hi,geometry_or_contact_or_base_dynamics_certified=False,actuator_command_authorized=False)


def native_arm_inner_limits(runtime):
    """Original SOURCE-contract soft limits, not guessed scaling of URDF ranges."""
    s=runtime.sim;robot=s.robot
    slots=[robot.joint_names.index('joint'+str(i)) for i in range(1,7)]
    soft=robot.data.soft_joint_pos_limits
    if hasattr(soft,'detach'):soft=soft.detach().cpu().numpy()
    soft=np.asarray(soft)[0,slots,:];physical=np.asarray(s.model.jnt_range)[s.jids[12:],:]
    if soft.shape!=(6,2) or physical.shape!=(6,2) or not np.isfinite(np.r_[soft,physical]).all():raise ValueError('Native selected arm source/physical limits missing')
    inner=np.column_stack((np.maximum(soft[:,0],physical[:,0])+.01,np.minimum(soft[:,1],physical[:,1])-.01))
    if np.any(inner[:,0]>=inner[:,1]):raise ValueError('Original inner arm-domain intersection empty')
    return inner
