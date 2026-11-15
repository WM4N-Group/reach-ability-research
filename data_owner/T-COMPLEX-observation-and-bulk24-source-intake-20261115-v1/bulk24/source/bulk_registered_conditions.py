"""Finite lane/step-width source assembly, not a launcher or new controller.

Only a NEW source snapshot may contain the additive plan. Original integrated
code/validator/construction, HostProfile, finite candidates and native gates are
unchanged. There is no code that installs into another owner's source tree.
"""
from pathlib import Path
from dataclasses import dataclass
from copy import deepcopy
import hashlib,inspect,json

OWN=Path(__file__).parent
PINS={
 'mujoco_zyh/integrated_course.py':'4f95873e1b34b5778c28b18711e0461d18ab7f13d3e31b547f93b901e593a6fb',
 'mujoco_zyh/reselect_B_recorded_protocol_v2.json':'a37bdbb90b35a83a3cf1ea558c065ac6ea0f89b13103ffab9a632079e67d4b46',
 'ainav/native/full_course.py':'a1033e74482a04a5232d775b6f24bfd52f889d8b2876a5a8ef908d0b6d769327',
 'ainav/deployment.py':'b651fa5bbfc961db01ea09adc58e8b6b931722871524102d4a4c0358e3537200'}
CANDIDATE_SHA='1c40a748bd1d93e3684853b60f2dc038e673f019976d60cf33eb8195ff9942d0'
GROUPS=tuple(f'bulk-g{i:02d}'for i in range(1,11));PREFIXES=('left','right')
CANDIDATES=('original','lateral_plus_0p04','lateral_minus_0p04')
def need(ok,message):
 if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

@dataclass(frozen=True)
class BulkCondition:
 group_id:str
 prefix_side:str
 candidate_id:str='original'
 def __post_init__(self):
  need(type(self.group_id)is str and self.group_id in GROUPS,'Exact predeclared geometry group')
  need(type(self.prefix_side)is str and self.prefix_side in PREFIXES,'Original two finite prefixes only')
  need(type(self.candidate_id)is str and self.candidate_id in CANDIDATES,'Original preparation candidate only')

def source_delta(*,enabled=False):
 need(type(enabled)is bool,'Explicit opt-in')
 if not enabled:return None
 m=json.loads((OWN/'BULK_MATRIX.json').read_bytes());p=OWN/m['source_delta']['replacement_file']
 need(sha(p)==m['new_plan_sha256'],'Owned finite plan drift')
 return dict(relative_path=m['source_delta']['target'],original_sha256=m['original_plan_sha256'],
  new_sha256=m['new_plan_sha256'],replacement_bytes=p.read_bytes(),
  fresh_source_snapshot_only=True,install_performed=False,physical_admission=False)

def build_condition(*,selection=None,source_root=None,integrated=None,host_profile=None,candidate_api=None,enabled=False):
 need(type(enabled)is bool,'Explicit default-off flag')
 if not enabled:return None
 need(type(selection)is BulkCondition,'Immutable exact finite bulk selection')
 root=Path(source_root).resolve(strict=True);m=json.loads((OWN/'BULK_MATRIX.json').read_bytes());delta=source_delta(enabled=True)
 for rel,h in {**PINS,delta['relative_path']:delta['new_sha256']}.items():
  p=root/rel;need(not p.is_symlink()and p.resolve().is_relative_to(root)and sha(p)==h,'Exact new snapshot source mismatch: '+rel)
 need(Path(integrated.__file__).resolve()==root/'mujoco_zyh/integrated_course.py','Original same-source module')
 need(Path(integrated.PLAN).resolve()==root/delta['relative_path'],'Original plan must read the actual new source snapshot, not another registry')
 for name in ('plan','protocol','validate_protocol','layout'):
  fn=getattr(integrated,name,None)
  need(callable(fn)and Path(fn.__code__.co_filename).resolve()==root/'mujoco_zyh/integrated_course.py'and fn.__globals__ is vars(integrated),'Original integrated callable namespace: '+name)
 need(Path(inspect.getsourcefile(type(host_profile))).resolve()==root/'ainav/deployment.py','Original same-source HostProfile')
 cp=root.parent/'climb_preparation_candidates.py';need(Path(candidate_api.__file__).resolve()==cp and sha(cp)==CANDIDATE_SHA,'Original finite candidate module')
 group=next(g for g in m['groups']if g['group_id']==selection.group_id)
 rows=[c for c in integrated.plan()['cases']if c['case_id']==group['case_id']];need(len(rows)==1 and rows[0]==group['source_case'],'Exact new finite case registry')
 case=deepcopy(rows[0]);base=next(c for c in integrated.plan()['cases']if c['case_id']=='full-4')
 need(set(case)==set(base)and {k for k in base if case[k]!=base[k]}<={'case_id','lane_y_m','step_width_m'},'Only declared lane/width geometry delta')
 native=integrated.protocol(case);integrated.validate_protocol(native)
 baseline=integrated.protocol(base);need(native['registered_materials']==baseline['registered_materials']and native['seed']==baseline['seed']==4301,'Materials/seed/Actor family unchanged')
 config=host_profile.runtime_config(native);need({k for k in set(native)|set(config)if native.get(k)!=config.get(k)}=={'actor_device'}and config['actor_device']in('cuda:0','cuda:1'),'Original device-only overlay')
 g=integrated.layout(case);lane=float(case['lane_y_m']);dy=.15 if selection.prefix_side=='left'else -.15
 requests=[dict(skill='NAV',target_ref='cuboid-2:approach:'+selection.prefix_side,parameters=dict(goal_world_x_m=.5-.58,goal_world_y_m=lane+dy,surface_height_m=0.)),
  dict(skill='PUSH',target_ref='cuboid-2:approach:center',parameters=dict(goal_world_x_m=float(g['step_docked_front']+case['step_length_m']/2),goal_world_y_m=lane,surface_height_m=0.)),
  dict(skill='CLIMB',target_ref='cuboid-2:upper-entry',parameters=dict(surface_height_m=.2))]
 approach=[float(g['step_docked_front']-1.05),lane]
 candidates=candidate_api.public_candidates(target_ref='cuboid-2:upper-entry',declared_approach_xy=approach,source_surface_height_m=0.,registered_climb=True)
 need(tuple(c['candidate_id']for c in candidates)==CANDIDATES,'No new or reordered native preparation candidate')
 payload=dict(schema='AINav-finite-CLIMB-preparation-selection-v1',target_ref='cuboid-2:upper-entry',candidate_id=selection.candidate_id);candidate_api.selection_from_payload(payload)
 return dict(group_id=selection.group_id,layout_id=case['case_id'],prefix_side=selection.prefix_side,candidate_id=selection.candidate_id,
  original_native_protocol=deepcopy(native),runtime_config=deepcopy(config),requested_intents=requests,preparation_payload=payload,public_prepare_candidates=deepcopy(candidates),
  planner_constructor_keyword=dict(max_requests=3),terminal_exact_successful_semantic_requests=3,
  ancestor_case_canonical_sha256=m['ancestor_case_canonical_sha256'],shared_ancestor_family=True,
  role='UNASSIGNED_NO_FIT_OR_DISPATCH',source_grouping_or_training_roles_assigned=False,
  qualified_dynamic_domain=False,independent_scene_group_proven=False,scope_allocated=False,physical_admission=False,dispatch=False)
