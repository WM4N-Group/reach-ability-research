"""Explicit per-owner reference/FF engineering candidate, not a new stop actor.

Original MovingPushExit.command code is retained with ONE private global binding.
The original module, safety/landing/stow methods and other owners are unchanged.
Private proposals count only after matching actual issuance; no fallback/retries.
"""
import hashlib
import inspect
from pathlib import Path
from types import MethodType
from .body_braking_reference import clone_with_globals
from .reconciled_unload import reconciled_unload_reference
from .stop_actor_trace import command_digest


class ReconciledUnloadBinding:
    def __init__(self,brake,*,max_proposals=2001):
        import numpy as np
        from mujoco_zyh.stall_stow import unload_reference
        if brake.hold_issued_arm or brake.stow is not None:
            raise ValueError('Explicit original unload owner before stow required')
        self.brake=brake;self.original_command=brake.command
        fn=self.original_command.__func__
        if fn.__globals__.get('unload_reference') is not unload_reference:
            raise ValueError('Original native unload command identity required')
        self.goal=brake.unload_target.copy();self.start=brake.reference_start.copy()
        self.kp=brake.pm.KP[12:].copy();self.kd=brake.pm.KD[12:].copy();self.effort=brake.pm.EFFORT[12:].copy();self.limits=brake.limits.copy()
        self.samples=[];self.max_proposals=max_proposals;self.closed=False;self.refusal=None
        self.original_function=fn;self.original_unload=unload_reference
        self.command=MethodType(clone_with_globals(fn,unload_reference=self.select),brake)
        self.source_sha256=hashlib.sha256(inspect.getsource(fn).encode()).hexdigest()
        self.assert_immutable()
    def assert_immutable(self):
        import numpy as np
        b=self.brake
        values=((b.unload_target,self.goal),(b.reference_start,self.start),(b.pm.KP[12:],self.kp),
            (b.pm.KD[12:],self.kd),(b.pm.EFFORT[12:],self.effort),(b.limits,self.limits))
        if b.hold_issued_arm or any(not np.array_equal(a,c) for a,c in values):
            raise RuntimeError('Declared unload target/start/gains/limits changed')
        if self.original_function.__globals__['unload_reference'] is not self.original_unload:
            raise RuntimeError('Original global unload function changed')
    def select(self,goal,start,reference,velocity,q,dq,kp,kd,gravity,effort,limits,age,dt=.005,start_ff=None):
        import numpy as np
        self.assert_immutable();b=self.brake;now=float(b.s.data.time)
        if self.closed or len(self.samples)>=self.max_proposals:
            raise RuntimeError('Private reference/FF trace budget exceeded')
        if self.samples and now<=self.samples[-1]['proposal_time_s']:
            raise RuntimeError('Reference/FF proposal requires a new actual native time')
        if dt!=.005 or not all(np.array_equal(a,c) for a,c in ((goal,self.goal),(start,self.start),(kp,self.kp),(kd,self.kd),(effort,self.effort),(limits,self.limits),(reference,b.reference),(velocity,b.velocity))):
            raise RuntimeError('Original explicit unload arguments changed')
        row=dict(proposal_time_s=now,reference_before=np.array(reference,copy=True),velocity_before=np.array(velocity,copy=True),
            q=np.array(q,copy=True),dq=np.array(dq,copy=True),gravity=np.array(gravity,copy=True),previous_ff=b.r.last.feedforward[12:].copy(),
            input_actual_command_sha256=command_digest(b.r.last.array()))
        try:
            position,speed,ff,receipts=reconciled_unload_reference(self.goal,reference,velocity,q,dq,kp,kd,gravity,row['previous_ff'],effort,limits)
        except (RuntimeError,ValueError) as error:
            self.refusal=dict(error=type(error).__name__+': '+str(error),**{k:v.tolist() if hasattr(v,'tolist') else v for k,v in row.items()})
            raise
        row.update(selected_reference=position.copy(),selected_velocity=speed.copy(),selected_ff=ff.copy(),
            first_actual_issue_tick=-1,first_actual_issue_time_s=-1.,issued_command_sha256='')
        self.samples.append(row);b.last_arm_receipts=receipts
        return position,speed,ff,receipts
    def after_actual_issue(self,command,*,physical_tick,time_s):
        import numpy as np
        if not self.samples:return
        row=self.samples[-1]
        if row['first_actual_issue_tick']>=0:return
        if not (0<time_s-row['proposal_time_s']<=.005+1e-8):return
        if not np.array_equal(command.position[12:],row['selected_reference']) or not np.array_equal(command.feedforward[12:],row['selected_ff']):return
        row.update(first_actual_issue_tick=int(physical_tick),first_actual_issue_time_s=float(time_s),issued_command_sha256=command_digest(command.array()))
    def receipt(self):
        return dict(schema='ainav-private-reconciled-unload-binding-v1',
            original_command_code_object_reused=self.command.__func__.__code__ is self.original_function.__code__,
            original_command_source_sha256=self.source_sha256,original_module_global_unchanged=self.original_function.__globals__['unload_reference'] is self.original_unload,
            fixed_goal=self.goal.tolist(),fixed_start=self.start.tolist(),kp=self.kp.tolist(),kd=self.kd.tolist(),effort=self.effort.tolist(),limits=self.limits.tolist(),
            proposals=len(self.samples),actually_committed=sum(r['first_actual_issue_tick']>=0 for r in self.samples),max_proposals=self.max_proposals,
            original_actor_landing_stow_or_safety_gates_replaced=False,private_only=True,model_input_allowed=False,task_success_inferred=False,refusal=self.refusal)
    def close(self,root):
        import numpy as np
        if self.closed:raise RuntimeError('Reference/FF trace closes once')
        self.closed=True;r=self.receipt()
        if self.samples:
            path=Path(root)/'private-reconciled-unload-trace-v1.npz'
            with path.open('xb') as f:np.savez_compressed(f,**{k:np.asarray([row[k] for row in self.samples]) for k in self.samples[0]})
            r.update(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
        return r
