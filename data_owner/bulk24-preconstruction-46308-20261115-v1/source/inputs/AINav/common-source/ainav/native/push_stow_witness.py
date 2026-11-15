"""Live same-world original VerifiedStowOwner after actual PUSH success.

Never reconstructed from episode files or a geometry/NN-only receipt. The
selected native runtime stays the original owner; global runtime identity is
separately checked, not overwritten to disguise selected/global aliases.
"""
from .supported_capture import capture_ready


def require_live_success_boundary(runtime,session,executor):
    if (getattr(session,'runtime',None) is not runtime or executor.runtime is not runtime
            or executor.session is not session or not executor.reported_end
            or executor.last_outcome!='succeeded' or session.outcome!='succeeded'):
        raise ValueError('Actual executor/session succeeded boundary required')


class ActualPushStowSupportWitness:
    def __init__(self,runtime,session,executor,registry,*,support_ref):
        from mujoco_zyh.native_behavior_executor import NativeOptionSession,world_snapshot
        from mujoco_zyh.verified_stow_owner import VerifiedStowOwner
        from mujoco_zyh.stall_stow import ProtectedStow
        from .placement_handoff import TwoPhasePlacementMachine
        import numpy as np
        if not isinstance(session,NativeOptionSession) or session.runtime is not runtime:
            raise ValueError('Actual same-global-runtime native PUSH session required')
        if not isinstance(session.machine,TwoPhasePlacementMachine):raise ValueError('Actual placement/stow machine required')
        require_live_success_boundary(runtime,session,executor)
        if support_ref not in registry.surfaces:raise ValueError('Explicit registered support required')
        before=world_snapshot(runtime);session.sync();machine=session.machine
        if not machine.complete or machine.brake is None:raise ValueError('Geometry or NN confirmation alone cannot hand back ownership')
        stow=machine.brake.stow;selected=machine.native.r
        if not isinstance(stow,ProtectedStow) or not stow.complete or stow.r is not selected or stow.phase!='STOW_VERIFIED':
            raise ValueError('Actual original completed protected stow required')
        if (selected.sim.data is not runtime.sim.data or selected.sim.queue is not runtime.sim.queue
                or stow.s.data is not runtime.sim.data or stow.s.queue is not runtime.sim.queue):
            raise ValueError('Selected PUSH/stow and global runtime must share actual world/FIFO')
        if len(session.last_two)!=2 or runtime.step_count<2 or not np.array_equal(session.last_two[-1],runtime.last.position):
            raise ValueError('Two actual latest issued references required')
        self.r,self.session,self.executor,self.registry=runtime,session,executor,registry
        self.data,self.queue=runtime.sim.data,runtime.sim.queue;self.support_ref=support_ref
        self.selected_runtime=selected;self.stow=stow;self.observed_time=float(self.data.time);self.observed_tick=runtime.step_count
        self.owner=VerifiedStowOwner(selected,machine.native,stow,list(session.last_two),reason='actual_placement_success_guarded_stow',original_termination=selected.sim.termination)
        # Native NAV's capture interface needs these original guarded objects.
        # Aliases on this new owner only; original class/source/world untouched.
        self.owner.guard=stow.native.guard;self.owner.limits=stow.limits
        self.actual_issued_steps=runtime.step_count-round(stow.started/.005)
        if self.actual_issued_steps<2:raise ValueError('Actual protected stow command history required')
        self.validate(runtime)
        if world_snapshot(runtime)!=before:raise RuntimeError('Live owner construction changed actual world/FIFO')

    def validate(self,runtime):
        import numpy as np
        from .registered_compact_nav import validate_support_and_goal
        from .registered_guards import check_object_contacts
        if runtime is not self.r or runtime.sim.data is not self.data or runtime.sim.queue is not self.queue:
            raise ValueError('PUSH stow witness belongs to another world/runtime/FIFO')
        if self.executor.session is not self.session or not self.executor.reported_end or self.executor.last_outcome!='succeeded':
            raise ValueError('Original completed PUSH no longer owns the dispatch boundary')
        if float(self.data.time)<self.observed_time or runtime.step_count<self.observed_tick:raise ValueError('Actual owner clock regressed')
        self.session.sync();self.session.check_guards()
        if not self.session.machine.complete or not self.stow.complete or self.stow.phase!='STOW_VERIFIED':raise RuntimeError('Original complete PUSH/stow gate lost')
        p=runtime.sim;surface=self.registry.surfaces[self.support_ref]
        validate_support_and_goal(surface,p.data.xpos[p.feet_ids].tolist(),p.forces[p.feet_ids,2].tolist(),p.data.qpos[:2].tolist())
        check_object_contacts(runtime,self.registry)
        reason=self.owner.guard.check(p.data.qpos[p.qids[12:]],allow_hand_contact=False,record=True)
        if reason:raise RuntimeError('Actual PUSH handback geometry:'+reason)
        metrics=self.stow.measure();metrics.update(reference_error=float(np.max(abs(self.stow.reference-self.stow.compact_goal))),
            reference_speed=float(np.max(abs(self.stow.velocity))),on_declared_support=True)
        if not capture_ready(metrics) or metrics['legal_hand_contact']:raise RuntimeError('Actual original compact supported handback gate lost')
        if not np.array_equal(self.session.last_two[-1],runtime.last.position):raise RuntimeError('Actual final issued reference changed without owner receipt')
        return True

    def report(self):
        return dict(kind='actual_successful_PUSH_original_verified_stow_owner',time_s=self.observed_time,physical_tick=self.observed_tick,
            support_ref=self.support_ref,actual_issued_steps=self.actual_issued_steps,selected_native_runtime_preserved=True,
            no_failed_PUSH_or_cold_start_or_NAV_arrival_claimed=True,no_recorded_state_recovery=True,automatic_successor_admission=False,model_input=False)
