#!/usr/bin/env python3
"""Original native velocity BYTECODE on explicit synthetic CPU Torch inputs.

Contact/front-face predicates are stubbed for controlled math, not robot data.
There is no Runtime/MuJoCo world, actor, task step, calibration or API call.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType,SimpleNamespace as NS,MethodType,FunctionType


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class SyntheticScene(dict):pass


class SyntheticView:
    def observation(self):return box_push.push_velocity_commands(self,None)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('source','bundle','root'):ap.add_argument('--'+k,required=True)
    a=ap.parse_args();source,bundle,root=(Path(p).resolve() for p in (a.source,a.bundle,a.root))
    root.mkdir(parents=True,exist_ok=False)
    os.environ.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1');sys.path.insert(0,str(source));sys.path.insert(0,str(bundle/'switch'))
    import torch
    from plugins import Plugin
    from mujoco_zyh.source_bundle import verify_bundle
    from ainav.native.body_braking_reference import BodyBrakingBinding,clone_with_globals
    assets=verify_bundle(bundle);manifest=json.loads((source/'ainav-source.json').read_text())
    if any(sha(source/k)!=h for k,h in manifest['files'].items()):raise ValueError('Frozen source changed')
    bridge=Plugin('push',['bridge'])['bridge'];native=bridge.box_push
    def make(feedback,goal_gain):
        fixture=ModuleType('explicit_synthetic_native_velocity')
        fixture.__dict__.update(native.__dict__)
        fixture.front_face=lambda env:torch.tensor([[.6,0.,0.]])
        fixture.hand_contact=lambda *a,**k:torch.ones(1,dtype=torch.bool)
        fixture.forbidden_box_contact=lambda *a,**k:torch.zeros(1,dtype=torch.bool)
        for n in ('nominal_push_velocity_commands','push_control_at_goal'):
            f=getattr(native,n);fixture.__dict__[n]=FunctionType(f.__code__,fixture.__dict__,f.__name__,f.__defaults__,f.__closure__)
        f=native.push_velocity_commands
        fixture.push_velocity_commands=FunctionType(f.__code__,fixture.__dict__,f.__name__,f.__defaults__,f.__closure__)
        v=SyntheticView();v.history=None;v.data=NS(time=0.)
        v.scene=SyntheticScene({'box':NS(data=NS(root_pos_w=torch.tensor([[9.15,-2.,.5]]),root_quat_w=torch.tensor([[1.,0.,0.,0.]]),root_lin_vel_w=torch.zeros((1,3)))),
            'robot':NS(data=NS(root_quat_w=torch.tensor([[1.,0.,0.,0.]]),root_pos_w=torch.zeros((1,3)),root_lin_vel_w=torch.tensor([[.1,0.,0.]])))})
        v.scene.sensors={'box_contact_hand':NS(data=NS(contact_pos_w=torch.tensor([[[[9.15,-2.,.5]]]])))}
        v.box_push_target=torch.tensor([[9.31,-2.,.5]])
        v.box_push_approach_face_ready=torch.ones(1,dtype=torch.bool);v.box_push_safe_approach_complete=torch.ones(1,dtype=torch.bool)
        v.cfg=NS(push_stop_distance=.11,push_forward_command_gain=2.,push_preapproach_base_gap=.34,push_full_body_preapproach=False,
            push_body_first=False,push_velocity_feedback_gain=feedback,push_goal_brake_gain=goal_gain,push_contact_gap_slowdown_start=0.)
        scope=dict(SyntheticView.observation.__globals__,box_push=fixture)
        obs=FunctionType(SyntheticView.observation.__code__,scope,'observation',SyntheticView.observation.__defaults__)
        v.observation=MethodType(obs,v)
        return v,fixture
    records=[]
    for feedback,goal_gain in ((0.,0.),(1.,0.),(0.,1.),(1.,1.)):
        v,fixture=make(feedback,goal_gain);goal_before=v.box_push_target.clone()
        original=v.observation().clone();functions={n:getattr(fixture,n) for n in ('nominal_push_velocity_commands','push_velocity_commands','push_control_at_goal')}
        binding=BodyBrakingBinding(v,fixture,body_goal_xy_m=(9.2,-2.));modified=v.observation().clone()
        assert float(original[0,0])>0 and float(modified[0,0])<=0
        assert not bool(fixture.push_control_at_goal(v)[0]) and bool(binding.at_goal(v)[0])
        assert torch.equal(v.box_push_target,goal_before)
        assert all(getattr(fixture,n) is f for n,f in functions.items())
        assert all(getattr(fixture,n).__code__ is getattr(native,n).__code__ for n in functions)
        inverse_view,inverse_fixture=make(feedback,goal_gain);baseline=inverse_view.observation().clone()
        inverse=BodyBrakingBinding(inverse_view,inverse_fixture,body_goal_xy_m=(float(inverse_view.box_push_target[0,0]),-2.))
        assert torch.equal(inverse_view.observation(),baseline)
        records.append(dict(fixture_feedback_gain=feedback,fixture_goal_brake_gain=goal_gain,original_requested_velocity=original.tolist(),
            body_reference_requested_velocity=modified.tolist(),inverse_same_reference_bit_identical=True,original_arm_goal_unchanged=True,
            original_global_functions_unmodified=True,original_native_function_code_objects_reused=True,receipt=binding.receipt()))
    result=dict(schema='ainav-original-body-reference-velocity-synthetic-regression-v1',regression_passed=True,
        source_manifest_sha256=sha(source/'ainav-source.json'),asset_verification=assets,records=records,
        synthetic_predicates_explicitly_stubbed=['fixed front face','legal contact true','forbidden contact false','synthetic contact sensor point'],
        synthetic_fixture_not_robot_or_sensor_test=True,Runtime_instances_constructed=0,MuJoCo_worlds_constructed=0,
        main_motor_steps=0,actor_forwards=0,auxiliary_calibration_worlds=0,model_API_calls=0,task_success=False,
        probe_source_sha256=sha(__file__))
    with (root/'report.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
