#!/usr/bin/env python3
"""Original stop method + reverse native blend on SYNTHETIC inputs, not robot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace as NS


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('source','bundle','root'):ap.add_argument('--'+k,required=True)
    a=ap.parse_args();source,bundle,root=(Path(p).resolve() for p in (a.source,a.bundle,a.root));root.mkdir(parents=True,exist_ok=False)
    os.environ.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1');sys.path[:0]=[str(source),str(bundle/'switch')]
    import numpy as np
    import torch
    from plugins import Plugin
    from mujoco_zyh.native_push_stop import NativePushLegStop
    from ainav.native.leg_release_brake import NativeLegReleaseBrake
    plugin=Plugin('push',['model','bridge','timing']);pm=plugin['model'];raw=np.linspace(-.6,.6,12)
    stop=NativePushLegStop.__new__(NativePushLegStop);shape=(3,3,18,18,18,3,7)
    stop.history=[np.zeros((3,n)) for n in shape];stop.ee=np.asarray([0.,0.,0.,1.,0.,0.,0.]);stop.slots=np.arange(12);stop.scale=.8
    stop.last_policy_time=-np.inf;stop.forwards=0;stop.targets=pm.REFERENCE[:12].copy();stop.pm=pm
    robot=NS(data=NS(root_ang_vel_b=torch.zeros((1,3)),projected_gravity_b=torch.tensor([[0.,0.,-1.]])))
    p=NS(data=NS(time=0.,qpos=pm.REFERENCE.copy(),qvel=np.zeros(18)),qids=np.arange(18),dids=np.arange(18),robot=robot,
        cfg=NS(push_leg_release_ramp_s=plugin['timing'].DEFAULT_APPROACH.leg_release_seconds),box_push_pose_override_active=torch.zeros(1,dtype=torch.bool),hand_cfg=NS())
    box=NS(box_observation=lambda s:torch.zeros((1,14)),hand_contact=lambda s,c:torch.zeros(1,dtype=torch.bool))
    stop.s=p;stop.r=NS(push={'bridge':NS(box_push=box)},push_actors=[object()],device='cpu',last=NS(position=pm.REFERENCE.copy()))
    calls=[];stop.infer=lambda *args:(calls.append(1) or raw.copy())
    ready=[False];events=[];blend=plugin['bridge'].PushArmIK.apply.__globals__['contact_action_blend']
    binding=NativeLegReleaseBrake(stop,native_blend=blend,ramp_s=p.cfg.push_leg_release_ramp_s,native_confirmation=lambda:ready[0],journal=events.append)
    try:binding.confirm()
    except RuntimeError:pass
    else:raise AssertionError('Fake confirmation accepted')
    original_history=stop.history
    target=stop.command_legs();assert np.allclose(target,pm.REFERENCE[:12]+.25*.8*raw)
    stop.r.last.position[:12]=target
    ready[0]=True;assert binding.confirm();assert not binding.confirm();confirmed=binding.confirmed_at
    records=[]
    for i in range(1,41):
        p.data.time=i*.02;before=stop.history
        targets=stop.command_legs();expected=.8*max(0.,1.-p.data.time/p.cfg.push_leg_release_ramp_s)
        assert abs(stop.scale-expected)<1e-12
        assert np.allclose(targets,pm.REFERENCE[:12]+.25*expected*raw)
        assert np.allclose(stop.history[4][-1],(stop.r.last.position-pm.REFERENCE)/.25)
        assert np.array_equal(stop.history[0][:-1],before[0][1:])
        stop.r.last.position[:12]=targets;records.append(dict(time_s=p.data.time,scale=stop.scale))
    assert binding.confirmed_at==confirmed and len(events)==1 and stop.forwards==len(calls)==41
    assert stop.scale==0. and np.array_equal(targets,pm.REFERENCE[:12]);binding.assert_immutable()
    report=dict(schema='ainav-reverse-leg-release-native-synthetic-v1',source_manifest_sha256=sha(source/'ainav-source.json'),regression_passed=True,
        synthetic_fixture_not_robot_or_sensor_test=True,original_stop_method_used=True,original_native_blend_used=True,
        false_confirmation_denied=True,first_confirmation_not_reset=True,actual_history_shift_and_previous_issued_action_retained=True,
        actor_weights_loaded_or_executed=False,synthetic_infer_calls=len(calls),actual_actor_forwards=0,actual_task_steps=0,mj_step_calls=0,Runtime_instances_constructed=0,
        binding=binding.receipt(),records=records)
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return 0


if __name__=='__main__':raise SystemExit(main())
