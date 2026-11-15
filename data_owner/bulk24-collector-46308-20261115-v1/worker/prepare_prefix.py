"""New bulk24 caller binding, original types/config only; no constructors/dispatch.
All24 source geometries and3 finite preparation payloads come from the exact
Reach prospective protocol and source-owned helper, not Data-defined routes.
"""
from pathlib import Path
import json,sys,hashlib,copy,importlib
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='bulk24-collector-46308-20261115-v1';W=B/'workers'/N
ENVIRONMENT=Path('/mnt/yuanyue/data-team/env-native-v1');SDK_ROOT=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle')
D=B/'development/bulk24-preconstruction-46308-20261115-v1';A=D/'inputs/AINav';SOURCE=A/'common-source';QUESTION=D/'inputs'
P=json.loads((W/'protocol.json').read_bytes());IDS=tuple(P['order']);SCOPES=P['scopes'];PROTOCOL_SHA=P['Reach_protocol_sha256'];SOURCE_FORK=P['source_custody_sha256'];SOURCE_RELEASE=hashlib.sha256((D/'inputs/BULK_SOURCE_OWNER_RECORD.json').read_bytes()).hexdigest()
EXPAT_LIBRARY=R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1';EXPAT_LIBRARY_SHA256='c995a80395904d85c4d35f4a185c3bae2fcdc562141dd6106c8ebe29571d33b3'
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load_package(package=A):
 need(Path(package).resolve()==A and sha(D/'SOURCE_CUSTODY.json')==SOURCE_FORK,'Exact new bulk source snapshot, never old cohort source')
 sys.path[:0]=[str(D),str(A),str(SOURCE)]
 import prepare_bulk24 as intake
 need(Path(intake.__file__).resolve()==D/'prepare_bulk24.py','Exact new preconstruction input verifier')
 custody=intake.verify_custody();consumer=importlib.import_module('explicit_preparation_consumer')
 need(Path(consumer.__file__).resolve()==A/'explicit_preparation_consumer.py','Fresh exact own new five-delta metadata verifier, no mixed tree')
 source=consumer.verify_reference(SOURCE);return consumer,source,custody
def conditions():
 need(sha(QUESTION/'BULK24_COLLECTION_PROTOCOL.json')==PROTOCOL_SHA,'Exact Reach prospective24 collection scope')
 protocol=json.loads((QUESTION/'BULK24_COLLECTION_PROTOCOL.json').read_bytes());need(tuple(r['attempt_key']for r in protocol['attempt_schedule'])==IDS and len(IDS)==24,'Exact pre-outcome24 order, no extension or replacement')
 return protocol['attempt_schedule']
def make_planner(types,requests,journal):
 p=json.loads((QUESTION/'BULK24_COLLECTION_PROTOCOL.json').read_bytes());need(any(requests==c['requested_intents']for c in p['conditions']),'Only actual source-bound fixed request floats')
 need(types.source==SOURCE and len(requests)==3,'Same original3 semantic requests, not native preparation count')
 return types.RequestedPlanner(copy.deepcopy(requests),journal,max_requests=3)
def build_plan(condition_id):
 need(condition_id in IDS,'Exact fixed bulk24 acquisition only; no arbitrary group/seed')
 need(not any(n in('ainav','mujoco_zyh')or n.startswith(('ainav.','mujoco_zyh.'))for n in sys.modules),'Fresh same-source worker process only')
 sys.path.insert(0,str(D));import prepare_bulk24 as intake
 bound=intake.build_all(enabled=True);condition=next(r for r in bound['rows']if r['attempt_key']==condition_id);attempt=next(r for r in conditions()if r['attempt_key']==condition_id);consumer,source,custody=load_package();types=consumer.load_original_types(source)
 from mujoco_zyh import integrated_course as integrated
 from ainav.deployment import HostProfile
 sys.path.insert(0,str(D/'inputs/bulk-source'));import bulk_registered_conditions as bulk
 import climb_preparation_candidates as candidates
 actual=bulk.build_condition(selection=bulk.BulkCondition(attempt['group_id'],attempt['prefix_side'],attempt['candidate_id']),source_root=source,integrated=integrated,host_profile=HostProfile('Data-bulk24-GPU1',str(R),'cuda:0',1,True),candidate_api=candidates,enabled=True)
 original=actual['original_native_protocol'];cfg=actual['runtime_config'];need(digest(original)==condition['original_native_protocol_sha256_canonical'] and cfg==condition['runtime_config']and actual['requested_intents']==condition['requested_intents']and actual['preparation_payload']==condition['preparation_payload'],'Exact actual original code/config/helper consumption, no fallback')
 delta={k:dict(original=original.get(k),actual=cfg.get(k))for k in set(original)|set(cfg)if original.get(k)!=cfg.get(k)};need(set(delta)=={'actor_device'}and cfg['actor_device']=='cuda:0'and cfg['seed']==4301,'Original runtime only device overlay')
 rows=[];planner=make_planner(types,actual['requested_intents'],rows.append);need(not rows and not planner.complete and planner.index==0,'No fake receipts during prepare')
 sdk=json.loads((SDK_ROOT/'MANIFEST.json').read_bytes())
 return dict(schema='Data-bulk24-new-preregistered-acquisition-preconstruction-v1',candidate_id=condition_id,condition_id=condition_id,scope_id=SCOPES[condition_id],stage='NEW_PREREGISTERED_HIGH_LEVEL_SUCCESSOR_CRITIC_COLLECTION',data_purpose=P['purpose'],split='TRAIN',source_scene_sha256=condition['source_scene_sha256'],scene_ancestry_key=condition['scene_ancestry_key'],condition_binding_sha256=condition['condition_binding_sha256'],new_use_protocol_file_sha256=PROTOCOL_SHA,ordinal=attempt['ordinal'],attempt_key=condition_id,source_scene_case_id=actual['layout_id'],public_preparation_candidate_id=attempt['candidate_id'],source_owner_release_sha256=SOURCE_RELEASE,source_owner_release_field_is_code_source_receipt_not_native_qualification=True,source_manifest_sha256='314b6650918cbf88c6bd7166ad3f2d26f9c3b30f92094db98d6f8832f8d1fd8c',baseline_release_sha256='3098297041dbfa50dd1928ee81ce28c68d3458ed544cc494dea7374177b7c49e',current_source_fork_manifest_sha256=SOURCE_FORK,original_native_protocol=original,runtime_config=cfg,native_config_delta=delta,requested_intents=copy.deepcopy(actual['requested_intents']),planner_capacity=3,terminal_exact_successful_semantic_requests=3,selected_host=types.Host.__module__+'.'+types.Host.__name__,SDK_manifest_sha256=sha(SDK_ROOT/'MANIFEST.json'),actor_sha256=sdk['actor_sha256'],seed=4301,preparation_payload=copy.deepcopy(actual['preparation_payload']),common_stow_binding='V2_ALL_ACTUALLY_LOADED_ALIASES',original_pose_init_and_native_RNG_seed_not_changed=True,no_outcome_conditioned_initial_state=True,actual_hidden_state_equivalence_claimed=False,condition_observability_at_later_PREPARE_proven=False,qualified_entry_condition_family=False,data_role='NEW_PREREGISTERED_HIGH_LEVEL_SUCCESSOR_CRITIC_TRAIN',training_role_is_future_acquisition_not_DEV_conversion=True,Runtime_Actor_observer_host_constructed=False,physical_admission=False,dispatch=False,automatic_retry=False,training_allowed=False,current_critic_refit_allowed=False)
