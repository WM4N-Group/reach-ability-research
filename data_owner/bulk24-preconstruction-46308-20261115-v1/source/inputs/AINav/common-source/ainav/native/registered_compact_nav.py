"""Native compact NAV from an actual supported capture on an explicit surface.

Not a task planner: goal is supplied by the caller. A development probe is not a
VLM decision. Height comes from checked registry geometry and loaded feet, not a
hardcoded 0/.4 list. Actual commands/history stay in world-Z; actor input uses the original
training support frame through the existing three-command-height adapter.
"""
from collections import deque
from dataclasses import replace
import math
from types import SimpleNamespace


def validate_support_and_goal(surface,feet,loads,goal):
    if len(feet)!=4 or any(len(f)!=3 for f in feet) or len(loads)!=4 or len(goal)!=2:
        raise ValueError('Actual four-foot support and explicit XY goal required')
    if not all(math.isfinite(v) for f in feet for v in f) or not all(math.isfinite(v) for v in [*loads,*goal]):
        raise ValueError('Finite actual support/goal required')
    x0,x1,y0,y1=surface.bounds_xy_m
    if not all(x0<f[0]<x1 and y0<f[1]<y1 and abs(f[2]-surface.top_z_m-.022)<.04 for f in feet) or min(loads)<12.:
        raise ValueError('Actual stationary feet are not loaded on the declared support')
    if not (x0+.35<goal[0]<x1-.35 and y0+.3<goal[1]<y1-.3):raise ValueError('NAV target footprint leaves declared support rectangle')
    return surface.top_z_m


def arrival_runtime_view(runtime,surface_height):
    """Same physical runtime with only the native Finish surface reference view.

    Instance vars do not include class-defined methods. Delegate nav_state to
    its actual original owner; never replace it with a synthetic READY state.
    """
    proxy=SimpleNamespace(**vars(runtime))
    proxy.nav_state=runtime.nav_state
    if surface_height:
        from mujoco_zyh.integrated_course import PushSurfaceView
        proxy.push=PushSurfaceView(runtime.push,surface_height)
    return proxy


class ActualArrivalSupportWitness:
    """Hand back a genuinely completed same-world NAV/stow for another option."""
    def __init__(self,nav_owner):
        if not isinstance(nav_owner,RegisteredCompactNav) or not nav_owner.complete or nav_owner.arrival is None or not nav_owner.arrival.complete:
            raise ValueError('Actual completed native NAV and protected arrival required')
        self.nav_owner=nav_owner;self.r=nav_owner.r;self.data=self.r.sim.data;self.queue=self.r.sim.queue
        self.observed_time=float(self.data.time);self.observed_tick=self.r.step_count
        self.support_ref=nav_owner.surface.ref;self.owner=self
        self.guard=nav_owner.arrival.native.guard;self.limits=nav_owner.arrival.limits
        self.last_two=deque([v.copy() for v in nav_owner.last_two],maxlen=2)
        self.actual_issued_steps=self.observed_tick-nav_owner.started_tick
        if len(self.last_two)!=2 or self.actual_issued_steps<2:raise ValueError('Actual arrival command history required')
        self.validate(self.r)

    def validate(self,runtime):
        if runtime is not self.r or runtime.sim.data is not self.data or runtime.sim.queue is not self.queue:
            raise ValueError('Arrival witness belongs to another runtime/world/FIFO')
        if float(self.data.time)<self.observed_time or runtime.step_count<self.observed_tick:raise ValueError('Arrival clock regressed')
        nav=self.nav_owner
        if not nav.complete or not nav.arrival.complete:raise RuntimeError('Original NAV/stow completion lost')
        nav._sync_arrival();nav.check_guards();nav.arrival.native_arrival.validate(nav.arrival_runtime)
        p=runtime.sim
        validate_support_and_goal(nav.surface,p.data.xpos[p.feet_ids].tolist(),p.forces[p.feet_ids,2].tolist(),nav.goal)
        return True

    def report(self):return dict(kind='actual_native_NAV_protected_arrival',time_s=self.observed_time,support_ref=self.support_ref,
        actual_issued_steps=self.actual_issued_steps,no_PUSH_failure_claimed=True,no_cold_start_claimed=True,
        previous_goal_xy=list(self.nav_owner.goal),model_input=False)


class RegisteredCompactNav:
    def __init__(self,runtime,registry,*,capture_witness,goal_xy,journal):
        import numpy as np
        from .supported_capture import ActualCaptureWitness
        from .push_stow_witness import ActualPushStowSupportWitness
        from mujoco_zyh.resume_nav import make_compact_nav,nominal_compact_ee,NAV_ARM,compact_contract
        from mujoco_zyh.stall_stow import history_sha
        from mujoco_zyh.native_behavior_executor import world_snapshot,array_sha
        if not isinstance(capture_witness,(ActualCaptureWitness,ActualArrivalSupportWitness,ActualPushStowSupportWitness)):raise ValueError('Actual supported capture required, not a fake failed PUSH owner')
        capture_witness.validate(runtime)
        r=runtime;p=r.sim;self.r,self.registry,self.journal=r,registry,journal
        self.capture_witness=capture_witness;self.capture=capture_witness.owner
        self.surface=registry.surfaces[capture_witness.support_ref];self.goal=tuple(float(v) for v in goal_xy)
        self.height=validate_support_and_goal(self.surface,p.data.xpos[p.feet_ids].tolist(),p.forces[p.feet_ids,2].tolist(),self.goal)
        self.contract=compact_contract(r);before=world_snapshot(r)
        self.started=float(p.data.time);self.started_tick=r.step_count;self.origin=p.data.qpos[:2].copy()
        self.goal_sha=array_sha(p.box_push_target.numpy());self.history_sha=history_sha(p)
        self.last_two=deque([v.copy() for v in self.capture.last_two],maxlen=2)
        self.arm_ref=r.last.position[12:].copy();self.arm_velocity=(self.last_two[-1][12:]-self.last_two[-2][12:])/.005
        self.old_command=r.last;self.arrival=None;self.arrival_runtime=None;self.phase='NAV';self.complete=False;self.actor_forwards=0
        r.reset_nav_history(self.height);r.n.ee_command=nominal_compact_ee(r);r.n.ee_command[2]+=self.height
        self.nav=make_compact_nav(r,self.goal);self.nav_started=False
        # The .24s path was registered for a long-running failed-PUSH recovery,
        # not a newly started actor. Restore the native skills cold-start profile
        # (startup PD + policy warmup), without changing any arrival predicate.
        original_cfg=r.nav['navigation'].profile_nav_config('skills')
        self.nav.native.config=replace(self.nav.native.config,warmup_seconds=original_cfg.warmup_seconds)
        self.nav.config=self.nav.native.config
        self.cold_policy_warmup_s=original_cfg.warmup_seconds
        if world_snapshot(r)!=before:raise RuntimeError('NAV installation changed physical state/FIFO')
        journal(dict(event='registered_compact_NAV_started',time_s=self.started,goal_xy=list(self.goal),support_ref=self.surface.ref,
            support_height_m=self.height,original_cold_policy_warmup_s=self.cold_policy_warmup_s,actual_world_z_command_history_preserved=True,policy_support_frame_translation=True,actual_support_capture=capture_witness.report(),
            no_failed_PUSH_owner_fabricated=True,model_input=False))

    def check_guards(self):
        import numpy as np
        from mujoco_zyh.stall_stow import history_sha
        from mujoco_zyh.native_behavior_executor import array_sha
        from .registered_guards import check_object_contacts
        p=self.r.sim
        if history_sha(p)!=self.history_sha or array_sha(p.box_push_target.numpy())!=self.goal_sha:raise RuntimeError('Original PUSH history/goal changed during NAV')
        check_object_contacts(self.r,self.registry)
        reason=self.capture.guard.check(p.data.qpos[p.qids[12:]],allow_hand_contact=False,record=True)
        if reason:raise RuntimeError('registered_NAV_actual_arm_geometry:'+reason)
        if np.max(abs(p.torque[12:])/self.r.push['model'].EFFORT[12:])>=.98:raise RuntimeError('registered_NAV_original_arm_effort')
        # Same declared planar support; no airborne shortcut to a different layer.
        x,y=p.data.qpos[:2];x0,x1,y0,y1=self.surface.bounds_xy_m
        if not x0<x<x1 or not y0<y<y1:raise RuntimeError('Registered NAV left declared support region')

    def _sync_arrival(self):
        if self.arrival_runtime is not None:
            self.arrival_runtime.last=self.r.last;self.arrival_runtime.step_count=self.r.step_count

    def update(self):
        import numpy as np
        import torch
        from mujoco_zyh.resume_nav import NAV_ARM
        self.check_guards();r=self.r;p=r.sim;self._sync_arrival()
        if float(p.data.time)-self.started>60.:raise RuntimeError('Registered NAV budget exhausted')
        if self.arrival is not None:
            self.arrival.update();self.nav.observe(r.nav_state(self.started))
            checks=self.nav.native.stability_checks(r.nav_state(self.started))
            if not checks['position'] or not checks['yaw']:raise RuntimeError('Original NAV position/yaw lost during arrival capture')
            return
        velocity=self.nav.update(r.nav_state(self.started));r.n.set_wbc_command(velocity,r.n.ee_command)
        r.n.previous_action=(r.last.position-r.nav['bridge'].REFERENCE)/r.nav['bridge'].C['ACTION_SCALE']
        from mujoco_zyh.integrated_course import surface_nav_observation
        raw_observation=r.n.observation()
        # Translate only three historical command Z scalars, never robot state,
        # time, issued actions, gains or native task-world coordinates.
        observation=surface_nav_observation(raw_observation,np.asarray(r.n.history[6]),self.height)
        with torch.inference_mode():action=r.nav_actor(torch.as_tensor(observation,device=r.device)[None]).cpu().numpy()[0]
        r.n.set_action(action);r.n.targets[12:]=self.arm_ref
        r.n.previous_action[12:]=(self.arm_ref-r.nav['bridge'].REFERENCE[12:])/r.nav['bridge'].C['ACTION_SCALE']
        self.actor_forwards+=1
        self.journal(dict(event='registered_NAV_actual_actor_forward',time_s=float(p.data.time),observation=observation.tolist(),raw_world_frame_observation=raw_observation.tolist(),policy_support_height_m=self.height,
            action=action.tolist(),last_actually_issued=r.last.array().tolist(),requested_velocity=velocity.tolist(),model_input=False))
        if self.nav.arrived:
            from mujoco_zyh.native_nav_arrival_witness import NativeNAVArrivalWitness
            from mujoco_zyh.stall_stow import ProtectedStow
            proxy=arrival_runtime_view(r,self.height)
            witness=NativeNAVArrivalWitness(proxy,self.nav,self.started,NAV_ARM)
            self.arrival_runtime=proxy;self.arrival=ProtectedStow(proxy,list(self.last_two),compact_goal=NAV_ARM,native_arrival=witness)
            cfg=replace(self.arrival.native.config,stance_posture_weight=r.push['finish'].FinishConfig().stance_posture_weight)
            self.arrival.native.config=cfg;self.arrival.native.qp.config=cfg
            self.arrival.reference=self.arm_ref.copy();self.arrival.velocity=self.arm_velocity.copy();self.phase='ARRIVAL_CAPTURE'
            self.journal(dict(event='registered_NAV_actual_goal_hold_then_arrival_capture',time_s=float(p.data.time),support_height_m=self.height,
                actual_goal_checks=witness.checks,original_goal_preserved=True,model_input=False))

    def command(self):
        import numpy as np
        from mujoco_zyh.moving_arm_reference import brake_arm_hold
        from mujoco_zyh.resume_nav import NAV_ARM
        from runtime import blend_command
        r=self.r;p=r.sim;self._sync_arrival()
        if self.arrival is not None:return self.arrival.command()
        if self.actor_forwards==0:raise RuntimeError('NAV actor has not observed actual entry')
        pm=r.push['model'];gravity=p.robot.get_gravity_compensation_forces().numpy()[0]
        gravity=gravity[[p.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]]
        try:
            self.arm_ref,self.arm_velocity,arm_ff,self.arm_receipts=brake_arm_hold(NAV_ARM,self.arm_ref,self.arm_velocity,
                p.data.qpos[p.qids[12:]],p.data.qvel[p.dids[12:]],pm.KP[12:],pm.KD[12:],r.last.feedforward[12:],pm.EFFORT[12:],self.capture.limits,dt=.005)
        except RuntimeError as error:
            error.wm_reference_inputs=dict(reference=self.arm_ref,velocity=self.arm_velocity,q=p.data.qpos[p.qids[12:]].copy(),
                dq=p.data.qvel[p.dids[12:]].copy(),actual_previous_ff=r.last.feedforward[12:].copy(),limits=self.capture.limits)
            raise
        new=r.nav_command();new.position[12:]=self.arm_ref;new.velocity[12:]=0.
        new.kp[12:]=pm.KP[12:];new.kd[12:]=pm.KD[12:];new.feedforward[12:]=arm_ff
        age=float(p.data.time)-self.started
        if age<.2:
            new=blend_command(r.Command,self.old_command,new,age/.2)
            new.position[12:]=self.arm_ref;new.velocity[12:]=0.;new.kp[12:]=pm.KP[12:];new.kd[12:]=pm.KD[12:];new.feedforward[12:]=arm_ff
        return new

    def after_step(self):
        self.last_two.append(self.r.last.position.copy());self._sync_arrival();self.check_guards()
        self.nav.observe(self.r.nav_state(self.started))
        if self.arrival is not None:
            self.arrival.after_step()
            if self.arrival.complete:
                self.arrival.native_arrival.validate(self.arrival_runtime)
                self.complete=True;self.phase='ARRIVAL_VERIFIED'

    def report(self):
        import numpy as np
        return dict(kind='registered_compact_NAV',complete=self.complete,phase=self.phase,goal_xy=list(self.goal),
            started_time_s=self.started,observed_time_s=float(self.r.sim.data.time),entry_witness=self.capture_witness.report(),
            support_height_m=self.height,original_cold_policy_warmup_s=self.cold_policy_warmup_s,actor_forwards=self.actor_forwards,actual_displacement_m=float(np.linalg.norm(self.r.sim.data.qpos[:2]-self.origin)),
            native_goal_checks=self.nav.native.stability_checks(self.r.nav_state(self.started)),
            protected_arrival=self.arrival.report() if self.arrival is not None else None,
            engineering_probe_not_model_decision=True,no_failed_PUSH_owner_created=True,
            arm_hold_uses_existing_position_FF_intersection=True,original_effort_rate_and_geometry_limits_retained=True,
            actor_input_frame="declared_support_relative_command_Z_only",actual_world_command_history_unchanged=True)
