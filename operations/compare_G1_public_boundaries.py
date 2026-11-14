#!/usr/bin/env python3
"""Finite preregistered G1 public-input comparison on two ACTUAL closed branches.
No fit, private GT/association, native runtime, capture or candidate selection.
"""
from pathlib import Path
import argparse,datetime as dt,hashlib,importlib.util,json,sys
p=argparse.ArgumentParser(description=__doc__)
for name in ('left','right','proposer','component-helper','output'):p.add_argument('--'+name,required=True)
a=p.parse_args();forbidden=[]
def fence(event,args):
    if event=='import' and str(args[0]).split('.')[0] in ('torch','mujoco','onnxruntime'):
        forbidden.append(str(args[0]));raise RuntimeError('No native/Actor')
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        forbidden.append(event);raise RuntimeError('No network/child')
    if event=='open' and isinstance(args[0],str) and ('/query-private-' in args[0] or args[0].endswith(('/catalog.json','/association.json'))):
        forbidden.append('PRIVATE_INPUT');raise RuntimeError('Public only')
sys.addaudithook(fence)
import numpy as np
from PIL import Image
assert np.__version__=='1.26.4'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
pins={str(Path(__file__).resolve()):sha(__file__)}
mods=[]
for i,(path,expected) in enumerate(((a.proposer,'837e95ecd7bc3249154b8a53097f71fd90974a2df9fb4a35d87116d0254af304'),
                                  (a.component_helper,'0b66cbf44925722dedaea46cb3e5800cf69e7e7e39253ffb861299f837b1540b'))):
    assert sha(path)==expected;pins[path]=expected
    spec=importlib.util.spec_from_file_location('Reach_G1_numeric_'+str(i),path)
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod);mods.append(mod)
proposer,helper=mods
reports=[json.loads(Path(path).read_bytes()) for path in (a.left,a.right)]
for path in (a.left,a.right):pins[path]=sha(path)
frames=[];components=[]
for report in reports:
    assert report['role']=='DEV_AUDIT_ONLY_NOT_TRAIN_OR_ONLINE'
    assert report['status']=='ACTUAL_FIRST_CLIMB_PREPARE_PUBLIC_QUERY_BOUND'
    q=report['first_PREPARE']
    for field,hash_field in (('actual_query_path','actual_query_file_sha256'),('RGB_file','RGB_encoded_sha256'),('depth_file','depth_file_sha256'),('calibration_file','calibration_file_sha256')):
        assert sha(q[field])==q[hash_field];pins[q[field]]=q[hash_field]
    value=json.loads(Path(q['actual_query_path']).read_bytes())
    with Image.open(q['RGB_file']) as im:rgb=np.asarray(im).copy()
    depth=np.load(q['depth_file'],allow_pickle=False);K=np.asarray(q['camera_K']);T=np.asarray(q['T_base_optical'])
    derived=helper.derive_original_component_support(proposer,rgb,depth,K,T,
        acquisition_time_s=value['rgb']['time_s'],encoded_rgb_sha256=value['rgb']['sha256'])
    joins=helper.join_current_public_components(value,derived)
    alias=[o for o in value['objects'] if o['label'].startswith('cuboid-2; dimensions ')]
    comp=dict(status='UNKNOWN_NO_UNIQUE_PUBLIC_ALIAS',valid_depth_pixels=None,nominal_visible_median_parent_base_m=None)
    if len(alias)==1:
        match=[r for r in joins if r['public_target_ref']==alias[0]['target_ref']]
        if len(match)==1 and match[0]['public_bbox_component_correspondence_exact']:
            row=match[0];c=next(c for c in derived['component_support'] if c['frame_local_ref']==row['frame_local_ref'])
            prop=next(c for c in derived['original_proposals']['candidates'] if c['frame_local_ref']==row['frame_local_ref'])
            yx=np.asarray(c['pixel_indices_yx'],dtype=np.int64);z=depth[yx[:,0],yx[:,1],0]
            comp.update(status='EXACT_PUBLIC_COMPONENT_NOMINAL_ONLY',component_pixels=c['pixel_count'],
                valid_depth_pixels=int((np.isfinite(z)&(z>=.05)&(z<=15.)).sum()),
                nominal_visible_median_parent_base_m=prop['visible_surface_median_base_xyz_m'],
                public_native_matcher_conditioned=True,object_identity_or_reference_pose_certified=False)
        else:comp['status']='UNKNOWN_NO_UNIQUE_ACCEPTED_COMPONENT'
    frames.append((rgb,depth,K,T));components.append(comp)
L,R=[r['first_PREPARE'] for r in reports]
units={'q':'rad','dq':'rad/s','gravity':'1','angular_velocity':'rad/s','linear_velocity':'m/s'}
blocks={}
for name,unit in units.items():
    x=np.asarray(L['public45D_vectors'][name]);y=np.asarray(R['public45D_vectors'][name]);delta=y-x
    blocks[name]=dict(unit=unit,exact_numeric_equal=bool(np.array_equal(x,y)),different_channels=int((x!=y).sum()),
        signed_right_minus_left_per_channel=delta.tolist(),max_abs_delta=float(np.max(np.abs(delta))),L2_delta=float(np.linalg.norm(delta)))
left,right=frames
same_rgb=left[0].shape==right[0].shape and np.array_equal(left[0],right[0])
same_depth=left[1].shape==right[1].shape and np.array_equal(left[1],right[1],equal_nan=True)
component_delta=None
if all(c['nominal_visible_median_parent_base_m'] is not None for c in components):
    difference=np.asarray(components[1]['nominal_visible_median_parent_base_m'])-np.asarray(components[0]['nominal_visible_median_parent_base_m'])
    component_delta=dict(signed_right_minus_left_XYZ_m=difference.tolist(),L2_m=float(np.linalg.norm(difference)),
        physical_error_or_tracking_uncertainty_bound_m=None,not_object_center_or_reference_relative_pose=True)
for path,expected in pins.items():assert sha(path)==expected
assert not forbidden
out=dict(at=dt.datetime.now().astimezone().isoformat(),role='G1_FINITE_DEV_INFORMATION_COMPARISON_NOT_FIT_OR_POLICY_EVALUATION',
    conditions=[r['scope_id'] for r in reports],query_times_s=[L['query_time_s'],R['query_time_s']],
    source_pins=pins,public45D_blocks=blocks,
    all45D_exact_numeric_equal=all(b['exact_numeric_equal'] for b in blocks.values()),
    action_offsets_same_original=[0.,0.],acquisition_ages_s=[L['acquisition_age_s'],R['acquisition_age_s']],
    decoded_RGB_exact_numeric_equal=bool(same_rgb),depth_exact_numeric_equal_NaNs_equal=bool(same_depth),
    camera_K_exact_numeric_equal=bool(np.array_equal(left[2],right[2])),T_base_optical_exact_numeric_equal=bool(np.array_equal(left[3],right[3])),
    component_estimates=components,nominal_component_delta=component_delta,
    actual_original_proposer_calls=2,old_query_indices_or_nearest_used=False,GT_or_private_association_used=False,
    all_refusals_preserved=True,full_condition_family_qualification_inferred=False,measurement_error_bound_or_statistical_power_claimed=False,
    candidate_ranking_or_optimizer_benefit_computed=False,new_fit_or_Runtime_or_physics=False,forbidden_attempts=forbidden)
with Path(a.output).open('x') as stream:json.dump(out,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({k:out[k] for k in ('all45D_exact_numeric_equal','decoded_RGB_exact_numeric_equal','depth_exact_numeric_equal_NaNs_equal','nominal_component_delta')}))
for name,b in blocks.items():print(name,b['different_channels'],b['max_abs_delta'],b['L2_delta'])
