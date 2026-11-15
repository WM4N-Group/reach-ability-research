"""Explicit COMPACT_NAV_READY adaptation; original zero-arm READY is NOT passed.

Frozen 210D actor and native body-XY navigation adapter are reused. The protected
arm target stays inside original soft+.01 limits, and actual observations and
previous-issued action history are retained. No physical state/queue reset.
"""
from dataclasses import replace
from pathlib import Path
import json
import numpy as np
from .stall_stow import StallStowRouter,ProtectedStow,STOW_ARM,history_sha,select_reference
from .nav_efficiency import EfficientNav

MODE='compact-arm-failed-push-resume-nav-v5'
NAV_ARM=np.array([0.,.30,-.30,0.,0.,0.])


def validate_protocol(p):
    expected=json.loads(Path(__file__).with_name('resume_nav_protocol_v5.json').read_text())
    if p!=expected:raise ValueError('Exact independent compact-resume protocol required')
    from .stall_stow import validate_protocol as base
    base(json.loads(Path(__file__).with_name('soft_stall_stow_protocol_v7.json').read_text()))
    return p


def compact_contract(runtime):
    s=runtime.sim
    soft=s.robot.data.soft_joint_pos_limits.numpy()[0][[s.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]]
    physical=s.model.jnt_range[s.jids[12:]]
    limits=np.column_stack((np.maximum(soft[:,0],physical[:,0]),np.minimum(soft[:,1],physical[:,1])))
    if not np.all((NAV_ARM>limits[:,0]+.01)&(NAV_ARM<limits[:,1]-.01)):raise ValueError('Compact target outside protected domain')
    incompatible=bool(np.any(limits[:,0]+.01>.12)|np.any(limits[:,1]-.01<-.12))
    if not incompatible:raise ValueError('Expected source-pinned zero-arm READY conflict no longer matches')
    return dict(name='COMPACT_NAV_READY_v5',original_zero_arm_READY_passed=False,
        original_entry_abs_arm_limit=.12,original_NAV_arrival_abs_arm_limit=.1,
        protected_soft_limits=limits.tolist(),compact_target=NAV_ARM.tolist(),
        compact_entry_error_limit=.04,compact_entry_arm_speed_limit=.12,hold_seconds=.5,
        original_zero_arm_contract_incompatible=True,threshold_relaxation=False,
        native_NAV_arm_kp=[40.,40.,40.,20.,20.,20.],native_NAV_arm_kd=[1.]*6,
        protected_arm_kp=[50.,50.,80.,30.,30.,20.],protected_arm_kd=[3.,2.,3.,3.,2.5,1.],
        native_NAV_arm_motor_interface_unchanged=False,native_NAV_leg_gains_unchanged=True,
        adaptation='Explicit compact arm TARGET and native-PUSH-PD/FF arm-interface adaptation; not fake observations, original zero READY, or unchanged native NAV arm gains')


def make_compact_nav(runtime,goal):
    module=runtime.nav['navigation']
    class CompactNav(module.NavSkill):
        def stability_checks(self,state):
            result=super().stability_checks(state)
            # Original .10rad tracking tolerance, relative to declared safe
            # target instead of zero. All other native predicates unchanged.
            result['arm_joints']=bool(np.max(abs(state.arm_q-NAV_ARM))<=self.config.arm_joint_tolerance)
            return result
    config=replace(module.profile_nav_config('skills'),warmup_seconds=.24)
    return EfficientNav(CompactNav(goal,0.,config,arm_zero=True))


def nominal_compact_ee(runtime):
    import mujoco
    n=runtime.n
    data=mujoco.MjData(n.model)
    data.qpos[:3]=[0.,0.,.35]  # original NavBridge nominal constructor height
    data.qpos[3:7]=[1.,0.,0.,0.]
    data.qpos[n.qids]=runtime.nav['bridge'].REFERENCE
    data.qpos[n.qids[12:]]=NAV_ARM
    mujoco.mj_forward(n.model,data)
    return n.ee_pose(data)


def protected_owner_log_handles(owner):
    if hasattr(owner,'retained_log_handles'):return owner.retained_log_handles
    return (owner.recovery_log,owner.log)


def protected_owner_log_bytes(owner):
    return sum(f.tell() for f in protected_owner_log_handles(owner))


class ResumeNavRouter:
    def __init__(self,r,native,root,*,completed_prefix=None):
        from .verified_stow_owner import VerifiedStowOwner
        if completed_prefix is not None and (not isinstance(completed_prefix,(StallStowRouter,VerifiedStowOwner))
                or completed_prefix.r is not r or completed_prefix.native is not native
                or not completed_prefix.complete):
            raise ValueError('Actual completed protected PUSH owner required for explicit NAV handoff')
        self.r=r;self.prefix=(StallStowRouter(r,native,root) if completed_prefix is None else completed_prefix);self.native=native
        self.stage=None;self.nav=None;self.arrival=None;self.ready_since=None;self.started=None
        self.extra_events=[];self.prefix_receipt=None;self.ready_contract=compact_contract(r)
        self.policy_log=(Path(root)/'resume-nav-policy-50hz.jsonl').open('x')
        self.actual_log=(Path(root)/'resume-nav-200hz.jsonl').open('x')
        self.observations=0;self.arm_ref=NAV_ARM.copy();self.arm_velocity=np.zeros(6)
        self.old_command=None;self.max_travel=0.;self.nav_start_xy=None;self.goal=None
        self.capture_since=None;self.last_state=None
    @property
    def complete(self):return self.arrival is not None and self.arrival.complete
    @property
    def phase(self):return self.stage or self.prefix.phase
    @property
    def kind(self):return 'nav' if self.stage and self.stage!='COMPACT_READY_CAPTURE' else self.prefix.kind
    @property
    def index(self):return 1 if self.stage else self.prefix.index
    @property
    def events(self):return self.prefix.events+self.extra_events+(self.arrival.events if self.arrival else [])
    @property
    def results(self):return self.prefix.results
    @property
    def switch_metrics(self):return self.prefix.switch_metrics
    @property
    def finish(self):return self.prefix.finish
    def event(self,name,**kw):
        item=dict(time=float(self.r.sim.data.time),event=name,**kw);self.extra_events.append(item);print(item,flush=True)
    def ready(self):
        rec=self.prefix.recovery;m=rec.measure()
        return bool(m['hand_force_N']<3 and not m['legal_hand_contact'] and min(m['foot_normal_N'])>=12 and m['base_linear_speed']<.02 and m['base_angular_speed']<.1 and m['tilt_rad']<.1 and m['max_foot_speed']<.03 and m['arm_error']<.04 and m['arm_speed']<.12 and np.max(abs(rec.reference-NAV_ARM))<.002 and np.max(abs(rec.velocity))<.02)
    def begin_nav(self):
        r,s=self.r,self.r.sim;before=np.r_[s.data.qpos,s.data.qvel].copy();queue=[x.copy() for x in s.queue]
        self.arm_ref=self.prefix.recovery.reference.copy();self.arm_velocity=self.prefix.recovery.velocity.copy()
        self.started=float(s.data.time);self.nav_start_xy=s.data.qpos[:2].copy();self.goal=np.array(getattr(self,'registered_goal_xy',self.nav_start_xy+np.array([0.,-.35])),dtype=float)
        surface=getattr(self,'declared_surface_height_m',0.)
        if surface not in (0.,.4):raise ValueError('Registered protected NAV support surface required')
        if surface==0.:r.reset_nav_history()
        else:r.reset_nav_history(surface)
        r.n.ee_command=nominal_compact_ee(r)
        r.n.ee_command[2]+=surface
        self.nav=make_compact_nav(r,self.goal);self.stage='RESUME_NAV';self.old_command=r.last
        self.event('compact_NAV_authority_started',goal_xy=self.goal.tolist(),arm_contract=self.ready_contract)
        if not np.array_equal(before,np.r_[s.data.qpos,s.data.qvel]) or len(queue)!=len(s.queue) or any(not np.array_equal(a,b) for a,b in zip(queue,s.queue)):raise RuntimeError('NAV entry changed physical state/queue')
    def update(self):
        r,s=self.r,self.r.sim;now=float(s.data.time)
        if self.stage is None:
            self.prefix.update()
            if self.prefix.complete:
                self.prefix_receipt=json.loads(json.dumps(self.prefix.report()));self.stage='COMPACT_READY_CAPTURE'
                self.event('failed_PUSH_stow_prefix_verified' if isinstance(self.prefix,StallStowRouter) else 'actual_verified_stow_handback')
                rec=self.prefix.recovery
                reason=rec.native.guard.segment(rec.reference,NAV_ARM)
                if reason:raise RuntimeError('compact_NAV_arm_transfer_path:'+reason)
                rec.compact_goal=NAV_ARM.copy();rec.complete=False;rec.stable_since=None;rec.phase='STOW_VERIFY'
                self.event('protected_NAV_compact_target_transfer_started',target=NAV_ARM.tolist())
            return
        if history_sha(s)!=self.prefix.recovery.retired_history_sha:raise RuntimeError('retired_PUSH_history_changed_during_NAV')
        if self.stage=='COMPACT_READY_CAPTURE':
            self.prefix.recovery.update()
            self.ready_since=(self.ready_since if self.ready_since is not None else now) if self.ready() else None
            if self.ready_since is not None and now-self.ready_since>=.5-1e-9:self.begin_nav()
        if self.stage=='RESUME_NAV':
            state=r.nav_state(self.started);velocity=self.nav.update(state);r.n.set_wbc_command(velocity,r.n.ee_command)
            # The actor's past action is the last ACTUALLY ISSUED motor target,
            # including protected arm and blend, never a discarded proposal.
            r.n.previous_action=(r.last.position-r.nav['bridge'].REFERENCE)/r.nav['bridge'].C['ACTION_SCALE']
            obs=r.n.observation()
            import torch
            with torch.inference_mode():action=r.nav_actor(torch.as_tensor(obs,device=r.device)[None]).cpu().numpy()[0]
            r.n.set_action(action);r.n.targets[12:]=self.arm_ref
            r.n.previous_action[12:]=(self.arm_ref-r.nav['bridge'].REFERENCE[12:])/r.nav['bridge'].C['ACTION_SCALE']
            self.observations+=1
            self.policy_log.write(json.dumps(dict(time_s=now,observation=obs.tolist(),terms_current=[h[-1].tolist() for h in r.n.history],actor_action=action.tolist(),last_actually_issued=r.last.array().tolist(),requested_velocity=velocity.tolist(),nominal_compact_ee=r.n.ee_command.tolist()))+'\n');self.policy_log.flush()
            m=self.prefix.recovery.measure()
            capture=self.nav.arrived and m['base_linear_speed']<.08
            self.capture_since=(self.capture_since if self.capture_since is not None else now) if capture else None
            if self.capture_since is not None:
                minimum_travel=0. if getattr(self,'behavior_verified_arrival_capture',False) else .1
                if self.max_travel<minimum_travel or self.observations<3:raise RuntimeError('NAV did not actually move')
                if getattr(self,'behavior_verified_arrival_capture',False):
                    self.event('actual_native_NAV_goal_hold_observed',actual_travel_m=self.max_travel,
                        stationary_or_short_reposition_not_counted_as_channel_demonstration=self.max_travel<.1)

                if getattr(self,'behavior_verified_arrival_capture',False):
                    from .native_nav_arrival_witness import NativeNAVArrivalWitness
                    witness=NativeNAVArrivalWitness(r,self.nav,self.started,NAV_ARM)
                    self.arrival=ProtectedStow(r,list(self.prefix.last_two),compact_goal=NAV_ARM,native_arrival=witness)
                else:self.arrival=ProtectedStow(r,list(self.prefix.last_two),compact_goal=NAV_ARM)

                self.arrival.phase='ARRIVAL_CAPTURE'  # native grounded foot references; QP must actually land/load feet
                self.arrival.arrival_balance=True
                cfg=replace(self.arrival.native.config,stance_posture_weight=r.push['finish'].FinishConfig().stance_posture_weight)
                self.arrival.native.config=cfg;self.arrival.native.qp.config=cfg
                self.arrival.reference=self.arm_ref.copy();self.arrival.velocity=self.arm_velocity.copy()
                self.stage='ARRIVAL_CAPTURE';self.event('actual_NAV_arrived_QP_brake_capture_started',travel_m=self.max_travel)
        elif self.arrival:
            self.arrival.update()
            self.nav.observe(r.nav_state(self.started))
            goal_checks=self.nav.native.stability_checks(r.nav_state(self.started))
            if not goal_checks['position'] or not goal_checks['yaw']:raise RuntimeError('arrival_original_NAV_goal_gate_lost')
            if self.arrival.complete and not self.nav.arrived:raise RuntimeError('arrival_original_NAV_stationary_hold_lost')
            if self.arrival.phase=='STOW_VERIFY':self.stage='ARRIVAL_COMPACT_VERIFY'
            if self.arrival.complete:self.stage='ARRIVAL_COMPACT_VERIFIED'
    def next_command(self):
        r,s=self.r,self.r.sim
        if self.stage is None:return self.prefix.next_command()
        if self.stage=='COMPACT_READY_CAPTURE':return self.prefix.recovery.command()
        if self.arrival:return self.arrival.command()
        old=self.prefix.recovery;pm=r.push['model'];gravity=s.robot.get_gravity_compensation_forces().numpy()[0]
        gravity=gravity[[s.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]]
        self.arm_ref,self.arm_velocity,_=select_reference(NAV_ARM,self.arm_ref,self.arm_velocity,s.data.qpos[s.qids[12:]],s.data.qvel[s.dids[12:]],pm.KP[12:],pm.KD[12:],gravity,pm.EFFORT[12:],old.limits,dt=.005)
        new=r.nav_command();new.position[12:]=self.arm_ref;new.velocity[12:]=self.arm_velocity
        new.kp[12:]=pm.KP[12:];new.kd[12:]=pm.KD[12:];new.feedforward[12:]=gravity
        age=float(s.data.time)-self.started
        if age<.2:
            from runtime import blend_command
            new=blend_command(r.Command,self.old_command,new,age/.2)
            # Retain strict protected arm semantics; only legs are crossfaded.
            new.position[12:]=self.arm_ref;new.velocity[12:]=self.arm_velocity
            new.kp[12:]=pm.KP[12:];new.kd[12:]=pm.KD[12:];new.feedforward[12:]=gravity
        return new
    def after_step(self):
        r,s=self.r,self.r.sim
        if self.stage is None or self.stage=='COMPACT_READY_CAPTURE':self.prefix.after_step();return
        limits=s.model.jnt_range[s.jids];q=s.data.qpos[s.qids];dq=s.data.qvel[s.dids]
        if not np.isfinite(np.r_[s.data.qpos,s.data.qvel]).all() or np.any(q<limits[:,0]) or np.any(q>limits[:,1]) or np.any(abs(dq)>r.push['model'].SPEED):raise RuntimeError('resume_NAV_actual_range_speed_nonfinite')
        reason=self.prefix.recovery.native.guard.check(q[12:],record=True)
        if reason:raise RuntimeError('resume_NAV_actual_geometry:'+reason)
        flags=self.prefix.original_termination();bad=[k for k,v in flags.items() if k!='box_settled' and v]
        if bad:raise RuntimeError('resume_NAV_native_hard_flags:'+','.join(bad))
        self.prefix.last_two.append(r.last.position.copy())
        if self.arrival:self.arrival.after_step()
        self.nav.observe(r.nav_state(self.started))
        travel=float(np.linalg.norm(s.data.qpos[:2]-self.nav_start_xy));self.max_travel=max(self.max_travel,travel)
        if history_sha(s)!=self.prefix.recovery.retired_history_sha:raise RuntimeError('retired_PUSH_history_changed_after_NAV_step')
        self.actual_log.write(json.dumps(dict(time_s=float(s.data.time),phase=self.stage,q=q.tolist(),dq=dq.tolist(),base_xyz=s.data.qpos[:3].tolist(),velocity=r.n.velocity().tolist(),foot_normal_N=s.forces[s.feet_ids,2].tolist(),nav_checks=self.nav.native.stability_checks(r.nav_state(self.started)),actual_travel_m=travel,original_PUSH_history_preserved=True,arrival_metrics=self.arrival.metrics if self.arrival else None))+'\n')
        if self.actual_log.tell()+self.policy_log.tell()+protected_owner_log_bytes(self.prefix)>32*1024*1024:raise RuntimeError('resume_NAV_private_log_quota')
    def diagnostics(self):return dict(phase=self.phase,abort=self.prefix.abort,compact_NAV=self.nav.diagnostics() if self.nav else None)
    def report(self):
        result=self.prefix_receipt or self.prefix.report()
        result['resume_NAV']=dict(contract=self.ready_contract,stage=self.stage,goal_xy=self.goal.tolist() if self.goal is not None else None,actual_travel_m=self.max_travel,actual_policy_observations=self.observations,original_PUSH_history_preserved=self.prefix.recovery is not None and history_sha(self.r.sim)==self.prefix.recovery.retired_history_sha,arrival=self.arrival.report() if self.arrival else None,original_zero_arm_READY_passed=False,scope='explicit compact-target adaptation; frozen actor, no B/full route')
        return result
    def close(self):self.prefix.close();self.policy_log.close();self.actual_log.close()
