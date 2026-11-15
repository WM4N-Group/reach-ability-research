#!/usr/bin/env python3
"""Synthetic binding/trace/native interval regression: NO robot/actor/physics."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace as NS


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',required=True);ap.add_argument('--root',required=True)
    a=ap.parse_args();source=Path(a.source).resolve();root=Path(a.root).resolve();root.mkdir(parents=True,exist_ok=False)
    os.environ.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1');sys.path.insert(0,str(source))
    import numpy as np
    from mujoco_zyh.moving_push_exit import MovingPushExit
    from mujoco_zyh.stall_stow import unload_reference
    from ainav.native.unload_reference_binding import ReconciledUnloadBinding
    def command(position,ff):
        x=NS(position=np.r_[np.zeros(12),position],feedforward=np.r_[np.zeros(12),ff])
        x.array=lambda:np.stack((x.position,np.zeros(18),np.ones(18)*50,np.ones(18)*3,x.feedforward))
        return x
    brake=MovingPushExit.__new__(MovingPushExit)
    brake.hold_issued_arm=False;brake.stow=None;brake.unload_target=np.ones(6)*.2;brake.reference_start=np.zeros(6)
    brake.reference=np.zeros(6);brake.velocity=np.zeros(6);brake.pm=NS(KP=np.ones(18)*50,KD=np.ones(18)*3,EFFORT=np.ones(18)*20)
    brake.limits=np.asarray([[-1.,1.]]*6);brake.s=NS(data=NS(time=0.));brake.r=NS(last=command(np.zeros(6),np.zeros(6)))
    original=brake.command;binding=ReconciledUnloadBinding(brake)
    assert binding.command.__func__.__code__ is original.__func__.__code__
    assert original.__func__.__globals__['unload_reference'] is unload_reference
    assert binding.original_command.__func__ is MovingPushExit.command
    def proposed():
        return binding.select(brake.unload_target,brake.reference_start,brake.reference,brake.velocity,np.zeros(6),np.zeros(6),
            brake.pm.KP[12:],brake.pm.KD[12:],np.ones(6)*-2.,brake.pm.EFFORT[12:],brake.limits,brake.s.data.time,start_ff=np.zeros(6))
    pos,vel,ff,_=proposed();mismatch=command(pos+.01,ff)
    binding.after_actual_issue(mismatch,physical_tick=1,time_s=.005)
    assert binding.receipt()['actually_committed']==0
    actual=command(pos,ff);binding.after_actual_issue(actual,physical_tick=1,time_s=.005)
    binding.after_actual_issue(actual,physical_tick=2,time_s=.01)
    assert binding.receipt()['actually_committed']==1
    try:proposed()
    except RuntimeError as error:assert 'new actual native time' in str(error)
    else:raise AssertionError('Repeated same-time proposal accepted')
    brake.s.data.time=.005;brake.r.last=actual;brake.reference=pos;brake.velocity=vel
    proposed()  # deliberately never issued
    brake.unload_target[0]+=.1
    try:binding.assert_immutable()
    except RuntimeError:pass
    else:raise AssertionError('Fixed unload goal mutation accepted')
    brake.unload_target=binding.goal.copy();binding.assert_immutable()
    trace=binding.close(root)
    assert trace['proposals']==2 and trace['actually_committed']==1
    assert original.__func__.__globals__['unload_reference'] is unload_reference
    r=dict(schema='ainav-reconciled-unload-synthetic-binding-v1',regression_passed=True,
        source_manifest_sha256=hashlib.sha256((source/'ainav-source.json').read_bytes()).hexdigest(),
        synthetic_fixture_not_robot_or_sensor_test=True,original_code_object_and_inverse_preserved=True,
        original_module_global_unchanged=True,fixed_goal_mutation_denied=True,same_time_repeat_denied=True,
        unissued_and_mismatching_proposals_not_credited=True,first_actual_commit_not_double_counted=True,
        trace=trace,main_motor_steps=0,actor_forwards=0,mj_step_calls=0,Runtime_instances_constructed=0,API_calls=0)
    (root/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return 0


if __name__=='__main__':raise SystemExit(main())
