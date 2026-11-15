#!/usr/bin/env python3
"""Read-only actual prefix equality and native consumption, NOT pair outcomes.

Run on46308 against the exact frozen Data pair. Only closed command chunks and
closed first-query files are read. The live B journal is validated as a complete
append-only PREFIX, never treated as a terminal journal/result. No source/world,
Actor, renderer, model fit, private pose or counterfactual rollout is created.
"""
import argparse,copy,datetime as dt,hashlib,io,json,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('protocol','expected-protocol-sha','workers-root','source-root','output'):p.add_argument('--'+n,required=True)
a=p.parse_args()
blocked=[]
def fence(event,args):
    if event=='import'and str(args[0]).split('.')[0]in('torch','mujoco','onnxruntime'):
        blocked.append(str(args[0]));raise RuntimeError('Read-only arrays/contract audit; no native/Actor')
    if event in('subprocess.Popen','socket.connect','socket.bind','socket.getaddrinfo'):
        blocked.append(event);raise RuntimeError('No child/network')
sys.addaudithook(fence)
import numpy as np
sys.path.insert(0,str(Path(a.source_root).resolve()))
from ainav.contracts import sha as canonical_sha
sha=lambda raw:hashlib.sha256(raw).hexdigest()
protocol_bytes=Path(a.protocol).read_bytes();assert sha(protocol_bytes)==a.expected_protocol_sha
protocol=json.loads(protocol_bytes)
assert protocol['schema']=='Data-T-COMPLEX-first-native-DEV-source-method-pair-v1'
assert protocol['arms']['A']['method']=='greedy'and protocol['arms']['B']['method']=='multistep'
roots={arm:Path(a.workers_root)/r['scope_id']/'main'for arm,r in protocol['arms'].items()}
pins={};arrays={};observations={};events={};prefixes={}
def read(path):
    raw=path.read_bytes();pins[str(path)]=sha(raw);return raw
a_result_raw=read(roots['A']/'result.json');a_result=json.loads(a_result_raw)
a_ledger=json.loads(read(roots['A'].parent/'accounting/ledger.json'))
a_main_rows=[row for row in a_ledger['rows']if row['phase']=='main']
assert len(a_main_rows)==1 and a_main_rows[0]['closed']and a_main_rows[0]['report_sha256']==sha(a_result_raw)
assert a_result['scope_id']==protocol['arms']['A']['scope_id']and a_result['phase']=='main'
assert a_result['status']=='FAILED_NO_RETRY'and a_result['passed']is False and a_result['task_success']is False
for arm,root in roots.items():
    observation=json.loads(read(root/'intent-observation-0001.json'))
    frame=Path(observation['rgb']['path']).parent
    assert frame.resolve().is_relative_to((root/'query-observations').resolve())
    assert sha(read(frame/'rgb.png'))==observation['rgb']['sha256']
    read(frame/'depth_m.npy');read(frame/'calibration.json');observations[arm]=observation
    collected={}
    for path in sorted((root/'episode/commands').glob('*.npz'))[:3]:
        with np.load(io.BytesIO(read(path)),allow_pickle=False)as chunk:
            for key in chunk.files:collected.setdefault(key,[]).append(chunk[key].copy())
    arrays[arm]={k:np.concatenate(v,axis=0)for k,v in collected.items()}
    assert len(arrays[arm]['physical_tick'])>=448
    assert np.array_equal(arrays[arm]['physical_tick'][:448].reshape(-1),np.arange(1,449))
    path=root/'events.jsonl';raw=path.read_bytes();end=raw.rfind(b'\n')+1;raw=raw[:end]
    previous='0'*64;rows=[]
    for index,line in enumerate(raw.splitlines()):
        item=json.loads(line);claim=item.pop('sha256')
        assert item['sequence']==index and item['previous_sha256']==previous and canonical_sha(item)==claim
        previous=claim;rows.append(item['payload'])
    assert path.read_bytes().startswith(raw),'Original journal prefix was rewritten'
    events[arm]=rows;prefixes[arm]=dict(rows=len(rows),last_sha256=previous,prefix_bytes=len(raw),prefix_sha256=sha(raw),
        original_journal_path=str(path),prefix_valid=True,full_journal_closed=arm=='A')
keys={'issued','delayed','torque','raw_torque','q_before','dq_before','physical_tick','time_s'}
assert set(arrays['A'])==set(arrays['B'])==keys
checks={}
for key in sorted(keys):
    x,y=arrays['A'][key][:448],arrays['B'][key][:448]
    checks[key]=dict(dtype_and_shape_equal=x.dtype==y.dtype and x.shape==y.shape,
                    actual_bytes_equal=x.tobytes()==y.tobytes())
assert all(all(c.values())for c in checks.values())
x,y=copy.deepcopy(observations['A']),copy.deepcopy(observations['B'])
x['rgb']['path']=y['rgb']['path']='EXCLUDED_STORAGE_PATH_FOR_EQUALITY_ONLY_NOT_CANONICAL_SOURCE_HASH'
assert x==y
assert observations['A']['objects']==observations['B']['objects']==[]
def only(arm,name):
    rows=[e for e in events[arm]if e.get('event')==name]
    assert len(rows)==1,(arm,name,len(rows));return rows[0]
decisions={arm:only(arm,'reach_complex_public_decision')for arm in ('A','B')}
selected={arm:only(arm,'reach_complex_semantic_intent_selected')for arm in ('A','B')}
assert decisions['A']['method']=='greedy'and decisions['B']['method']=='multistep'
assert selected['A']['actual_source_target_ref']=='cuboid_a'
assert selected['B']['actual_source_target_ref']=='cx-nav-000'
bound=only('B','intent_native_execution_bound');installed=only('B','native_option_installed')
assert bound['intent_sha256']==selected['B']['intent_sha256']
assert bound['native_option_sha256']==installed['option_sha256']and bound['execution_role']=='interaction'
assert bound['native_option']['skill']=='NAV'and bound['native_option']['target_ref']=='cx-nav-000'
assert dict(bound['native_option']['parameters'])==selected['B']['actual_source_parameters']
assert not any(e.get('event')=='native_option_installed'for e in events['A'])
forwards=[e for e in events['B']if e.get('event')=='registered_NAV_actual_actor_forward'];assert forwards
assert len(arrays['B']['physical_tick'])>448 and int(arrays['B']['physical_tick'].reshape(-1)[448])==449
assert not(roots['B']/'result.json').exists(),'B closed; use a terminal-result reader instead of an in-progress report'
for path,h in pins.items():assert sha(Path(path).read_bytes())==h,'Closed original input drift'
assert Path(a.protocol).read_bytes()==protocol_bytes and not blocked
out=dict(at=dt.datetime.now().astimezone().isoformat(),role='INDEPENDENT_ACTUAL_CONTROLLED_PREFIX_AND_NATIVE_CONSUMPTION_NOT_TASK_GAIN',
    protocol_sha256=a.expected_protocol_sha,reader_source_sha256=sha(Path(__file__).read_bytes()),
    A_original_closed_result_sha256=sha(a_result_raw),A_main_ledger_closed=True,
    predecision_capture_steps=448,actual_capture_channel_checks=checks,
    first_public_observations_equal_except_storage_path=True,canonical_original_observation_hashes_not_overridden=True,
    exact_original_observation_file_sha256={arm:pins[str(root/'intent-observation-0001.json')]for arm,root in roots.items()},
    both_first_public_observed_object_lists_empty=True,actual_decision_events=decisions,actual_selected_intent_events=selected,
    B_original_native_option_sha256=installed['option_sha256'],B_original_NAV_actor_forward_events_in_snapshot=len(forwards),
    B_first_actual_postcapture_command_physical_tick=449,B_first_actual_postcapture_command_time_s=float(arrays['B']['time_s'].reshape(-1)[448]),
    B_journal_prefix_not_terminal=prefixes['B'],A_closed_journal=prefixes['A'],source_input_file_pins=pins,
    A_native_task_options=0,B_main_result_not_yet_published=True,task_NAV_success_or_reconstruction_or_three_choices_claimed=False,
    full_task_or_algorithm_advantage_claimed=False,standard_search_not_algorithm_novelty=True,
    private_pose_or_future_route_used=False,original_source_or_records_modified=False,new_Runtime_Actor_Renderer_physics_or_fit=0,
    forbidden_attempts=blocked)
with Path(a.output).open('x')as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:out[k]for k in ('role','predecision_capture_steps','B_original_native_option_sha256',
    'B_original_NAV_actor_forward_events_in_snapshot','B_first_actual_postcapture_command_physical_tick',
    'B_first_actual_postcapture_command_time_s','B_main_result_not_yet_published')},ensure_ascii=False))
