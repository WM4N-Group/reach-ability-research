"""Preconstruction source/config checks for ONE original full1 native prefix condition.
No simulator/Host/Actor constructor, dispatch, state edit or permission grant.
"""
from pathlib import Path
import copy,hashlib,importlib,json,sys
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='g2-full1-46308-20261115-v1'
ENVIRONMENT=Path('/mnt/yuanyue/data-team/env-native-v1');SDK_ROOT=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle')
W=B/'workers'/N;A=W/'inputs/AINav';SOURCE=A/'common-source';QUESTION=W/'inputs/full1-question'
SOURCE_RELEASE='bc03afc0a3bdc7964546edac8d1de89ed8e354ee9b5d4c01f3fee90449f35f17'
SOURCE_FORK='f1d1d68ca78b5fa189928c1dc78f86adcd5d4093395e2abee45cb7833f36cecf'
IDS=('g2_full1_native_NAV_prefix_left',)
SCOPES={c:'data-46308-G2-full1-'+c.rsplit('_',1)[1]+'-PUSH-CLIMB-20261115-v1' for c in IDS}
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

def conditions():
    v=json.loads((QUESTION/'FIXED_TWO_CONDITIONS.json').read_bytes())
    need(tuple(c['condition_id'] for c in v['conditions'])==IDS and v['new_main_upper_bound']==1 and v['per_condition_main_attempts']==1,'Exactly original full1 left only, no repetition or expansion')
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
    option=json.loads((QUESTION/'NEXT_THIRD_SCENE_FULL1_SOURCE_OPTION_NOT_QUEUED.json').read_bytes())
    need(sha(QUESTION/'NEXT_THIRD_SCENE_FULL1_SOURCE_OPTION_NOT_QUEUED.json')==OPTION_SHA,'Exact separately declared full1 source, never expand full2 helper')
    condition=next(c for c in conditions() if c['condition_id']==condition_id)
    original=integrated.protocol(next(c for c in integrated.plan()['cases'] if c['case_id']=='full-1'));integrated.validate_protocol(original)
    need(digest(original)=='7492762cbb1b3a268d5a2a7d4d148956a32d4a675e83e1a29bf7099d60e13d55','Exact ORIGINAL full1 protocol including registered materials, no material guard bypass')
    need(original['registered_materials']=={'A_bottom_mu':.15,'B_bottom_mu':.4,'C_bottom_mu':.3,'C_mass_kg':1.,'box_foot_mu':.8}and option['registered_materials']==original['registered_materials'],'Explicit multi-factor source, not full2 same-material condition family')
    need(option['requested_intents']==condition['requested_intents'] and condition['prefix_side']=='left','Exactly source-owner full1-left original references and float goals')
    cfg=HostProfile('Data-G2-original-full1-left-new-source-qualification',str(R),'cuda:0',0,True).runtime_config(original)
    delta={k:dict(original=original.get(k),actual=cfg.get(k)) for k in set(original)|set(cfg) if original.get(k)!=cfg.get(k)}
    need(set(delta)=={'actor_device'}and cfg['actor_device']=='cuda:0'and cfg['seed']==4301,'Device-only overlay of exact original full1/init/4301')
    rows=[];planner=make_planner(types,condition['requested_intents'],rows.append);need(not rows,'No software receipt fabrication')
    manifest=SDK_ROOT/'MANIFEST.json';sdk=json.loads(manifest.read_bytes())
    return dict(schema='Data-new-SINGLE-full1-native-prefix-preconstruction-NOT-AUTHORIZATION-v1',candidate_id=condition_id,condition_id=condition_id,
      scope_id=SCOPES[condition_id],stage='G2_REGISTERED_FULL1_SCENE_QUALIFICATION',registered_layout_source_sha256=OPTION_SHA,source_scene_case_id='full-1',explicit_registered_C_material_change=True,full2_helper_not_modified_or_used_for_full1=True,cross_registered_layout_qualification_not_pure_prefix_causal_contrast=True,source_owner_release_sha256=SOURCE_RELEASE,
      source_manifest_sha256='314b6650918cbf88c6bd7166ad3f2d26f9c3b30f92094db98d6f8832f8d1fd8c',baseline_release_sha256='3098297041dbfa50dd1928ee81ce28c68d3458ed544cc494dea7374177b7c49e',
      current_source_fork_manifest_sha256=SOURCE_FORK,original_native_protocol=original,runtime_config=cfg,native_config_delta=delta,
      requested_intents=copy.deepcopy(condition['requested_intents']),planner_capacity=3,terminal_exact_successful_semantic_requests=3,
      selected_host=types.Host.__module__+'.'+types.Host.__name__,SDK_manifest_sha256=sha(manifest),actor_sha256=sdk['actor_sha256'],seed=cfg['seed'],
      preparation_payload=dict(schema='AINav-finite-CLIMB-preparation-selection-v1',target_ref='cuboid-2:upper-entry',candidate_id='original'),
      common_stow_binding='V2_ALL_ACTUALLY_LOADED_ALIASES',original_pose_init_and_native_RNG_seed_not_changed=True,
      no_outcome_conditioned_initial_state=True,actual_hidden_state_equivalence_claimed=False,
      condition_observability_at_later_PREPARE_proven=False,qualified_entry_condition_family=False,data_role='NEW_DEV_AUDIT_ONLY',
      Runtime_Actor_observer_host_constructed=False,physical_admission=False,dispatch=False,automatic_retry=False,training_allowed=False)

EXPAT_LIBRARY=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1')
EXPAT_LIBRARY_SHA256='c995a80395904d85c4d35f4a185c3bae2fcdc562141dd6106c8ebe29571d33b3'

OPTION_SHA='350df86b133abfb5dc2cced5c8ba820ece542f4086713ea1d57554b5729731fc'
