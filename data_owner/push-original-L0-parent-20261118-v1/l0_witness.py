"""Genuine L0 startup owner/witness, NOT an invented SupportedCapture instance.

Original standalone3N startup and CURRENT original PUSH12N support are separate.
No commands are added to make the second gate pass. No NAV capability/arrival.
"""
from pathlib import Path
import hashlib,importlib
from standard_runtime import need
from l0_startup import prepare_startup,PLAY_SHA,BRIDGE_SHA


class L0StartupOwner:
    kind='original_L0_initialization'
    def __init__(self,components,*,bundle,trace,guard):
        self.r=components['runtime'];self.registry=components['registry'];self.trace=trace;self.owner_guard=guard
        self.support_ref='ground';self.phase='ORIGINAL_INDEPENDENT_SETTLE'
        with self.r.push.active():module=importlib.import_module('play')
        sdk=Path(bundle).resolve(strict=True)
        need(Path(module.__file__).resolve()==sdk/'push/play.py'and
             hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()==PLAY_SHA,'Exact original independent startup')
        physics=type(self.r.sim).physics_step
        need(hashlib.sha256((sdk/'push/bridge.py').read_bytes()).hexdigest()==BRIDGE_SHA,'Original default PD body')
        self.startup=prepare_startup(self.r,guard=guard,actor_call_count=lambda:sum(
            x['attempted']for x in trace.rows.values()),original_settle=module.settle,play_path=sdk/'push/play.py',
            original_physics_step=physics,bridge_path=sdk/'push/bridge.py',enabled=True)
        self.witness=None

    def command(self):return self.startup.next_command()
    def after_step(self,*,native_error=None):return self.startup.after_actual_issue(native_error=native_error)
    def finish(self):
        need(self.startup.finished and not self.startup.failed and
             self.startup.original_result['stable']is True,'Original standalone startup must ACTUALLY settle')
        need(self.startup.issued==self.r.step_count>=2 and len(self.startup.last_two)==2 and
             abs(float(self.r.sim.data.time)-self.r.step_count*.005)<1e-7,'Every actual startup issue accounted; no count backfill')
        self.phase='ORIGINAL_STARTUP_FINISHED_AWAIT_REGISTERED_PUSH12N'
        if self.witness is None:self.witness=OriginalL0Witness(self)
        self.witness.validate(self.r);self.phase='ORIGINAL_L0_SETTLED_CURRENT_PUSH12N_READY'
        return self.witness

    def report(self):return dict(kind=self.kind,phase=self.phase,**self.startup.snapshot())


class OriginalL0Witness:
    """Read-only actual standalone startup + original PUSH source/FIFO/effort gates.

    Does NOT claim SupportedCapture/compact-transfer .5s or NAV-arrival status.
    Original PushEntry's own physical stance/preparation remains in the session.
    """
    def __init__(self,owner):
        from mujoco_zyh.native_behavior_executor import array_sha
        from mujoco_zyh.stall_stow import history_sha
        self.owner=owner;self.r=owner.r;self.support_ref=owner.support_ref;p=self.r.sim
        self.world=(p,p.model,p.data,p.queue,p.controller,p.box_push_target)
        self.observed_steps=self.r.step_count;self.observed_time=float(p.data.time)
        self.goal_sha=array_sha(p.box_push_target.detach().cpu().numpy());self.history_sha=history_sha(p)
        self.command_sha=array_sha(self.r.last.array())
        self.collision=self.r.push['finish'].CollisionGuard(p,self.r.push['finish'].FinishConfig())
        self.validate(self.r)

    def validate(self,runtime):
        import numpy as np
        from mujoco_zyh.native_behavior_executor import array_sha,world_snapshot
        from mujoco_zyh.stall_stow import history_sha
        from mujoco_zyh.recovery_design import committed_queue_screen
        from ainav.native.push_support_gate import current_push_source_support
        from ainav.native.registered_guards import check_object_contacts
        p=runtime.sim
        need(runtime is self.r and all(a is b for a,b in zip(self.world,
            (p,p.model,p.data,p.queue,p.controller,p.box_push_target))),'Actual same L0 world/FIFO/goal aliases')
        need(runtime.step_count==self.observed_steps and float(p.data.time)==self.observed_time and
             self.owner.startup.finished and not self.owner.startup.failed,'Fresh startup boundary, not reused after a skill')
        need(self.owner.owner_guard()is not False,'Current original owner/resource guard')
        before=world_snapshot(runtime)
        need(array_sha(p.box_push_target.detach().cpu().numpy())==self.goal_sha and history_sha(p)==self.history_sha and
             array_sha(runtime.last.array())==self.command_sha,'Actual L0 history/goal/issued reference immutable')
        current_push_source_support(runtime,self.owner.registry,'push_box',0.) # Original FOUR12N gate, not startup3N.
        check_object_contacts(runtime,self.owner.registry)
        reason=self.collision.check(p.data.qpos[p.qids[12:]],allow_hand_contact=False,record=True)
        need(not reason,'Original L0 geometry/contact/arm gate')
        need(np.linalg.norm(p.data.qvel[:3])<.035 and np.linalg.norm(p.data.qvel[3:6])<.12,
             'Original independent startup stationary envelope still live')
        need(np.max(abs(p.torque[12:])/runtime.push['model'].EFFORT[12:])<.98,'Original arm effort margin')
        screen=committed_queue_screen(queue=[x.tolist()for x in p.queue],delay_steps=[int(x)for x in p.delays],
            q=p.data.qpos[p.qids].tolist(),dq=p.data.qvel[p.dids].tolist(),effort=runtime.push['model'].EFFORT.tolist())
        need(screen['screen_pass'],'Actual immutable committed FIFO torque screen')
        need(world_snapshot(runtime)==before,'Witness is read-only, never a reset/command')
        return True

    def report(self):return dict(kind='actual_original_L0_settle_and_current_registered_PUSH_support',
        actual_startup_steps=self.observed_steps,time_s=self.observed_time,support_ref=self.support_ref,
        original_startup_3N_is_not_PUSH12N=True,actual_current_PUSH12N_and_FIFO_checked=True,
        no_SupportedCapture_or_NAV_arrival_claimed=True,model_input=False)
