"""Real original E method, required task0 own-zero then one full-goal main.
No WM/VLM/critic/optional prefix. New source/asset/scope; never resume a component.
"""
from pathlib import Path
import os,sys,json,time,hashlib,datetime,argparse,traceback,signal,resource
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='V4-E-first-direct-live-46308-20261116-v3';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';AUTH=B/'registry/V4_E_FIRST_AUTHORITY_20261116_v3.json';KEY='active_V4_E_first_main_v3_scope';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';SDK=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle');SOURCE=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source';ADAPTER=B/'development/bulk-resource-adapter-46308-20261115-v1';C=json.loads((W/'protocol.json').read_bytes());S=R/'runtime/workers'/C['scope_id'];PHASE='zero';ROOT=S/'zero';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat()
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def write(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def authority():
 h=json.loads(H.read_bytes());need(not h['bulk24_collector_v1']['global_stop'],'Do not bypass shared source/resource stop');q=h[KEY];a=json.loads(AUTH.read_bytes());need(h['executing_thread_id']==q['owner']==OWNER and q['active']and q['scope_id']==C['scope_id'],'Actual E owner/scope');need(q['authorization_sha256']==sha(AUTH)and a['own_zero_max']==a['main_max']==1,'One E own-zero/main only');need(all(not v['active']for k,v in h.items()if k.startswith('active_')and k!=KEY and isinstance(v,dict)and'active'in v),'Old scopes closed; no concurrent other Data worker');return h,q,a

def prepare(pin):
 need({'ffmpeg_path', 'ffmpeg_sha256', 'cameras', 'main_task_step_cap', 'scene_sha256', 'own_GPU_cap_bytes', 'main_task_sim_cap_s', 'model_sha256', 'GPU_UUID', 'own_RSS_cap_bytes', 'plan_sha256', 'zero_wall_cap_s', 'source_commit', 'model_path', 'scope_id', 'appearance_revision', 'output_cap_bytes', 'camera_candidates', 'main_wall_cap_s'}<=C.keys(),'Complete E protocol before native imports');need(C['cameras']==C['camera_candidates'],'Exact shared camera candidates')
 need(sha(M/'program-freeze.json')==pin,'Exact E complete program');freeze=json.loads((M/'program-freeze.json').read_bytes())
 for name,digest in freeze['files'].items():
  p=Path(name);need(not p.is_symlink()and(p.resolve().is_relative_to(R)or p.resolve().is_relative_to(SDK))and sha(p)==digest,'E frozen source/SDK/asset drift: '+name)
 need(sys.prefix=='/mnt/yuanyue/data-team/env-native-v1'and sys.version_info[:3]==(3,11,16),'Exact private interpreter');need(os.environ.get('CUDA_VISIBLE_DEVICES')==C['GPU_UUID']and os.environ.get('MUJOCO_GL')=='egl'and os.environ.get('MUJOCO_EGL_DEVICE_ID')=='0','E exact GPU/EGL');need(os.environ.get('LD_PRELOAD')==str(R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1'),'Private XML loader');authority();sys.path[:0]=[str(W),str(W/'inputs/ainav/development/complex_v4_four_arm_v1'),str(SOURCE),str(ADAPTER),str(B/'workers/new-critic-cohort-46308-20261115-v1')]
 import e_entry,native_entry
 need(e_entry.build_E_driver(enabled=False)is None and native_entry.construct_cold_components(enabled=False)is None,'Default-off E/native entries');return freeze

def run(pin,phase):
 global PHASE,ROOT
 PHASE=phase;ROOT=S/phase;start=time.monotonic();prepare(pin);_,q,_=authority();need(q['zero_dispatch_count']==1 and(phase=='zero'and q['main_dispatch_count']==0 or phase=='main'and q['main_dispatch_count']==1 and q['zero_passed']and q['camera_sha256']is not None),'Explicit own-zero/main CAS');need(not ROOT.exists(),'Never reopen phase');ROOT.mkdir(parents=True);write(ROOT/'claim.json',dict(at=now(),PID=os.getpid(),scope=C['scope_id'],phase=phase,program_sha256=pin))
 from fresh_size import fresh_size
 from per_gpu_lease import PerGpuLease
 from raw_third_view import LiveMuJoCoCamera,OptionalRawThirdView
 from private_catalog_boundary import PrivateCatalogBoundaryWriter
 lease=runtime=observer=writer=driver=journal=video=None;errors=[];metrics={};progress=None;cap=float(C['zero_wall_cap_s']if phase=='zero'else C['main_wall_cap_s']);result=dict(scope_id=C['scope_id'],phase=phase,program_sha256=pin,source_commit=C['source_commit'],PID=os.getpid(),passed=False,method='E_original_RuleBaseline_full_V4_goal_attempt'if phase=='main'else'E_technical_own_zero_NOT_main',full_task_success=False,VLM_calls=0,WM_calls=0,fit_calls=0,training_allowed=False,main_invocations=int(phase=='main'),automatic_retry=False,asset_sha256=C['model_sha256'])
 def guard():
  begin=time.monotonic()
  try:
   authority()
   if lease is not None:lease.check()
   t=sys.modules.get('torch')
   if t is not None and t.cuda.is_initialized():need(t.cuda.memory_reserved()<=C['own_GPU_cap_bytes']and t.cuda.max_memory_reserved()<=C['own_GPU_cap_bytes'],'Own GPU cap')
   need(time.monotonic()-start<cap-30,'E finite wall cap with teardown reserve');need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=C['own_RSS_cap_bytes'],'Own RSS cap');need(fresh_size(S)<C['output_cap_bytes']-64*1024**2,'E scope output cap with reports/codec reserve')
  finally:
   m=metrics.setdefault('Data_guard_inclusive',dict(calls=0,wall_s=0.));m['calls']+=1;m['wall_s']+=time.monotonic()-begin
 def timeout(*_):raise RuntimeError('E hard wall deadline no retry')
 signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,cap-10);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.nice(15)
 try:
  import torch
  torch.set_num_threads(2);lease=PerGpuLease(physical_index=0,authority_check=authority).__enter__();write(ROOT/'resource-lease.json',dict(locks=lease.rows,GPU=lease.last_gpu));from ainav.evidence import Journal
  journal=Journal(ROOT/'events.jsonl');import native_entry,e_entry
  need(sha(C['model_path'])==C['model_sha256'],'Existing qualified STATIC new-palette bytes, not old state');components=native_entry.construct_cold_components(source_root=SOURCE,bundle=SDK,model_path=Path(C['model_path']),model_sha256=C['model_sha256'],scene_path=W/'inputs/ainav/development/complex_v4_four_arm_v1/scene.json',expected_scene_sha256=C['scene_sha256'],guard=guard,journal=journal,actor_device='cuda:0',enabled=True);runtime=components['runtime'];observer=components['observer'];need(runtime.step_count==0 and float(runtime.sim.data.time)==0 and not runtime.sim.queue,'Fresh task0/FIFO');need(runtime.wm_auxiliary_calibration['worlds']==1 and runtime.wm_auxiliary_calibration['sim_seconds']<=10.5,'Original separately-accounted auxiliary stance');guard()
  from mujoco_zyh.streams import ChunkedEpisodeWriter
  meta=dict(source_id=C['scope_id'],episode_id=C['scope_id']+'-'+phase,role='E_MAIN_DIRECT_LIVE'if phase=='main'else'E_TECHNICAL_ZERO_NOT_MAIN',source_group=C['scope_id'],forecast_study_training_authorized=False,max_payload_bytes=768*1024**2,command_chunk_steps=200,visual_chunk_frames=32,visual_stride_control_ticks=5,joint_names=runtime.push['model'].JOINTS,actor_sha256=json.loads((SDK/'MANIFEST.json').read_bytes())['actor_sha256'],program_sha256=pin,whole_artifact_model_input_allowed=False,appearance_revision=C['appearance_revision'])
  writer=PrivateCatalogBoundaryWriter(ChunkedEpisodeWriter(ROOT/'episode',meta));driver=e_entry.build_E_driver(components,source_root=SOURCE,bundle=SDK,output_root=ROOT,writer=writer,journal=journal,guard=guard,enabled=True);need(driver.planner.__class__.__name__=='RuleBaseline'and driver.planner.method=='E_public_geometry_engineering_rule_v1','True original E, not engineering component');need(hasattr(runtime,'staircase')and runtime.staircase is not None,'Real source57 registered terrain installed, no dummy')
  if phase=='zero':
   from PIL import Image
   frames=[]
   for i,spec in enumerate(C['camera_candidates']):
    cam=LiveMuJoCoCamera(runtime,spec,snapshot=observer.snapshot,unchanged=observer.unchanged)
    try:
     tick,stamp,rgb=cam.frame();need(tick==0 and stamp==0,'Zero camera cannot advance task');p=ROOT/('camera-%d.png'%i);Image.fromarray(rgb).save(p);frames.append(dict(index=i,path=str(p),sha256=sha(p),spec=spec))
    finally:cam.close()
   need(runtime.step_count==0 and not runtime.sim.queue,'Technical zero has no task commands');result.update(passed=True,status='E_TECHNICAL_ZERO_PASS_NEEDS_FROZEN_CAMERA_CHOICE_NOT_MAIN',camera_frames=frames,task_commands=0)
  else:
   chosen=q['camera_spec'];need(hashlib.sha256(json.dumps(chosen,sort_keys=True,separators=(',',':')).encode()).hexdigest()==q['camera_sha256'],'Pre-main frozen camera');video=OptionalRawThirdView(ROOT/'direct-third-view',enabled=True,source_factory=lambda:LiveMuJoCoCamera(runtime,chosen,snapshot=observer.snapshot,unchanged=observer.unchanged),scope_id=C['scope_id'],episode_id=C['scope_id']+'-main',program_sha256=pin);need(video.status=='CAPTURING','Direct video init required after zero');video.capture_if_due();progress=(ROOT/'progress.jsonl').open('x')
   while not driver.complete:
    need(runtime.step_count<C['main_task_step_cap']and float(runtime.sim.data.time)<C['main_task_sim_cap_s'],'E finite task cap; no retry');guard();before=runtime.step_count;began=time.monotonic()
    try:driver.step_one()
    finally:
     if runtime.step_count>before:video.capture_if_due()
     row=metrics.setdefault('actual_driver_step',dict(calls=0,commands=0,wall_s=0.));row['calls']+=1;row['commands']+=runtime.step_count-before;row['wall_s']+=time.monotonic()-began
     if runtime.step_count>before and runtime.step_count%400==0:progress.write(json.dumps(dict(at=now(),task_steps=runtime.step_count,time_s=float(runtime.sim.data.time),wall_s=time.monotonic()-start,method='E',metrics=metrics))+'\n');progress.flush()
   need(driver.complete and driver.planner.complete,'Only actual source terminal proof confirms complete E');result.update(passed=True,status='E_V4_ORIGINAL_COMPLETE_TASK_SUCCESS',full_task_success=True)
 except BaseException as e:result.update(status='E_REAL_MAIN_STOP_NO_RETRY'if phase=='main'else'E_TECHNICAL_ZERO_FAILED_NO_MAIN',error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc(),resource_censored='finite'in str(e)or'wall'in str(e),native_success_or_failure_label_not_inferred_from_exception=True)
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  if progress is not None:progress.close()
  if driver is not None:
   result['E_rule']=dict(decisions=driver.planner.decision_count,native_semantic_successes=driver.planner.native_success_count,placed=sorted(driver.planner.placed),support_height=driver.planner.support_height,complete=driver.planner.complete);result['factor_counts']=dict(driver._v4_factor_journal.counts)
   try:driver.close_metadata_workers()
   except BaseException as e:errors.append(dict(stage='metadata_close',error=repr(e)))
  if writer is not None:
   try:result['episode_closure']=writer.close(outcome=result['status'],terminal_time_s=float(runtime.sim.data.time),censored=not result['passed'])
   except BaseException as e:errors.append(dict(stage='writer_close',error=repr(e)))
  if video is not None:
   try:result['direct_video_raw_closure']=video.close()
   except BaseException as e:errors.append(dict(stage='video_close',error=repr(e)))
  if observer is not None:
   try:observer.close()
   except BaseException as e:errors.append(dict(stage='observer_close',error=repr(e)))
  if runtime is not None:result.update(actual_task_steps=runtime.step_count,actual_task_sim_s=float(runtime.sim.data.time),actual_auxiliary_calibration=runtime.wm_auxiliary_calibration)
  if lease is not None:
   try:result['final_GPU']=lease.check(force=True)
   except BaseException as e:errors.append(dict(stage='final_GPU',error=repr(e)))
   lease.__exit__()
  result.update(close_errors=errors,wall_s=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,usage_known=runtime is not None,metrics=metrics,guard_and_step_times_overlap=True)
  if errors:result['passed']=False
  write(ROOT/'result.json',result);write(ROOT/'ledger.json',dict(scope_id=C['scope_id'],phase=phase,closed=True,result_sha256=sha(ROOT/'result.json'),actual_task_sim_s=result.get('actual_task_sim_s'),actual_aux_sim_s=None if runtime is None else runtime.wm_auxiliary_calibration['sim_seconds'],wall_s=result['wall_s'],usage_known=result['usage_known'],output_bytes=fresh_size(S),main_calls=int(phase=='main'),automatic_retry=False))
 print(json.dumps(result));return 0 if result['passed']else 1
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=('prepare','zero','main'),required=True);p.add_argument('--program-sha256',required=True);a=p.parse_args()
 if a.phase=='prepare':prepare(a.program_sha256);print(json.dumps(dict(prepared=True,native_called=False)))
 else:sys.exit(run(a.program_sha256,a.phase))
