#!/usr/bin/env python3
"""One fixed G1-full4 or G2-full2 pair: public equality + component statistic delta.

No fitting/thresholds or joint-unit score; full45D block statistics belong to Reach.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,sys
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--left',type=Path,required=True);p.add_argument('--right',type=Path,required=True)
p.add_argument('--pair-family',choices=('G1_full4_v2','G2_full2_v1','G2_cross_layout_left_v1','G2_cross_layout_right_v1'),default='G1_full4_v2',help='Explicit within-scene or declared SAME-prefix cross-layout pair; no arbitrary mixing')
a=p.parse_args();blocked=[]
pair_templates={'G1_full4_v2':'data-46308-native-prefix-{side}-PUSH-CLIMB-20261115-v2',
 'G2_full2_v1':'data-46308-G2-full2-{side}-PUSH-CLIMB-20261115-v1'}
# Reach's pre-outcome four-cell protocol: two SAME-prefix cross-layout pairs.
# CLI left/right identify ordered input slots here, not different prefix sides.
# This is a whole registered-layout contrast, not a pure prefix causal effect.
within_scene=a.pair_family in pair_templates
if within_scene:
 expected_scopes=[pair_templates[a.pair_family].format(side=s) for s in ('left','right')]
 roles=['prefix_left','prefix_right']
else:
 prefix='left' if a.pair_family=='G2_cross_layout_left_v1' else 'right'
 expected_scopes=[pair_templates['G1_full4_v2'].format(side=prefix),pair_templates['G2_full2_v1'].format(side=prefix)]
 roles=['full4_'+prefix,'full2_'+prefix]
def fence(event,args):
 if event=='import' and str(args[0]).split('.')[0] in ('torch','mujoco','onnxruntime'):
  blocked.append(str(args[0]));raise RuntimeError('No native/model import')
 if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
  blocked.append(event);raise RuntimeError('No network/child')
 if event=='open' and isinstance(args[0],str) and ('/query-private-' in args[0] or args[0].endswith(('/catalog.json','/association.json','.npz','.mjb','.mjb.gz'))):
  blocked.append('PRIVATE_OR_MOTOR_ARRAY');raise RuntimeError('PUBLIC values only')
sys.addaudithook(fence)
import numpy as np
from PIL import Image
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest();data=[];pins={}
for slot,(side,path) in enumerate([('left',a.left),('right',a.right)]):
 j=json.loads(path.read_bytes());pins[str(path)]=sha(path)
 assert j['scope_id']==expected_scopes[slot],'Exact fixed within-scene or same-prefix cross-layout pair; no arbitrary/reversed mixing'
 assert j['training_or_fit_allowed'] is False and j['role']=='NEW_DEV_AUDIT_ONLY_NOT_ONLINE_REPLAY_OR_FIT'
 for f,h in j['inputs_sha256'].items():assert sha(f)==h;pins[f]=h
 data.append(j)
result={'at':datetime.datetime.now().astimezone().isoformat(),'role':'NEW_DEV_AUDIT_ONLY_NOT_TRAIN_CALIBRATION_OR_TEST',
 'pair_family_metadata_not_state':a.pair_family,'ordered_input_roles_metadata_not_state':roles,'scopes':[j['scope_id'] for j in data],'query_denominator':2,'statuses':[j['boundary_status'] for j in data],'paired_values_available':False,
 'robust_condition_family_or_critic_learning_or_policy_gain_certified':False,'training_or_fit':False}
if all(j['boundary_status']=='FIRST_PREPARE_EXACT_PUBLIC_VALUES_MEASURED' for j in data):
 v=[j['public_features'] for j in data];keys=('q','dq','gravity','angular_velocity','linear_velocity')
 eq={k:v[0]['public_state_45D_blocks'][k]==v[1]['public_state_45D_blocks'][k] for k in keys}
 images=[];depths=[]
 for j in data:
  rgb=next(Path(f) for f in j['inputs_sha256'] if f.endswith('/rgb.png'))
  depth=next(Path(f) for f in j['inputs_sha256'] if f.endswith('/depth_m.npy'))
  with Image.open(rgb) as im:assert im.mode=='RGB';images.append(np.asarray(im).copy())
  depths.append(np.load(depth,allow_pickle=False))
 assert all(x.shape==images[0].shape and x.dtype==images[0].dtype for x in images)
 assert all(x.shape==depths[0].shape and x.dtype==depths[0].dtype for x in depths)
 result.update(paired_values_available=True,public_45D_exact_equal=all(eq.values()),public_45D_block_exact_equal=eq,
  RGB_decoded_values_exact_equal=bool(np.array_equal(*images)),depth_values_exact_equal_default_numpy=bool(np.array_equal(*depths)),
  depth_NaN_locations_equal=bool(np.array_equal(np.isnan(depths[0]),np.isnan(depths[1]))),
  depth_values_equal_treating_corresponding_NaN_as_missing=bool(np.array_equal(*depths,equal_nan=True)),
  camera_K_exact_equal=bool(np.array_equal(v[0]['camera_K'],v[1]['camera_K'])),
  T_base_optical_exact_equal=bool(np.array_equal(v[0]['T_base_optical'],v[1]['T_base_optical'])),
  task_component_statuses=[x['task_component_status'] for x in v],
  component_pixel_counts=[x.get('component_pixel_count') for x in v])
 med=[x['component_visible_point_median_base_xyz_m'] for x in v]
 if all(x is not None for x in med):
  delta=np.asarray(med[1])-np.asarray(med[0])
  key='right_minus_left_nominal_component_median_base_XYZ_m' if within_scene else 'full2_minus_full4_nominal_component_median_base_XYZ_m'
  result.update({key:delta.tolist(),'nominal_component_median_delta_L2_m':float(np.linalg.norm(delta)),
   'coordinate_frame_limitation':'Each point is in its own acquisition body frame; delta is NOT world motion, object truth or reference-relative error.'})
 result['interpretation']='Exact differences describe THIS two-run public representation only. No repeatability/noise/material threshold, object truth, candidate ranking, unseen evaluation or benefit follows.'
for f,h in pins.items():assert sha(f)==h
assert not blocked
result.update(inputs_sha256=pins,forbidden_attempts=blocked,raw_arrays_remain_on_remote=True,new_capture_Runtime_Actor_Renderer_or_physics=False)
print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
