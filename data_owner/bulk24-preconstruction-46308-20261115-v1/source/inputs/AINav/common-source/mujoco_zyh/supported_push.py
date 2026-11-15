"""Compact entry + real four-foot QP support + from-start protected arm targets.

Explicitly DIFFERENT motor executor: frozen NN still proposes, but its leg
commands are replaced throughout protected PUSH by native support QP; arm gets
native gravity FF and rate/effort projection. No claim of original motor skill.
No physical state writes, queue clears, or relaxed original hard/stow gates.
"""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from .resume_nav import NAV_ARM
from .stall_stow import StallStowRouter,ProtectedStow
from .push_protection import native_arm_inner_limits,protected_position_reference_step,screen
from .failure_capsules import emit

MODE='compact-supported-PUSH-v25'


def fixed_base_com_goal(com,com_velocity,base_position,base_velocity,target_base,position_gain,velocity_gain):
    """Track an explicit world base pose despite a changing arm/COM offset."""
    com=np.asarray(com,dtype=float);cv=np.asarray(com_velocity,dtype=float)
    base=np.asarray(base_position,dtype=float);bv=np.asarray(base_velocity,dtype=float)
    target=np.asarray(target_base,dtype=float)
    if any(x.shape!=(3,) for x in (com,cv,base,bv,target)) or not np.isfinite(np.r_[com,cv,base,bv,target]).all() or min(position_gain,velocity_gain)<=0:
        raise ValueError('Measured COM/base position and velocity with positive native gains required')
    return com+(target-base)+(velocity_gain/position_gain)*(cv-bv)


def alignment_waypoints(base,box_rotation,hand_local,retreat_x=-.70,center_z=-.03):
    base=np.asarray(base,dtype=float);R=np.asarray(box_rotation,dtype=float);local=np.asarray(hand_local,dtype=float)
    if base.shape!=(3,) or R.shape!=(3,3) or local.shape!=(3,) or not np.isfinite(np.r_[base,R.ravel(),local]).all():
        raise ValueError('Finite measured base/box/hand coordinates required')
    retreat=R@np.array([min(retreat_x,local[0])-local[0],0.,0.])
    align=R@np.array([0.,-local[1],center_z-local[2]])
    if (retreat_x>=-.6 or local[0]>-.6 or np.linalg.norm(retreat)>.12 or
            np.linalg.norm(align)>.14 or np.linalg.norm(retreat+align)>.18):
        raise ValueError('Precontact base alignment outside registered displacement envelope')
    return np.stack((base,base+retreat,base+retreat+align))


def admit_alignment_path(sim,finish,config,waypoints,arm,anchors):
    """Read-only source guard and four-foot IK over the complete proposed path."""
    import mujoco
    from scipy.optimize import least_squares
    data=mujoco.MjData(sim.model);data.qpos[:]=sim.data.qpos
    proxy=SimpleNamespace(model=sim.model,data=data,jids=sim.jids,qids=sim.qids,
                          base_id=sim.base_id,box_id=sim.box_id)
    guard=finish.CollisionGuard(proxy,config)
    feet=np.asarray(anchors,dtype=float);leg_ids=sim.qids[:12]
    leg_soft=np.asarray(sim.soft_limits[:12],dtype=float)
    physical=sim.model.jnt_range[sim.jids[:12]]
    inner=np.column_stack((np.maximum(leg_soft[:,0],physical[:,0])+.01,
                           np.minimum(leg_soft[:,1],physical[:,1])-.01))
    q=np.clip(sim.data.qpos[leg_ids].copy(),inner[:,0]+1e-6,inner[:,1]-1e-6)
    maximum_error=0.;minimum_margin=float('inf');samples=0
    for start,end in zip(waypoints[:-1],waypoints[1:]):
        for fraction in np.linspace(0.,1.,21):
            samples+=1
            base=start+fraction*(end-start)
            def error(candidate):
                data.qpos[:]=sim.data.qpos;data.qpos[:3]=base
                data.qpos[leg_ids]=candidate;data.qpos[sim.qids[12:]]=arm
                mujoco.mj_kinematics(sim.model,data)
                return (data.xpos[sim.feet_ids]-feet).ravel()
            fit=least_squares(error,q,bounds=(inner[:,0],inner[:,1]),max_nfev=80)
            foot_error=np.max(np.linalg.norm(error(fit.x).reshape(4,3),axis=1))
            margin=np.min(np.minimum(fit.x-inner[:,0],inner[:,1]-fit.x))
            if not fit.success or foot_error>.002 or margin<.01:
                raise RuntimeError('supported_PUSH_precontact_foot_path_unreachable')
            reason=guard.check(arm)
            if reason:raise RuntimeError('supported_PUSH_precontact_path_geometry:'+reason)
            maximum_error=max(maximum_error,float(foot_error));minimum_margin=min(minimum_margin,float(margin))
            q=fit.x
    return dict(samples=samples,max_foot_anchor_error_m=maximum_error,min_leg_margin_rad=minimum_margin)


def maximum_measured_foot_speed(sim):
    import mujoco
    speeds=[]
    for body in sim.feet_ids:
        jac=np.zeros((3,sim.model.nv))
        mujoco.mj_jacBody(sim.model,sim.data,jac,None,int(body))
        speeds.append(np.linalg.norm((jac@sim.data.qvel)[:2]))
    return float(max(speeds))


def hand_center_base_velocity(hand_local,box_rotation,target_local_y=0.):
    local=np.asarray(hand_local,dtype=float);R=np.asarray(box_rotation,dtype=float)
    if local.shape!=(3,) or R.shape!=(3,3) or not np.isfinite(np.r_[local,R.ravel(),target_local_y]).all() or abs(target_local_y)>.03:
        raise ValueError('Measured finite local hand position and box rotation required')
    velocity=np.array([0.,np.clip(2.*(target_local_y-local[1]),-.02,.02),
                       np.clip(-2.*(local[2]+.03),-.02,.02)])
    velocity*=min(1.,.02/max(np.linalg.norm(velocity),1e-12))
    return R@velocity


def precontact_support_admission(foot_loads,foot_speed):
    loads=np.asarray(foot_loads,dtype=float)
    if loads.shape!=(4,) or not np.isfinite(np.r_[loads,foot_speed]).all():
        raise ValueError('Four measured foot loads and foot speed required')
    slow=foot_speed<.03
    return dict(corrective_centering=bool(slow and np.min(loads)>4.),
                forward_approach=bool(slow and np.min(loads)>=12.))


def supported_base_height_floor(foot_heights,foot_loads):
    heights=np.asarray(foot_heights,dtype=float);loads=np.asarray(foot_loads,dtype=float)
    if heights.shape!=(4,) or loads.shape!=(4,) or not np.isfinite(np.r_[heights,loads]).all() or not np.any(loads>2.):
        raise ValueError('Actual four-foot support heights and loads required')
    return float(np.min(heights[loads>2.]-.0225)+.19)


def rebalance_completion(start_base,actual_base,box_rotation,issued_target,
                         retreat_target,base_velocity,foot_loads):
    start=np.asarray(start_base,dtype=float);actual=np.asarray(actual_base,dtype=float)
    R=np.asarray(box_rotation,dtype=float);issued=np.asarray(issued_target,dtype=float)
    target=np.asarray(retreat_target,dtype=float);velocity=np.asarray(base_velocity,dtype=float)
    loads=np.asarray(foot_loads,dtype=float)
    if (any(x.shape!=(3,) for x in (start,actual,issued,target,velocity)) or
            R.shape!=(3,3) or loads.shape!=(4,) or
            not np.isfinite(np.r_[start,actual,R.ravel(),issued,target,velocity,loads]).all()):
        raise ValueError('Measured finite base, box rotation, target, velocity and four-foot loads required')
    delta=R.T@(actual-start)
    return dict(allow_arm_contact=bool(np.linalg.norm(issued-target)<.001 and
        -delta[0]>=.045 and abs(delta[1])<.025 and abs(delta[2])<.01 and
        np.linalg.norm(velocity)<.015 and np.min(loads)>=12.),
        measured_retreat_m=float(-delta[0]),lateral_drift_m=float(abs(delta[1])),
        vertical_drift_m=float(abs(delta[2])),minimum_foot_N=float(np.min(loads)))


def lateral_reload_completion(start_base,actual_base,target_base,box_rotation,
                              base_velocity,foot_loads,foot_speed):
    start=np.asarray(start_base,dtype=float);actual=np.asarray(actual_base,dtype=float)
    target=np.asarray(target_base,dtype=float);R=np.asarray(box_rotation,dtype=float)
    velocity=np.asarray(base_velocity,dtype=float);loads=np.asarray(foot_loads,dtype=float)
    if (any(x.shape!=(3,) for x in (start,actual,target,velocity)) or
            R.shape!=(3,3) or loads.shape!=(4,) or
            not np.isfinite(np.r_[start,actual,target,R.ravel(),velocity,loads,foot_speed]).all()):
        raise ValueError('Measured finite lateral reload state required')
    lateral=float(R[:,1]@(actual-start))
    return dict(allow_arm_recenter=bool(lateral>=.06 and
        np.linalg.norm(actual-target)<.008 and np.linalg.norm(velocity)<.015 and
        np.min(loads)>=18. and foot_speed<.03),
        measured_lateral_reload_m=lateral,
        actual_target_error_m=float(np.linalg.norm(actual-target)),
        minimum_foot_N=float(np.min(loads)))


def lateral_reload_target_issued(base_target,lateral_target):
    issued=np.asarray(base_target,dtype=float);target=np.asarray(lateral_target,dtype=float)
    if issued.shape!=(3,) or target.shape!=(3,) or not np.isfinite(np.r_[issued,target]).all():
        raise ValueError('Finite three-dimensional base targets required')
    return bool(np.linalg.norm((issued-target)[:2])<.001)


def zero_base_com_goal(com,com_velocity,base_velocity,position_gain,velocity_gain):
    com=np.array(com,dtype=float,copy=True);cv=np.asarray(com_velocity);bv=np.asarray(base_velocity)
    if com.shape!=(3,) or cv.shape!=(3,) or bv.shape!=(3,) or not np.isfinite(np.r_[com,cv,bv]).all() or min(position_gain,velocity_gain)<=0:
        raise ValueError('Actual finite world COM/base kinematics and positive native gains required')
    com[:2]+=velocity_gain/position_gain*(cv[:2]-bv[:2])
    return com


def approach_com_goal(com,com_velocity,base_velocity,standoff,position_gain,velocity_gain):
    """Bounded measured box-gap approach using SAME native COM task.

    Fixed COM can leave face out of arm workspace when heavy arm extends.
    Target .53m gap, cap.02m/s: original recovery .645gap needs~.115m retreat,
    within unchanged.18m only if actually measured at takeover. No pose write.
    """
    com=np.asarray(com,dtype=float);cv=np.asarray(com_velocity,dtype=float);bv=np.asarray(base_velocity,dtype=float)
    if com.shape!=(3,) or cv.shape!=(3,) or bv.shape!=(3,) or not np.isfinite(np.r_[com,cv,bv,standoff]).all() or min(position_gain,velocity_gain)<=0:
        raise ValueError('Actual finite support COM/base/gap kinematics required')
    desired=np.array([float(np.clip(2.*(standoff-.485),-.02,.02)),0.])
    target=com.copy();target[:2]+=velocity_gain/position_gain*(desired+cv[:2]-bv[:2])
    return target,desired


def uncompensated_native_arm_goal(compensated_target,gravity,kp):
    """Original IK already includes gravity/Kp in its POSITION output.

    New executor uses explicit FF, so remove that original position offset
    before adding FF; never double-compensate. No controller cache rewrite.
    """
    target=np.asarray(compensated_target,dtype=float);g=np.asarray(gravity,dtype=float);K=np.asarray(kp,dtype=float)
    if target.shape!=(6,) or g.shape!=(6,) or K.shape!=(6,) or not np.isfinite(np.r_[target,g,K]).all() or np.any(K<=0):
        raise ValueError('Finite original gravity-compensated sixaxis target/Kp required')
    return target-g/K


def projection_goal(proposal,inner):
    # First native safe waypoint is .157/-.148, tolerance .04. .02execution
    # reserve inside ORIGINAL+.01 domain is compatible, never relaxes limits.
    return np.clip(np.asarray(proposal),inner[:,0]+.02,inner[:,1]-.02)


def protected_line_reference_step(*,start,goal,progress,reference,reference_velocity,
                                  q,dq,kp,kd,feedforward,effort,inner_limits,
                                  speed_cap=.4499):
    """Keep the issued six-axis reference on one collision-checked joint line."""
    start=np.asarray(start,dtype=float);goal=np.asarray(goal,dtype=float)
    reference=np.asarray(reference,dtype=float);velocity=np.asarray(reference_velocity,dtype=float)
    delta=goal-start
    if (start.shape!=(6,) or goal.shape!=(6,) or not np.isfinite(np.r_[start,goal,progress]).all()
            or not 0.<=progress<=1. or not 0.<speed_cap<=.4499 or
            np.max(np.abs(reference-(start+progress*delta)))>1e-6):
        raise ValueError('Issued arm reference must remain on its admitted joint path')
    bounds=protected_position_reference_step(desired=goal,reference=reference,
        reference_velocity=velocity,q=q,dq=dq,kp=kp,kd=kd,feedforward=feedforward,
        effort=effort,inner_limits=inner_limits)
    lower,upper=bounds['lower'],bounds['upper']
    alpha_min,alpha_max=progress,1.
    for i,d in enumerate(delta):
        if abs(d)<1e-10:
            if not lower[i]-1e-9<=start[i]<=upper[i]+1e-9:
                raise RuntimeError('supported_PUSH_zero_motion_axis_reference_intersection_empty')
            continue
        left,right=sorted(((lower[i]-start[i])/d,(upper[i]-start[i])/d))
        alpha_min=max(alpha_min,left);alpha_max=min(alpha_max,right)
    if alpha_max<alpha_min-1e-9:
        raise RuntimeError(f'supported_PUSH_coupled_arm_reference_intersection_empty:{progress:.8f}:{alpha_min:.8f}:{alpha_max:.8f}')
    maximum_delta=max(float(np.max(np.abs(delta))),1e-12)
    remaining=max(0.,1.-progress)
    alpha_speed=min(speed_cap/maximum_delta,.5*np.sqrt(2.*.999*remaining/maximum_delta))
    next_alpha=min(1.,alpha_max,progress+.005*alpha_speed)
    next_alpha=max(alpha_min,next_alpha)
    selected=start+next_alpha*delta
    new_velocity=(selected-reference)/.005
    if (np.any(selected<lower-1e-8) or np.any(selected>upper+1e-8) or
            np.max(np.abs(new_velocity))>speed_cap+1e-8 or
            np.max(np.abs((new_velocity-velocity)/.005))>1.+1e-8):
        raise RuntimeError('supported_PUSH_coupled_arm_reference_limits')
    return dict(reference=selected,reference_velocity=new_velocity,
                PD_velocity=np.zeros(6),feedforward=np.asarray(feedforward).copy(),
                lower=lower,upper=upper,path_progress=float(next_alpha))


def plan_loaded_arm_contact(sim,guard,inner,box_rotation,box_position,start_reference=None,
                            target_local=(-.59,-.03,-.03)):
    """Fit a guarded arm path to a registered box-local target at fixed base pose."""
    import mujoco
    from scipy.optimize import least_squares
    from scipy.spatial.transform import Rotation

    model=sim.model;data=mujoco.MjData(model);data.qpos[:]=sim.data.qpos
    arm_qids=sim.qids[12:];start=sim.data.qpos[arm_qids].copy()
    reference_start=np.asarray(start if start_reference is None else start_reference,dtype=float)
    if reference_start.shape!=(6,) or not np.isfinite(reference_start).all():
        raise ValueError('Actual last-issued arm reference required')
    hand_id=model.body('end_effector').id
    hand_rotation=sim.controller.hand_rotation.detach().cpu().numpy()[0]
    box_quaternion=sim.data.xquat[sim.box_id]
    rotation=lambda q:Rotation.from_quat(np.asarray(q)[[1,2,3,0]])
    target_rotation=rotation(box_quaternion)*rotation(hand_rotation)
    target_local=np.asarray(target_local,dtype=float)
    if (target_local.shape!=(3,) or not np.isfinite(target_local).all() or
            target_local[0]>-.59):
        raise ValueError('Finite registered target outside the box front required')
    target=np.asarray(box_position)+np.asarray(box_rotation)@target_local

    def pose(q):
        data.qpos[arm_qids]=q;mujoco.mj_kinematics(model,data)
        return data.xpos[hand_id].copy(),(target_rotation*rotation(data.xquat[hand_id]).inv()).as_rotvec()

    def residual(q):
        position,angle=pose(q)
        return np.r_[20.*(position-target),angle,.03*(q-start)]

    fit=least_squares(residual,np.clip(start,inner[:,0]+1e-8,inner[:,1]-1e-8),
                      bounds=(inner[:,0],inner[:,1]),max_nfev=160)
    position,angle=pose(fit.x)
    if (not fit.success or np.linalg.norm(position-target)>.002 or
            np.linalg.norm(angle)>.10 or
            np.min(np.minimum(fit.x-inner[:,0],inner[:,1]-fit.x))<.01):
        raise RuntimeError('supported_PUSH_arm_contact_IK_unreachable')
    planning_guard=guard.__class__(sim,replace(guard.config,surface_clearance=.038))
    maximum_y=0.;maximum_z_error=0.
    for fraction in np.linspace(0.,1.,101):
        q=reference_start+fraction*(fit.x-reference_start)
        position,_=pose(q)
        local=np.asarray(box_rotation).T@(position-box_position)
        reason=planning_guard.check(q,allow_hand_contact=bool(local[0]>=-.63),record=True)
        if reason:raise RuntimeError('supported_PUSH_arm_contact_path_geometry:'+reason)
        if local[0]>=-.63:
            maximum_y=max(maximum_y,abs(float(local[1])))
            maximum_z_error=max(maximum_z_error,abs(float(local[2]+.03)))
            if maximum_y>=.04 or maximum_z_error>=.025:
                raise RuntimeError('supported_PUSH_arm_contact_path_offcenter')
    return fit.x.copy(),dict(samples=101,position_error_m=float(np.linalg.norm(position-target)),
                             target_box_local_m=target_local.tolist(),
                             maximum_contact_zone_abs_y_m=maximum_y,
                             maximum_contact_zone_z_error_m=maximum_z_error,
                             planned_minimum_body_clearance_m=planning_guard.minimum_surface,
                             planned_body_clearance_reserve_m=.003,
                             actual_start_arm_rad=start.tolist(),
                             issued_start_arm_rad=reference_start.tolist(),
                             goal_arm_rad=fit.x.tolist())


class SupportedPushRouter(StallStowRouter):
    def __init__(self,r,native,root):
        super().__init__(r,native,root)
        self.entry_arm=NAV_ARM.copy();self.support=None;self.support_steps=0
        self.original_push_approach_distance=float(r.sim.cfg.push_approach_distance)
        self.original_hand_height_offset=float(r.sim.cfg.push_hand_height_offset)
        # Frozen PushArmIK and native box target terms bind to the live
        # controller.env. Explicitly prove it is the same actual sim config.
        self.active_push_cfg=r.sim.controller.env.cfg
        if self.active_push_cfg is not r.sim.cfg:raise ValueError('Native PUSH controller env/config is not the active simulation bridge')
        self.active_push_cfg.push_approach_distance=.005  # native contact preload; force gate unchanged
        self.active_push_cfg.push_hand_height_offset=-.03  # native contact center; geometry classifier unchanged
        self.retirement=None;self.maximum_target_projection=0.;self.minimum_support_load=float('inf')
        self.precontact_wait_start=None
        self.base_target=None;self.alignment_path=None;self.alignment_admission=None
        self.arm_hold=None;self.alignment_stage='native_waypoint';self.load_balance_local_y=0.
        self.arm_contact_goal=None;self.arm_contact_admission=None
        self.arm_contact_start=None;self.arm_path_progress=0.
        self.rebalance_target=None;self.rebalance_start_base=None
        self.lateral_reload_start_base=None;self.lateral_reload_target=None
        self.arm_center_goal=None;self.arm_center_admission=None
        self.support_log=(Path(root)/'supported-push-200hz.jsonl').open('x')

    def update(self):
        if self.recovery is None and self.kind=='push' and self.native.phase in ('blend','run'):
            # Native observation's previous applied target must describe what
            # actually reached the issuing interface, NOT the rejected proposal.
            self.r.sim.applied_commands=(self.r.last.position-self.r.push['model'].REFERENCE)/.25
        super().update()

    def make_recovery(self):
        return ProtectedStow(self.r,list(self.last_two),unload_initial_ff=self.r.last.feedforward[12:].copy())

    def hard_flags(self):
        s=self.r.sim;box=self.r.push['bridge'].box_push
        return dict(box_contact=bool(box.forbidden_box_contact(s)[0]),
                    invalid_hand_contact=bool(box.invalid_hand_contact(s,s.hand_cfg)[0]),box_tipped=bool(box.box_tipped(s)[0]))

    def start_support(self):
        r,s=self.r,self.r.sim
        if np.linalg.norm(s.data.qvel[:3])>.12 or min(s.forces[s.feet_ids,2])<12:
            raise RuntimeError('protected_PUSH_entry_requires_actual_loaded_stationary_support')
        self.inner=native_arm_inner_limits(r)
        refs=np.stack(list(self.last_two))[:,12:];v=(refs[-1]-refs[-2])/.005
        if np.max(abs(v))>.45:raise RuntimeError('protected_PUSH_entry_actual_reference_not_rate_compatible')
        finish=r.push['finish']
        self.support=finish.FinishController(s,replace(finish.FinishConfig(),arm_pose=tuple(NAV_ARM),stance_posture_weight=0.))
        # Native QP reference buffers ONLY. First measured feet are already loaded.
        self.support.anchors=s.data.xpos[s.feet_ids].copy()
        self.support_events=dict(time_s=float(s.data.time),base_position_world_m=s.data.qpos[:3].tolist(),actual_entry_arm=s.data.qpos[s.qids[12:]].tolist(),
            actual_reference_velocity=v.tolist(),actual_loaded_foot_N=s.forces[s.feet_ids,2].tolist(),
            physical_state_or_queue_modified=False)
        self.precontact_wait_start=float(s.data.time)
        self.base_target=s.data.qpos[:3].copy()

    def advance_alignment(self,local,rotation,arm_reference):
        s=self.r.sim;c=self.support
        if self.alignment_stage=='native_waypoint' and bool(s.controller.safe_approach_complete[0]):
            if np.max(np.abs(s.data.qvel[s.dids[12:]]))>=.12:
                return
            self.arm_hold=arm_reference.copy()
            path=alignment_waypoints(s.data.qpos[:3],rotation,local)
            reason=c.guard.segment(s.data.qpos[s.qids[12:]],self.arm_hold)
            if reason:raise RuntimeError('supported_PUSH_precontact_arm_hold_geometry:'+reason)
            self.alignment_admission=admit_alignment_path(s,self.r.push['finish'],c.config,path,
                                                           self.arm_hold,c.anchors)
            self.alignment_path=path;self.alignment_stage='retreat'
        if self.alignment_stage=='approach' and local[0]>=-.685:
            self.rebalance_start_base=s.data.qpos[:3].copy()
            self.rebalance_target=s.data.qpos[:3].copy()-rotation[:,0]*.05
            self.rebalance_target[2]=s.data.qpos[2]
            self.alignment_admission=admit_alignment_path(s,self.r.push['finish'],c.config,
                np.stack((s.data.qpos[:3].copy(),self.rebalance_target)),self.arm_hold,c.anchors)
            self.base_target=s.data.qpos[:3].copy()
            self.alignment_stage='rebalance_retreat'
        if self.alignment_stage=='rebalance_retreat':
            if np.min(s.forces[s.feet_ids,2])<=4. or maximum_measured_foot_speed(s)>=.03:
                return
            delta=self.rebalance_target-self.base_target
            self.base_target+=min(1.,.02*.005/max(np.linalg.norm(delta),1e-12))*delta
            measured=rebalance_completion(self.rebalance_start_base,s.data.qpos[:3],
                rotation,self.base_target,self.rebalance_target,s.data.qvel[:3],
                s.forces[s.feet_ids,2])
            if measured['allow_arm_contact']:
                self.base_target=s.data.qpos[:3].copy()
                self.lateral_reload_start_base=s.data.qpos[:3].copy()
                self.lateral_reload_target=self.lateral_reload_start_base+rotation[:,1]*.07
                self.alignment_admission=admit_alignment_path(s,self.r.push['finish'],
                    c.config,np.stack((self.lateral_reload_start_base,
                                       self.lateral_reload_target)),self.arm_hold,c.anchors)
                self.alignment_stage='lateral_reload'
            return
        if self.alignment_stage=='lateral_reload':
            if np.min(s.forces[s.feet_ids,2])<=4. or maximum_measured_foot_speed(s)>=.03:
                return
            delta=(self.lateral_reload_target-self.base_target)[:2]
            self.base_target[:2]+=min(1.,.02*.005/max(np.linalg.norm(delta),1e-12))*delta
            measured=lateral_reload_completion(self.lateral_reload_start_base,
                s.data.qpos[:3],self.lateral_reload_target,rotation,s.data.qvel[:3],
                s.forces[s.feet_ids,2],maximum_measured_foot_speed(s))
            if (lateral_reload_target_issued(self.base_target,self.lateral_reload_target) and
                    measured['allow_arm_recenter']):
                self.base_target=s.data.qpos[:3].copy()
                self.arm_center_goal,self.arm_center_admission=plan_loaded_arm_contact(
                    s,c.guard,self.inner,rotation,s.data.xpos[s.box_id],arm_reference,
                    target_local=(-.68,measured['measured_lateral_reload_m']+.01,-.02))
                self.arm_contact_start=arm_reference.copy();self.arm_path_progress=0.
                self.alignment_stage='arm_recenter'
            return
        if self.alignment_stage=='arm_recenter' and self.arm_path_progress>=1.:
            if (np.max(np.abs(s.data.qpos[s.qids[12:]]-arm_reference))<.025 and
                    np.max(np.abs(s.data.qvel[s.dids[12:]]))<.12 and
                    np.min(s.forces[s.feet_ids,2])>=18. and
                    np.linalg.norm(s.data.qvel[:3])<.015):
                self.base_target=s.data.qpos[:3].copy()
                self.arm_contact_goal,self.arm_contact_admission=plan_loaded_arm_contact(
                    s,c.guard,self.inner,rotation,s.data.xpos[s.box_id],arm_reference)
                self.arm_contact_start=arm_reference.copy();self.arm_path_progress=0.
                self.alignment_stage='arm_contact'
            return
        if self.alignment_stage not in ('retreat','align'):
            return
        loaded=bool(np.min(s.forces[s.feet_ids,2])>=12.)
        feet_stable=maximum_measured_foot_speed(s)<.03
        base_stable=np.linalg.norm(s.data.qvel[:3])<.015
        if (self.alignment_stage=='align' and loaded and feet_stable and base_stable and
                local[0]<=-.70 and abs(local[1])<.04 and abs(local[2]+.03)<.025 and
                np.max(np.abs(s.data.qvel[s.dids[12:]]))<.12):
            self.base_target=s.data.qpos[:3].copy()
            self.alignment_stage='approach'
            return
        if not loaded or not feet_stable:
            return
        index=1 if self.alignment_stage=='retreat' else 2
        target=self.alignment_path[index]
        delta=target-self.base_target
        step=min(1.,.02*.005/max(np.linalg.norm(delta),1e-12))
        self.base_target=self.base_target+step*delta
        pose_error=np.linalg.norm(s.data.qpos[:3]-target)
        if (np.linalg.norm(self.base_target-target)<.001 and pose_error<.008 and
                base_stable and loaded and feet_stable):
            self.alignment_stage='align' if index==1 else 'approach'
            if index==2:self.base_target=s.data.qpos[:3].copy()

    def retire(self,reason,decision,proposal):
        r,s=self.r,self.r.sim;box=r.push['bridge'].box_push
        self.retirement=dict(time_s=float(s.data.time),reason=reason,decision=decision,
            actual_legal_hand_contact=bool(box.hand_contact(s,s.hand_cfg)[0]),native_motion_ready=bool(s.controller.motion_ready[0]),
            native_goal_success=False,original60ms_no_progress_observed=False,
            rejected_proposal=proposal.array().tolist(),last_actually_issued=r.last.array().tolist())
        self.abort=dict(self.retirement,original_goal=s.box_push_target.numpy().tolist(),native_goal_success=False)
        emit(r,'supported_push_protective_abort',extra=self.retirement)
        self.recovery=self.make_recovery()
        return self.recovery.command()

    def next_command(self):
        if self.recovery is not None:return self.recovery.command()
        nominal=self.native.next_command()
        if self.kind!='push' or self.native.phase not in ('blend','run') or self.native.finish is not None:return nominal
        if self.support is None:self.start_support()
        r,s=self.r,self.r.sim;c=self.support;pm=r.push['model']
        gravity=s.robot.get_gravity_compensation_forces().numpy()[0]
        gravity=gravity[[s.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]]
        refs=np.stack(list(self.last_two))[:,12:];velocity=(refs[-1]-refs[-2])/.005
        hand=s.data.xpos[s.model.body('end_effector').id]
        box=s.data.xpos[s.box_id];Rbox=s.data.xmat[s.box_id].reshape(3,3)
        local=Rbox.T@(hand-box)
        self.advance_alignment(local,Rbox,r.last.position[12:])
        height_floor=supported_base_height_floor(s.data.xpos[s.feet_ids,2],s.forces[s.feet_ids,2])
        self.base_target[2]=max(self.base_target[2],height_floor)
        desired=(self.arm_hold if self.arm_hold is not None else
                 projection_goal(s.controller.reference.detach().cpu().numpy()[0],self.inner))
        if self.alignment_stage in ('arm_recenter','arm_contact') and np.min(s.forces[s.feet_ids,2])<12.:
            emit(r,'supported_push_arm_contact_support_lost',preserve_primary_failure=True)
            raise RuntimeError('supported_PUSH_arm_contact_support_below_12N')
        try:
            common=dict(reference=r.last.position[12:],reference_velocity=velocity,
                q=s.data.qpos[s.qids[12:]],dq=s.data.qvel[s.dids[12:]],
                kp=pm.KP[12:],kd=pm.KD[12:],feedforward=gravity,
                effort=pm.EFFORT[12:],inner_limits=self.inner)
            if self.alignment_stage in ('arm_recenter','arm_contact'):
                arm=protected_line_reference_step(start=self.arm_contact_start,
                    goal=(self.arm_center_goal if self.alignment_stage=='arm_recenter'
                          else self.arm_contact_goal),progress=self.arm_path_progress,
                    speed_cap=.25,**common)
                self.arm_path_progress=arm['path_progress']
            else:
                arm=protected_position_reference_step(desired=desired,**common)
        except (ValueError,RuntimeError) as error:
            return self.retire('arm_projection_requires_brake',dict(error=repr(error)),nominal)
        reason=c.guard.check(arm['reference'],allow_hand_contact=True)
        if reason:raise RuntimeError('protected_PUSH_reference_geometry:'+reason)
        reason=c.guard.check(s.data.qpos[s.qids[12:]]+.1*s.data.qvel[s.dids[12:]],allow_hand_contact=True,joint_limits=False)
        if reason:raise RuntimeError('protected_PUSH_actual_velocity_geometry:'+reason)
        posture=c.entry_posture.copy()
        command=r.Command(np.r_[posture,arm['reference']],np.zeros(18),pm.KP.copy(),pm.KD.copy(),np.r_[np.zeros(12),gravity])
        import mujoco
        J=np.zeros((3,s.model.nv));mujoco.mj_jacSubtreeCom(s.model,s.data,J,s.base_id)
        # Keep the measured base pose while the arm changes the subtree COM.
        gap=float(np.dot(s.data.xpos[s.box_id]-s.data.qpos[:3],s.data.xmat[s.box_id].reshape(3,3)[:,0])-.6)
        controller=s.controller
        ready=bool(controller.motion_ready[0])
        entry=contact_entry_admission(hand_local_box=local,
            arm_velocity=s.data.qvel[s.dids[12:]],reference_velocity=arm['reference_velocity'])
        # While native joint waypoint/center-height face alignment is incomplete,
        # hold the measured body velocity near zero while compensating full arm
        # shape COM motion. Never let whole-body base advance into a high hand.
        stage=body_approach_stage_admission(entry,
            native_safe_approach_complete=bool(controller.safe_approach_complete[0]),native_motion_ready=ready)
        if not ready and float(s.data.time)-self.precontact_wait_start>40.:
            emit(r,'supported_push_precontact_alignment_timeout',extra=dict(entry=entry,stage=stage,alignment_stage=self.alignment_stage),preserve_primary_failure=True)
            raise RuntimeError('supported_PUSH_precontact_alignment_timeout')
        foot_speed=maximum_measured_foot_speed(s)
        support_admission=precontact_support_admission(s.forces[s.feet_ids,2],foot_speed)
        support_stable=support_admission['forward_approach']
        actual_braked=bool(np.linalg.norm(s.data.qvel[:3])<.015 and support_stable)
        center_velocity=np.zeros(3)
        if (self.alignment_stage=='approach' and
                s.forces[s.feet_ids[3],2]<12. and np.min(s.forces[s.feet_ids,2])>4.):
            self.load_balance_local_y=.03
        if self.alignment_stage=='approach' and support_admission['corrective_centering']:
            center_velocity=hand_center_base_velocity(local,Rbox,self.load_balance_local_y)
            self.base_target+=center_velocity*.005
        local_base_velocity=Rbox.T@s.data.qvel[:3]
        lateral_height_slow=bool(np.max(np.abs(local_base_velocity[1:]))<.008)
        if (self.alignment_stage=='approach' and (stage['allow_body_approach'] or ready) and
                support_stable and lateral_height_slow):
            desired_velocity=float(np.clip(2.*(gap-.485),-.02,.02))
            self.base_target[:2]+=Rbox[:2,0]*desired_velocity*.005
            approach_velocity=Rbox[:2,0]*desired_velocity
            body_mode='bounded_body_approach_after_centered_native_waypoint_gate'
        else:
            approach_velocity=np.zeros(2);body_mode='fixed_base_brake_'+self.alignment_stage
        if np.linalg.norm(self.base_target-self.support_events['base_position_world_m'])>.18:
            raise RuntimeError('supported_PUSH_precontact_base_displacement_limit')
        self.base_target[2]=max(self.base_target[2],height_floor)
        com=fixed_base_com_goal(s.data.subtree_com[s.base_id],J@s.data.qvel,s.data.qpos[:3],
                                s.data.qvel[:3],self.base_target,c.config.position_gain,c.config.velocity_gain)
        contacts=s.forces[s.feet_ids,2]>4.
        torque,*_=c.qp.solve(contacts,c.anchors,np.zeros((4,3)),np.zeros((4,3)),com,c.yaw,posture,command)
        q=s.data.qpos[s.qids[:12]];dq=s.data.qvel[s.dids[:12]]
        command.position[:12]=q;command.kp[:12]=5.;command.kd[:12]=1.;command.feedforward[:12]=torque+dq
        tilt=float(np.arccos(np.clip(s.data.xmat[s.base_id].reshape(3,3)[2,2],-1,1)))
        decision=screen(proposed=command.array(),queue=s.queue,delay_steps=s.delays,q=s.data.qpos[s.qids],dq=s.data.qvel[s.dids],
            effort=pm.EFFORT,base_velocity_world=s.data.qvel[:3],measured_acceleration_world=s.data.qacc[:3],
            foot_normal_N=s.forces[s.feet_ids,2],tilt_rad=tilt,hard_flags=self.hard_flags(),arm_warning_fraction=.85)
        if decision['action']=='STOP_AND_CENSOR':
            emit(r,'supported_push_hard_censor',extra=decision,preserve_primary_failure=True)
            raise RuntimeError('supported_PUSH_native_hard_censor:'+str(decision['hard_flags']))
        if decision['action']=='BRAKE_RETIRE_PUSH':return self.retire('prequeue_support_speed_reserve',decision,nominal)
        self.support_steps+=1;self.maximum_target_projection=max(self.maximum_target_projection,float(abs(command.position[12:]-nominal.position[12:]).max()))
        self.minimum_support_load=min(self.minimum_support_load,float(min(s.forces[s.feet_ids,2])))
        self.support_log.write(json.dumps(dict(time_s=float(s.data.time),nominal_frozen_actor_motor_proposal=nominal.array().tolist(),
            original_controller_uncompensated_reference=s.controller.reference.detach().cpu().numpy()[0].tolist(),
            actual_protected_proposal=command.array().tolist(),actual_reference_velocity=arm['reference_velocity'].tolist(),
            decision=decision,actual_standoff_m=gap,approach_velocity_target_m_s=approach_velocity.tolist(),body_mode=body_mode,
            actual_box_local_hand=list(map(float,local)),native_motion_ready=ready,measured_contact_entry_admission=entry,body_approach_stage_admission=stage,
            alignment_stage=self.alignment_stage,alignment_path_admission=self.alignment_admission,
            arm_contact_path_admission=self.arm_contact_admission,
            arm_center_path_admission=self.arm_center_admission,
            arm_contact_path_progress=self.arm_path_progress,
            lateral_reload_start_base_world_m=(self.lateral_reload_start_base.tolist()
                if self.lateral_reload_start_base is not None else None),
            lateral_reload_target_world_m=(self.lateral_reload_target.tolist()
                if self.lateral_reload_target is not None else None),
            rebalance_start_base_world_m=(self.rebalance_start_base.tolist()
                if self.rebalance_start_base is not None else None),
            measured_foot_normal_N=s.forces[s.feet_ids,2].tolist(),
            fixed_base_target_world_m=self.base_target.tolist(),actual_braked=actual_braked,
            original_low_posture_guard_base_target_floor_m=height_floor,
            hand_center_base_velocity_target_m_s=center_velocity.tolist(),lateral_height_slow=lateral_height_slow,
            loaded_rear_left_balance_hand_local_y_target_m=self.load_balance_local_y,
            precontact_support_admission=support_admission,
            maximum_measured_foot_speed_m_s=foot_speed,
            actual_foot_anchor_error_m=np.linalg.norm(s.data.xpos[s.feet_ids]-c.anchors,axis=1).tolist(),
            actual_base_velocity=s.data.qvel[:3].tolist(),native_QP_residual=c.qp.maximum_residual))+'\n')
        if self.support_log.tell()>64*1024*1024:raise RuntimeError('supported_PUSH_private_log_quota')
        return command

    def after_step(self):
        super().after_step()
        if self.recovery is None and self.kind=='push' and self.native.phase not in ('startup','prepare'):
            flags=self.hard_flags()
            if any(flags.values()):
                emit(self.r,'supported_push_actual_hard_guard',extra=flags,preserve_primary_failure=True)
                raise RuntimeError('supported_PUSH_actual_hard_contact:'+str(flags))

    def report(self):
        out=super().report()
        out['supported_push']=dict(mode=MODE,active_native_precontact_distance_m=float(self.active_push_cfg.push_approach_distance),original_hand_height_offset_m=self.original_hand_height_offset,registered_hand_height_offset_m=float(self.active_push_cfg.push_hand_height_offset),source_skill_weights_frozen=True,original_motor_executor_unchanged=False,
            native_NN_proposals_evaluated_but_leg_targets_replaced_by_QP=True,
            native_gravity_FF_and_projected_arm_reference=True,original_gravity_position_offset_removed_before_FF=True,actual_uncompensated_controller_reference_used_before_native_actionclip=True,
            actual_entry_COM_fixed_as_measured_support_capture_target=False,measured_gap_target_m=.485,approach_velocity_cap_m_s=.02,actual_previous_action_interface_updated=True,
            fixed_base_capture=True,alignment_stage=self.alignment_stage,read_only_alignment_path_admission=self.alignment_admission,
            read_only_arm_center_path_admission=self.arm_center_admission,
            read_only_arm_contact_path_admission=self.arm_contact_admission,
            protected_motor_steps=self.support_steps,entry=getattr(self,'support_events',None),protective_abort=self.retirement,
            maximum_arm_proposal_projection_rad=self.maximum_target_projection,
            minimum_measured_foot_N=self.minimum_support_load if self.support_steps else None,
            original60ms_no_progress_failure=self.retirement is None and self.abort is not None,
            actual_recovery_complete=bool(self.recovery is not None and self.recovery.complete),
            reliability_acceptance=False,WM_training_or_control=False)
        if self.retirement and out.get('recovery'):
            out['recovery']['native_PUSH_attempt_failed']=False;out['recovery']['protectively_aborted_PUSH']=True
        return out

    def close(self):super().close();self.support_log.close()


def contact_entry_admission(*,hand_local_box,arm_velocity,reference_velocity,tip_radius=.07):
    """Measured precontact gate, integrated as an UNVALIDATED control candidate.

    Upper-edge collision in known off-axis TRAIN3 requires real height/lateral
    settling BEFORE body closes gap. Never change actualcontact classifier or
    synthesize native motion_ready. Hard stopping after collision is too late.
    """
    local=np.asarray(hand_local_box,dtype=float);dq=np.asarray(arm_velocity,dtype=float);v=np.asarray(reference_velocity,dtype=float)
    if local.shape!=(3,) or dq.shape!=(6,) or v.shape!=(6,) or not np.isfinite(np.r_[local,dq,v]).all() or tip_radius!=.07:
        raise ValueError('Exact measured current localhand/arm/reference velocities and originaltipradius required')
    checks=dict(actual_hand_height_inside_center_band=bool(abs(local[2]-(-.03))<.025),
                actual_hand_lateral_inside_center_band=bool(abs(local[1])<.04),
                actual_hand_outside_box_front=bool(local[0]<=-.6),
                actual_arm_slow=bool(abs(dq).max()<.12),actual_reference_slow=bool(abs(v).max()<.12))
    return dict(reference_stage_admitted=all(checks.values()),checks=checks,
                required_control='REAL_CENTER_HEIGHT_ALIGNMENT_BEFORE_BODY_APPROACH' if not all(checks.values()) else 'BOUNDED_REAL_CONTACT_APPROACH_CANDIDATE',
                native_contact_force_height_axis_or_tip_gate_changed=False,actual_future_contact_safety_certified=False,
                native_motion_ready_modified=False,physical_command_authorized=False)


def body_approach_stage_admission(entry,*,native_safe_approach_complete,native_motion_ready):
    """Do not confuse completed joint waypoints with contact DRIVE readiness.

    Pinned native motion_ready depends on box_push_approached/contact, so using
    it as a prerequisite for precontact closure creates a circular wait. The
    original drive flag remains untouched and still owns actual PUSH readiness.
    This gate authorizes only a bounded QP approach target, not task success.
    """
    if (not isinstance(entry,dict) or type(entry.get('reference_stage_admitted')) is not bool or
            type(native_safe_approach_complete) is not bool or type(native_motion_ready) is not bool):
        raise ValueError('Measured entry decision and actual native scalar booleans required')
    return dict(allow_body_approach=entry['reference_stage_admitted'] and native_safe_approach_complete,
        native_joint_waypoint_complete=native_safe_approach_complete,native_contact_drive_ready=native_motion_ready,
        contact_drive_readiness_required_before_precontact_approach=False,native_flags_modified=False,
        actual_future_contact_safety_certified=False)
