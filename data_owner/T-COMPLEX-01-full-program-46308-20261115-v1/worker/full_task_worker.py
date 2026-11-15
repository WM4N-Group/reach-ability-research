"""Default-off new common source host, A/B differ ONLY shared method parameter.
Data owns lifecycle/recorders/limits, never algorithms, source native control or
success definitions. No replay, restoration, private route or critic input.
"""
from pathlib import Path
import argparse,os,sys,json,time,hashlib,signal,resource,traceback
sys.path.insert(0,str(Path(__file__).parent))
from support import *
EXPAT=R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1';EXPAT_SHA='c995a80395904d85c4d35f4a185c3bae2fcdc562141dd6106c8ebe29571d33b3'
ADAPTER=B/'development/bulk-resource-adapter-46308-20261115-v1';OLD=B/'workers/new-critic-cohort-46308-20261115-v1'
def prepare(pin):
 verify_program(pin);authority();need(sys.prefix==str(ENVIRONMENT)and sys.version_info[:3]==(3,11,16),'Original private interpreter');need(os.environ.get('LD_PRELOAD')==str(EXPAT)and sha(EXPAT)==EXPAT_SHA,'Exact private XML overlay')
 import importlib.metadata,pyexpat
 expected={'numpy':'1.26.4','torch':'2.7.0+cu128','mujoco':'3.3.2','scipy':'1.13.1','osqp':'1.1.3','pillow':'11.3.0'};need({k:importlib.metadata.version(k)for k in expected}==expected and pyexpat.EXPAT_VERSION=='expat_2.8.1','Original dependency pins')
 sys.path[:0]=[str(OWN),str(SOURCE),str(ADAPTER),str(OLD)]
 import native_construction as source
 from complex_scene import load_scene
 from public_planner_binding import make_public_planner
 need(Path(source.__file__).resolve()==OWN/'native_construction.py','Exact source owner module');need(source.compile_static_asset(enabled=False)is None and source.construct_cold_components(enabled=False)is None,'Source construction default off');source._source(SOURCE)
 selection=json.loads((OWN/'SOURCE_SELECTION_V2.json').read_bytes());scene_file=OWN/selection['scene_file'];need(sha(scene_file)==selection['scene_sha256']==PROTOCOL['scene_sha256'],'Same selected scene all arms')
 scene=load_scene(scene_file);binding=json.loads((OWN/'REACH_METHOD_SOURCE_BINDING.json').read_bytes());planner=make_public_planner(scene,reach_source_root=REACH,expected_module_hashes=binding['files_sha256'],method=PROTOCOL['arms'][ARM]['method'],journal=lambda row:'CPU_PREPARE_NOT_NATIVE',limits=binding['same_limits'])
 return source,scene_file,scene,planner

def run(phase,pin):
 start=time.monotonic();source,scene_file,scene,planner=prepare(pin);authority(phase,pin);need(os.environ.get('CUDA_VISIBLE_DEVICES')==PROTOCOL['GPU_UUID']and os.environ.get('MUJOCO_GL')=='egl'and os.environ.get('MUJOCO_EGL_DEVICE_ID')=='0','Exact GPU0/EGL allocation')
 need(not(ROOT/phase).exists(),'No phase restoration');ledger=Ledger(ROOT,program_sha=pin,auth_sha=sha(AUTH));ledger.claim(phase,start);root=ROOT/phase;root.mkdir();prior_wall=sum(row['wall_s']for row in ledger.read()['rows']if row['closed']);runtime=components=host=observer=writer=review=video=journal=lease=None;errors=[];last_disk=0.;last_review=None;model_hash=None;known=False
 result=dict(schema='Data-T-complex-source-full-task-phase-v1',scope_id=SCOPE,arm=ARM,method=PROTOCOL['arms'][ARM]['method'],phase=phase,PID=os.getpid(),program_sha256=pin,authorization_sha256=sha(AUTH),passed=False,status='NOT_RESULT',training_allowed=False,automatic_retry=False,task_success=False,source_scene_sha256=PROTOCOL['scene_sha256'],source_owner_commit=PROTOCOL['source_owner_commit'],all_previous_scopes_preserved=True)
 def used():
  return (float(runtime.sim.data.time)+float(runtime.wm_auxiliary_calibration['sim_seconds']))if runtime is not None else 0.
 def guard(force=False,cleanup=False):
  nonlocal last_disk,last_review
  authority(phase,pin)
  if lease is not None:lease.check(force=force)
  need(time.monotonic()-start+prior_wall<CAPS['wall_s']-15.,'Own full-task wall cap');need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=4*1024**3,'Own RSS4GiB cap')
  torch_module=sys.modules.get('torch')
  if torch_module is not None and torch_module.cuda.is_initialized():need(torch_module.cuda.memory_reserved()<=3*1024**3 and torch_module.cuda.max_memory_reserved()<=3*1024**3,'Own Torch3GiB cap')
  if runtime is not None:need(float(runtime.sim.data.time)<=PROTOCOL['task_sim_cap_s'],'Task simulation time cap')
  if video is not None and not cleanup:video.capture_if_due()
  if review is not None and runtime.step_count%20==0 and last_review!=runtime.step_count:
   review.capture(runtime.step_count//4);last_review=runtime.step_count
  if force or time.monotonic()-last_disk>=1.:
   ledger.observe(phase,sim_s=used(),wall_s=time.monotonic()-start,cleanup=cleanup);last_disk=time.monotonic()
 def deadline(*args):raise Stop('Full-task owned wall watchdog, no retry')
 signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,min(180. if phase=='zero'else CAPS['wall_s']-prior_wall,CAPS['wall_s']-prior_wall)-20.);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.nice(15)
 try:
  import torch,numpy as np
  torch.set_num_threads(2)
  from per_gpu_lease import PerGpuLease
  lease=PerGpuLease(physical_index=0,authority_check=lambda:authority(phase,pin)).__enter__();write_new(root/'resource-lease.json',dict(locks=lease.rows,GPU=lease.last_gpu,owner=OWNER))
  from ainav.evidence import Journal
  journal=Journal(root/'events.jsonl');journal(dict(event='Data_T_complex_phase_claimed',arm=ARM,method=PROTOCOL['arms'][ARM]['method'],phase=phase,program_sha256=pin))
  asset=source.compile_static_asset(source_root=SOURCE,bundle=SDK_ROOT,output_model=root/'static-scene.mjb',scene_path=scene_file,expected_scene_sha256=PROTOCOL['scene_sha256'],guard=guard,enabled=True);write_new(root/'native-asset-construction.json',asset)
  components=source.construct_cold_components(source_root=SOURCE,bundle=SDK_ROOT,model_path=root/'static-scene.mjb',model_sha256=asset['model_sha256'],scene_path=scene_file,expected_scene_sha256=PROTOCOL['scene_sha256'],guard=guard,journal=journal,actor_device='cuda:0',enabled=True);runtime=components['runtime'];observer=components['observer'];aux=runtime.wm_auxiliary_calibration;need(aux['worlds']==1 and aux['sim_seconds']<=10.5 and aux['main_world_unchanged'],'Original auxiliary only, no task recovery');known=True
  from mujoco_zyh.streams import ChunkedEpisodeWriter
  from mujoco_zyh.review_capture import WorldStateRecorder
  from private_catalog_writer import PrivateCatalogWriter
  from scene_driver import ComplexSceneDriver
  from public_planner_binding import make_public_planner
  binding=json.loads((OWN/'REACH_METHOD_SOURCE_BINDING.json').read_bytes());planner=make_public_planner(scene,reach_source_root=REACH,expected_module_hashes=binding['files_sha256'],method=PROTOCOL['arms'][ARM]['method'],journal=journal,limits=binding['same_limits'])
  config=dict(source_id=SCOPE+'-'+phase,episode_id=SCOPE+'-'+phase,source_group='T-COMPLEX-01-DEV-COMPARISON-NOT-FIT',scene_recipe='registered',suite_case='T-COMPLEX-01-v2',review_scope='Actual three lightweight boxes/ground/remote goal, not task success',selected_object_id='ALL_REGISTERED_V2_NOT_A_SELECTED_SKILL',visual_stride_control_ticks=5,visual_chunk_frames=20,command_chunk_steps=200,max_payload_bytes=1024**3,max_review_state_bytes=256*1024**2,max_compiled_model_cache_bytes=256*1024**2,role='DEV_COMPARISON_NOT_TRAIN',forecast_study_training_authorized=False)
  writer=PrivateCatalogWriter(ChunkedEpisodeWriter(root/'episode',dict(config,joint_names=runtime.push['model'].JOINTS,actor_sha256=json.loads((SDK_ROOT/'MANIFEST.json').read_bytes())['actor_sha256'],physics_dt_s=.005,control_dt_s=.02,VLM_control=False)),root/'original-registered-private-catalog.jsonl');review=WorldStateRecorder(root/'review-state',runtime,config,model_cache_dir=ROOT/'compiled-review-models')
  host=ComplexSceneDriver(components,source_root=SOURCE,bundle=SDK_ROOT,root=root,writer=writer,planner=planner,journal=journal,guard=guard)
  from raw_third_view import OptionalRawThirdView,LiveMuJoCoCamera
  s=scene['third_view'];camera=dict(kind='fixed_free',width=s['width'],height=s['height'],stride_physics_ticks=20,chunk_frames=10,max_bytes=1024**3,lookat=s['lookat'],distance=s['distance'],azimuth=s['azimuth'],elevation=s['elevation'])
  video=OptionalRawThirdView(root/'raw-third-view',enabled=True,source_factory=lambda:LiveMuJoCoCamera(runtime,camera,snapshot=observer.snapshot,unchanged=observer.unchanged),scope_id=SCOPE,episode_id=SCOPE+'-'+phase,program_sha256=pin)
  from model_identity import identity
  model_hash,record=identity(runtime.sim.model);write_new(root/'actual-model-identity.json',dict(model_sha256=model_hash,model=record,program_sha256=pin));write_new(root/'actual-config.json',dict(config=config,scene_sha256=PROTOCOL['scene_sha256'],scope_caps=CAPS,method=PROTOCOL['arms'][ARM]['method'],camera=camera))
  host._native_guards();host._contact_guard();guard(force=True)
  if phase=='zero':
   before=observer.snapshot();host.capture_grid();guard(force=True);need(observer.unchanged(before,observer.snapshot())and host.tick==runtime.step_count==0 and runtime.sim.data.time==0 and not runtime.sim.queue and writer.steps==0 and writer.frames==1,'Own zero actual same full-host no command or step');need(not host.complete and host.execution is None,'No fabricated task/capture witness');result.update(passed=True,status='OWN_ZERO_PASS',full_host_assembled=True,original_INPUT8_recorded=True,actual_private_catalog_alias_only=True)
  else:
   zero=json.loads((ROOT/'zero/result.json').read_bytes());need(zero['passed']and zero['program_sha256']==pin and zero['actual_model_numeric_sha256']==model_hash,'Same full program own-zero/model, no component reuse')
   while not host.complete:
    guard();host.step_one()
    if host.coordinator is not None and getattr(host.coordinator,'complete',False)and not host.complete:raise Stop('Planner/coordinator ended without original full-task terminal proof')
   guard(force=True,cleanup=True);need(host.execution is not None and host.execution['placements'].current_required()and planner.complete,'Original all placements/final protected stop required');result.update(passed=True,status='COMPLEX_TASK_PASS',task_success=True,distinct_original_placement_count=len(host.execution['placements'].records),actual_capture_witness=host.execution['initial_witness'].report())
 except BaseException as e:
  result.update(passed=False,status='FAILED_NO_RETRY',error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc(),resource_censored=isinstance(e,Stop)and any(v in str(e).lower()for v in('cap','watchdog','headroom','budget')),method_failure_not_inferred_from_infra=True)
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);sim=float(runtime.sim.data.time)if runtime is not None else None
  for name,fn in [('raw_third_view',lambda:video.close()if video is not None else None),('review',lambda:review.close()if review is not None and not review.closed else None),('episode',lambda:writer.close(outcome=result['status'],terminal_time_s=sim or 0.,censored=not result['passed'])if writer is not None and not writer.closed else None),('observer',lambda:observer.close()if observer is not None else None)]:
   try:
    value=fn()
    if value is not None:result[name+'_closure']=value
   except BaseException as e:errors.append(dict(stage=name,error=repr(e)))
  if journal is not None:
   try:journal(dict(event='Data_T_complex_teardown',phase=phase,close_errors=errors));journal.close()
   except BaseException as e:errors.append(dict(stage='journal',error=repr(e)))
  if lease is not None:
   try:result['last_GPU_observation']=lease.check(force=True);result['peak_observed_own_GPU_bytes']=lease.peak_own_compute_bytes
   except BaseException as e:errors.append(dict(stage='GPU',error=repr(e)))
  result.update(close_errors=errors,actual_main_world_sim_s=sim,task_physics_steps=runtime.step_count if runtime is not None else None,actual_auxiliary_calibration=runtime.wm_auxiliary_calibration if runtime is not None else None,usage_known=known,actual_model_numeric_sha256=model_hash,observed_process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,wall_s=time.monotonic()-start,actual_recorded_commands=writer.written_steps if writer is not None else None,actual_recorded_visual_frames=writer.written_frames if writer is not None else None,actual_method_status=getattr(planner,'status',None),same_source_original_native_control=True)
  if errors:result.update(passed=False,status='TEARDOWN_FAILED_NO_RETRY')
  if result['passed']and not(result.get('episode_closure',{}).get('storage_complete')and result['actual_recorded_commands']==result['task_physics_steps']):result.update(passed=False,status='INCOMPLETE_COMMAND_EVIDENCE_NO_RETRY')
  result['direct_video_grid_complete']=bool(result.get('raw_third_view_closure',{}).get('complete_for_capture_grid'));result['task_video_master_not_created_yet']=True
  if phase=='zero'and result['passed']and not result['direct_video_grid_complete']:result.update(passed=False,status='OWN_ZERO_DIRECT_CAMERA_FAILED_NO_RETRY')
  try:result['cumulative_observed_usage']=ledger.observe(phase,sim_s=used(),wall_s=time.monotonic()-start,cleanup=True)
  except BaseException as e:result.update(passed=False,status='BUDGET_FINAL_USAGE_FAILED_NO_RETRY',budget_close_error=repr(e))
  try:
   write_new(root/'result.json',result);ledger.close(phase,result['status'],sim_s=used(),wall_s=time.monotonic()-start,report_sha=sha(root/'result.json'),usage_known=known)
  finally:
   if lease is not None:lease.__exit__()
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=('prepare','zero','main'),default='prepare');ap.add_argument('--program-sha256',required=True);args=ap.parse_args()
 if args.phase=='prepare':
  def fence(event,values):
   if event=='import'and str(values[0]).split('.')[0]in('torch','mujoco','onnxruntime'):raise Stop('Default prepare forbids all native/Actor imports')
  sys.addaudithook(fence);prepare(args.program_sha256);value=dict(prepared=True,constructor_or_physics_started=False,arm=ARM,program_sha256=args.program_sha256,full_public_method_factory_checked=True);write_new(M/ARM/'fenced-prepare.json',value)
 else:value=run(args.phase,args.program_sha256)
 print(json.dumps(value,ensure_ascii=False));sys.exit(0 if value.get('passed',value.get('prepared'))else 1)
