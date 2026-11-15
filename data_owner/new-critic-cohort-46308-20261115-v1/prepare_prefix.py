"""Preconstruction source/config checks for ONE original full1 native prefix condition.
No simulator/Host/Actor constructor, dispatch, state edit or permission grant.
"""
from pathlib import Path
import copy,hashlib,importlib,json,sys
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='new-critic-cohort-46308-20261115-v1'
ENVIRONMENT=Path('/mnt/yuanyue/data-team/env-native-v1');SDK_ROOT=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle')
W=B/'workers'/N;A=W/'inputs/AINav';SOURCE=A/'common-source';QUESTION=W/'inputs/new-cohort'
SOURCE_RELEASE='bc03afc0a3bdc7964546edac8d1de89ed8e354ee9b5d4c01f3fee90449f35f17'
SOURCE_FORK='f1d1d68ca78b5fa189928c1dc78f86adcd5d4093395e2abee45cb7833f36cecf'
IDS=('new_critic_01_full4_left_original', 'new_critic_02_full4_right_original', 'new_critic_03_full4_left_lateral_plus_0p04', 'new_critic_04_full4_right_lateral_plus_0p04', 'new_critic_05_full4_left_lateral_minus_0p04', 'new_critic_06_full4_right_lateral_minus_0p04', 'new_critic_07_full1_left_original', 'new_critic_08_full1_left_lateral_plus_0p04', 'new_critic_09_full1_left_lateral_minus_0p04', 'new_critic_10_full2_left_original', 'new_critic_11_full2_left_lateral_plus_0p04', 'new_critic_12_full2_left_lateral_minus_0p04')
SCOPES={'new_critic_01_full4_left_original': 'data-46308-new-critic-01-full4-left-original-20261115-v1', 'new_critic_02_full4_right_original': 'data-46308-new-critic-02-full4-right-original-20261115-v1', 'new_critic_03_full4_left_lateral_plus_0p04': 'data-46308-new-critic-03-full4-left-lateral_plus_0p04-20261115-v1', 'new_critic_04_full4_right_lateral_plus_0p04': 'data-46308-new-critic-04-full4-right-lateral_plus_0p04-20261115-v1', 'new_critic_05_full4_left_lateral_minus_0p04': 'data-46308-new-critic-05-full4-left-lateral_minus_0p04-20261115-v1', 'new_critic_06_full4_right_lateral_minus_0p04': 'data-46308-new-critic-06-full4-right-lateral_minus_0p04-20261115-v1', 'new_critic_07_full1_left_original': 'data-46308-new-critic-07-full1-left-original-20261115-v1', 'new_critic_08_full1_left_lateral_plus_0p04': 'data-46308-new-critic-08-full1-left-lateral_plus_0p04-20261115-v1', 'new_critic_09_full1_left_lateral_minus_0p04': 'data-46308-new-critic-09-full1-left-lateral_minus_0p04-20261115-v1', 'new_critic_10_full2_left_original': 'data-46308-new-critic-10-full2-left-original-20261115-v1', 'new_critic_11_full2_left_lateral_plus_0p04': 'data-46308-new-critic-11-full2-left-lateral_plus_0p04-20261115-v1', 'new_critic_12_full2_left_lateral_minus_0p04': 'data-46308-new-critic-12-full2-left-lateral_minus_0p04-20261115-v1'}
PROTOCOL_SHA='2f82530d1f880892c631c7b62cc79bfbd72d57e1b369faf99f542d02d4a53eda'
def need(ok,message):
    if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load_package(package=A):
    need(Path(package).resolve()==A,'Exact new owned FOUR-delta source, never old worker')
    need(sha(A/'DATA_PREFIX_RELEASE.json')==SOURCE_RELEASE,'New owned input release drift')
    release=json.loads((A/'DATA_PREFIX_RELEASE.json').read_bytes())
    for rel,pin in release['files_sha256'].items():
        p=W/'inputs'/rel
        need(not Path(rel).is_absolute() and '..' not in Path(rel).parts and not p.is_symlink() and p.resolve().is_relative_to(W/'inputs') and sha(p)==pin,'Prefix input drift: '+rel)
    need(sha(A/'DATA_PREFIX_FOUR_DELTA_MANIFEST.json')==SOURCE_FORK,'Explicit four-delta source identity')
    sys.path.insert(0,str(A));consumer=importlib.import_module('explicit_preparation_consumer')
    need(Path(consumer.__file__).resolve()==A/'explicit_preparation_consumer.py','Fresh owned consumer namespace')
    source=consumer.verify_reference(SOURCE)
    return consumer,source,release

def protocol():
    need(sha(QUESTION/'FINITE_COHORT_PROTOCOL.json')==PROTOCOL_SHA,'Exact future NEW-use protocol, not prior DEV role rewrite')
    return json.loads((QUESTION/'FINITE_COHORT_PROTOCOL.json').read_bytes())
def conditions():
    v=json.loads((QUESTION/'FIXED_ACQUISITIONS.json').read_bytes());p=protocol()
    need(v['protocol_file_sha256']==PROTOCOL_SHA and tuple(c['condition_id']for c in v['conditions'])==IDS and v['new_main_upper_bound']==12 and len(IDS)==12,'Exactly predeclared12 new roots; staged TRAIN gate before CAL/VAL')
    for c,r in zip(v['conditions'],p['attempt_schedule']):
        need(all(c[k]==r[k]for k in r if k!='scope_id') and r['scope_id']is None and r['physical_program_sha256']is None and c['scope_id']==SCOPES[c['condition_id']],'Exact registered acquisition ordinal/candidate/source/role')
    return v['conditions']

def make_planner(types,requests,journal):
    need(any(requests==c['requested_intents'] for c in conditions()),'Exact predeclared NAV/PUSH/CLIMB sequence')
    need(types.source==SOURCE,'Exact new source types')
    planner=types.RequestedPlanner(copy.deepcopy(requests),journal,max_requests=3)
    need(len(planner.requests)==3 and planner.index==0 and planner.pending is None and not planner.complete,'Fresh explicitly opt-in3 planner')
    return planner

def build_plan(condition_id):
    need(condition_id in IDS,'Only the two fixed native prefix references; no arbitrary XY/seed')
    consumer,source,release=load_package();types=consumer.load_original_types(source)
    from mujoco_zyh import integrated_course as integrated
    from ainav.deployment import HostProfile
    p=protocol();condition=next(c for c in conditions()if c['condition_id']==condition_id);scene=next(r for r in p['scenes']if r['source_scene_sha256']==condition['source_scene_sha256']);co=next(r for r in p['conditions']if r['condition_key']==condition['condition_key'])
    need(digest(scene['scene_key_canonical_payload'])==scene['source_scene_sha256'] and digest(co['condition_binding_payload'])==co['condition_binding_sha256'],'Reach fixed canonical whole-scene/condition domain keys; not episode IDs')
    if condition['layout_id'] in ('full-4','full-2'):
        import climb_preparation_candidates as candidates
        helper=W/'inputs/g2-question/registered_layout_conditions.py';need(sha(helper)=='458ec66e0e65e573c7e98a91e8c496b0ad8449ebcaec686e6ff338486010dcff','Unchanged source-owner finite layout helper')
        sys.path.insert(0,str(helper.parent));import registered_layout_conditions as layout_api
        bound=layout_api.build_condition(selection=layout_api.LayoutCondition(condition['layout_id'],condition['prefix_side'],condition['candidate_id']),source_root=source,integrated=integrated,host_profile=HostProfile('Data-NEW-purpose-finite-critic-cohort',str(R),'cuda:0',0,True),candidate_api=candidates,enabled=True)
        original=bound['original_native_protocol'];cfg=bound['runtime_config'];need(bound['requested_intents']==condition['requested_intents'] and bound['preparation_payload']==condition['preparation_payload'],'Exact source helper public task/candidate payload')
    else:
        need(condition['layout_id']=='full-1'and condition['prefix_side']=='left','Only registered independent full1-left source; never loosen full2 material guard')
        original=integrated.protocol(next(c for c in integrated.plan()['cases']if c['case_id']=='full-1'));integrated.validate_protocol(original)
        need(digest(original)=='7492762cbb1b3a268d5a2a7d4d148956a32d4a675e83e1a29bf7099d60e13d55','Exact already qualified full1 protocol including1kg/mu.3 original C')
        cfg=HostProfile('Data-NEW-purpose-finite-critic-cohort',str(R),'cuda:0',0,True).runtime_config(original)
        old_question=json.loads((W/'inputs/full1-question/NEXT_THIRD_SCENE_FULL1_SOURCE_OPTION_NOT_QUEUED.json').read_bytes());need(old_question['requested_intents']==condition['requested_intents'],'Exact qualified independent full1 caller request floats')
    delta={k:dict(original=original.get(k),actual=cfg.get(k))for k in set(original)|set(cfg)if original.get(k)!=cfg.get(k)}
    need(set(delta)=={'actor_device'}and cfg['actor_device']=='cuda:0'and cfg['seed']==4301,'Original physical protocol only GPU device overlay, no training/goal/seed alteration')
    need(digest(original)==scene['original_native_protocol_sha256_canonical'],'Selected actual original protocol matches new-use scene role')
    payload=scene['scene_key_canonical_payload'];need(all(payload[k]==original[k]for k in ('integrated_case','registered_materials','scene_recipe','seed','initialization'))and payload['constructor_source_sha256']==sha(source/'mujoco_zyh/integrated_course.py'),'Actual whole scene source/config mapping, not label split')
    need(co['requested_intents']==condition['requested_intents']and condition['preparation_payload']['candidate_id']==condition['candidate_id'],'Fixed role/source/arm/request binding')
    from climb_preparation_candidates import selection_from_payload
    selected=selection_from_payload(condition['preparation_payload']);need(selected.candidate_id==condition['candidate_id'],'Exact existing public finite preparation API')
    rows=[];planner=make_planner(types,condition['requested_intents'],rows.append);need(not rows,'No software receipt fabrication')
    manifest=SDK_ROOT/'MANIFEST.json';sdk=json.loads(manifest.read_bytes())
    return dict(schema='Data-new-preregistered-finite-critic-acquisition-preconstruction-v1',candidate_id=condition_id,condition_id=condition_id,
      scope_id=SCOPES[condition_id],stage='NEW_PREREGISTERED_HIGH_LEVEL_SUCCESSOR_CRITIC_COLLECTION',data_purpose=p['data_purpose'],split=condition['split'],source_scene_sha256=condition['source_scene_sha256'],scene_ancestry_key=scene['scene_ancestry_key'],condition_binding_sha256=condition['condition_binding_sha256'],new_use_protocol_file_sha256=PROTOCOL_SHA,ordinal=condition['ordinal'],attempt_key=condition['attempt_key'],source_scene_case_id=condition['layout_id'],public_preparation_candidate_id=condition['candidate_id'],source_owner_release_sha256=SOURCE_RELEASE,
      source_manifest_sha256='314b6650918cbf88c6bd7166ad3f2d26f9c3b30f92094db98d6f8832f8d1fd8c',baseline_release_sha256='3098297041dbfa50dd1928ee81ce28c68d3458ed544cc494dea7374177b7c49e',
      current_source_fork_manifest_sha256=SOURCE_FORK,original_native_protocol=original,runtime_config=cfg,native_config_delta=delta,
      requested_intents=copy.deepcopy(condition['requested_intents']),planner_capacity=3,terminal_exact_successful_semantic_requests=3,
      selected_host=types.Host.__module__+'.'+types.Host.__name__,SDK_manifest_sha256=sha(manifest),actor_sha256=sdk['actor_sha256'],seed=cfg['seed'],
      preparation_payload=copy.deepcopy(condition['preparation_payload']),
      common_stow_binding='V2_ALL_ACTUALLY_LOADED_ALIASES',original_pose_init_and_native_RNG_seed_not_changed=True,
      no_outcome_conditioned_initial_state=True,actual_hidden_state_equivalence_claimed=False,
      condition_observability_at_later_PREPARE_proven=False,qualified_entry_condition_family=False,data_role='NEW_PREREGISTERED_HIGH_LEVEL_SUCCESSOR_CRITIC_'+condition['split'],training_role_is_future_acquisition_not_DEV_conversion=True,
      Runtime_Actor_observer_host_constructed=False,physical_admission=False,dispatch=False,automatic_retry=False,training_allowed=False)

EXPAT_LIBRARY=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1')
EXPAT_LIBRARY_SHA256='c995a80395904d85c4d35f4a185c3bae2fcdc562141dd6106c8ebe29571d33b3'

OPTION_SHA='350df86b133abfb5dc2cced5c8ba820ece542f4086713ea1d57554b5729731fc'
