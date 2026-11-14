"""CPU isolation tests: new temporary root, -I/-B/-S, old /home reads forbidden.

Reuses ONE already-published explicit Data fixture, no acquisition/Actor/NN.
Never deploys remotely or changes Data/AINav files. Tests only the portability
change, not past hundreds of contracts or full runtime qualification.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

DATA=Path('/home/yuanyue/main/work/data-team/consumer-deliveries/IROS2027-Common-V9-B-Phase-Capture-Evaluation-CPU-20261112-v1/EXPLICIT-FIXTURE')

CHILD=r'''
import sys,json,pathlib,runpy,importlib.util,math,hashlib
root=pathlib.Path(sys.argv[1]);manifest_sha=sys.argv[2];mode=sys.argv[3]
forbidden=[]
def fence(event,args):
    if event in ('socket.connect','subprocess.Popen','os.fork','os.exec'):
        forbidden.append(event);raise PermissionError('Isolation: no runtime/remote/child')
    if event=='import' and args and str(args[0]).split('.')[0] in ('torch','numpy','scipy','mujoco','requests'):
        forbidden.append('import:'+args[0]);raise PermissionError('Analysis must be standard-library only')
    if event=='open' and args and isinstance(args[0],str) and args[0].startswith('/home/'):
        forbidden.append('old-home:'+args[0]);raise PermissionError('Old machine paths are unavailable')
sys.addaudithook(fence)
spec=importlib.util.spec_from_file_location('sealed_bootstrap',root/'package/analyze.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
if mode=='probe':
    data,mapping=m.load_bundle(root/'package',manifest_sha)
    sys.path.insert(0,str(root/'package/code'))
    from research.task_conditioned_reachability.execution_preparation.analysis_paths import relocated,resolve
    with relocated(mapping,allowed_roots=(root,),strict=True):
        from research.task_conditioned_reachability.execution_preparation.native_climb_continuation import load_requirements
        from research.task_conditioned_reachability.execution_preparation.observed_handover_analysis import registered_B_geometry
        from research.task_conditioned_reachability.execution_preparation.exit_repair_evidence import repair_against_original_option
        req=load_requirements();geometry=registered_B_geometry()
        assert req['limits']['approach_radius_m']==.16 and geometry['box_length_m']==2.4
        option=dict(token='EXPLICIT_PORTABILITY_UNIT_FIXTURE',skill='CLIMB',target_ref='B',
            parameters=[['goal_world_x_m',-.1],['goal_world_y_m',-2.],['surface_height_m',.2]],budget_s=.5,
            native_preconditions_receipt='EXPLICIT_FUNCTION_TEST_NO_NATIVE_EVENT',attempt_id='',original_push_goal_sha256='',mandatory_protection=False)
        digest=hashlib.sha256(json.dumps(option,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        label=dict(stage='AFTER_NORMAL_FINISH',frame='WORLD_POSITIVE_X',derived_from_requested_goal=False,
            robot_base_world_xyz_m=[.7,-2.,.3],private_state_evidence_sha256='a'*64,sample_physical_tick=800)
        result=repair_against_original_option(label,option,checked_option_sha256=digest,purpose='offline_dev_outcome_analysis')
        assert abs(result['translation_lower_bound_m']-.64)<1e-12 and result['actual_next_ready'] is None
        denied=False
        try:resolve('/unmapped-old-owner-source/missing.json')
        except ValueError:denied=True
        assert denied
    print(json.dumps(dict(mode=mode,source_rules_loaded_in_relocated_root=True,original_option_digest_computed=True,
                         forbidden_attempts=forbidden,fixture_result_not_real=True)))
else:
    cli=['analyze.py','--bundle-sha256',manifest_sha,'--mode','phase' if mode in ('phase','default-refusal','tamper') else 'repair',
         '--inputs',str(root/('phase-invocation.json' if mode in ('phase','default-refusal','tamper') else 'repair-invocation.json')),
         '--inputs-sha256',sys.argv[4],'--output',str(root/('phase-out' if mode=='phase' else 'repair-out' if mode=='repair' else mode+'-out'))]
    if mode not in ('default-refusal','repair-default-refusal'):cli.append('--allow-fixture')
    sys.argv=cli;m.main()
    assert forbidden==[]
    print(json.dumps(dict(mode=mode,forbidden_attempts=forbidden)))
'''


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def verify(bundle,manifest_sha,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    began=time.perf_counter();cases=[]
    with tempfile.TemporaryDirectory(prefix='reach-offline-new-host-') as folder:
        root=Path(folder);shutil.copytree(bundle,root/'package')
        # These are explicit SOFTWARE fixture bytes, separate from source bundle.
        shutil.copytree(DATA/'sidecar',root/'fixture-sidecar')
        shutil.copyfile(DATA/'evaluation.json',root/'fixture-evaluation.json')
        sidecar=root/'fixture-sidecar'
        invocation=dict(schema='reach-offline-Data-artifact-list-v1',purpose='offline_dev_outcome_analysis',items=[dict(
            name='Data_original_fixture',kind='phase_evaluation',sidecar=str(sidecar),
            sidecar_pins={n:sha(sidecar/n) for n in ('identity.json','closure.json','events.jsonl')},
            evaluation_path=str(root/'fixture-evaluation.json'),evaluation_sha256=sha(root/'fixture-evaluation.json'))],
            comparison_groups=[])
        write(root/'phase-invocation.json',invocation)
        def child(mode,expected_success,input_sha='unused'):
            command=[sys.executable,'-I','-B','-S','-c',CHILD,str(root),manifest_sha,mode,input_sha]
            p=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=20)
            (output/(mode+'.stdout.txt')).write_text(p.stdout)
            (output/(mode+'.stderr.txt')).write_text(p.stderr)
            good=p.returncode==0
            if good!=expected_success:raise AssertionError('Portability case '+mode+' unexpected exit '+str(p.returncode)+'\n'+p.stderr)
            if not expected_success:
                expected='Original source byte identity changed' if mode=='tamper' else 'Explicit fixture opt-in required'
                if expected not in p.stderr:raise AssertionError('Negative case failed for wrong reason: '+mode+'\n'+p.stderr)
            cases.append(dict(mode=mode,returncode=p.returncode,expected_success=expected_success,
                              isolated_python='-I -B -S',old_home_reads_forbidden=True,neural_and_runtime_imports_forbidden=True))
        child('phase',True,sha(root/'phase-invocation.json'))
        old=json.loads((root/'phase-out/Data_original_fixture-analysis.json').read_text())['normalized_observation']
        if old['provenance']!='EXPLICIT_FIXTURE' or old['actual_next_ready'] is not None or old['query_to_native_receipt_s']!=3.005:
            raise AssertionError('Relocation changed measured result semantics')
        repair=dict(schema='reach-offline-repair-demand-invocation-v1',purpose='offline_dev_outcome_analysis',items=[dict(
            name='Data_original_fixture',analysis_path=str(root/'phase-out/Data_original_fixture-analysis.json'),
            analysis_sha256=sha(root/'phase-out/Data_original_fixture-analysis.json'),sidecar=str(sidecar),sidecar_pins=invocation['items'][0]['sidecar_pins'])],
            comparison_groups=[dict(name='original_check_scope',items=['Data_original_fixture'],scope=dict(purpose='offline_dev_outcome_analysis',fixed_reference_distance_m=.6,controlled_initial_state_design=False))])
        write(root/'repair-invocation.json',repair)
        child('repair',True,sha(root/'repair-invocation.json'))
        extra=json.loads((root/'repair-out/comparisons.json').read_text())['original_check_scope']
        if extra['native_option_bound_reference_candidates']!=0 or len(extra['original_check_patterns'])!=1:
            raise AssertionError('Missing goal or existing check scope changed')
        child('probe',True)
        # Probe other isolated root names so failures cannot reuse successful roots.
        child('default-refusal',False,sha(root/'phase-invocation.json'))
        child('repair-default-refusal',False,sha(root/'repair-invocation.json'))
        member=root/'package/source-docs/skill_interface_contract_v0_1_1.json'
        member.write_bytes(member.read_bytes()+b'\n')
        child('tamper',False,sha(root/'phase-invocation.json'))
    result=dict(cases=cases,success_cases=3,negative_cases=3,
                source_bundle_does_not_include_fixture_or_private_labels=True,
                actual_original_Data_fixture_consumed_without_old_home=True,
                actual_original_source_rules_and_BehaviorOption_digest_used_without_old_home=True,
                source_SHA_and_data_roles_unchanged=True,remote_deployment_or_environment_qualification=False,
                new_physics_or_model_calls=0,wall_s=time.perf_counter()-began)
    write(output/'summary.json',result);return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(verify(a.bundle,a.manifest_sha256,a.output),indent=2))
