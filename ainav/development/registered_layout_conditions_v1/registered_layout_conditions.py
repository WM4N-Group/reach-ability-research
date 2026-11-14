"""Finite ORIGINAL registered-layout request source for prospective G2 design.

Pure preconstruction only: reuses original protocol validator and public finite
candidate API. Does not construct a runtime, allocate scopes, fit data or dispatch.
"""
from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
import hashlib,inspect

LAYOUTS=('full-4','full-2')
SIDES=('left','right','center','upper-entry')
PREFIXES_BY_LAYOUT={'full-4':SIDES,'full-2':('left','right')}
CANDIDATES=('original','lateral_plus_0p04','lateral_minus_0p04')
PINS={
 'mujoco_zyh/integrated_course.py':'4f95873e1b34b5778c28b18711e0461d18ab7f13d3e31b547f93b901e593a6fb',
 'mujoco_zyh/integrated_course_plan_v1.json':'3449b3744ff46c7d0c99237303eca96aca5b72edcda6873a33e287272f19c842',
 'mujoco_zyh/reselect_B_recorded_protocol_v2.json':'a37bdbb90b35a83a3cf1ea558c065ac6ea0f89b13103ffab9a632079e67d4b46',
 'ainav/native/full_course.py':'a1033e74482a04a5232d775b6f24bfd52f889d8b2876a5a8ef908d0b6d769327',
 'ainav/deployment.py':'b651fa5bbfc961db01ea09adc58e8b6b931722871524102d4a4c0358e3537200'}
CANDIDATE_SHA='1c40a748bd1d93e3684853b60f2dc038e673f019976d60cf33eb8195ff9942d0'

def need(ok,message):
 if not ok:raise ValueError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

@dataclass(frozen=True)
class LayoutCondition:
 layout_id:str
 prefix_side:str
 candidate_id:str='original'
 def __post_init__(self):
  need(type(self.layout_id) is str and self.layout_id in LAYOUTS,'Exact registered full-4/full-2, not arbitrary scene floats')
  need(type(self.prefix_side) is str and self.prefix_side in PREFIXES_BY_LAYOUT[self.layout_id],'Original prefix explicitly registered for this selected layout')
  need(type(self.candidate_id) is str and self.candidate_id in CANDIDATES,'Original finite CLIMB preparation candidate, not a continuous control')

def build_condition(*,selection=None,source_root=None,integrated=None,host_profile=None,candidate_api=None,enabled=False):
 """Map one explicit named condition to the EXISTING caller fields.

 Default-off reads no source/module. Enabled still produces no native permit.
 The caller must consume returned original_native_protocol/runtime_config,
 requested_intents and preparation_payload in its NEW exact frozen program.
 """
 need(type(enabled) is bool,'Explicit default-off flag')
 if not enabled:return None
 need(type(selection) is LayoutCondition,'Immutable exact source selection')
 root=Path(source_root).resolve(strict=True)
 for rel,h in PINS.items():
  path=root/rel;need(not path.is_symlink() and path.resolve().is_relative_to(root) and sha(path)==h,'Pinned registered source mismatch: '+rel)
 need(Path(integrated.__file__).resolve()==root/'mujoco_zyh/integrated_course.py','Original same-source integrated module only')
 for name in ('plan','protocol','validate_protocol','layout'):
  fn=getattr(integrated,name,None)
  need(callable(fn) and Path(fn.__code__.co_filename).resolve()==root/'mujoco_zyh/integrated_course.py' and fn.__globals__ is vars(integrated),'Original callable namespace: '+name)
 need(Path(inspect.getsourcefile(type(host_profile))).resolve()==root/'ainav/deployment.py','Original same-source HostProfile, not controller/config shim')
 cp=root.parent/'climb_preparation_candidates.py'
 need(Path(candidate_api.__file__).resolve()==cp and sha(cp)==CANDIDATE_SHA,'Stable original finite candidate API source')
 rows=[c for c in integrated.plan()['cases'] if c['case_id']==selection.layout_id]
 need(len(rows)==1,'One exact registered original layout')
 case=deepcopy(rows[0]);native=integrated.protocol(case);integrated.validate_protocol(native)
 baseline=integrated.protocol(next(c for c in integrated.plan()['cases'] if c['case_id']=='full-4'))
 need(native['registered_materials']==baseline['registered_materials'] and native['seed']==baseline['seed']==4301,
      'This source experiment varies original geometry, not Actor/materials/seed')
 config=host_profile.runtime_config(native)
 changed={k for k in set(native)|set(config) if native.get(k)!=config.get(k)}
 need(changed=={'actor_device'} and config['actor_device'] in ('cuda:0','cuda:1'),'Original explicit device-only host overlay')
 g=integrated.layout(case);lane=float(case['lane_y_m'])
 # Constants below are the EXACT pinned FullCourse entity/ref construction:
 # initial_front=.5; source0; side +/- .15; approach front-.58;
 # public dock goal=docked_front+length/2; upper-entry=docked_front-1.05.
 if selection.prefix_side=='upper-entry':
  nav_ref='cuboid-2:upper-entry';nav_xy=(float(g['step_docked_front']-1.05),lane)
 else:
  dy={'left':.15,'right':-.15,'center':0.}[selection.prefix_side]
  nav_ref='cuboid-2:approach:'+selection.prefix_side;nav_xy=(.5-.58,lane+dy)
 requests=[dict(skill='NAV',target_ref=nav_ref,parameters=dict(goal_world_x_m=nav_xy[0],goal_world_y_m=nav_xy[1],surface_height_m=0.)),
  dict(skill='PUSH',target_ref='cuboid-2:approach:center',parameters=dict(goal_world_x_m=float(g['step_docked_front']+case['step_length_m']/2),goal_world_y_m=lane,surface_height_m=0.)),
  dict(skill='CLIMB',target_ref='cuboid-2:upper-entry',parameters=dict(surface_height_m=.2))]
 approach=[float(g['step_docked_front']-1.05),lane]
 candidates=candidate_api.public_candidates(target_ref='cuboid-2:upper-entry',declared_approach_xy=approach,source_surface_height_m=0.,registered_climb=True)
 need(tuple(c['candidate_id'] for c in candidates)==CANDIDATES,'No candidate expansion/reordering')
 payload=dict(schema='AINav-finite-CLIMB-preparation-selection-v1',target_ref='cuboid-2:upper-entry',candidate_id=selection.candidate_id)
 candidate_api.selection_from_payload(payload)
 return dict(layout_id=selection.layout_id,prefix_side=selection.prefix_side,candidate_id=selection.candidate_id,
  original_native_protocol=deepcopy(native),runtime_config=deepcopy(config),requested_intents=deepcopy(requests),
  preparation_payload=payload,public_prepare_candidates=deepcopy(candidates),
  declared_CLIMB_reference_xy=approach,planner_constructor_keyword=dict(max_requests=3),
  source_grouping_or_training_roles_assigned=False,qualified_dynamic_domain=False,
  scope_allocated=False,physical_admission=False,dispatch=False,
  source_note='Named original geometry only; actual source caller/G2 use/ancestor grouping/own-zero still required. Not an independent group or learning certificate.')
