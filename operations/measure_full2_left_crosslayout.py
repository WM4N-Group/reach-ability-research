#!/usr/bin/env python3
"""One finite matched-left-prefix cross-layout DEV measurement.
Reuse exact frozen full-4 component result; run original proposer only on NEW
full-2 public pixels. No fitting, GT, policy choice, new capture or simulation.
"""
from pathlib import Path
import argparse,datetime as dt,hashlib,importlib.util,json,sys
p=argparse.ArgumentParser(description=__doc__)
for name in ('runs-root','baseline-cache-sha','proposer','component-helper','output'):p.add_argument('--'+name,required=True)
a=p.parse_args();runs=Path(a.runs_root);forbidden=[]
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
cache_file=runs/'G1-pair-public-comparison-20261115-v2.json';assert sha(cache_file)==a.baseline_cache_sha
cache=json.loads(cache_file.read_bytes());pins[str(cache_file)]=a.baseline_cache_sha
paths=[runs/'G1-left-public-boundary-20261115-v2.json',runs/'G2-full2-left-public-boundary-20261115-v1.json']
reports=[json.loads(p.read_bytes()) for p in paths]
assert [r['scope_id'] for r in reports]==['data-46308-native-prefix-left-PUSH-CLIMB-20261115-v2','data-46308-G2-full2-left-PUSH-CLIMB-20261115-v1']
assert cache['conditions'][0]==reports[0]['scope_id'] and cache['source_pins'][str(paths[0])]==sha(paths[0])
mods=[]
for i,(path,expected) in enumerate(((a.proposer,'837e95ecd7bc3249154b8a53097f71fd90974a2df9fb4a35d87116d0254af304'),
                                  (a.component_helper,'0b66cbf44925722dedaea46cb3e5800cf69e7e7e39253ffb861299f837b1540b'))):
    assert sha(path)==expected and expected in cache['source_pins'].values();pins[path]=expected
    spec=importlib.util.spec_from_file_location('Reach_G2_left_'+str(i),path)
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod);mods.append(mod)
original,helper=mods;frames=[]
for report,path in zip(reports,paths):
    assert report['status']=='ACTUAL_FIRST_CLIMB_PREPARE_PUBLIC_QUERY_BOUND' and report['role']=='DEV_AUDIT_ONLY_NOT_TRAIN_OR_ONLINE'
    pins[str(path)]=sha(path);q=report['first_PREPARE']
    for field,h in (('actual_query_path','actual_query_file_sha256'),('RGB_file','RGB_encoded_sha256'),('depth_file','depth_file_sha256'),('calibration_file','calibration_file_sha256')):
        assert sha(q[field])==q[h];pins[q[field]]=q[h]
        if report is reports[0]:assert cache['source_pins'][q[field]]==q[h]
    with Image.open(q['RGB_file']) as im:rgb=np.asarray(im).copy()
    depth=np.load(q['depth_file'],allow_pickle=False)
    frames.append((rgb,depth,np.asarray(q['camera_K']),np.asarray(q['T_base_optical'])))
new=reports[1]['first_PREPARE'];obs=json.loads(Path(new['actual_query_path']).read_bytes());rgb,depth,K,T=frames[1]
support=helper.derive_original_component_support(original,rgb,depth,K,T,acquisition_time_s=obs['rgb']['time_s'],encoded_rgb_sha256=obs['rgb']['sha256'])
joins=helper.join_current_public_components(obs,support)
alias=[o for o in obs['objects'] if o['label'].startswith('cuboid-2; dimensions ')]
comp=dict(status='UNKNOWN_NO_UNIQUE_PUBLIC_ALIAS',nominal_visible_median_parent_base_m=None)
if len(alias)==1:
    match=[r for r in joins if r['public_target_ref']==alias[0]['target_ref']]
    if len(match)==1 and match[0]['public_bbox_component_correspondence_exact']:
        c=next(c for c in support['component_support'] if c['frame_local_ref']==match[0]['frame_local_ref'])
        prop=next(c for c in support['original_proposals']['candidates'] if c['frame_local_ref']==match[0]['frame_local_ref'])
        yx=np.asarray(c['pixel_indices_yx'],dtype=np.int64);z=depth[yx[:,0],yx[:,1],0]
        comp.update(status='EXACT_PUBLIC_COMPONENT_NOMINAL_ONLY',component_pixels=c['pixel_count'],valid_depth_pixels=int((np.isfinite(z)&(z>=.05)&(z<=15.)).sum()),nominal_visible_median_parent_base_m=prop['visible_surface_median_base_xyz_m'])
    else:comp['status']='UNKNOWN_NO_ACCEPTED_COMPONENT'
base=cache['component_estimates'][0];delta=None
if base['nominal_visible_median_parent_base_m'] is not None and comp['nominal_visible_median_parent_base_m'] is not None:
    d=np.asarray(comp['nominal_visible_median_parent_base_m'])-np.asarray(base['nominal_visible_median_parent_base_m'])
    delta=dict(full2_minus_full4_XYZ_m=d.tolist(),L2_m=float(np.linalg.norm(d)),physical_error_or_reference_relative_bound_m=None)
blocks={}
for name,unit in {'q':'rad','dq':'rad/s','gravity':'1','angular_velocity':'rad/s','linear_velocity':'m/s'}.items():
    x,y=[np.asarray(r['first_PREPARE']['public45D_vectors'][name]) for r in reports];d=y-x
    blocks[name]=dict(unit=unit,exact_numeric_equal=bool(np.array_equal(x,y)),different_channels=int((x!=y).sum()),full2_minus_full4_per_channel=d.tolist(),max_abs_delta=float(np.max(np.abs(d))),L2_delta=float(np.linalg.norm(d)))
f0,f1=frames
for path,expected in pins.items():assert sha(path)==expected
assert not forbidden
out=dict(at=dt.datetime.now().astimezone().isoformat(),role='MATCHED_PREFIX_CROSS_LAYOUT_DEV_AUDIT_NOT_FIT_OR_POLICY_COMPARISON',
    comparison_axis='full4_left_vs_full2_left_not_G1_left_vs_right',conditions=[r['scope_id'] for r in reports],query_times_s=[r['first_PREPARE']['query_time_s'] for r in reports],source_pins=pins,
    public45D_blocks=blocks,all45D_exact_numeric_equal=all(b['exact_numeric_equal'] for b in blocks.values()),
    decoded_RGB_exact_numeric_equal=bool(np.array_equal(f0[0],f1[0])),depth_exact_numeric_equal_NaNs_equal=bool(np.array_equal(f0[1],f1[1],equal_nan=True)),
    camera_K_exact_numeric_equal=bool(np.array_equal(f0[2],f1[2])),T_base_optical_exact_numeric_equal=bool(np.array_equal(f0[3],f1[3])),
    component_estimates=[base,comp],nominal_component_delta=delta,baseline_original_proposer_reexecutions=0,new_full2_original_proposer_calls=1,
    completed_grid_cells=3,planned_grid_cells=4,right_full2_result_unavailable_for_this_measurement=True,
    raw_point_difference_not_object_pose_world_motion_or_sensor_accuracy=True,native_filter_conditioned_population=True,
    condition_family_or_training_split_qualification=False,old_DEV_not_relabelled=True,old_host_connections=0,
    new_simulator_capture_Actor_or_model_fit=False,forbidden_attempts=forbidden)
with Path(a.output).open('x') as stream:json.dump(out,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({k:out[k] for k in ('all45D_exact_numeric_equal','decoded_RGB_exact_numeric_equal','depth_exact_numeric_equal_NaNs_equal','nominal_component_delta')}))
print('component pixels',base.get('component_pixels'),comp.get('component_pixels'))
for name,b in blocks.items():print(name,b['max_abs_delta'],b['L2_delta'])
