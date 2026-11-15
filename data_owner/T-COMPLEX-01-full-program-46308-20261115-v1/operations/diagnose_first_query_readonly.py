"""Actual closed public image/candidate contract diagnostic, not B native result.
No private geometry/state/replay, no alternative parameters, no target imputation.
"""
from pathlib import Path
import sys,os,json,hashlib,ast
assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('torch','mujoco','onnxruntime'):raise RuntimeError('Readonly public diagnostic forbids native/model imports')
sys.addaudithook(fence)
import numpy as np
from PIL import Image
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';W=B/'workers/T-COMPLEX-01-full-program-46308-20261115-v1';M=B/'manifests/T-COMPLEX-01-full-program-46308-20261115-v1';S=R/'runtime/workers/data-46308-T-COMPLEX-01-v2-full-A-greedy-20261115-v1/main';SOURCE=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();freeze=json.loads((M/'A/program-freeze.json').read_bytes())
for p in [SOURCE/'visual_box_proposals.py',SOURCE/'ainav/contracts.py',SOURCE/'ainav/intents.py',SOURCE/'ainav/planner.py',SOURCE/'ainav/native/behavior_authority.py',W/'inputs/scene/scene_driver.py']:
 assert sha(p)==freeze['files'][str(p)]
method=json.loads((W/'inputs/COMMON_METHOD_PROTOCOL.json').read_bytes())
for name,pin in method['code_sha256'].items():assert sha(W/'inputs/Reach'/name)==pin
sys.path[:0]=[str(SOURCE),str(W/'inputs/Reach')]
from ainav.contracts import Observation,canonical
from ainav.intents import IntentBatch,SkillIntent
from research.task_conditioned_reachability.execution_preparation.complex_source_adapter import build_source_bound_planner
from visual_box_proposals import propose_visual_candidates,single_visible_hypothesis
before={str(p):sha(p)for p in[S/'result.json',S/'events.jsonl',S/'intent-observation-0001.json']};observation=Observation((S/'intent-observation-0001.json').read_text().strip());observation.verify_image();value=observation.value;directory=Path(value['rgb']['path']).parent;cal=json.loads((directory/'calibration.json').read_bytes());rgb=np.asarray(Image.open(value['rgb']['path']));depth=np.load(directory/'depth_m.npy',allow_pickle=False);K=np.array(cal['camera_K']);T=np.array(cal['T_base_optical']);proposal=propose_visual_candidates(rgb,depth,K,T);single=[]
for p in proposal['candidates']:
 try:single_visible_hypothesis(proposal,p['frame_local_ref'],current_RGB_sha256=proposal['RGB_sha256']);single.append(dict(frame_local_ref=p['frame_local_ref'],accepted_as_single_visible_hypothesis=True))
 except ValueError as e:single.append(dict(frame_local_ref=p['frame_local_ref'],accepted_as_single_visible_hypothesis=False,original_rejection=str(e)))
events=[json.loads(x)['payload']for x in(S/'events.jsonl').read_text().splitlines()];selected=[e for e in events if e.get('event')=='skill_intent_selected'];cat=[e for e in events if e.get('event')=='semantic_intent_catalogue'];assert len(selected)==len(cat)==1 and value['time_s']==cat[0]['time_s'];options=tuple(SkillIntent('cx-intent-1-%d'%i,r['skill'],r['target_ref'],tuple(sorted(r['parameters'].items())))for i,r in enumerate(cat[0]['intents']))
tree=ast.parse((W/'inputs/scene/scene_driver.py').read_text());nodes=[n.value for n in ast.walk(tree)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Attribute)and t.attr=='capabilities'for t in n.targets)];assert len(nodes)==1;call=nodes[0].args[0];assert isinstance(call,ast.Call)and call.func.id=='dict';cap={k.arg:ast.literal_eval(k.value)for k in call.keywords};batch=IntentBatch('ainav-intent-000001',observation,options,canonical(cap));assert batch.sha256==selected[0]['semantic_query_sha256']
logs=[]
def emit(row):logs.append(row);return 'READONLY_PUBLIC_CPU_DIAGNOSTIC:'+str(len(logs))
planner=build_source_bound_planner(public_task_path=W/'inputs/scene/PUBLIC_TASK_V2.json',expected_task_sha256=method['public_files']['PUBLIC_TASK_V2.json'],finite_placements_path=W/'inputs/scene/FINITE_PLACEMENTS_V2.json',expected_placements_sha256=method['public_files']['FINITE_PLACEMENTS_V2.json'],method='multistep',journal=emit,terminal_target_ref='cx-goal');choice=planner.select(batch);matches=[o for o in options if o.sha256==choice.option_sha256];assert len(matches)==1;option=matches[0];available={o['label'].split(';')[0]for o in value['objects']};assert all(sha(p)==pin for p,pin in before.items())
report=dict(role='CLOSED_PUBLIC_QUERY_READONLY_INTERFACE_DIAGNOSTIC_NOT_B_NATIVE_OR_REPLAY',source_observation_file_sha256=sha(S/'intent-observation-0001.json'),original_public_observation_sha256=observation.sha256,original_semantic_batch_sha256=batch.sha256,original_A_selected_intent=selected[0]['intent'],original_public_associated_object_count=len(value['objects']),original_public_associated_refs=sorted(available),source_packet_time_s=value['time_s'],source_RGB_file_sha256=sha(Path(value['rgb']['path'])),source_depth_file_sha256=sha(directory/'depth_m.npy'),source_calibration_file_sha256=sha(directory/'calibration.json'),pixel_only_proposal=proposal,unchanged_original_single_visible_hypotheses=single,B_frozen_method_CPU_first_intent=dict(skill=option.skill,target_ref=option.target_ref,parameters=dict(option.parameters)),B_first_intent_target_associated_in_this_original_A_public_query=option.target_ref in available,same_first_target_as_actual_A=option.target_ref==selected[0]['intent']['target_ref'],B_native_zero_or_main_calls=0,source_files_and_original_bytes_unchanged=True,no_GT_private_state_or_existence_route_consumed=True,no_alternative_pixel_config_mask_or_threshold_sweep=True,not_B_actual_result_or_dynamic_counterfactual_gain=True,for_source_owner_technical_interface_only=True)
with(M/'A/first-query-public-readonly-diagnostic.json').open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(report,ensure_ascii=False))
