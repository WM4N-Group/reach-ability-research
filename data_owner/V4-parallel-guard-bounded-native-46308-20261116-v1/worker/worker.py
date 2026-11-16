"""New exact41 parallel-current-guard bounded applicability program; fresh own-zero, not a five-arm method or old retry."""
from pathlib import Path
import os,sys,json,hashlib,time,datetime,signal,resource,argparse,traceback
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='V4-parallel-guard-bounded-native-46308-20261116-v1';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';AUTH=B/'registry/V4_PARALLEL_GUARD_BOUNDED_AUTHORITY_20261116_v1.json';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';ENV=Path('/mnt/yuanyue/data-team/env-native-v1');SDK=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle');SOURCE=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source';ADAPTER=B/'development/bulk-resource-adapter-46308-20261115-v1';EXPAT=R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1';C=json.loads((W/'protocol.json').read_bytes());ROOT=R/'runtime/workers'/C['scope_id'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat()
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def authority():
 h=json.loads(H.read_bytes());q=h['active_V4_parallel_guard_bounded_scope'];a=json.loads(AUTH.read_bytes());need(h['executing_thread_id']==q['owner']==OWNER and q['active']and q['scope_id']==C['scope_id'],'Actual Data component preflight owner/scope');need(q['authorization_sha256']==sha(AUTH)and a['allowed_component_zero_invocations']==1 and a['allowed_task_main_invocations']==0,'One new component-only claim, never task main');need(h['active_new_critic_cohort_scope']['active']is False and h['new_critic_cohort_v1']['TRAIN_native_collection_complete'],'Do not overlap/hot-change frozen TRAIN lifecycle');need(all(not h[k]['active']for k in ['active_T_COMPLEX_component_zero_scope','active_T_COMPLEX_v2_camera_component_scope','active_T_COMPLEX_observation_study_scope','active_T_COMPLEX_full_program_scope']),'All old GPU0 scopes remain closed, no retry');need(not h['active_V4_bounded_climb_nav_scope']['active']and not h['active_V4_bounded_climb_nav_v2_scope']['active'],'Both old bounded scopes remain closed with original cost/result');need(not h['active_V4_capture_execution_scope']['active'],'Previous capture scope remains closed');need(not h['active_bulk24_collector_scope']['active'],'Fixed24 is already closed');need(not h['active_V4_native_component_scope']['active'],'Never overlap or resume closed asset component');need(not h['bulk24_collector_v1']['global_stop'],'Do not bypass a shared-source/resource global stop');return h,q,a
def verify(pin):
 p=M/'program-freeze.json';need(sha(p)==pin,'Exact component program freeze');v=json.loads(p.read_bytes());need(v['scope_id']==C['scope_id']and v['authorization_sha256']==sha(AUTH),'Frozen component scope/auth')
 for name,digest in v['files'].items():
  p=Path(name);need(not p.is_symlink()and(p.resolve().is_relative_to(R)or p.resolve().is_relative_to(SDK))and sha(p)==digest,'Frozen component/source/SDK/library drift: '+name)
 import importlib.metadata
 expected={'numpy':'1.26.4','torch':'2.7.0+cu128','mujoco':'3.3.2','scipy':'1.13.1','osqp':'1.1.3','pillow':'11.3.0'}
 need({k:importlib.metadata.version(k)for k in expected}==expected,'Original private dependency versions')
 need(sys.prefix==str(ENV)and sys.version_info[:3]==(3,11,16),'Private native interpreter');need(os.environ.get('LD_PRELOAD')==str(EXPAT)and sha(EXPAT)=='c995a80395904d85c4d35f4a185c3bae2fcdc562141dd6106c8ebe29571d33b3','Exact private XML loader')
 import pyexpat
 need(pyexpat.EXPAT_VERSION=='expat_2.8.1','Original XML loader version');need(os.environ.get('CUDA_VISIBLE_DEVICES')==C['GPU_UUID']and os.environ.get('MUJOCO_GL')=='egl'and os.environ.get('MUJOCO_EGL_DEVICE_ID')=='0','Exact new GPU0/EGL binding')
 return v
def prepare(pin):
 verify(pin);authority();sys.path[:0]=[str(W/'inputs/ainav/development/complex_v4_four_arm_v1'),str(SOURCE),str(W)];import native_entry as src
 need(Path(src.__file__).resolve()==W/'inputs/ainav/development/complex_v4_four_arm_v1/native_entry.py','Exact V4 source owner entry');need(src.compile_static_asset(enabled=False)is None and src.construct_cold_components(enabled=False)is None,'Default-off source APIs');src._exact_base()[0]._source(SOURCE)
 return src

def run(pin):
 start=time.monotonic();prepare(pin);_,q,_=authority();need(q['component_zero_dispatch_count']==1 and q['component_zero_dispatch_program_sha256']==pin,'Explicit component zero dispatch only');need(not ROOT.exists(),'Never resume/reopen component output root');ROOT.mkdir(parents=True);write(ROOT/'claim.json',dict(at=now(),PID=os.getpid(),program_sha256=pin,phase='component_zero',scope_id=C['scope_id'],task_main=False,invocation=1))
 sys.path[:0]=[str(ADAPTER),str(B/'workers/new-critic-cohort-46308-20261115-v1')]
 from per_gpu_lease import PerGpuLease
 from raw_third_view import LiveMuJoCoCamera,OptionalRawThirdView
 runtime=components=observer=video=lease=journal=writer=driver=planner=None;phase='BEFORE_SOURCE';result=dict(scope_id=C['scope_id'],phase='component_zero',PID=os.getpid(),program_sha256=pin,authorization_sha256=sha(AUTH),source_owner_commit=C['new_source_owner_commit'],passed=False,actual_task_steps=None,actual_auxiliary_calibration=None,full_task_or_AB_admitted=False,comparison_main_calls=0,capture_witness_complete=False,task_videos=0,training_allowed=False,automatic_retry=False,V4_five_arm_main_calls=0,VLM_calls=0,WM_calls=0,fit_calls=0);errors=[];metrics={};progress=None;capture_boundary=None
 def add_metric(name,elapsed,commands=0):
  row=metrics.setdefault(name,dict(calls=0,wall_s=0.,commands=0));row['calls']+=1;row['wall_s']+=elapsed;row['commands']+=commands
 def snapshot_metrics(event):
  return dict(at=now(),event=event,task_steps=runtime.step_count,task_sim_s=float(runtime.sim.data.time),wall_s=time.monotonic()-start,phase=phase,metrics=metrics,component_only_not_method_gain=True)
 def profile_progress(event):
  progress.write(json.dumps(snapshot_metrics(event),allow_nan=False)+'\n');progress.flush();os.fsync(progress.fileno())
 def checked_resources():
  authority()
  if lease is not None:lease.check()
  torch_module=sys.modules.get('torch')
  if torch_module is not None and torch_module.cuda.is_initialized():need(torch_module.cuda.memory_reserved()<=C['own_GPU_cap_bytes']and torch_module.cuda.max_memory_reserved()<=C['own_GPU_cap_bytes'],'Own Torch3GiB cap')
  need(time.monotonic()-start<C['wall_cap_s']-60.,'ParallelBounded21600wall cap with teardown reserve');need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=C['own_RSS_cap_bytes'],'Own4GiB RSS cap');size=sum(p.stat().st_size for p in ROOT.rglob('*')if p.is_file());need(size<C['output_cap_bytes']-32*1024**2,'Component output cap with report reserve')
 def guard():
  began=time.monotonic()
  try:return checked_resources()
  finally:add_metric('Data_owner_resource_guard_inclusive',time.monotonic()-began)
 def timeout(*args):raise RuntimeError('Component preflight wall deadline no retry')
 signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,C['wall_cap_s']-30.);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.nice(15)
 try:
  import torch,numpy as np
  torch.set_num_threads(2);lease=PerGpuLease(physical_index=0,authority_check=authority).__enter__();write(ROOT/'resource-lease.json',dict(locks=lease.rows,GPU=lease.last_gpu,owner=OWNER))
  from ainav.evidence import Journal
  journal=Journal(ROOT/'events.jsonl');import native_entry as src;phase='STATIC_MJB_INPUT_VERIFY_NOT_RECOMPILE'
  model_path=Path(C['static_MJB_input']);need(sha(model_path)==C['static_MJB_sha256'],'Exact previously compiled STATIC MJB, never saved state');model=dict(model_path=str(model_path),model_sha256=sha(model_path),static_asset_only_not_prior_Runtime_or_zero=True)
  write(ROOT/'static-MJB-input.json',model);scene_file=W/'inputs/ainav/development/complex_v4_four_arm_v1'/C['selected_scene_file'];phase='NEW_FRESH_COLD_COMPONENTS'
  components=src.construct_cold_components(source_root=SOURCE,bundle=SDK,model_path=model_path,model_sha256=model['model_sha256'],scene_path=scene_file,expected_scene_sha256=C['scene_sha256'],guard=guard,journal=journal,actor_device='cuda:0',enabled=True);runtime=components['runtime'];observer=components['observer'];guard()
  need(runtime.step_count==0 and float(runtime.sim.data.time)==0. and not runtime.sim.queue,'No task step, command, replay or capture witness');aux=runtime.wm_auxiliary_calibration;need(aux['worlds']==1 and aux['sim_seconds']<=10.5 and aux['main_world_unchanged'],'Original auxiliary cost, no task recovery')
  reg=components['registry'];need(reg.goal.surface_ref=='goal_deck'and reg.surfaces['goal_deck'].top_z_m==.6,'Actual elevated registry, no ground-only fallback');gid=int(runtime.sim.model.geom('goal_deck').id);need(int(runtime.sim.model.geom_bodyid[gid])==0,'Actual static worldbody deck, no movable alias');write(ROOT/'V4-elevated-registry.json',dict(goal_surface_ref=reg.goal.surface_ref,goal_top_z_m=reg.surfaces['goal_deck'].top_z_m,deck_geom_id=gid,deck_body_id=int(runtime.sim.model.geom_bodyid[gid]),declared_scene_sha256=C['scene_sha256'],not_complete_CLIMB_or_task_qualification=True))
  phase='ORIGINAL_CAPTURE_THEN_BOUNDED_LIVE_DRIVER';progress=(ROOT/'software-phase-timing.jsonl').open('x')
  from mujoco_zyh.streams import ChunkedEpisodeWriter
  from engineering_policy import BoundedEngineeringPolicy
  from private_catalog_boundary import PrivateCatalogBoundaryWriter
  import live_driver
  metadata=dict(source_id=C['scope_id'],episode_id=C['scope_id']+'-component0',role='bounded_native_integration_qualification_only',source_group=C['scope_id'],forecast_study_training_authorized=False,max_payload_bytes=768*1024**2,command_chunk_steps=200,visual_chunk_frames=32,visual_stride_control_ticks=5,joint_names=runtime.push['model'].JOINTS,actor_sha256=json.loads((SDK/'MANIFEST.json').read_bytes())['actor_sha256'],program_sha256=pin,not_E_or_A_B_C_D_method=True,component_factor_route=C['component_factor_route'],whole_artifact_model_input_allowed=False)
  writer=PrivateCatalogBoundaryWriter(ChunkedEpisodeWriter(ROOT/'episode',metadata));planner=BoundedEngineeringPolicy(components['scene'],journal=journal);cls=live_driver.driver_class(source_root=SOURCE,enabled=True);driver=cls(components,bundle=SDK,output_root=ROOT,writer=writer,planner=planner,journal=journal,guard=guard,arm='C');write(ROOT/'component-identity-NOT-METHOD-C.json',dict(API0_engineering_only=True,source_factor_route_C_for_common_H_ON_new_successor_OFF=True,not_actual_C_baseline_or_E_rule_or_five_arm_main=True,policy='First declared X-order box required PUSH -> same box20cm CLIMB -> its shared top-centre NAV; optional one shared original approach'))
  while not planner.complete:
   need(runtime.step_count<C['task_world_steps_allowed']and float(runtime.sim.data.time)<C['task_world_sim_cap_s'],'Bounded native component sim cap; no retry')
   guard()
   if driver.loop is not None:
    driver.loop._receipts()
    if planner.complete:break
   step_start=time.monotonic();steps_before=runtime.step_count;step_phase='capture_or_assembly'if driver.loop is None else'original_native_execution'
   try:driver.step_one()
   finally:
    delta=runtime.step_count-steps_before;add_metric(step_phase,time.monotonic()-step_start,delta)
    if capture_boundary is None and driver.capture.complete:
     capture_boundary=json.loads(json.dumps(dict(task_steps=runtime.step_count,task_sim_s=float(runtime.sim.data.time),report=driver.capture.report())));write(ROOT/'actual-supported-capture-completion-boundary.json',capture_boundary);result['capture_witness_complete']=True
    if runtime.step_count>steps_before and runtime.step_count%C['profiling_stride_commands']==0:profile_progress('bounded_progress')
  need(planner.complete and not planner.failed and [r['stage']for r in planner.receipts if r['stage']!='APPROACH']==['PUSH','CLIMB','TOP_NAV']and all(r['receipt']['status']=='succeeded'for r in planner.receipts),'Only real original three semantic successes count as component PASS')
  need(driver.executor.reported_end and driver.executor.last_outcome=='succeeded'and driver.executor.option.skill=='NAV','Original final NAV success receipt, not guessed stopped pose')
  witnesses=list(driver.factory._climb_nav_witnesses.values());need(len(witnesses)==1,'One exact bounded typed source handoff');typed=witnesses[0];typed.validate(runtime);need(typed.report()['active_native_NAV_owner'],'Actually installed/entered original NAV owner, not constructed pointer');need(len(driver.actual_climb_boundaries)==1,'One original CLIMB boundary only')
  write(ROOT/'actual-bounded-component-outcomes.json',dict(semantic_receipts=planner.receipts,typed_source=typed.report(),original_capture=driver.capture.report(),legacy_vs_new_factor_counts=dict(driver._v4_factor_journal.counts),not_five_arm_or_whole_task_success=True,no_static_deck_or_second_handoff_claim=True))
  result.update(passed=True,status='V4_BOUNDED_NATIVE_PUSH_CLIMB_NAV_COMPONENT_PASS_NOT_FIVE_ARM',actual_task_steps=runtime.step_count,actual_task_time_s=float(runtime.sim.data.time),actual_supported_capture=driver.capture.report(),capture_witness_complete=True,actual_bounded_native_handoff=True,actual_model_sha256=model['model_sha256'],actual_auxiliary_calibration=aux,five_arm_main_calls=0,WM_API_or_fit_calls=0)

 except BaseException as e:result.update(resource_wall_censored='ParallelBounded21600wall'in str(e)or'wall deadline'in str(e),status='COMPONENT_PREFLIGHT_FAILED_CLOSED_NO_RETRY',failure_stage=phase,error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc())
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  if driver is not None:
   try:driver.close_metadata_workers();result['metadata_read_pool_closed']=True
   except BaseException as e:errors.append(dict(stage='metadata_thread_close',error=repr(e)))
  if progress is not None:
   try:profile_progress('bounded_close');progress.close()
   except BaseException as e:errors.append(dict(stage='software_progress_close',error=repr(e)))
  result['actual_capture_completion_boundary']=capture_boundary;result['actual_software_phase_timings']=metrics;result['source_parallel_guard_is_common_engineering_not_BD_method_gain']=True
  if planner is not None:result.update(actual_component_receipts=planner.receipts,actual_component_stage=planner.stage,actual_component_decisions=planner.decision_count,component_not_C_or_E_method=True)
  if driver is not None:
   result['actual_capture_report']=driver.capture.report()
   if hasattr(driver,'_v4_factor_journal'):result['actual_factor_counts']=dict(driver._v4_factor_journal.counts)
  if writer is not None:
   try:
    result['episode_closure']=writer.close(outcome=result.get('status','failed_no_retry'),terminal_time_s=float(runtime.sim.data.time),censored=not result['passed']);need(result['episode_closure']['storage_complete'],'Original episode storage must close fully')
   except BaseException as e:errors.append(dict(stage='episode_close',error=repr(e)))
  for name,fn in [('video',lambda:video.close()if video is not None and not video.closed else None),('observer',lambda:observer.close()if observer is not None else None),('journal',lambda:journal.close()if journal is not None and hasattr(journal,'close')else None)]:
   try:fn()
   except BaseException as e:errors.append(dict(stage=name,error=repr(e)))
  if runtime is not None:result.update(actual_task_steps=runtime.step_count,actual_task_time_s=float(runtime.sim.data.time),actual_auxiliary_calibration=getattr(runtime,'wm_auxiliary_calibration',None))
  if lease is not None:
   try:result['last_GPU_observation']=lease.check(force=True);result['peak_observed_own_GPU_bytes']=lease.peak_own_compute_bytes
   except BaseException as e:errors.append(dict(stage='GPU_final_observation',error=repr(e)))
   lease.__exit__()
  result.update(close_errors=errors,wall_s=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,usage_known=runtime is not None,final_output_bytes_before_report=sum(p.stat().st_size for p in ROOT.rglob('*')if p.is_file()),preflight_is_not_comparison_or_dynamic_plan_qualification=True)
  if errors:result['passed']=False;result['status']='COMPONENT_PREFLIGHT_CLOSE_ERROR_NO_RETRY'
  write(ROOT/'result.json',result);write(ROOT/'ledger.json',dict(scope_id=C['scope_id'],program_sha256=pin,phase_invocations=1,closed=True,status=result['status'],result_sha256=sha(ROOT/'result.json'),actual_auxiliary_sim_s=None if result.get('actual_auxiliary_calibration')is None else result['actual_auxiliary_calibration']['sim_seconds'],actual_task_sim_s=result.get('actual_task_time_s'),wall_s=result['wall_s'],usage_known=result['usage_known'],output_bytes=sum(p.stat().st_size for p in ROOT.rglob('*')if p.is_file()),AB_main_calls=0,automatic_retry=False))
 print(json.dumps(result));return 0 if result['passed']else 1
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=('prepare','component-zero'),default='prepare');ap.add_argument('--program-sha256',required=True);args=ap.parse_args()
 if args.phase=='prepare':
  def fence(event,values):
   if event=='import'and str(values[0]).split('.')[0]in('torch','mujoco','onnxruntime'):raise RuntimeError('Default prepare cannot construct native/Actor')
  sys.addaudithook(fence);prepare(args.program_sha256);print(json.dumps(dict(prepared=True,task_steps=0,new_native_constructor=False,default_source_entries_disabled=True)))
 else:sys.exit(run(args.program_sha256))
