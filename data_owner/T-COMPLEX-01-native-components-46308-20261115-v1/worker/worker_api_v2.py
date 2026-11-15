"""Default-off guarded native component ZERO ONLY. No task commands/AB/fit."""
from pathlib import Path
import os,sys,json,hashlib,time,datetime,signal,resource,argparse,traceback
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='T-COMPLEX-01-native-components-46308-20261115-v1';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';AUTH=B/'registry/T_COMPLEX_NATIVE_COMPONENT_ZERO_API_v2_AUTHORITY_20261115.json';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';ENV=Path('/mnt/yuanyue/data-team/env-native-v1');SDK=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle');SOURCE=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source';ADAPTER=B/'development/bulk-resource-adapter-46308-20261115-v1';EXPAT=R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1';C=json.loads((W/'protocol.json').read_bytes());ROOT=R/'runtime/workers'/C['scope_id'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat()
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def authority():
 h=json.loads(H.read_bytes());q=h['active_T_COMPLEX_component_zero_scope'];a=json.loads(AUTH.read_bytes());need(h['executing_thread_id']==q['owner']==OWNER and q['active']and q['scope_id']==C['scope_id'],'Actual Data component preflight owner/scope');need(q['authorization_sha256']==sha(AUTH)and a['allowed_component_zero_invocations']==1 and a['allowed_task_main_invocations']==0,'One new component-only claim, never task main');need(h['active_new_critic_cohort_scope']['active']is False and h['new_critic_cohort_v1']['TRAIN_native_collection_complete'],'Do not overlap/hot-change frozen TRAIN lifecycle');return h,q,a
def verify(pin):
 p=M/'program-freeze-api-v2.json';need(sha(p)==pin,'Exact component program freeze');v=json.loads(p.read_bytes());need(v['scope_id']==C['scope_id']and v['authorization_sha256']==sha(AUTH),'Frozen component scope/auth')
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
 verify(pin);authority();sys.path[:0]=[str(W/'inputs/scene'),str(SOURCE)];import native_construction as src
 need(Path(src.__file__).resolve()==W/'inputs/scene/native_construction.py','Exact new source owner module');need(src.compile_static_asset(enabled=False)is None and src.construct_cold_components(enabled=False)is None,'Default-off source APIs');src._source(SOURCE)
 return src

def run(pin):
 start=time.monotonic();prepare(pin);_,q,_=authority();need(q['component_zero_dispatch_count']==1 and q['component_zero_dispatch_program_sha256']==pin,'Explicit component zero dispatch only');need(not ROOT.exists(),'Never resume/reopen component output root');ROOT.mkdir(parents=True);write(ROOT/'claim.json',dict(at=now(),PID=os.getpid(),program_sha256=pin,phase='component_zero',scope_id=C['scope_id'],task_main=False,invocation=1))
 sys.path[:0]=[str(ADAPTER),str(B/'workers/new-critic-cohort-46308-20261115-v1')]
 from per_gpu_lease import PerGpuLease
 from raw_third_view import LiveMuJoCoCamera,OptionalRawThirdView
 runtime=components=observer=video=lease=journal=None;phase='BEFORE_SOURCE';result=dict(scope_id=C['scope_id'],phase='component_zero',PID=os.getpid(),program_sha256=pin,authorization_sha256=sha(AUTH),source_owner_commit=C['new_source_owner_commit'],passed=False,actual_task_steps=None,actual_auxiliary_calibration=None,full_task_or_AB_admitted=False,comparison_main_calls=0,capture_witness_complete=False,task_videos=0,training_allowed=False,automatic_retry=False);errors=[]
 def guard():
  authority()
  if lease is not None:lease.check()
  torch_module=sys.modules.get('torch')
  if torch_module is not None and torch_module.cuda.is_initialized():need(torch_module.cuda.memory_reserved()<=C['own_GPU_cap_bytes']and torch_module.cuda.max_memory_reserved()<=C['own_GPU_cap_bytes'],'Own Torch3GiB cap')
  need(time.monotonic()-start<165.,'Component180wall cap with teardown reserve');need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=C['own_RSS_cap_bytes'],'Own4GiB RSS cap');size=sum(p.stat().st_size for p in ROOT.rglob('*')if p.is_file());need(size<C['output_cap_bytes']-32*1024**2,'Component output cap with report reserve')
 def timeout(*args):raise RuntimeError('Component preflight wall deadline no retry')
 signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,175.);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.nice(15)
 try:
  import torch,numpy as np
  torch.set_num_threads(2);lease=PerGpuLease(physical_index=0,authority_check=authority).__enter__();write(ROOT/'resource-lease.json',dict(locks=lease.rows,GPU=lease.last_gpu,owner=OWNER))
  from ainav.evidence import Journal
  journal=Journal(ROOT/'events.jsonl');import native_construction as src;phase='STATIC_ASSET_COMPILE'
  model=src.compile_static_asset(source_root=SOURCE,bundle=SDK,output_model=ROOT/'complex-static.mjb',guard=guard,enabled=True);write(ROOT/'native-asset-construction.json',model);phase='NATIVE_MODEL_CAMERA_ABI'
  import mujoco
  check_model=mujoco.MjModel.from_binary_path(str(ROOT/'complex-static.mjb'));camera_names=[check_model.camera(i).name for i in range(check_model.ncam)];write(ROOT/'native-model-camera-ABI.json',dict(cameras=camera_names,offwidth=int(check_model.vis.global_.offwidth),offheight=int(check_model.vis.global_.offheight),nq=check_model.nq,nv=check_model.nv,nu=check_model.nu,step_calls=0,no_MjData_or_replay=True));need('wm_onboard_rgbd'in camera_names,'native_asset_missing_required_onboard_camera:wm_onboard_rgbd');del check_model;phase='COLD_COMPONENTS'
  components=src.construct_cold_components(source_root=SOURCE,bundle=SDK,model_path=ROOT/'complex-static.mjb',model_sha256=model['model_sha256'],guard=guard,journal=journal,actor_device='cuda:0',enabled=True);runtime=components['runtime'];observer=components['observer'];guard()
  need(runtime.step_count==0 and float(runtime.sim.data.time)==0. and not runtime.sim.queue,'No task step, command, replay or capture witness');aux=runtime.wm_auxiliary_calibration;need(aux['worlds']==1 and aux['sim_seconds']<=10.5 and aux['main_world_unchanged'],'Original auxiliary cost, no task recovery')
  phase='LIVE_HD_FRAME';scene=json.loads((W/'inputs/scene/scene.json').read_bytes());s=scene['third_view'];camera=dict(kind='fixed_free',width=s['width'],height=s['height'],stride_physics_ticks=20,chunk_frames=1,max_bytes=16*1024**2,lookat=s['lookat'],distance=s['distance'],azimuth=s['azimuth'],elevation=s['elevation'])
  video=OptionalRawThirdView(ROOT/'raw-third-view-preflight-frame',enabled=True,source_factory=lambda:LiveMuJoCoCamera(runtime,camera,snapshot=observer.snapshot,unchanged=observer.unchanged),scope_id=C['scope_id'],episode_id=C['scope_id']+'-component-zero-NOT-AB',program_sha256=pin);video.capture_if_due();closure=video.close();need(closure['complete_for_capture_grid']and closure['archived_frames']==1,'Actual full-size zero frame, not software or upscale')
  packet,catalog=observer.capture(0,np.zeros(18,dtype=np.float32));need(set(packet)==set(('rgb','depth_m','camera_K','T_base_optical','proprio','actions_previous','action_valid','timestamps_s')),'Original INPUT8 onboard unchanged');need(tuple(packet['rgb'].shape)==(1,1,128,192,3),'Original onboard resolution not replaced by third view');need(runtime.step_count==0 and float(runtime.sim.data.time)==0. and not runtime.sim.queue,'No step during pure capture')
  result.update(passed=True,status='NATIVE_COMPONENT_ZERO_AND_HD_FRAME_PASS_NOT_TASK_READY',actual_task_steps=0,actual_task_time_s=0.,actual_auxiliary_calibration=aux,actual_model_sha256=model['model_sha256'],actual_offscreen_capacity=model['offscreen_capacity'],actual_HD_frame=dict(width=camera['width'],height=camera['height'],frames=1,origin=closure['origin'],source_sha256=closure['metadata_sha256'],not_an_AB_arm_master=True),actual_onboard_INPUT8_shapes={k:list(v.shape)for k,v in packet.items()},capture_is_incomplete_no_witness=components['capture_is_not_yet_complete'],raw_HD_frame_closure=closure);phase='COMPONENTS_CHECKED';guard()
 except BaseException as e:result.update(status='COMPONENT_PREFLIGHT_FAILED_CLOSED_NO_RETRY',failure_stage=phase,error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc())
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
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
