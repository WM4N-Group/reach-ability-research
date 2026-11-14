"""NEW installer and actual source ABI on NumPy SOFTWARE object graph only.
Never constructs Host/Runtime/TargetBridge physical backend or native machine.
"""
from pathlib import Path
import sys,json,hashlib,dataclasses
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W));attempts=[]
def fence(event,args):
    if event=='import' and str(args[0]).split('.')[0] in ('torch','mujoco','onnxruntime'):
        attempts.append(str(args[0]));raise RuntimeError('CPU preparation/installer probe forbids Actor/native')
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen'):raise RuntimeError('CPU-only no child/network')
sys.addaudithook(fence)
from prepare_prefix import build_plan,load_package,make_planner,SOURCE,R,IDS,digest,sha,SDK_ROOT
from prefix_bindings import install_preexecution_choices
from types import SimpleNamespace as NS
import numpy as np
condition_id=sys.argv[1];candidate='original';plan=build_plan(condition_id);consumer,source,_=load_package();types=consumer.load_original_types(source)
from mujoco_zyh import native_behavior_executor as api
from ainav.native.full_verified_placement import PlacementCourseFactory,LatchedCompletedPlacement
from ainav.native.course_tools import PublicReference
from ainav.native.intent_execution import IntentExecutionCoordinator
from ainav.native.execution_judge import EntrySpec
from ainav.intents import SkillIntent
from types import MappingProxyType
# Real classes and full alias graph, but constructor state is EXPLICIT SOFTWARE.
data=NS(time=0.,qpos=np.zeros(25),qvel=np.zeros(24));model=object();queue=[]
r=NS(sim=NS(model=model,data=data,queue=queue),step_count=0,last=NS(position=np.zeros(18)))
factory=PlacementCourseFactory.__new__(PlacementCourseFactory);factory.runtime=r
reference=PublicReference('cuboid-2:upper-entry',(.050000000000000044,-1.8),0.,'SOFTWARE-map',climb_surface='B',body_name='wm_object_middle')
factory.references=MappingProxyType({reference.ref:reference})
rows=[]
def journal(row):rows.append(row);return '/SOFTWARE-NOT-EXPERIMENT/events.jsonl#'+str(len(rows))
executor=api.NativeOptionExecutor(r,factory,journal);factory.executor=executor
planner=make_planner(types,plan['requested_intents'],journal)
coordinator=IntentExecutionCoordinator(planner=planner,observe=None,catalogue=None,judge=None,bind=None,
    snapshot=lambda:api.world_snapshot(r),protection=None,journal=journal,capability_contract='SOFTWARE_NOT_A_QUERY')
host=types.Host.__new__(types.Host);host.tick=0;host.r=r;host.factory=factory;host.executor=executor;host.coordinator=coordinator
host.refs_by_id={reference.ref:reference};host.api=api;host.journal=journal;host.execution_sequence=1
entry_ports=[];host._entry=lambda skill,ref:entry_ports.append((skill,ref))  # explicit geometry/admission software port
before=api.world_snapshot(r)
# Refuse dirty zero before installing any module callbacks, no rollback.
r.step_count=1
try:install_preexecution_choices(host,candidate_id=candidate,emit=journal)
except ValueError:pass
else:raise AssertionError('Hot install not rejected')
r.step_count=0
bindings=install_preexecution_choices(host,candidate_id=candidate,emit=journal)
assert api.world_snapshot(r)==before and len(bindings['common_stow_aliases'])>=1
try:install_preexecution_choices(host,candidate_id=candidate,emit=journal)
except ValueError:pass
else:raise AssertionError('Second install accepted')
# Preserve previous PUSH root/session plus a distinct selected view/proxy.
view=NS(model=model,data=data,queue=queue);proxy=NS(sim=view,last=r.last,step_count=0)
machine=LatchedCompletedPlacement.__new__(LatchedCompletedPlacement);machine.tasks=[dict(skill='push')];machine.r=proxy;machine.native=NS(r=proxy)
session=api.NativeOptionSession(r,machine);executor.session=session;executor.reported_end=True
executor.option=NS(skill='PUSH')
intent=SkillIntent('SOFTWARE-climb','CLIMB',reference.ref,(('surface_height_m',.2),));coordinator.intent=intent
spec=EntrySpec('CLIMB',reference.ref,reference.xy,0.)
option=host._native_nav(intent,spec,0.)
expected_y=dict(original=-1.8,lateral_plus_0p04=-1.76,lateral_minus_0p04=-1.84)[candidate]
assert dict(option.parameters)['goal_world_y_m']==expected_y and host.refs_by_id[reference.ref] is reference and reference.xy[1]==-1.8
assert session.runtime is r and session.machine.r is proxy and proxy.sim is view and view is not r.sim
assert view.model is r.sim.model and view.data is r.sim.data and view.queue is r.sim.queue
assert api.world_snapshot(r)==before and session.entered is False
# A foreign previous root is refused, not collapsed or silently repaired.
session.runtime=NS(sim=r.sim)
try:host._native_nav(intent,spec,0.)
except ValueError:pass
else:raise AssertionError('Foreign previous root accepted')
assert not attempts
# Fresh checkpoint bytes are SHA-read, NEVER loaded by Torch/Actor.
actor_checks=[]
for rel,expected in plan['actor_sha256'].items():
    p=SDK_ROOT/rel;actual=sha(p);assert actual==expected;actor_checks.append(dict(path=str(p),sha256=actual))
initial=dict(schema='Data-prefix-common-constructor-init-RNG-binding-v1',runtime_config=plan['runtime_config'],
    original_native_protocol=plan['original_native_protocol'],seed=plan['seed'],actor_files=actor_checks,
    current_common_source_manifest_sha256=plan['current_source_fork_manifest_sha256'],
    original_initialization_functions=['mujoco_zyh.stall_stow.initial_posture','mujoco_zyh.stall_stow.initial_base','mujoco_zyh.runtime_adapter.construct_runtime'],
    no_random_perturbation_or_seed_selection=True,actual_full_hidden_state_equality=False)
out=dict(schema='Data-new-worker-prepare-and-installer-SOFTWARE-ABI-probe-v1',condition_id=condition_id,
    plan=plan,initial_binding=initial,initial_binding_sha256=digest(initial),bindings=bindings,
    actual_Host_constructor_executed=False,actual_runtime_model_capture_or_geometry_constructed=False,
    real_original_factory_executor_coordinator_session_classes_used=True,previous_PUSH_root_proxy_selected_view_not_collapsed=True,
    actual_native_nav_caller_invoked=True,native_NAV_option=dataclasses.asdict(option),
    geometry_entry_is_explicit_software_port=True,world_FIFO_unchanged=True,
    dirty_zero_duplicate_install_and_foreign_previous_root_refused=True,actor_checkpoint_SHA_verified_without_load=actor_checks,
    camera_not_constructed=True,native_module_attempts=attempts,new_physical_calls=0,physical_admission=False)
print(json.dumps(out,ensure_ascii=False,indent=2))
