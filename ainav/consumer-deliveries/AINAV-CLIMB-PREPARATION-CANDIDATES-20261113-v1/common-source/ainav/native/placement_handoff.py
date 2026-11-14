"""Two-phase placement: admissible braking is NOT native task success.

This LOCAL wrapper leaves the original NativeOptionSession/actor/goal/history
and motor FIFO in place. Only a genuine clocked native settled result permits
NN-confirmed landing or final success. There are no scene-time/box/route triggers; only native phase clocks.
"""


def original_brake_entry(runtime,last_two,*,arm_policy='issued_hold'):
    """Read-only necessary entry math. NOT leg/contact/dynamic certification."""
    import numpy as np
    from mujoco_zyh.recovery_design import committed_queue_screen
    from mujoco_zyh.moving_arm_reference import brake_arm_hold
    from mujoco_zyh.native_behavior_executor import array_sha
    p=runtime.sim;pm=runtime.push['model'];old=runtime.last
    if len(last_two)!=2 or not np.array_equal(last_two[-1],old.position):
        raise RuntimeError('Brake requires the last two actually issued references')
    if not np.array_equal(old.kp[12:],pm.KP[12:]) or not np.array_equal(old.kd[12:],pm.KD[12:]):
        raise RuntimeError('Brake entry must retain actual original PUSH arm gains')
    prefix=committed_queue_screen(queue=[x.tolist() for x in p.queue],delay_steps=[int(x) for x in p.delays],
        q=p.data.qpos[p.qids].tolist(),dq=p.data.qvel[p.dids].tolist(),effort=pm.EFFORT.tolist())
    if not prefix['screen_pass']:raise RuntimeError('placement_arrival_original_immutable_FIFO_refused')
    limits=np.column_stack((np.maximum(p.model.jnt_range[p.jids[12:],0],p.soft_limits[12:,0]),
        np.minimum(p.model.jnt_range[p.jids[12:],1],p.soft_limits[12:,1])))
    velocity=(last_two[-1][12:]-last_two[-2][12:])/.005
    if arm_policy=='issued_hold':
        _,_,ff,receipts=brake_arm_hold(old.position[12:],old.position[12:],velocity,
            p.data.qpos[p.qids[12:]],p.data.qvel[p.dids[12:]],pm.KP[12:],pm.KD[12:],old.feedforward[12:],pm.EFFORT[12:],limits)
    elif arm_policy=='original_unload':
        from mujoco_zyh.stall_stow import unload_reference
        gravity=p.robot.get_gravity_compensation_forces().numpy()[0]
        gravity=gravity[[p.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]]
        _,_,ff,receipts=unload_reference(p.data.qpos[p.qids[12:]],old.position[12:],old.position[12:],velocity,
            p.data.qpos[p.qids[12:]],p.data.qvel[p.dids[12:]],pm.KP[12:],pm.KD[12:],gravity,pm.EFFORT[12:],limits,0.,start_ff=old.feedforward[12:])
    elif arm_policy=='reconciled_unload':
        from .reconciled_unload import reconciled_unload_reference
        gravity=p.robot.get_gravity_compensation_forces().numpy()[0]
        gravity=gravity[[p.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]]
        _,_,ff,receipts=reconciled_unload_reference(p.data.qpos[p.qids[12:]],old.position[12:],velocity,
            p.data.qpos[p.qids[12:]],p.data.qvel[p.dids[12:]],pm.KP[12:],pm.KD[12:],gravity,old.feedforward[12:],pm.EFFORT[12:],limits)
    else:raise ValueError('Explicit original brake arm policy required')
    from .stop_actor_trace import require_original_arm_ff_slew
    require_original_arm_ff_slew(old.feedforward[12:],ff,pm.EFFORT[12:])
    return dict(original_FIFO_screen=prefix,original_first_arm_step_receipts=receipts,
        last_actually_issued_command_sha256=array_sha(old.array()),necessary_math_only=True,
        arm_policy=arm_policy,physics_steps=0,original_goal_and_FIFO_not_modified=True,model_input=False)


class NativePlacementServices:
    """Private native measurement/construction authority, never model input."""
    def __init__(self,native,session,issued,contract,*,arm_policy='issued_hold',stop_trace=None,leg_policy='held_native_scale',journal=None):
        from mujoco_zyh import native_behavior_executor as api
        from .completion_clock import ClockedNativeSettled
        if arm_policy not in ('issued_hold','original_unload','reconciled_unload'):raise ValueError('Explicit registered native brake arm policy required')
        if leg_policy not in ('held_native_scale','reverse_after_native_confirmation'):raise ValueError('Explicit native stop-leg policy required')
        self.leg_policy=leg_policy;self._original_leg_policy=leg_policy;self.leg_release=None
        self.arm_policy=arm_policy;self._original_arm_policy=arm_policy;self.stop_trace=stop_trace;self.unload_binding=None
        self.native,self.session,self.issued,self.contract,self.api=native,session,issued,contract,api
        if leg_policy=='reverse_after_native_confirmation' and not callable(journal):raise ValueError('Native confirmation journal required')
        self.journal=journal
        self.p=native.r.sim;self.contract_sha=contract.sha256
        self.goal_sha=api.array_sha(self.p.box_push_target.detach().cpu().numpy())
        self.body_binding=getattr(self.p,'body_braking_reference',None)
        if self.body_binding is not None and self.body_binding.declaration.body_goal_xy_m!=contract.public_goal_xy_m:
            raise ValueError('Published public placement and prebound body-braking reference differ')
        if not isinstance(self.p.settled,ClockedNativeSettled):
            raise ValueError('Two-phase handoff requires the actual original clocked native settled term')
    def assert_immutable(self):
        if self.leg_policy!=self._original_leg_policy:raise RuntimeError('Declared leg stop policy changed')
        if self.leg_release is not None:self.leg_release.assert_immutable()
        if self.arm_policy!=self._original_arm_policy:raise RuntimeError('Declared stop arm policy changed')
        if self.unload_binding is not None:self.unload_binding.assert_immutable()
        if self.contract.sha256!=self.contract_sha or self.api.array_sha(self.p.box_push_target.detach().cpu().numpy())!=self.goal_sha:
            raise RuntimeError('Immutable public placement or native drive goal changed')
        if getattr(self.p,'body_braking_reference',None) is not self.body_binding:
            raise RuntimeError('Selected body-braking binding replaced')
        if self.body_binding is not None:self.body_binding.assert_immutable()
    def measure(self):
        self.assert_immutable();p=self.p
        r=self.contract.evaluate(box_position=p.data.xpos[p.box_id].tolist(),
            rotation_world_from_box=p.data.xmat[p.box_id].reshape(3,3).tolist(),
            native_goal_xy=p.box_push_target.detach().cpu().numpy()[0,:2].tolist())
        height=abs(float(p.data.xpos[p.box_id,2])-self.contract.source_surface_height_m-self.contract.box_size_m[2]/2)
        r.update(task_geometry_pass=bool(r['public_XY_error_m']<.02 and abs(r['actual_signed_dock_gap_m'])<=.01 and height<.02),
            time_s=float(p.data.time),actual_box_position_m=p.data.xpos[p.box_id].tolist(),
            actual_box_rotation=p.data.xmat[p.box_id].reshape(3,3).tolist(),
            actual_box_linear_velocity_m_s=p.data.qvel[p.box_did:p.box_did+3].tolist(),
            original_native_drive_goal_sha256=self.goal_sha)
        if self.body_binding is not None:r['body_braking_reference_sha256']=self.body_binding.sha256
        return r
    def native_ready(self):
        self.assert_immutable();ready=bool(self.p.settled(self.p,self.p.hand_cfg)[0])
        state=self.p.settled.report()
        if ready and (state['failed'] or state['native_duration_s']<.5 or not state['native_contact_seen']):
            raise RuntimeError('Original native settled result lacks genuine 0.5s clocked confirmation')
        return ready
    def clock_report(self):return self.p.settled.report()
    def begin_brake(self,*,confirmed):
        from mujoco_zyh.moving_push_exit import MovingPushExit
        from mujoco_zyh.resume_nav import NAV_ARM
        self.session.check_guards();self.assert_immutable()
        before=self.api.world_snapshot(self.session.runtime)
        receipt=original_brake_entry(self.native.r,list(self.session.last_two),arm_policy=self.arm_policy)
        seed=self.issued.seed()
        # The original seed reader only commits proposals after real issuance.
        if seed['first_actual_issued_time_s']>float(self.p.data.time) or not (seed['targets']==self.native.r.last.position).all():
            raise RuntimeError('Brake seed does not match an actually issued native PUSH command')
        if confirmed and not self.native_ready():raise RuntimeError('NN-confirmed landing cannot precede actual native confirmation')
        brake=MovingPushExit(self.native.r,list(self.session.last_two),compact_goal=NAV_ARM,
            hold_issued_arm=self.arm_policy=='issued_hold',leg_stop_seed=seed,nn_handoff=confirmed,nn_handoff_dwell_s=.1,
            retirement_reason='voluntary_early_exit')
        # Keep the inherited 0.05E arm FF slew gate even on the original unload
        # branch, whose algebra alone does not promise a per-step FF bound.
        from types import MethodType
        from .stop_actor_trace import require_original_arm_ff_slew
        original_command=brake.command
        if self.arm_policy=='reconciled_unload':
            from .unload_reference_binding import ReconciledUnloadBinding
            self.unload_binding=ReconciledUnloadBinding(brake)
            original_command=self.unload_binding.command
            receipt['reconciled_unload_binding']=self.unload_binding.receipt()
        def guarded_command(this):
            command=original_command()
            require_original_arm_ff_slew(this.r.last.feedforward[12:],command.feedforward[12:],this.pm.EFFORT[12:])
            return command
        brake.command=MethodType(guarded_command,brake)
        if self.leg_policy=='reverse_after_native_confirmation':
            from .leg_release_brake import NativeLegReleaseBrake
            original_blend=self.native.r.push['bridge'].PushArmIK.apply.__globals__['contact_action_blend']
            self.leg_release=NativeLegReleaseBrake(brake.leg_stop,native_blend=original_blend,
                ramp_s=float(self.p.cfg.push_leg_release_ramp_s),native_confirmation=self.native_ready,journal=self.journal)
            if confirmed:self.leg_release.confirm()
            receipt['reverse_leg_release']=self.leg_release.receipt()
        if self.stop_trace is not None and brake.leg_stop is not None:
            stop=brake.leg_stop;original_infer=stop.infer;trace=self.stop_trace
            def audited_infer(actor,observation,device):
                if actor is not self.native.r.push_actors[0]:raise RuntimeError('Original PUSH leg actor identity changed')
                raw=original_infer(actor,observation,device)
                trace.propose(time_s=float(self.p.data.time),observation=observation,raw_leg=raw,
                    scale=stop.scale,slots=stop.slots,reference=stop.pm.REFERENCE)
                return raw
            stop.infer=audited_infer
        if self.api.world_snapshot(self.session.runtime)!=before:raise RuntimeError('Brake construction changed actual world/FIFO')
        self.assert_immutable()
        receipt.update(actual_stop_seed_time_s=seed['time_s'],actual_stop_seed_first_issue_s=seed['first_actual_issued_time_s'],
            native_confirmation_before_brake=confirmed,NN_confirmed_landing_used=confirmed)
        return brake,receipt
    def promote_confirmed_landing(self,brake):
        if not self.native_ready():raise RuntimeError('Cannot promote landing without original native settled confirmation')
        if self.leg_release is not None:self.leg_release.confirm()
        if brake.nn_handoff or brake.leg_stop_completed:return False
        # Explicit mode transition after genuine confirmation, not a reconstructed
        # controller/seed. All references, FIFO and stop observation histories stay.
        brake.nn_handoff=True
        return True


class TwoPhasePlacementMachine:
    """Service-injected state logic; production wrap below always uses natives."""
    def __init__(self,native,services,journal):
        self.native,self.services,self.journal=native,services,journal
        self.brake=None;self.confirmed=False;self._result=None;self.entry_receipt=None
    def __getattr__(self,name):return getattr(self.native,name)
    @property
    def phase(self):return self.brake.phase if self.brake is not None else self.native.phase
    def _confirmation(self):
        ready=self.services.native_ready()
        if self.confirmed and not ready:raise RuntimeError('Original native settled confirmation lost during placement brake')
        if ready and not self.confirmed:
            self.confirmed=True
            self.journal(dict(event='placement_original_native_clock_confirmed',native_clock=self.services.clock_report(),
                **self.services.measure()))
        if ready and self.brake is not None and self.services.promote_confirmed_landing(self.brake):
            self.journal(dict(event='placement_original_NN_confirmed_landing_promoted_without_reset',
                native_clock=self.services.clock_report(),**self.services.measure()))
        return ready
    def _begin(self,confirmed):
        self.brake,self.entry_receipt=self.services.begin_brake(confirmed=confirmed)
        self.journal(dict(event='placement_arrival_original_brake_started',native_success_not_declared=True,
            genuine_native_confirmation=confirmed,entry=self.entry_receipt,**self.services.measure()))
    def update(self):
        self.services.assert_immutable();measurement=self.services.measure()
        self.journal(dict(event='placement_actual_20ms_measurement',phase=self.phase,
            native_clock=self.services.clock_report(),**measurement))
        if self.brake is None:
            ready=self._confirmation()
            if self.native.phase=='run' and measurement['task_geometry_pass']:
                self._begin(ready)
            else:
                self.native.update();self.services.assert_immutable()
                if self.native.finish is not None:
                    if not self._confirmation() or not self.services.measure()['placement_geometry_verified']:
                        raise RuntimeError('Native confirmation before immutable placement verified')
                    self._begin(True)
        if self.brake is not None:
            self._confirmation();self.brake.update();self._verify_complete()
    def next_command(self):return self.brake.command() if self.brake is not None else self.native.next_command()
    def after_step(self):
        if self.brake is None:self.native.after_step()
        else:
            self.brake.after_step();self._confirmation();self._verify_complete()
    def _verify_complete(self):
        self.services.assert_immutable()
        if self.brake is None or not self.brake.complete:return False
        if not self._confirmation():raise RuntimeError('Protected stow alone is not original native PUSH success')
        m=self.services.measure()
        if not m['placement_geometry_verified']:raise RuntimeError('Original immutable public/native placement lost after stow')
        if self._result is None:
            self._result=dict(skill='push',successful=True,finish=self.brake.report(),placement=m,
                original_native_clock=self.services.clock_report(),entry=self.entry_receipt,
                completion_definition='original clocked native settled + immutable placement + actual original guarded stow',
                original_direct_finish_claimed_complete=False,task_success_not_inferred=True)
        return True
    @property
    def complete(self):return self._verify_complete()
    @property
    def results(self):
        # Cleanup cannot fabricate success from geometry or a retired owner.
        complete=self._verify_complete()
        return list(self.native.results)+([self._result] if complete else [])
    def placement_receipt(self):return self.services.measure()


def wrap_two_phase_placement(session,contract,journal,*,arm_policy='issued_hold',stop_trace=None,leg_policy='held_native_scale'):
    from mujoco_zyh.native_push_stop import IssuedPushObservation
    from types import MethodType
    native=session.machine;observed=IssuedPushObservation(native.r.sim)
    services=NativePlacementServices(native,session,observed,contract,arm_policy=arm_policy,stop_trace=stop_trace,leg_policy=leg_policy,journal=journal)
    session.machine=TwoPhasePlacementMachine(native,services,journal)
    original_after=session.after_step
    def audit_actual_issue(this):
        # The native executor calls this only after a validated real step;
        # do not lose its final commit when an after-step hard guard refuses.
        if services.unload_binding is not None:
            services.unload_binding.after_actual_issue(this.runtime.last,physical_tick=this.runtime.step_count,time_s=float(this.runtime.sim.data.time))
        if services.stop_trace is not None:
            services.stop_trace.actual_issue(this.runtime.last,physical_tick=this.runtime.step_count,time_s=float(this.runtime.sim.data.time))
        previous=observed.committed['time_s'] if observed.committed is not None else None
        observed.after_actual_issuance(this.runtime.last)
        actual=observed.committed
        if (services.body_binding is not None and actual is not None and actual['time_s']!=previous):
            journal(dict(event='body_reference_native_observation_actually_committed',
                time_s=float(this.runtime.sim.data.time),observation_time_s=actual['time_s'],
                original_native_goal_sha256=services.goal_sha,
                body_reference_sha256=services.body_binding.sha256,
                observation_sha256=services.api.array_sha(actual['observation']),
                actual_issued_command_sha256=services.api.array_sha(this.runtime.last.array()),
                requested_velocity_history=actual['observation'][180:189].reshape(3,3).tolist(),
                model_input=False))
    def after_actual_issue(this):
        from .stop_actor_trace import run_after_step_with_audit
        run_after_step_with_audit(original_after,lambda:audit_actual_issue(this))
    session.after_step=MethodType(after_actual_issue,session)
    return session
