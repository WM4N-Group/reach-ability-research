"""Prospective bulk24 exact source binding ONLY; no world/Actor/dispatch APIs.
Default verifies immutable code custody and returns no selected condition.
Enabled means pure source/config intake, NOT execution or physical admission.
"""
from pathlib import Path
import json,hashlib,sys,importlib
ROOT=Path(__file__).resolve().parent;A=ROOT/'inputs/AINav';SOURCE=A/'common-source'
CUSTODY_SHA='ba932cda090a84f414c563399e521897ad30e49be961c351d9facdc52a087a1a'
PROTOCOL_SHA='0f9e0e03a4cdf8263b1c69f69db9697968040023f42d4c1f383a320631d9e57e'
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114')
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def verify_custody():
 need(sha(ROOT/'SOURCE_CUSTODY.json')==CUSTODY_SHA,'Exact new source/verifier custody')
 c=json.loads((ROOT/'SOURCE_CUSTODY.json').read_bytes())
 for rel,pin in c['files_sha256'].items():
  p=ROOT/'inputs'/rel;need(not Path(rel).is_absolute()and '..'not in Path(rel).parts and not p.is_symlink()and p.resolve().is_relative_to((ROOT/'inputs').resolve())and sha(p)==pin,'Source custody drift: '+rel)
 need(sha(ROOT/'inputs/BULK24_COLLECTION_PROTOCOL.json')==PROTOCOL_SHA,'Exact Reach prospective 24 row collection protocol')
 return c
def build_all(*,enabled=False):
 need(type(enabled)is bool,'Explicit pure source opt-in, no physical meaning')
 c=verify_custody()
 if not enabled:return None
 need(not any(n in ('ainav','mujoco_zyh','explicit_preparation_consumer')or n.startswith(('ainav.','mujoco_zyh.'))for n in sys.modules),'Fresh one-source interpreter only; never unload or alias another source')
 sys.path[:0]=[str(A),str(SOURCE),str(ROOT/'inputs/bulk-source')]
 consumer=importlib.import_module('explicit_preparation_consumer');need(Path(consumer.__file__).resolve()==A/'explicit_preparation_consumer.py','Exact new five-delta verifier, unchanged original consumer mechanics')
 need(consumer.verify_reference(SOURCE)==SOURCE,'Whole original283 + exact priorfour + explicit plan-only delta')
 from mujoco_zyh import integrated_course as integrated
 from ainav.deployment import HostProfile
 import bulk_registered_conditions as bulk
 import climb_preparation_candidates as candidates
 p=json.loads((ROOT/'inputs/BULK24_COLLECTION_PROTOCOL.json').read_bytes());ancestor=json.loads((ROOT/'inputs/EXISTING_TRAIN_FULL4_ANCESTRY.json').read_bytes());need(ancestor['case_id']=='full-4'and ancestor['split']=='TRAIN'and digest(ancestor['scene_key_canonical_payload'])==ancestor['source_scene_sha256']==ancestor['scene_ancestry_key'],'Original full4 TRAIN whole-scene ancestry, not case-only digest');rows=[]
 need(p['source_owner_commit']==c['source_owner_commit']and len(p['attempt_schedule'])==24 and not p['dispatch']and not p['physical_admission']and not p['current_frozen_critic_refit_allowed'],'Exact24 future collection only; no native/refit gate inferred')
 for ordinal,attempt in enumerate(p['attempt_schedule'],1):
  need(attempt['ordinal']==ordinal and attempt['scope_id']is None and attempt['physical_program_sha256']is None and attempt['own_zero_max']==attempt['main_max']==1,'No scope allocation/physical claim during pure source binding')
  scene=next(x for x in p['scenes']if x['source_scene_sha256']==attempt['source_scene_sha256']);condition=next(x for x in p['conditions']if x['condition_key']==attempt['condition_key'])
  need(digest(scene['scene_key_canonical_payload'])==scene['source_scene_sha256']and digest(condition['condition_binding_payload'])==condition['condition_binding_sha256'],'Exact canonical whole scene and request context')
  bound=bulk.build_condition(selection=bulk.BulkCondition(attempt['group_id'],attempt['prefix_side'],attempt['candidate_id']),source_root=SOURCE,integrated=integrated,host_profile=HostProfile('Data-prospective-bulk24-GPU1',str(R),'cuda:0',1,True),candidate_api=candidates,enabled=True)
  need(bound['requested_intents']==condition['requested_intents']and bound['preparation_payload']==attempt['preparation_payload'],'Actual owner source API must match Reach exact prospective request floats and actual prep binder payload')
  original=bound['original_native_protocol'];cfg=bound['runtime_config']
  need(digest(original)==scene['original_native_protocol_sha256_canonical'],'Actual unmodified original protocol/validator must match Reach original pure source protocol binding')
  need({k for k in set(original)|set(cfg)if original.get(k)!=cfg.get(k)}=={'actor_device'}and cfg['actor_device']=='cuda:0'and cfg['seed']==4301,'Only original device overlay; no material/seed/initial pose/control change')
  need(bound['ancestor_case_canonical_sha256']==digest(ancestor['scene_key_canonical_payload']['integrated_case'])and scene['scene_ancestry_key']==ancestor['scene_ancestry_key']and scene['same_existing_TRAIN_ancestor']and attempt['split']==scene['split']=='TRAIN','One existing TRAIN ancestry; not independent TEST or refit')
  rows.append(dict(ordinal=ordinal,attempt_key=attempt['attempt_key'],group_id=attempt['group_id'],condition_key=attempt['condition_key'],candidate_id=attempt['candidate_id'],source_scene_sha256=scene['source_scene_sha256'],scene_ancestry_key=scene['scene_ancestry_key'],source_case_only_ancestry_sha256=bound['ancestor_case_canonical_sha256'],case_hash_is_not_whole_scene_hash=True,condition_binding_sha256=condition['condition_binding_sha256'],original_native_protocol_sha256_canonical=digest(original),runtime_config=cfg,requested_intents=bound['requested_intents'],preparation_payload=bound['preparation_payload'],planner_capacity=3,terminal_exact_successful_semantic_requests=3,scope_id=None,physical_program_sha256=None,physical_admission=False,source_dynamic_domain_qualified=False))
 need(len({r['attempt_key']for r in rows})==24 and len({r['source_scene_sha256']for r in rows})==4 and len({r['condition_key']for r in rows})==8 and len({r['scene_ancestry_key']for r in rows})==1,'24 fixedattempts/4geometries/8contexts/one TRAINancestor, not independent scenes')
 return dict(schema='Data-bulk24-actual-pure-source-binding-v1',purpose='NEW_PREREGISTERED_HIGH_LEVEL_SUCCESSOR_CRITIC_COLLECTION_PROSPECTIVE_ONLY',protocol_sha256=PROTOCOL_SHA,source_custody_sha256=CUSTODY_SHA,source_owner_commit=c['source_owner_commit'],rows=rows,all24_exact_original_protocol_and_requests_verified=True,old_TRAIN6_CAL_VAL_and_T_observation_scope_unchanged=True,scope_allocated=False,physical_program_frozen=False,zero_dispatch_count=0,main_dispatch_count=0,critic_refit_allowed=False,not_source_fixture_rerun_or_research_samples=True)
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--enable-pure-source-binding',action='store_true');args=ap.parse_args()
 forbidden=[]
 def fence(event,args):
  if event=='import'and str(args[0]).split('.')[0]in ('torch','mujoco','onnxruntime'):
   forbidden.append(str(args[0]));raise RuntimeError('Pure source binding forbids native/Actor imports')
  if event in ('socket.connect','subprocess.Popen'):
   forbidden.append(event);raise RuntimeError('No network or child/native launcher')
 sys.addaudithook(fence);v=build_all(enabled=args.enable_pure_source_binding);need(not forbidden,'No attempted native/Actor import')
 print(json.dumps(v if v is not None else dict(default_off=True,source_custody_verified=True,conditions_built=False,new_physical_calls=0),ensure_ascii=False))
