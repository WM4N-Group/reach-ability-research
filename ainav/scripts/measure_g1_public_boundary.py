#!/usr/bin/env python3
"""Fixed G1-full4/G2-full2/full1 closed-scope PUBLIC measurement; no world/fit/GT input.

Uses the original evidence reader and original pixel proposer/component helpers.
Only the first CLIMB judgment is eligible; never substitute a later READY frame.
"""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,sys
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--code-root',type=Path,required=True);p.add_argument('--main-root',type=Path,required=True)
p.add_argument('--expected-program-sha',required=True);p.add_argument('--expected-journal-sha',required=True)
p.add_argument('--expected-journal-rows',type=int,required=True)
a=p.parse_args();code=a.code_root.resolve();main=a.main_root.resolve();scope=main.parent.name
# Only already frozen named cohorts; this never grants a physical-run permit.
scopes={
 'data-46308-native-prefix-left-PUSH-CLIMB-20261115-v2':('G1_full4_v2','full-4','8da5a1f4c4d12163d2588ba5166c087381ff3df5c0f3769471cd3222816ef682'),
 'data-46308-native-prefix-right-PUSH-CLIMB-20261115-v2':('G1_full4_v2','full-4','c663dabc280b6bd2ea95c1f350fcfec7af7a45dc9fe983667522468a7e724b33'),
 'data-46308-G2-full2-left-PUSH-CLIMB-20261115-v1':('G2_full2_v1','full-2','6ee69a5f2a08c8ed8e5212b2c22ead90daf54dc4bb581bd9e4a09712ab2535e1'),
 'data-46308-G2-full2-right-PUSH-CLIMB-20261115-v1':('G2_full2_v1','full-2','b0c2d41b07a3bf0d36d488970c17f17814fb205c1cc0b6e6aff01be9a9949f0a'),
 'data-46308-G2-full1-left-PUSH-CLIMB-20261115-v1':('G2_full1_left_v1','full-1','3b5e9d4d4366479394cf825419f47f6c1875c32519fca26c40762ffa4e82ee8f')}
assert main.name=='main' and scope in scopes
family,layout,program=scopes[scope]
assert a.expected_program_sha==program,'Exact previously frozen program, not an arbitrary scope label'
blocked=[]
def fence(event,args):
 if event=='import' and str(args[0]).split('.')[0] in ('torch','mujoco','onnxruntime'):
  blocked.append(str(args[0]));raise RuntimeError('No model/native imports in public measurement')
 if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
  blocked.append(event);raise RuntimeError('No network/child in public measurement')
 if event=='open' and isinstance(args[0],str) and ('/query-private-' in args[0] or args[0].endswith(('/catalog.json','/association.json','.npz','.mjb','.mjb.gz'))):
  blocked.append('PRIVATE_OR_COMMAND_ARRAY');raise RuntimeError('Public query files only, no private catalogue/state/motor arrays')
sys.addaudithook(fence)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();pins={}
def pin(path):path=Path(path);h=sha(path);pins[str(path)]=h;return h
def read(path):pin(path);return json.loads(Path(path).read_bytes())
def module(name,path):
 pin(path);spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
base=code/'consumer-deliveries/AINAV-CLIMB-PREPARATION-CANDIDATES-20261113-v1/common-source'
sys.path.insert(0,str(base))
from ainav.evidence import verify
from ainav.contracts import Observation
ledger=read(main.parent/'accounting/ledger.json')
assert ledger['scope_id']==scope and ledger['program_sha256']==a.expected_program_sha
rows_main=[r for r in ledger['rows'] if r['phase']=='main'];assert len(rows_main)==1 and rows_main[0]['closed'] is True
journal=main/'events.jsonl';assert pin(journal)==a.expected_journal_sha
chain=verify(journal);assert chain['rows']==a.expected_journal_rows
# Only literal event/intent/status/time and exact reference linkage are projected.
# Private measurement fields in judgment records never enter the public features.
records=[json.loads(line) for line in journal.read_text().splitlines()]
first=next(((i,e['payload']) for i,e in enumerate(records,1) if e['payload'].get('event')=='skill_execution_judgment' and e['payload'].get('spec',{}).get('skill')=='CLIMB'),None)
result={'at':datetime.datetime.now().astimezone().isoformat(),'role':'NEW_DEV_AUDIT_ONLY_NOT_ONLINE_REPLAY_OR_FIT',
 'scope_id':scope,'pair_family_metadata_not_state':family,'source_layout_metadata_not_state':layout,'program_sha256':a.expected_program_sha,'journal_sha256':a.expected_journal_sha,
 'journal_chain':chain,'training_or_fit_allowed':False,'boundary_status':'NO_CLIMB_JUDGMENT_RECORDED',
 'public_features':None,'pairwise_condition_comparison_or_critic_qualification_claimed':False,
 'raw_pixels_depth_and_motor_arrays_downloaded_to_local_or_Git':False}
obs_sha=None;clock=None
if first:
 line,judgment=first;status=judgment['status'];ref=str(journal)+'#'+str(line)
 result.update(first_judgment_line_1based=line,first_judgment_status=status,intent_sha256=judgment['intent_sha256'])
 if status=='READY':result['boundary_status']='NO_PREPARE_BOUNDARY_ALREADY_READY'
 elif status=='BLOCKED':result['boundary_status']='NO_PREPARE_BOUNDARY_FIRST_JUDGMENT_BLOCKED'
 elif status=='PREPARE':
  result['boundary_status']='PREPARE_UNBOUND_NO_EXACT_PUBLIC_REFERENCE'
  bound=next(((i,e['payload']) for i,e in enumerate(records,1) if e['payload'].get('event')=='intent_native_execution_bound' and e['payload'].get('execution_role')=='preparation' and e['payload'].get('intent_sha256')==judgment['intent_sha256'] and e['payload'].get('judgment_ref')==ref),None)
  if bound:
   bi,b=bound;assert bi>line and b['intent']['skill']=='CLIMB' and b['native_option']['skill']=='NAV'
   obs_sha=b['physical_observation_sha256'];clock=judgment['state']['time_s']
   result.update(bound_line_1based=bi,judgment_ref=ref,physical_observation_sha256=obs_sha,publication_time_s=clock)
del records
if obs_sha is not None:
 target=None
 for path in sorted(main.glob('intent-observation-*.json')):
  value=read(path)
  if value['time_s']>clock:break
  actual=Observation.create(value)
  if actual.sha256==obs_sha:
   assert actual.time_s==clock;target=(path,value);break
 assert target is not None,'No exact original Host public query; do not use nearest/base/future query'
 obs_path,obs=target;window=module('g1_original_public_window',code/'development/climb_preparation_v2/public_observation_window.py')
 summary=window.summarize_public_window([obs]);assert summary['distinct_acquisition_times']==1
 raw_state={k:obs['public_state'][k] for k in window.CHANNELS}
 rgb_path=Path(obs['rgb']['path']);assert rgb_path.resolve().is_relative_to(main) and not rgb_path.is_symlink()
 assert pin(rgb_path)==obs['rgb']['sha256']
 cal_path=rgb_path.parent/'calibration.json';depth_path=rgb_path.parent/'depth_m.npy'
 cal=read(cal_path);pin(depth_path);assert cal['acquisition_time_s']==obs['rgb']['time_s']
 import numpy as np
 from PIL import Image
 assert np.__version__=='1.26.4'
 with Image.open(rgb_path) as image:
  assert image.mode=='RGB' and image.format=='PNG';rgb=np.asarray(image).copy()
 depth=np.load(depth_path,allow_pickle=False);assert depth.shape==(*rgb.shape[:2],1)
 K=np.asarray(cal['camera_K'],dtype=np.float64);T=np.asarray(cal['T_base_optical'],dtype=np.float64)
 proposer=module('g1_unchanged_pixel_proposer',base/'visual_box_proposals.py')
 helper=module('g1_existing_component_helper',code/'development/climb_preparation_v2/public_component_support.py')
 support=helper.derive_original_component_support(proposer,rgb,depth,K,T,acquisition_time_s=obs['rgb']['time_s'],encoded_rgb_sha256=obs['rgb']['sha256'])
 joins=helper.join_current_public_components(obs,support)
 aliases=[obj for obj in obs['objects'] if obj['label'].startswith('cuboid-2; dimensions ')]
 features={'public_query_file':str(obs_path),'acquisition_time_s':obs['rgb']['time_s'],'age_s':obs['time_s']-obs['rgb']['time_s'],
  'public_state_45D_blocks':raw_state,'status_text_UUID_clock_or_condition_label_NOT_state_features':True,
  'RGB_decoded_shape':list(rgb.shape),'RGB_decoded_dtype':str(rgb.dtype),'RGB_decoded_array_sha256':hashlib.sha256(rgb.tobytes()).hexdigest(),
  'depth_shape':list(depth.shape),'depth_dtype':str(depth.dtype),'depth_array_sha256':hashlib.sha256(depth.tobytes()).hexdigest(),
  'array_hashes_are_identity_only_NOT_pairwise_value_comparison':True,
  'camera_K':K.tolist(),'T_base_optical':T.tolist(),
  'raw_proposal_count':len(support['original_proposals']['candidates']),
  'raw_original_refused_count':sum(not c['original_single_visible_hypothesis_accepted'] for c in support['component_support']),
  'task_component_status':'UNKNOWN_NO_UNIQUE_PUBLIC_ALIAS','component_visible_point_median_base_xyz_m':None,
  'native_filtered_public_population':True,'physical_object_point_ownership_or_error_bound_certified':False}
 if len(aliases)==1:
  obj=aliases[0];join=next(j for j in joins if j['public_target_ref']==obj['target_ref']);features['task_component_status']=join['status']
  if join['public_bbox_component_correspondence_exact']:
   component=next(c for c in support['component_support'] if c['frame_local_ref']==join['frame_local_ref'])
   prop=next(x for x in support['original_proposals']['candidates'] if x['frame_local_ref']==join['frame_local_ref'])
   features.update(task_bbox_xyxy=obj['bbox_xyxy'],component_pixel_count=component['pixel_count'],component_valid_depth_pixels=component['valid_depth_pixels'],component_visible_point_median_base_xyz_m=prop['visible_surface_median_base_xyz_m'])
 result.update(boundary_status='FIRST_PREPARE_EXACT_PUBLIC_VALUES_MEASURED',public_features=features,
  numeric_environment={'numpy':np.__version__,'PIL':Image.__version__,'python':sys.version.split()[0]},
  no_private_pose_GT_successor_outcome_or_cost_used_for_public_values=True)
for path,h in pins.items():assert sha(path)==h
assert not blocked
result.update(inputs_sha256=pins,forbidden_attempts=blocked,new_capture_Runtime_Actor_Renderer_or_physics=False)
print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
