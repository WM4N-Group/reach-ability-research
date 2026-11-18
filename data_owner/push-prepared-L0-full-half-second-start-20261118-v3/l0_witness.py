"""Genuine L0 startup owner/witness, NOT an invented SupportedCapture instance.

Original standalone3N startup and CURRENT original PUSH12N support are separate.
No commands are added to make the second gate pass. No NAV capability/arrival.
"""
from pathlib import Path
import hashlib,importlib
from standard_runtime import need
from l0_startup import prepare_startup,PLAY_SHA,BRIDGE_SHA


def _current_arm_gate_once(owner, runtime, collision, *, enabled=False):
    """Private bounded audit around ONE original call; never admission authority.

    The record lives on owner BEFORE construction can fail, not on a witness
    whose assignment may never finish. No replay, second guard or live writes.
    """
    if enabled is not True:
        raise ValueError('Arm admission observer disabled; no guard called')
    import math
    import re
    p = runtime.sim
    q = p.data.qpos[p.qids[12:]]  # Same exact original call argument, not q_before.
    owner.arm_gate_attempts += 1
    audit = dict(schema='data-same-call-original-arm-admission-v1',
                 attempt=owner.arm_gate_attempts, stage='SAMPLING',
                 task_step=None, task_sim_s=None, sample_complete=False,
                 actual_arm_q=None, actual_arm_dq=None, actual_model_hard_limits=None,
                 actual_model_joint_names=None, outside_hard_limits_with_1mrad_slack=None,
                 original_hard_limit_slack_rad=.001, sample_error_type=None,
                 guard_passed=None, reason_class=None, original_reason_text=None,
                 original_reason_sha256=None, guard_error_type=None,
                 guard_errno=None, original_guard_calls=0,
                 same_call_private_observation_not_command_or_owner_authority=True,
                 model_input=False)
    owner.arm_gate_audit = audit
    try:
        tick, stamp = runtime.step_count, float(p.data.time)
        values = [float(v) for v in q]
        velocity = [float(v) for v in p.data.qvel[p.dids[12:]]]
        limits = [[float(v) for v in row] for row in p.model.jnt_range[p.jids[12:]]]
        names = [str(p.model.joint(int(j)).name) for j in p.jids[12:]]
        numbers = [stamp, *values, *velocity, *[x for row in limits for x in row]]
        if (type(tick) is not int or tick < 0 or not math.isfinite(stamp) or stamp < 0
                or len(values) != 6 or len(velocity) != 6 or len(limits) != 6
                or any(len(row) != 2 or row[0] > row[1] for row in limits)
                or not all(math.isfinite(v) for v in numbers)
                or any(not re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}', n) for n in names)):
            raise ValueError('Actual arm sample unavailable/invalid')
        audit.update(task_step=tick, task_sim_s=stamp, sample_complete=True,
                     actual_arm_q=values, actual_arm_dq=velocity,
                     actual_model_hard_limits=limits, actual_model_joint_names=names,
                     outside_hard_limits_with_1mrad_slack=[
                         value < lo-.001 or value > hi+.001
                         for value, (lo, hi) in zip(values, limits)])
    except BaseException as exc:
        audit['sample_error_type'] = type(exc).__name__
    audit['stage'] = 'ORIGINAL_GUARD_CALL'
    audit['original_guard_calls'] = 1
    try:
        reason = collision.check(q, allow_hand_contact=False, record=True)
    except BaseException as exc:
        try:
            number = getattr(exc, 'errno', None)
        except BaseException:
            number = None  # Metadata property failure cannot replace the primary.
        audit.update(stage='ORIGINAL_GUARD_RAISED', guard_error_type=type(exc).__name__,
                     guard_errno=number if type(number) is int else None)
        raise  # Original object/type/traceback, no new stateful check or retry.
    audit.update(stage='ORIGINAL_GUARD_RETURNED', guard_passed=(not reason) if type(reason) is str else None)
    if type(reason) is str:
        audit['original_reason_sha256'] = hashlib.sha256(reason.encode('utf-8', errors='backslashreplace')).hexdigest()
        if not reason or reason == 'arm_joint_limit':
            audit.update(reason_class='PASS' if not reason else 'ARM_JOINT_LIMIT', original_reason_text=reason)
        else:
            match = re.fullmatch(r'([A-Za-z0-9_.-]{1,64}):([A-Za-z0-9_.-]{1,64}):(-?[0-9]+\.[0-9]{5})m', reason)
            if match:
                audit.update(reason_class='ARM_GEOMETRY_PAIR', original_reason_text=reason,
                             original_pair=list(match.group(1, 2)),
                             original_returned_distance_rounded_m=float(match.group(3)))
            else:
                audit['reason_class'] = 'UNRECOGNIZED_NONEMPTY_REASON_HASH_ONLY'
    else:
        audit['reason_class'] = 'UNEXPECTED_RETURN_TYPE'
    # A refusal/exception remains the original refusal/exception. Successful
    # but unobservable/unknown-schema admission is conservatively disallowed.
    if not reason and (not audit['sample_complete'] or type(reason) is not str):
        audit['stage'] = 'AUDIT_UNAVAILABLE_NO_ADMISSION'
        raise RuntimeError('Arm admission audit unavailable; no admission')
    return reason


class L0StartupOwner:
    kind='prepared_L0_live_bias_initialization'
    def __init__(self,components,*,bundle,trace,guard):
        self.r=components['runtime'];self.registry=components['registry'];self.trace=trace;self.owner_guard=guard
        self.support_ref='ground';self.phase='PREPARED_L0_LIVE_BIAS_ORIGINAL_SETTLE_FLOW'
        with self.r.push.active():module=importlib.import_module('play')
        sdk=Path(bundle).resolve(strict=True)
        need(Path(module.__file__).resolve()==sdk/'push/play.py'and
             hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()==PLAY_SHA,'Exact original independent startup')
        physics=type(self.r.sim).physics_step
        need(hashlib.sha256((sdk/'push/bridge.py').read_bytes()).hexdigest()==BRIDGE_SHA,'Original default PD body')
        self.startup=prepare_startup(self.r,guard=guard,actor_call_count=lambda:sum(
            x['attempted']for x in trace.rows.values()),original_settle=module.settle,play_path=sdk/'push/play.py',
            original_physics_step=physics,bridge_path=sdk/'push/bridge.py',enabled=True)
        # Selected prospective PREPARED L0 delta is installed BEFORE next_command
        # generates/records expected bytes. No issued/sealed/r.last patch.
        from registered_arm_ff import prepare as prepare_live_bias_command
        import l0_startup
        self.prepared_arm_ff=prepare_live_bias_command(self.r,original_physics_step=physics,
            bridge_path=sdk/'push/bridge.py',push_entry_path=sdk/'switch/push_entry.py',
            startup_source_path=Path(l0_startup.__file__),enabled=True)
        need(self.startup.issued==0 and not self.startup.pending and not self.startup.finished,
             'Install selected command source only before first expected seal')
        self.startup.default_command=self.prepared_arm_ff
        self.witness=None
        self.arm_gate_attempts=0
        self.arm_gate_audit=None

    def command(self):return self.startup.next_command()
    def after_step(self,*,native_error=None):return self.startup.after_actual_issue(native_error=native_error)
    def finish(self):
        need(self.startup.finished and not self.startup.failed and
             self.startup.original_result['stable']is True,'Original standalone startup must ACTUALLY settle')
        need(self.startup.issued==self.r.step_count>=2 and len(self.startup.last_two)==2 and
             abs(float(self.r.sim.data.time)-self.r.step_count*.005)<1e-7,'Every actual startup issue accounted; no count backfill')
        self.phase='PREPARED_L0_SETTLE_FINISHED_AWAIT_REGISTERED_PUSH12N'
        if self.witness is None:self.witness=OriginalL0Witness(self)
        self.witness.validate(self.r);self.phase='PREPARED_L0_CURRENT_REGISTERED_PUSH12N_READY'
        return self.witness

    def report(self):
        result=dict(kind='actual_prepared_L0_registered_arm_live_bias_FF_only',phase=self.phase,
            **self.startup.snapshot(),arm_gate_attempts=self.arm_gate_attempts,arm_gate_audit=self.arm_gate_audit)
        result['original_settle_control_flow_result_with_prepared_arm_FF']=result.pop('original_startup_result')
        result.update(prepared_arm_FF_command_source=self.prepared_arm_ff.snapshot(),
            unmodified_standalone_L0=False,natural_predecessor_L1=False,
            only_control_delta='REGISTERED_SIX_ARM_LIVE_QFRC_BIAS_FF_ONLY')
        return result


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
        reason=_current_arm_gate_once(self.owner,runtime,self.collision,enabled=True)
        need(not reason,'Original L0 geometry/contact/arm gate')
        need(np.linalg.norm(p.data.qvel[:3])<.035 and np.linalg.norm(p.data.qvel[3:6])<.12,
             'Original independent startup stationary envelope still live')
        need(np.max(abs(p.torque[12:])/runtime.push['model'].EFFORT[12:])<.98,'Original arm effort margin')
        screen=committed_queue_screen(queue=[x.tolist()for x in p.queue],delay_steps=[int(x)for x in p.delays],
            q=p.data.qpos[p.qids].tolist(),dq=p.data.qvel[p.dids].tolist(),effort=runtime.push['model'].EFFORT.tolist())
        need(screen['screen_pass'],'Actual immutable committed FIFO torque screen')
        need(world_snapshot(runtime)==before,'Witness is read-only, never a reset/command')
        return True

    def report(self):return dict(kind='actual_prepared_L0_settle_flow_and_current_registered_PUSH_support',
        actual_startup_steps=self.observed_steps,time_s=self.observed_time,support_ref=self.support_ref,
        original_startup_3N_is_not_PUSH12N=True,actual_current_PUSH12N_and_FIFO_checked=True,
        no_SupportedCapture_or_NAV_arrival_claimed=True,model_input=False)
