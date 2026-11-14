#!/usr/bin/env python3
"""Read a closed branch's FIRST CLIMB PREPARE public query, not a new capture.

Consumes original journal verifier/Observation class and existing public RGBD.
No private catalogue/association, model, Actor, Runtime, state replay or fit.
Hashes bind records, not proof of independent world/hidden-state equality.
"""
from pathlib import Path
import argparse,hashlib,json,sys,datetime as dt

p=argparse.ArgumentParser(description=__doc__)
for name in ('run-root','source-root','expected-result-sha','expected-journal-sha','output'):
    p.add_argument('--'+name,required=True)
a=p.parse_args();root=Path(a.run_root).resolve();output=Path(a.output)
forbidden=[]
def fence(event,args):
    if event=='import' and str(args[0]).split('.')[0] in ('torch','mujoco','onnxruntime'):
        forbidden.append(str(args[0]));raise RuntimeError('No Runtime/Actor')
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):
        forbidden.append(event);raise RuntimeError('No network/child')
    if event=='open' and isinstance(args[0],str) and ('/query-private-' in args[0] or args[0].endswith(('/catalog.json','/association.json'))):
        forbidden.append('PRIVATE_INPUT');raise RuntimeError('Current public query only')
sys.addaudithook(fence)
sys.path.insert(0,a.source_root)
from ainav.contracts import Observation
from ainav.evidence import verify
import numpy as np
from PIL import Image
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(root/'result.json')==a.expected_result_sha
assert sha(root/'events.jsonl')==a.expected_journal_sha
result=json.loads((root/'result.json').read_bytes());chain=verify(root/'events.jsonl')
first=None;interaction=False
for line_number,line in enumerate((root/'events.jsonl').read_text().splitlines(),1):
    record=json.loads(line);row=record['payload']
    if row.get('event')!='intent_native_execution_bound':continue
    intent=row.get('intent',{})
    if intent.get('skill')!='CLIMB' or intent.get('target_ref')!='cuboid-2:upper-entry':continue
    if row['execution_role']=='interaction':interaction=True
    if row['execution_role']=='preparation' and first is None:first=(line_number,record)
out=dict(at=dt.datetime.now().astimezone().isoformat(),role='DEV_AUDIT_ONLY_NOT_TRAIN_OR_ONLINE',
    run_root=str(root),scope_id=result['scope_id'],program_sha256=result['program_sha256'],
    result_sha256=a.expected_result_sha,journal_sha256=a.expected_journal_sha,journal_chain=chain,
    source_status=result['status'],first_PREPARE=None,
    status='NO_PREPARE_BOUNDARY_ALREADY_READY' if interaction and first is None else 'PREPARE_NOT_REACHED_OR_BOUNDARY_NOT_RECORDED',
    runtime_or_capture_or_fit_calls=0,forbidden_attempts=forbidden)
if first is not None:
    line_number,record=first;event=record['payload'];matches=[]
    for path in root.glob('intent-observation-*.json'):
        assert not path.is_symlink()
        value=json.loads(path.read_bytes());obs=Observation.create(value)
        if obs.sha256==event['physical_observation_sha256']:matches.append((path,value))
    if len(matches)!=1:
        out['status']='UNKNOWN_NONUNIQUE_OR_MISSING_ACTUAL_QUERY';out['matching_public_queries']=len(matches)
    else:
        path,value=matches[0];rgb=Path(value['rgb']['path']).resolve()
        assert rgb.is_relative_to(root) and not rgb.is_symlink() and sha(rgb)==value['rgb']['sha256']
        depth_path=rgb.parent/'depth_m.npy';cal_path=rgb.parent/'calibration.json'
        assert not depth_path.is_symlink() and not cal_path.is_symlink()
        calibration=json.loads(cal_path.read_bytes())
        assert value['time_s']==value['rgb']['time_s']==calibration['acquisition_time_s']
        with Image.open(rgb) as im:
            assert im.mode=='RGB';pixels=np.asarray(im).copy()
        depth=np.load(depth_path,allow_pickle=False);assert depth.shape==(*pixels.shape[:2],1)
        layouts={'q':18,'dq':18,'gravity':3,'angular_velocity':3,'linear_velocity':3}
        vectors={k:value['public_state'][k] for k in layouts}
        assert all(len(vectors[k])==n and np.isfinite(vectors[k]).all() for k,n in layouts.items())
        array_info=lambda x:dict(shape=list(x.shape),dtype=x.dtype.str,raw_array_bytes_sha256=hashlib.sha256(x.tobytes()).hexdigest())
        out.update(status='ACTUAL_FIRST_CLIMB_PREPARE_PUBLIC_QUERY_BOUND',first_PREPARE=dict(
            journal_line_1based=line_number,journal_record_sha256=record['sha256'],intent_sha256=event['intent_sha256'],
            physical_observation_sha256=event['physical_observation_sha256'],actual_query_path=str(path),actual_query_file_sha256=sha(path),
            query_time_s=value['time_s'],acquisition_age_s=value['time_s']-value['rgb']['time_s'],
            public45D_vectors=vectors,RGB_file=str(rgb),RGB_encoded_sha256=sha(rgb),RGB_decoded=array_info(pixels),
            depth_file=str(depth_path),depth_file_sha256=sha(depth_path),depth_array=array_info(depth),
            calibration_file=str(cal_path),calibration_file_sha256=sha(cal_path),
            camera_K=calibration['camera_K'],T_base_optical=calibration['T_base_optical'],
            array_hash_is_byte_identity_not_numeric_equality_proof=True,private_association_not_followed=True,
            public_objects_native_filter_conditioned=True,component_estimate_not_yet_computed=True))
assert sha(root/'result.json')==a.expected_result_sha and sha(root/'events.jsonl')==a.expected_journal_sha
assert not forbidden
with output.open('x') as stream:json.dump(out,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps(dict(status=out['status'],scope_id=out['scope_id'],time_s=None if out['first_PREPARE'] is None else out['first_PREPARE']['query_time_s'],old_frame_number_or_nearest_selection_used=False)))
