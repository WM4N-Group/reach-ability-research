"""Data's bounded lifecycle around the ONE original AINav full host.
Default prepare; explicit CAS/freeze/user grant and own zero required to execute.
No native control reimplementation, additional Runtime.step, model API or reset.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,resource,signal,sys,time,traceback
sys.path.insert(0,str(Path(__file__).parent))
from support import *
from model_identity import identity
from prepare_prefix import build_plan,load_package,A as PACKAGE,SOURCE,ENVIRONMENT,SDK_ROOT,EXPAT_LIBRARY,EXPAT_LIBRARY_SHA256
from prefix_bindings import install_preexecution_choices
P=W
SDK=SDK_ROOT

def prepare(program_sha):
 verify_program(program_sha);authority()
 need(os.environ.get('LD_PRELOAD')==str(EXPAT_LIBRARY) and sha(EXPAT_LIBRARY)==EXPAT_LIBRARY_SHA256,'Exact private Expat2.8.1 loader binding; never downgrade parser or alter global environment')
 import pyexpat,xml.etree.ElementTree as ET
 need(pyexpat.EXPAT_VERSION=='expat_2.8.1','Python3.11.16 matching Expat symbol version')
 loaded={line.split()[-1]for line in Path('/proc/self/maps').read_text().splitlines()if '/libexpat.so' in line}
 need(loaded=={str(EXPAT_LIBRARY)},'Actual loaded XML library must be the pinned private overlay')
 need(ET.parse(SDK_ROOT/'push/robot/source_robot.xml').getroot().tag=='mujoco','Original pinned source XML parser binding before claim; no model constructor')
 need(sys.prefix==str(ENVIRONMENT) and sys.version_info[:3]==(3,11,16),'Exact private native interpreter')
 import importlib.metadata
 expected={'numpy':'1.26.4','torch':'2.7.0+cu128','mujoco':'3.3.2','scipy':'1.13.1','osqp':'1.1.3','imageio':'2.37.0','pillow':'11.3.0'}
 need({k:importlib.metadata.version(k) for k in expected}==expected,'Original dependencies plus repaired imageio overlay only')
 need(not any(n=='ainav' or n.startswith(('ainav.','mujoco_zyh.')) for n in sys.modules),'Fresh same-source interpreter required')
 plan=build_plan(CANDIDATE);consumer,source,_=load_package()
 from mujoco_zyh import runtime_adapter,observer,streams,review_capture,integrated_course,stall_stow,native_behavior_executor
 Runtime,Machine,plans,receipt=runtime_adapter.load_runtime_types(SDK,plan['runtime_config'])
 need(Runtime.step.__code__.co_filename==str(SDK/'switch/runtime.py')+'[scene-hook-only]','Actual same-source Runtime.step definition')
 return plan,consumer,source


def run(phase,program_sha):
 start=time.monotonic();plan,consumer,source=prepare(program_sha);authority(phase,program_sha)
 need(os.environ.get('CUDA_VISIBLE_DEVICES')==UUID and os.environ.get('MUJOCO_EGL_DEVICE_ID')=='1' and os.environ.get('MUJOCO_GL')=='egl','Exact authorized GPU/EGL binding')
 import torch,numpy as np
 torch.set_num_threads(2);os.nice(15);resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(536870912,536870912))
 ledger=Ledger(ROOT,program_sha=program_sha,auth_sha=sha(AUTH));ledger.claim(phase,start)
 root=ROOT/phase;need(not root.exists(),'Never reopen a phase output root');root.mkdir()
 prior_wall=sum(r['wall_s'] for r in ledger.read()['rows'] if r['closed'])
 def timeout(*args):raise Stop('Full-host cumulative wall deadline')
 signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,max(.1,CAPS['wall_s']-INHERITED['wall_s']-prior_wall-(time.monotonic()-start)-15.))
 selection_rows=[];binding_receipts=[]
 runtime=host=planner=observer=writer=review=journal=capsules=video=None;lease=None;primary=None;close_errors=[];last_review=None;last_disk_at=0;latest_totals=None;model_hash=None;model_record=None;usage_known=True
 result={'candidate_id':CANDIDATE,'schema':'Data-real-original-AINav-full-host-phase-result-v1','scope_id':SCOPE,'phase':phase,'program_sha256':program_sha,'authorization_sha256':sha(AUTH),'baseline_release_sha256':plan['baseline_release_sha256'],'reference_source_manifest_sha256':plan['source_manifest_sha256'],'PID':os.getpid(),'passed':False,'automatic_retry':False,'research_WM_or_API_calls':0,'training_allowed':False,'whole_task_success_claimed':False,'CLIMB_requested':True,'HIGH_or_other_object_requested':False,'source_profile':'EXPLICIT_FOUR_DELTA_NATIVE_PREFIX_ORIGINAL_PREPARATION','new_waypoint_choice_control_enabled':True,'new_preparation_choice_enabled':False,'condition_qualification_not_critic_training':True,'original_source_manifest_is_baseline_lineage_only':True,'source_fork_manifest_sha256':plan['current_source_fork_manifest_sha256']}
 def usage():
  aux=getattr(runtime,'wm_auxiliary_calibration',None) if runtime is not None else None
  return (float(runtime.sim.data.time) if runtime is not None and hasattr(runtime,'sim') else 0.)+(float(aux['sim_seconds']) if aux is not None else 0.)
 def guard(force=False,cleanup=False):
  nonlocal last_disk_at,latest_totals
  lease.check(force=force)
  if video is not None and not cleanup:video.capture_if_due()
  need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=RSS_CAP,'Own4GiB resident-memory technical cap')
  need(torch.cuda.memory_reserved()<=GPU_CAP,'Own PyTorch memory cap')
  now=time.monotonic();v=ledger.read();sim=INHERITED['sim_s']+sum(r['sim_s'] for r in v['rows'] if r['closed'])+usage();wall=INHERITED['wall_s']+sum(r['wall_s'] for r in v['rows'] if r['closed'])+(now-start)
  need(sim<CAPS['sim_s']-(0. if cleanup else .004999),'Cumulative sim/aux cap reached');need(wall<CAPS['wall_s']-(0. if cleanup else 15.),'Cumulative wall cap reached')
  if force or now-last_disk_at>=.5:
   latest_totals=ledger.observe(phase,sim_s=usage(),wall_s=now-start,cleanup=cleanup);last_disk_at=now
  if phase=='main' and review is not None and host is not None and not cleanup and host.tick%20==0 and last_review!=host.tick:
   capture_review()
 def capture_review():
  nonlocal last_review
  review.capture(host.tick//4);last_review=host.tick
 try:
  lease=Lease().__enter__();need(lease.last_gpu['free_MiB']*1024**2>=GPU_CAP+1024**3,'Initial headroom for own3GiB + shared1GiB')
  write_new(root/'resource-lease.json',{'canonical_binding_sha256':sha(BIND),'holder_PID':os.getpid(),'locks':lease.rows,'GPU':lease.last_gpu,'not_exclusive_GPU_ownership':True})
  from ainav.evidence import Journal
  journal=Journal(root/'events.jsonl')
  journal({'event':'Data_full_host_phase_claimed','phase':phase,'program_sha256':program_sha,'new_full_host_not_old_B_retry':True})
  from mujoco_zyh.runtime_adapter import construct_runtime
  from mujoco_zyh.observer import OnboardObserver
  from mujoco_zyh.streams import ChunkedEpisodeWriter
  from mujoco_zyh.review_capture import WorldStateRecorder
  from mujoco_zyh.failure_capsules import install as install_capsules
  from mujoco_zyh import native_behavior_executor as api,integrated_course as integrated,stall_stow as stall
  config=dict(plan['runtime_config'],bundle=str(SDK))
  # All side-effect-free program/config/class checks completed before claim.
  # Exact raw native machine goes to ORIGINAL host; no Data prefix is created.
  try:runtime,native,construction=construct_runtime(SDK,config)
  except BaseException as e:runtime=getattr(e,'wm_partial_runtime',None);raise
  need(float(runtime.sim.data.time)==0. and runtime.step_count==0 and not runtime.sim.queue,'Constructor must leave main world at zero, no queued task issue')
  aux=getattr(runtime,'wm_auxiliary_calibration',None);need(aux is not None and aux['worlds']==1 and aux['sim_seconds']<=10.5 and aux['main_world_unchanged'],'Original auxiliary calibration counted, no task recovery')
  need(str(runtime.device)=='cuda:0','Actual original Actor backend must match the explicit CUDA overlay')
  write_new(root/'construction.json',construction);write_new(root/'actual-config.json',{'original_native_protocol':plan['original_native_protocol'],'actual_runtime_config':config,'external_caps':CAPS,'inherited_old_failure_cost':INHERITED})
  capsules=install_capsules(runtime,root,config['private_failure_capsules'])
  observer=OnboardObserver.__new__(OnboardObserver);OnboardObserver.__init__(observer,runtime,config)
  manifest=json.loads((SDK/'MANIFEST.json').read_text())
  writer=ChunkedEpisodeWriter(root/'episode',dict(config,joint_names=runtime.push['model'].JOINTS,actor_sha256=manifest['actor_sha256'],physics_dt_s=.005,control_dt_s=.02,VLM_control=False,ainav_pilot_only=False,original_scene_source_id=config['source_id'],source_id=SCOPE+'-'+phase,episode_id=SCOPE+'-'+phase+'-episode0',source_group='AINav-native-prefix-NAV-PUSH-CLIMB-condition-qualification-DEV',Data_capture_role='audit_only_no_training'))
  review=WorldStateRecorder(root/'review-state',runtime,config,model_cache_dir=ROOT/'compiled-review-models')
  # Preserve a partial host reference even if its original __init__ raises.
  types=consumer.load_original_types(source)
  need(observer.r is runtime,'Original observer references the same Runtime')
  for module,relative in ((api,'mujoco_zyh/native_behavior_executor.py'),(integrated,'mujoco_zyh/integrated_course.py'),(stall,'mujoco_zyh/stall_stow.py')):
   need(Path(module.__file__).resolve()==source/relative,'One complete original source, no mixed backend')
  host=types.Host.__new__(types.Host)
  # Same constructor arguments/owner as source-owner compose_same_world_host;
  # original __init__ is called directly solely for exception-safe ownership.
  from prepare_prefix import make_planner
  planner=make_planner(types,plan['requested_intents'],journal)
  types.Host.__init__(host,runtime=runtime,native_a=native,observer=observer,writer=writer,root=root,config=config,api=api,integrated=integrated,stall=stall,planner=planner,journal=journal)
  need(host.r is runtime and host.coordinator.model is planner and not planner.complete,'Single original Runtime/host/semantic owner')
  def evidence(row):
   journal(row);selection_rows.append(dict(row))
  binding_receipts=install_preexecution_choices(host,candidate_id='original',emit=evidence)
  write_new(root/'prefix-common-choice-binding.json',binding_receipts)
  from raw_third_view import LiveMuJoCoCamera,OptionalRawThirdView
  camera=json.loads((W/'third-view-camera.json').read_text())
  video=OptionalRawThirdView(root/'raw-third-view',enabled=True,
    source_factory=lambda:LiveMuJoCoCamera(runtime,camera,snapshot=observer.snapshot,unchanged=observer.unchanged),
    scope_id=SCOPE,episode_id=SCOPE+'-'+phase,program_sha256=program_sha)
  video.capture_if_due()
  host._native_guards();host._contact_guard();model_hash,model_record=identity(runtime.sim.model)
  write_new(root/'actual-model-identity.json',{'model_sha256':model_hash,'model':model_record,'nq':runtime.sim.model.nq,'nv':runtime.sim.model.nv,'dt':runtime.sim.model.opt.timestep,'program_sha256':program_sha})
  need(runtime.sim.model.opt.timestep==.005,'Original native200Hz timestep')
  guard(force=True)
  if phase=='zero':
   before=observer.snapshot();host.capture_grid();capture_review()
   need(observer.unchanged(before,observer.snapshot()) and host.tick==0 and runtime.step_count==0 and float(runtime.sim.data.time)==0. and not runtime.sim.queue and writer.steps==0,'Own-zero must not step, issue, restore or edit state/FIFO')
   need(writer.frames==1 and observer.frames==1,'Actual same-host original8 RGBD captured once')
   packet=writer.visual[0]['packet'];need(set(packet)==set(('rgb','depth_m','camera_K','T_base_optical','proprio','actions_previous','action_valid','timestamps_s')),'Exact original8 fields')
   need(packet['rgb'].shape==(1,1,128,192,3) and packet['rgb'].dtype==np.uint8 and packet['depth_m'].shape==(1,1,128,192,1) and float(packet['timestamps_s'][0,0])==0.,'Actual native RGBD shape/dtype/zero epoch')
   result.update(passed=True,status='OWN_ZERO_PASS',actual_RGB_array_sha256=hashlib.sha256(packet['rgb'].tobytes()).hexdigest(),actual_INPUT8_sha256={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in packet.items()},task_physics_steps=0)
  else:
   zero=json.loads((ROOT/'zero/result.json').read_text());need(zero['passed'] is True and zero['status']=='OWN_ZERO_PASS' and zero['program_sha256']==program_sha and zero['actual_model_numeric_sha256']==model_hash,'Own same-program actual zero/model, no old zero/fixture/compile-only transfer')
   zr=ledger.read()['rows'][0];need(zr['report_sha256']==sha(ROOT/'zero/result.json'),'Sealed own-zero result identity')
   driven=consumer.drive_same_world_api0(source=source,host=host,planner=planner,max_calls=60001,budget_and_lease=guard,enabled=True)
   need(driven['status']=='ORIGINAL_REQUESTED_INTERACTIONS_COMPLETED','Original three-request driver must complete')
   from request_contract import verify_completed_requests
   from ainav.evidence import verify as verify_journal
   verify_journal(root/'events.jsonl')
   exact_three=verify_completed_requests(planner,plan['requested_intents'],[json.loads(line)['payload'] for line in (root/'events.jsonl').read_text().splitlines()])
   result['exact_three_semantic_native_successes']=exact_three
   host.monitor.check_a()
   if video is not None:video.capture_if_due()
   result.update(passed=True,status='REQUESTED_API0_PASS',drive_result=driven,task_physics_steps=host.tick,actual_dispatches=host.dispatched,actual_completed_skills=host.completed,actual_native_results=[r for session in host.executor.sessions for r in getattr(session.machine,'results',[])],selected_requests=plan['requested_intents'],requested_CLIMB_covered=True,private_surface_history=host.surface_visits.report())
  guard(force=True,cleanup=True)
 except BaseException as e:
  primary=e;result.update(passed=False,status='FAILED_NO_RETRY',error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc())
  if runtime is not None and host is not None:
   try:
    from ainav.native.failure_diagnostics import terminal_snapshot
    diagnostic=terminal_snapshot(host,e)
    if journal:journal(dict(diagnostic,time_s=float(runtime.sim.data.time),error=str(e)))
    from mujoco_zyh.failure_capsules import emit
    emit(runtime,'ainav_terminal_failure',extra=diagnostic,preserve_primary_failure=True)
   except BaseException as diagnostic_error:result['terminal_diagnostic_error']=repr(diagnostic_error)
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  now_sim=float(runtime.sim.data.time) if runtime is not None and hasattr(runtime,'sim') else 0.
  aux=getattr(runtime,'wm_auxiliary_calibration',None) if runtime is not None else None
  if runtime is not None and aux is None:usage_known=False
  actions=[('raw_third_view',lambda:video.close() if video is not None else None),('review',lambda:review.close() if review is not None and not review.closed else None),('episode',lambda:writer.close(outcome=result['status'],terminal_time_s=now_sim,censored=True) if writer is not None and not writer.closed else None),('capsules',lambda:capsules.close() if capsules is not None and not capsules.closed else None),('observer',lambda:observer.close() if observer is not None and getattr(observer,'renderer',None) is not None else None)]
  for name,action in actions:
   try:
    value=action()
    if value is not None:result[name+'_closure']=value
   except BaseException as e:close_errors.append({'stage':name,'error':repr(e)})
  if host is not None:
   prefix=getattr(host,'prefix',None)
   for name in ('log','recovery_log'):
    handle=getattr(prefix,name,None)
    if handle is not None:
     try:handle.close()
     except BaseException as e:close_errors.append({'stage':'prefix.'+name,'error':repr(e)})
   samples=getattr(host,'private_samples',None)
   if samples is not None:
    try:samples.close()
    except BaseException as e:close_errors.append({'stage':'private_samples','error':repr(e)})
  if journal is not None:
   try:journal({'event':'Data_full_host_phase_teardown','phase':phase,'close_errors':close_errors,'automatic_retry':False});journal.close()
   except BaseException as e:close_errors.append({'stage':'journal.close','error':repr(e)})
  result.update(observed_process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,stow_choice_records=selection_rows,stow_choice_bindings=binding_receipts,actual_preparation_proposals=[row for row in selection_rows if row.get('event')=='ainav_selected_CLIMB_preparation_NAV_goal_proposed'],actual_selection_recorded=bool(selection_rows),actual_choice_changed=any(row.get('changed') is True for row in selection_rows),method_benefit_or_distinct_algorithm_proven=False,actual_main_world_sim_s=now_sim,actual_auxiliary_calibration=aux,actual_model_numeric_sha256=model_hash,actual_Actor_backend=str(runtime.device) if runtime is not None and hasattr(runtime,'device') else None,close_errors=close_errors,wall_s=time.monotonic()-start,usage_known=usage_known,old_B_failure_and_root_preserved=True)
  if close_errors:result.update(passed=False,status='TEARDOWN_FAILED_NO_RETRY')
  if writer is not None:
   result['actual_recorded_commands']=writer.written_steps;result['actual_recorded_visual_frames']=writer.written_frames
   if result['passed'] and (not result.get('episode_closure',{}).get('storage_complete') or writer.written_steps!=round(now_sim/.005)):
    result.update(passed=False,status='INCOMPLETE_COMMAND_EVIDENCE_NO_RETRY')
  try:result['cumulative_observed_usage']=ledger.observe(phase,sim_s=usage(),wall_s=time.monotonic()-start,cleanup=True)
  except BaseException as e:result.update(passed=False,status='BUDGET_OR_FINAL_USAGE_FAILED_NO_RETRY',budget_close_error=repr(e))
  write_new(root/'result.json',result)
  ledger.close(phase,result['status'],sim_s=usage(),wall_s=time.monotonic()-start,report_sha=sha(root/'result.json'),usage_known=usage_known)
  if lease is not None:lease.__exit__(None,None,None)
  runtime=host=observer=writer=review=None
 return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=('prepare','zero','main'),default='prepare');ap.add_argument('--program-sha256',required=True);args=ap.parse_args()
 if args.phase=='prepare':
  need(os.environ.get('CUDA_VISIBLE_DEVICES')=='' and os.environ.get('MUJOCO_GL')=='disable','Prepare must remain CPU-only')
  import torch,mujoco
  attempts=[]
  def blocked(name):
   def call(*a,**kw):attempts.append(name);raise Stop('CPU_PREPARE_FORBIDDEN:'+name)
   return call
  need(not torch.cuda.is_initialized(),'CPU preparation cannot inherit CUDA context')
  torch.set_num_threads(2);torch.load=blocked('torch.load');torch.jit.load=blocked('torch.jit.load');torch.cuda._lazy_init=blocked('CUDA');torch.nn.Module.__call__=blocked('NN_forward');mujoco.MjSpec=blocked('MjSpec');mujoco.MjData=blocked('MjData');mujoco.Renderer=blocked('Renderer');mujoco.MjModel.from_xml_string=blocked('MjModel.from_xml_string');mujoco.MjModel.from_xml_path=blocked('MjModel.from_xml_path');mujoco.mj_step=blocked('mj_step')
  plan,consumer,source=prepare(args.program_sha256)
  need(not attempts and not torch.cuda.is_initialized(),'No constructor/Actor/GPU attempt during prepare')
  value={'prepared':True,'program_sha256':args.program_sha256,'source':str(source),'constructor_or_physics_started':False,'forbidden_attempts':attempts,'actual_whole_worker_entrypoint_checked_before_claim':True}
  write_new(M/('fenced-prepare-'+args.program_sha256+'.json'),value);print(json.dumps(value))
 else:
  value=run(args.phase,args.program_sha256);print(json.dumps({k:v for k,v in value.items() if k not in ('traceback','actual_dispatches','actual_completed_skills','actual_native_results')},ensure_ascii=False));sys.exit(0 if value['passed'] else 1)
