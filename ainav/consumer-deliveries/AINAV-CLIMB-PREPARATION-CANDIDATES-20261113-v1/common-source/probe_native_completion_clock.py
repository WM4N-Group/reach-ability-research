#!/usr/bin/env python3
"""A800 source-level native settled clock regression using SYNTHETIC fixtures.

Runs the unmodified, AST-extracted original PushSettled class with real CPU
Torch and the real NativeOptionSession callback schedule, but a stub machine
and explicitly synthetic stable/contact predicates. No Runtime/MuJoCo world,
physics, actor, calibration, task state or API is constructed/advanced.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace as NS


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('source','bundle','root'):ap.add_argument('--'+key,required=True)
    a=ap.parse_args();source,bundle,root=(Path(p).resolve() for p in (a.source,a.bundle,a.root))
    root.mkdir(parents=True,exist_ok=False)
    os.environ.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
    sys.path.insert(0,str(source));sys.path.insert(0,str(bundle/'switch'))
    import numpy as np
    import torch
    from plugins import Plugin
    from mujoco_zyh.native_behavior_executor import NativeOptionSession
    from mujoco_zyh.source_bundle import verify_bundle
    from ainav.native.completion_clock import ClockedNativeSettled
    manifest=json.loads((source/'ainav-source.json').read_text())
    if not all(sha(source/k)==v for k,v in manifest['files'].items()):raise ValueError('Frozen source changed')
    assets=verify_bundle(bundle);compat=Plugin('push',['compat'])['compat']
    path=bundle/'push/controller/box_push.py';raw=path.read_text();tree=ast.parse(raw)
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PushSettled')
    class_source=ast.get_source_segment(raw,node)
    yes=lambda *a,**k:torch.ones(1,dtype=torch.bool)
    no=lambda *a,**k:torch.zeros(1,dtype=torch.bool)
    ns=dict(__name__='ainav_original_settled_synthetic_fixture',torch=torch,
        ManagerTermBase=compat.ManagerTermBase,SceneEntityCfg=compat.SceneEntityCfg,
        hand_contact=yes,push_target=lambda env:torch.zeros((1,3)),box_tipped=no,forbidden_box_contact=no)
    # Compile the ORIGINAL AST node with ORIGINAL line numbers and file name.
    # No rewriting of the class, threshold or buffer reset semantics.
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
    Term=ns['PushSettled']
    def env():
        return NS(num_envs=1,device='cpu',step_dt=.02,data=NS(time=0.,qpos=np.zeros(7),qvel=np.zeros(6)),
            scene={'box':NS(data=NS(root_pos_w=torch.zeros((1,3)),root_lin_vel_w=torch.zeros((1,3))))})
    stationary=[]
    for clocked in (False,True):
        e=env();native=Term(None,e);reader=ClockedNativeSettled(native,e) if clocked else native
        values=[bool(reader(e)[0]) for _ in range(25)]
        stationary.append(dict(clocked=clocked,synthetic_elapsed_time_s=e.data.time,reads=25,
            native_duration_s=float(native.duration[0]),result=values[-1],
            native_clock_report=reader.report() if clocked else None))
    profiles=[]
    for clocked in (False,True):
        e=env();native=Term(None,e);reader=ClockedNativeSettled(native,e) if clocked else native
        calls=0;first_true=None;records=[]
        def read():
            nonlocal calls,first_true
            calls+=1;value=reader(e)
            if bool(value[0]) and first_true is None:first_true=e.data.time
        runtime=NS(sim=NS(data=e.data,queue=[]),last=NS(position=np.zeros(18)),step_count=0)
        class FixtureMachine:
            tasks=[dict(skill='push')]
            def __init__(self):self.r=runtime
            def enter(self):pass
            def update(self):read()  # synthetic flags at original Machine's update site
            def after_step(self):pass
        session=NativeOptionSession(runtime,FixtureMachine(),check_guards=read)
        session.enter()
        for tick in range(111):
            e.data.time=tick*.005;runtime.step_count=tick
            if tick and tick%4==0:session.update()
            if tick:session.after_step()
            if tick%4==0:records.append(dict(time_s=e.data.time,native_duration_s=float(native.duration[0])))
        profiles.append(dict(clocked=clocked,first_true_time_s=first_true,caller_reads=calls,
            synthetic_elapsed_time_s=e.data.time,native_duration_s=float(native.duration[0]),
            native_clock_report=reader.report() if clocked else None,checkpoints=records))
    passed=(stationary[0]['result'] and not stationary[1]['result']
        and profiles[0]['first_true_time_s']<.5 and profiles[1]['first_true_time_s']>=.5-1e-9
        and profiles[1]['native_duration_s']<=profiles[1]['synthetic_elapsed_time_s']+2e-6)
    result=dict(schema='ainav-native-settled-clock-synthetic-source-regression-v1',regression_passed=passed,
        source_manifest_sha256=sha(source/'ainav-source.json'),asset_verification=assets,
        original_native_source_sha256=sha(path),original_native_class_ast_source_sha256=hashlib.sha256(class_source.encode()).hexdigest(),
        synthetic_predicates_explicitly_stubbed=['hand_contact=true','box_tipped=false','forbidden_box_contact=false','zero distance and velocity'],
        actual_original_native_class_unmodified=True,actual_native_session_class_reused=True,
        stationary_same_timestamp=stationary,actual_session_callback_synthetic_clock_profiles=profiles,
        synthetic_fixture_not_robot_test=True,actual_task_success=False,
        Runtime_instances_constructed=0,MuJoCo_worlds_constructed=0,main_motor_steps=0,
        actor_forwards=0,auxiliary_calibration_worlds=0,model_API_calls=0,live_task_state_writes=0,
        automatic_retry=False,probe_source_sha256=sha(__file__))
    with (root/'report.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='actual_session_callback_synthetic_clock_profiles'}))
    print(json.dumps([dict(clocked=p['clocked'],first_true_time_s=p['first_true_time_s'],reads=p['caller_reads'],duration=p['native_duration_s']) for p in profiles]))
    return 0 if passed else 2


if __name__=='__main__':raise SystemExit(main())
