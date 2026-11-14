"""Closed real motor-footprint integrity comparison only, not research scoring.
No public-observability/geometry/critic evaluation and no model/simulator imports.
"""
from pathlib import Path
import json,hashlib,os,sys
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('torch','mujoco','onnxruntime'):raise RuntimeError('No native/model imports')
 if event in('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):raise RuntimeError('No child/network')
sys.addaudithook(fence)
import numpy as np
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');M=R/'workspace/manifests/native-prefix-46308-20261115-v2';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();keys=['issued','delayed','q_before','dq_before','raw_torque','torque'];arrays={};meta=[];pins={}
for side in('left','right'):
 root=R/'runtime/workers'/f'data-46308-native-prefix-{side}-PUSH-CLIMB-20261115-v2';main=root/'main';v=json.loads((main/'result.json').read_bytes());ledger=json.loads((root/'accounting/ledger.json').read_bytes());assert v['passed']and all(r['closed']for r in ledger['rows']);episode=main/'episode';index=json.loads((episode/'index.json').read_bytes());chunks={k:[]for k in keys};ticks=[];times=[]
 for p in(main/'result.json',root/'accounting/ledger.json',episode/'index.json'):pins[str(p)]=sha(p)
 for row in index['commands']:
  p=episode/row['path'];assert not p.is_symlink()and p.resolve().is_relative_to(episode)and sha(p)==row['sha256'];pins[str(p)]=row['sha256']
  with np.load(p,allow_pickle=False)as d:
   for k in keys:chunks[k].append(d[k])
   ticks.append(d['physical_tick']);times.append(d['time_s'])
 arrays[side]={k:np.concatenate(v,axis=0)for k,v in chunks.items()};arrays[side]['tick']=np.concatenate(ticks);arrays[side]['time_s']=np.concatenate(times);meta.append(dict(condition=side,scope_id=v['scope_id'],program_sha256=v['program_sha256'],main_result_sha256=sha(main/'result.json'),steps=len(arrays[side]['tick']),original_native_requests=v['selected_requests'],exact3_real_semantic_native_successes=v['exact_three_semantic_native_successes']['exact_requested_semantic_success_count']))
n=min(len(arrays['left']['tick']),len(arrays['right']['tick']));assert np.array_equal(arrays['left']['tick'][:n],arrays['right']['tick'][:n]);firsts={};all_equal=np.ones(n,dtype=bool)
for k in keys:
 a,b=arrays['left'][k][:n],arrays['right'][k][:n];eq=(a==b).reshape(n,-1).all(axis=1);all_equal &=eq;which=np.flatnonzero(~eq)
 if len(which):
  i=int(which[0]);firsts[k]=dict(sample_index_zero_based=i,recorded_physics_tick=int(arrays['left']['tick'][i]),recorded_time_s=float(arrays['left']['time_s'][i]),all_earlier_recorded_values_bitwise_equal=True)
 else:firsts[k]=None
which=np.flatnonzero(~all_equal);prefix=int(which[0])if len(which)else n
assert all(sha(p)==pin for p,pin in pins.items());out=dict(schema='Data-G1-closed-real-six-motor-stream-footprint-v1',conditions=meta,compared_common_steps=n,all_six_recorded_fields_bitwise_equal_prefix_steps=prefix,first_differences=firsts,issued_motor_command_difference_actually_observed=firsts['issued']is not None,private_motor_evidence_not_planner_input=True,covered_fields_only_not_complete_hidden_state_equivalence=True,does_not_evaluate_public_45D_RGBD_or_component_information=True,does_not_qualify_condition_family_or_critic=True,raw_source_files_SHA_unchanged=True,source_files_sha256=pins,new_Model_Runtime_Actor_Renderer_GPU_physics_or_training_calls=0)
with(M/'actual-six-field-control-footprints.json').open('x')as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write(chr(10))
print(json.dumps(out,ensure_ascii=False,indent=2))
