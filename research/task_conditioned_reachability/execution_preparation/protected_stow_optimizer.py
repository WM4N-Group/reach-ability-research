"""PHE H-only research hook for frozen successful WM-v9 protected stow.

NOT live-installed. Replaces no actor/QP/gate; can choose only an explicit arm
reference mode AFTER original unload/support/queue gates, BEFORE original full
path recheck. Same compact target, original .40/.80 timing, reference slew and
4s verification remain. This is an H-only ablation, not full upstream F7.
"""
import hashlib
import math
import time
import numpy as np

FROZEN_STALL_SHA256='ffbab28c81de7909fb8092f28a8917782e6918cdad53bcacbb0925e31589a28f'

ANCHOR='                for goal in ([self.compact_goal] if arrival_capture else self.waypoints):'
INSERT=('                if not arrival_capture:\n'
        '                    _reach_phe_prepare_path(self, start)\n')


def transform_stall_source(original):
    if hashlib.sha256(original.encode()).hexdigest()!=FROZEN_STALL_SHA256:
        raise ValueError('Not the frozen successful WM-v9 stow implementation')
    if original.count(ANCHOR)!=1 or 'class ProtectedStow:' not in original:
        raise ValueError('Exact frozen ProtectedStow caller required')
    needed=['self.segment_duration=max(.6,1.875*delta/.40,math.sqrt(5.78*delta/.80))',
            'if not queued[\'screen_pass\']:raise RuntimeError(\'fold_handoff_pending_queue_refused\')',
            "self.phase='STOW_VERIFY' if arrival_capture else 'PROTECTED_STOW'",
            'now-self.stable_since>=4.-1e-8']
    if not all(part in original for part in needed):raise ValueError('Original protected time/queue/verification contract mismatch')
    changed=original.replace(ANCHOR,INSERT+ANCHOR,1)
    if changed.replace(INSERT,'',1)!=original:raise ValueError('Not an exact additive reversible hook')
    return changed


def reference_seconds(start,waypoints):
    q=np.array(start,dtype=float,copy=True)
    if q.shape!=(6,) or not np.isfinite(q).all():raise ValueError('Finite six-joint issued reference required')
    values=[]
    for target in waypoints:
        target=np.asarray(target,dtype=float)
        if target.shape!=(6,) or not np.isfinite(target).all():raise ValueError('Six-joint path target required')
        d=float(np.max(np.abs(target-q)))
        values.append(max(.6,1.875*d/.40,math.sqrt(5.78*d/.80)))
        q=target
    if not values:raise ValueError('No empty path or skipped native verification')
    return values


def _snapshot(owner):
    sim=owner.s
    def raw(x):return np.asarray(x).tobytes()
    goal=sim.box_push_target
    if hasattr(goal,'numpy'):goal=goal.numpy()
    return (float(sim.data.time),raw(sim.data.qpos),raw(sim.data.qvel),
            tuple(raw(x) for x in sim.queue),raw(goal),
            raw(owner.reference),raw(owner.velocity),raw(owner.compact_goal),owner.phase,owner.index)


def choose_protected_path(owner,start,*,enabled,emit):
    """Use actual current native private guard, never planner/WM hidden inputs.

    Must be invoked at the qualified original capture boundary only. The hook
    does not itself prove the capture conditions; those caller tests are required
    before deployment. Output paths are nominal under original finite guard.
    """
    if type(enabled) is not bool:raise ValueError('Explicit study arm flag required')
    if not enabled:return dict(status='BASELINE_original_path_unchanged',changed=False)
    if owner.phase!='UNLOAD_CAPTURE' or owner.index!=0 or owner.native_arrival is not None:
        raise ValueError('Only original unloaded path boundary, not NAV arrival or active segment')
    t=time.perf_counter();before=_snapshot(owner)
    original=[np.array(q,dtype=float,copy=True) for q in owner.waypoints]
    goal=np.array(owner.compact_goal,dtype=float,copy=True)
    if not original or not np.array_equal(original[-1],goal):raise ValueError('Original immutable compact endpoint required')
    start=np.array(start,dtype=float,copy=True)
    if start.shape!=(6,) or not np.isfinite(start).all():raise ValueError('Actual finite arm q required')
    candidates=[('original',original),('direct_same_compact',[goal])]
    rows=[]
    for name,path in candidates:
        point=start.copy();reason=''
        for target in path:
            reason=owner.native.guard.segment(point,target)
            if reason:break
            point=target
        times=reference_seconds(owner.reference,path)
        rows.append(dict(mode=name,nominal_reference_s=sum(times),segment_reference_s=times,
                         native_finite_path_guard_pass=not bool(reason),reason=reason or None))
    # This hook adds no support certificate: original captured support/COM/QP
    # and current dynamic gates remain mandatory every real step.
    eligible=[(row,path) for row,(_,path) in zip(rows,candidates) if row['native_finite_path_guard_pass']]
    if eligible:
        best,path=min(eligible,key=lambda item:(item[0]['nominal_reference_s'],item[0]['mode']!='original'))
        chosen=best['mode']
    else:
        chosen='original';path=original
    if _snapshot(owner)!=before:raise RuntimeError('PHE query altered main state/FIFO/goal/issued references')
    changed=chosen!='original'
    result=dict(schema='reach-PHE-old-pass-H-only-decision-v1',status='CONDITIONAL_native_path_choice',
                chosen_mode=chosen,changed=changed,candidates=rows,
                original_endpoint_sha256=hashlib.sha256(goal.tobytes()).hexdigest(),
                actual_unload_boundary_time_s=float(owner.s.data.time),
                optimization_wall_s=time.perf_counter()-t,
                physical_safety_certificate=False,complete_F7_upstream_optimization=False,
                original_rate_accel_queue_QP_and_4s_verification_unchanged=True)
    # Recording must succeed BEFORE accepting a new path. Errors stop the run,
    # not silently drop planning evidence or restore/clear any live state.
    emit(result)
    if changed:owner.waypoints=[np.array(q,copy=True) for q in path]
    return result


def bind_owned_fork(module,*,owned_source_root,enabled,emit):
    """Bind hook only inside a fresh owned fork, before runtime construction.

    Does NOT patch any existing original/shared module. A fork builder must
    first write the exact transformed source and import it under its own study
    namespace/path; ordinary full source/protocol/zero admission still required.
    """
    from pathlib import Path
    from types import ModuleType
    if not isinstance(module,ModuleType) or type(enabled) is not bool:
        raise ValueError('Explicit fresh module and experiment arm required')
    root=Path(owned_source_root).resolve(strict=True);file=Path(module.__file__).resolve(strict=True)
    if not file.is_relative_to(root) or Path(module.__file__).is_symlink():
        raise ValueError('No installation into a shared/original source tree')
    if hasattr(module,'_reach_phe_prepare_path'):
        raise ValueError('One hook binder per fresh module, never overwrite live owner')
    text=file.read_text()
    if text.count(INSERT)!=1 or hashlib.sha256(text.replace(INSERT,'',1).encode()).hexdigest()!=FROZEN_STALL_SHA256:
        raise ValueError('Fresh source is not the exact registered one-hook fork')
    if '_reach_phe_prepare_path' not in module.ProtectedStow.update.__code__.co_names:
        raise ValueError('Actual caller does not consume the hook')
    module._reach_phe_prepare_path=lambda owner,start:choose_protected_path(owner,start,enabled=enabled,emit=emit)
    return dict(enabled=enabled,hook_bound_to_new_fork=True,
                whole_task_or_zero_admission=False,original_shared_source_modified=False)
