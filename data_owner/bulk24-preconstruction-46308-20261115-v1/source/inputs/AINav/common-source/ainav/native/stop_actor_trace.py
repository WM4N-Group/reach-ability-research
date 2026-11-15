"""Bounded PRIVATE original-stop actor audit data, never model/task authority.

A proposal is committed only when its original scaled leg targets were actually
issued. Capturing inputs/outputs does not modify observations or controller
history. Large numeric data stays in the experiment root, not source control.
"""
import hashlib
import json
import math
from pathlib import Path


def command_digest(value):
    return hashlib.sha256(str((value.shape,str(value.dtype))).encode()+value.tobytes()).hexdigest()


def require_original_arm_ff_slew(previous,proposed,effort):
    if not (len(previous)==len(proposed)==len(effort)==6):raise ValueError('Six actual arm FF/effort entries required')
    for j,(a,b,e) in enumerate(zip(previous,proposed,effort)):
        if not all(math.isfinite(float(x)) for x in (a,b,e)) or e<=0:raise ValueError('Finite actual FF and positive original effort required')
        if abs(float(b)-float(a))>.05*float(e)+1e-10:raise RuntimeError('original_arm_FF_slew_refused:'+str(j))


def run_after_step_with_audit(native_after,audit_after):
    """Audit an actually issued step without masking its primary native failure."""
    primary=None
    try:
        native_after()
    except BaseException as error:
        primary=error
        raise
    finally:
        try:
            audit_after()
        except BaseException as diagnostic:
            if primary is None:
                raise
            if hasattr(primary,'add_note'):
                primary.add_note('Post-issue diagnostic also failed: '+type(diagnostic).__name__+': '+str(diagnostic))


class StopActorTrace:
    def __init__(self,root,*,max_proposals=1000,max_bytes=8*1024*1024):
        self.root=Path(root);self.max_proposals=max_proposals;self.max_bytes=max_bytes
        self.samples=[];self.closed=False
    def propose(self,*,time_s,observation,raw_leg,scale,slots,reference):
        import numpy as np
        if self.closed or len(self.samples)>=self.max_proposals:raise RuntimeError('Private original-stop trace budget exceeded')
        obs=np.asarray(observation).copy();raw=np.asarray(raw_leg).copy()
        if obs.shape!=(226,) or raw.shape!=(12,) or not np.isfinite(obs).all() or not np.isfinite(raw).all():raise ValueError('Actual native stop input226/output12 required')
        if not 0<=float(scale)<=1 or sorted(int(x) for x in slots)!=list(range(12)):raise ValueError('Original actual stop release/mapping required')
        action=np.zeros(18);action[slots]=raw*scale
        targets=(reference+.25*np.clip(action,-10.,10.))[:12]
        self.samples.append(dict(proposal_time_s=float(time_s),observation=obs,raw_leg=raw,
            release_scale=float(scale),expected_leg_targets=targets.copy(),
            first_actual_issue_time_s=-1.,first_actual_issue_tick=-1,issued_command_sha256=''))
    def actual_issue(self,command,*,physical_tick,time_s):
        import numpy as np
        if not self.samples:return
        s=self.samples[-1]
        if s['first_actual_issue_tick']>=0 or time_s<=s['proposal_time_s']:return
        if not np.array_equal(command.position[:12],s['expected_leg_targets']):return
        s.update(first_actual_issue_time_s=float(time_s),first_actual_issue_tick=int(physical_tick),issued_command_sha256=command_digest(command.array()))
    def close(self):
        import numpy as np
        if self.closed:raise RuntimeError('Trace closes only once')
        self.closed=True
        summary=dict(schema='ainav-private-original-stop-policy-trace-v1',proposals=len(self.samples),
            actually_committed=sum(s['first_actual_issue_tick']>=0 for s in self.samples),
            private_only=True,model_input_allowed=False,task_success_not_inferred=True,
            actual_actor_weights_or_observation_or_history_modified=False,
            max_proposals=self.max_proposals,max_bytes=self.max_bytes)
        if self.samples:
            path=self.root/'private-stop-actor-trace-v1.npz'
            if path.exists():raise FileExistsError('Never overwrite original trace')
            arrays={k:np.asarray([s[k] for s in self.samples]) for k in self.samples[0]}
            with path.open('xb') as f:np.savez_compressed(f,**arrays)
            size=path.stat().st_size
            if size>self.max_bytes:raise RuntimeError('Private original-stop compressed byte budget exceeded')
            summary.update(path=path.name,bytes=size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        return summary
