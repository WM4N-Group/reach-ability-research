"""Pure source intake of AINav next finite option; creates no program/authority/queue."""
from pathlib import Path
import sys,json,hashlib,datetime
x=json.load(sys.stdin);forbidden=[]
def fence(event,args):
 if event=='import'and str(args[0]).split('.')[0]in('torch','mujoco','onnxruntime'):
  forbidden.append(str(args[0]));raise RuntimeError('Source intake: no Actor/native')
 if event in('socket.connect','socket.bind','subprocess.Popen'):raise RuntimeError('Source intake no child/network')
sys.addaudithook(fence)
W=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/workers/g2-full2-46308-20261115-v1');sys.path.insert(0,str(W));import prepare_prefix as prior_source
# Immutable completed worker INPUT source is reused READ ONLY, never its build_plan/authority/launcher.
consumer,source,_=prior_source.load_package();types=consumer.load_original_types(source)
from mujoco_zyh import integrated_course as integrated
from ainav.deployment import HostProfile
option=x['option'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
assert sha(source/'mujoco_zyh/integrated_course.py')==option['original_source_sha256'] and sha(source/'mujoco_zyh/integrated_course_plan_v1.json')==option['original_plan_sha256']
case=next(c for c in integrated.plan()['cases']if c['case_id']=='full-1');protocol=integrated.protocol(case);integrated.validate_protocol(protocol);assert hashlib.sha256(canonical(protocol)).hexdigest()==option['exact_original_protocol_sha256_canonical'];assert case==option['registered_case']and protocol['registered_materials']==option['registered_materials']
profile=HostProfile('Data-G2-full1-source-intake-NOT-AUTHORITY',str(prior_source.R),'cuda:0',0,True);cfg=profile.runtime_config(protocol);delta={k for k in set(cfg)|set(protocol)if cfg.get(k)!=protocol.get(k)};assert delta=={'actor_device'}and cfg['seed']==4301
assert option['requested_intents']==[dict(skill='NAV',target_ref='cuboid-2:approach:left',parameters=dict(goal_world_x_m=.5-.58,goal_world_y_m=-1.8+.15,surface_height_m=0.)),dict(skill='PUSH',target_ref='cuboid-2:approach:center',parameters=dict(goal_world_x_m=2.3,goal_world_y_m=-1.8,surface_height_m=0.)),dict(skill='CLIMB',target_ref='cuboid-2:upper-entry',parameters=dict(surface_height_m=.2))]
sys.path.insert(0,str(prior_source.QUESTION));import registered_layout_conditions as current_finite_helper
try:current_finite_helper.LayoutCondition('full-1','left','original')
except ValueError:rejected=True
else:raise AssertionError('Current full2 helper must still reject full1')
assert not forbidden
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),role='SOURCE_INTAKE_ONLY_NOT_PROGRAM_FREEZE_OR_NATIVE_QUALIFICATION',AINav_option_sha256=x['option_sha256'],original_source_sha256=option['original_source_sha256'],original_protocol=protocol,original_protocol_sha256=hashlib.sha256(canonical(protocol)).hexdigest(),prospective_runtime_config=cfg,device_only_overlay=True,requested_intents=option['requested_intents'],preparation='original',same_Actor_and_original_init_function_4301=True,C_material_difference_explicit=protocol['registered_materials'],not_geometry_only_or_single_variable_causal=True,old_full2_helper_unchanged_and_rejects_full1=rejected,new_separate_Data_caller_required=True,scope_ids_allocated=False,authority_allocated=False,physical_dispatch=False,Runtime_Actor_Renderer_constructed=False,forbidden_native_import_attempts=forbidden,training_role_or_split_not_assigned=True,training_or_fit_allowed=False,prospective_max_main=1,automatic_retry=False,full2_right_predecessor_error_preserved=True),ensure_ascii=False,indent=2))
