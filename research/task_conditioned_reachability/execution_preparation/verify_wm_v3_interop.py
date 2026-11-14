"""Read-only consumption of WM-published FAKE outputs and default-off prototype.

Never call its runner, loader/filter/forward, original runtime or dispatcher.
Original consumer functions are exercised only on an explicit nominal-view
software fixture. No private actual pose is read or returned to a planner.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from .recorded_v9_diagnostics import load_recorded_owner_sources
from .native_climb_continuation import load_requirements
from .model_sufficiency import rows_from_raw_batch,analyze

SCRIPTS=Path('/home/yuanyue/re-nav/GO2-PIPER/scripts/piper_world_model')
ARTIFACT=Path('/home/yuanyue/re-nav/artifacts/go2-piper-world-model/WM-offline-producer-standoff-20261112-v1')
INTEROP_SHA='9abc4b494f30cb1bb1deb3bc349f908e7b56735e83e300ef7bf040a4d40c2d22'
STANDOFF_SHA='a0172499a796b97ddbd9559884caa0bf8abe36d7bab4523cae733d2a0858fafb'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def module(name,path,expected):
    if sha(path)!=expected:raise ValueError('New owner source changed; explicit adaptation required')
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m


def verify(own_evidence):
    own_evidence=Path(own_evidence);public,original_rows=load_recorded_owner_sources()
    paths=[SCRIPTS/'skill_effect_offline_v3/reach_interop.py',SCRIPTS/'skill_effect_offline_v3/standoff.py',
           ARTIFACT/'fake-cli-published/result.json',ARTIFACT/'fake-cli-published/all-candidate-outputs.json',
           Path('/home/yuanyue/re-nav/artifacts/go2-piper-world-model/WM-day1-stage-producer-20261112-v1/candidate-input-pack.json')]
    before={str(p):sha(p) for p in paths};old_path=sys.path[:]
    try:
        sys.path.insert(0,str(SCRIPTS))
        interop=module('reach_consume_wm_v3_interop',paths[0],INTEROP_SHA)
        profile_module=module('reach_consume_wm_v3_standoff',paths[1],STANDOFF_SHA)
        result=json.loads(paths[2].read_text());envelope=json.loads(paths[3].read_text());pack=json.loads(paths[4].read_text())
        if result['is_real_inference'] is not False:raise ValueError('This verification is limited to the already-published fake run')
        default_rejected=False
        try:interop.raw_batch_payload(result,envelope,dict(pack=pack))
        except ValueError:default_rejected=True
        if not default_rejected:raise ValueError('Fake must be rejected from real branch by default')
        raw=interop.raw_batch_payload(result,envelope,dict(pack=pack),allow_fixture=True)
        normalized=rows_from_raw_batch(public,original_rows,raw,allow_synthetic=True)
        sufficiency=analyze(public,normalized,load_requirements(),allow_synthetic=True)
        if not sufficiency['levels']['model_response_comparison']['all_three_available'] or sufficiency['levels']['executable_selection']['sufficient']:
            raise ValueError('Response vs executable levels lost their boundary')
        # Bind existing source consumers to nominal PUBLIC-prior fixture values.
        # No actual runtime state, private poses, policy or FIFO is constructed.
        import numpy as np
        manifest=json.loads(Path('/home/yuanyue/re-nav/GO2-PIPER/docs/skill_executor_manifest_v0.json').read_text())
        entry_ref=manifest['frozen_source_excerpts']['mujoco_zyh/native_push_entry_reference.py']
        compiler_ref=manifest['frozen_source_excerpts']['mujoco_zyh/native_behavior_executor.py']
        original=module('reach_consume_original_relative_entry',Path(entry_ref['path']),entry_ref['sha256'])
        binding=json.loads((own_evidence/'task-binding.json').read_text());domain_source=own_evidence/'task-binding.json'
        proposed=profile_module.ResearchProfile('research-HYPOTHETICAL-GEOMETRY-ONLY',(.545,.58,.615),str(domain_source),sha(domain_source))
        view=SimpleNamespace(cfg=SimpleNamespace(box_size=[2.4,1.4,.2]),box_id=0,
                             data=SimpleNamespace(xpos=np.array([[1.7,-2.,.1]]),xmat=np.array([np.eye(3).ravel()])))
        rows=[]
        for s in proposed.allowed_values_m:
            request=profile_module.build_request(public_front_m=.5,lane_y_m=-2.,push_distance_m=.6,standoff_m=s,
                        profile=None if s==.58 else proposed,enable_research=s!=.58)
            config=profile_module.select_config(request)
            fn=profile_module.bind_consumer_candidate(original.relative_push_entry,source_ref=entry_ref,request=request,config=config)
            output=fn(view,dict(request['intent']['parameters']))
            profile_module.check_reference_result(request,config,output)
            # Height is an unmistakable SOFTWARE SENTINEL, not a physical value.
            assignment=profile_module.entry_target_fixture(request,config,output,entry_source_ref=compiler_ref,original_reference_height_m=1.234567)
            expected_x=binding['hypothetical_base_reference_world_x_m'][str(s)]
            if abs(assignment['private_base_goal_xyz_m'][0]-expected_x)>1e-12:raise ValueError('WM consumer reference disagrees with geometry parameter consumption')
            applicable=profile_module.old_model_applicability(request)
            if s!=.58 and applicable['status']!='UNKNOWN_OLD_MODEL_HAS_NO_STANDOFF_CHANNEL':raise ValueError('Research profile reused unsupported old model')
            rows.append(dict(standoff_m=s,software_nominal_reference_x_m=assignment['private_base_goal_xyz_m'][0],
                             matches_local_geometry_reference=True,source_code_object_preserved=fn.__code__ is original.relative_push_entry.__code__,
                             default_original_function_identity=(fn is original.relative_push_entry) if s==.58 else None,
                             old_model_applicability=applicable['status'],native_dispatch=False,fixture_not_dynamic_receipt=True))
        if original.CALIBRATED_FRONT_STANDOFF_M!=.58:raise ValueError('Original namespace mutated')
        denied=False
        try:profile_module.native_dispatch()
        except PermissionError:denied=True
        if not denied:raise ValueError('Even prototype dispatch must remain disabled')
    finally:
        sys.path[:]=old_path
    after={str(p):sha(p) for p in paths}
    if before!=after:raise ValueError('Owner artifacts changed during read-only consumption')
    return dict(schema='reach-WM-v3-readonly-integration-v1',owner_source_and_artifact_sha256=before,
                original_owner_files_unchanged=True,
                already_published_fake_output_consumed=True,new_fake_or_real_forward_executed=False,
                fake_default_rejected=default_rejected,explicit_synthetic_sufficiency=sufficiency,
                standoff_consumer_map=rows,original_constant_unchanged=True,prototype_dispatch_rejected=True,
                stage='ACTUAL_SOFTWARE_CROSS_MODULE_CALLS_ON_EXPLICIT_FIXTURES_NOT_NATIVE_RUNTIME',
                real_checkpoint_loaded=False,real_runtime_qualified=False,physical_dispatch=False)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    x=verify(a.root)
    with (a.root/'WM-v3-actual-software-interop.json').open('x') as f:json.dump(x,f,indent=2);f.write('\n')
    print(json.dumps(dict(fake_three_comparable=x['explicit_synthetic_sufficiency']['levels']['model_response_comparison']['all_three_available'],
                         fake_success_time_comparable=x['explicit_synthetic_sufficiency']['levels']['successful_time_comparison']['all_three_comparable'],
                         executable=x['explicit_synthetic_sufficiency']['levels']['executable_selection']['sufficient'],standoff_map=x['standoff_consumer_map']),indent=2))
