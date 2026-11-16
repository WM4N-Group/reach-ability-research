"""ONE static cold-MJB compile. Original SDK bridge task0 only; no Runtime/Actor/step/retry."""
from pathlib import Path
import os,sys,json,hashlib,time,datetime,signal,resource,traceback
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='E20-prearrival40-direct-live-46308-20261116-v2';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';KEY='active_E20_prearrival40_v2_scope';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';C=json.loads((M/'asset-compile-protocol.json').read_bytes());SOURCE=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source';SDK=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle');ADAPTER=B/'development/bulk-resource-adapter-46308-20261115-v1';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();start=time.monotonic();lease=None;errors=[];result=dict(scope_id=C['scope_id'],source_commit=C['source_commit'],phase='STATIC_COMPILE_ONLY',PID=os.getpid(),passed=False,actual_task_steps=0,actual_aux_sim_s=0.,Actor_forwards=0,Runtime_calls=0,automatic_retry=False)
def need(v,msg):
 if not v:raise RuntimeError(msg)
def authority():
 h=json.loads(H.read_bytes());q=h[KEY];need(h['executing_thread_id']==q['owner']==OWNER and q['active']and q['phase']=='STATIC_ASSET_DISPATCHED'and q['asset_compile_dispatch_count']==1 and q['zero_dispatch_count']==q['main_dispatch_count']==0,'One static compile authority only');need(not h['bulk24_collector_v1']['global_stop']and all(not v['active']for k,v in h.items()if k.startswith('active_')and k!=KEY and isinstance(v,dict)and'active'in v),'No shared stop or another Data active');return h,q
sys.path[:0]=[str(W),str(W/'inputs/ainav'/C['source_relative_path']),str(SOURCE),str(ADAPTER)]
from fresh_size import fresh_size
from per_gpu_lease import PerGpuLease
def guard():
 authority();need(time.monotonic()-start<C['compile_wall_cap_s']-30,'Static compile finite wall cap');need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=C['own_RSS_cap_bytes'],'Static compile own RSS4GiB cap');out=Path(C['model_path']).parent
 if out.exists():need(fresh_size(out)<C['output_cap_bytes']-64*1024**2,'Static asset bytes cap/reserve')
 if lease is not None:lease.check()
try:
 authority();freeze=json.loads((M/'asset-compile-freeze.json').read_bytes());need(sha(M/'asset-compile-freeze.json')==authority()[1]['asset_compile_freeze_sha256'],'Exact immutable compile subset');need(all(not Path(p).is_symlink()and sha(p)==pin for p,pin in freeze['files'].items()),'Static compile source/SDK drift');need(sys.version_info[:3]==(3,11,16)and sys.prefix=='/mnt/yuanyue/data-team/env-native-v1','Exact private interpreter');need(os.environ['CUDA_VISIBLE_DEVICES']==C['GPU_UUID'],'Only GPU0');out=Path(C['model_path']);need(not out.parent.exists(),'Fresh static asset root only');out.parent.mkdir(parents=True)
 def timeout(*_):raise RuntimeError('Static compile hard deadline no retry')
 signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,C['compile_wall_cap_s']-10);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.nice(15)
 import torch
 torch.set_num_threads(2);lease=PerGpuLease(physical_index=0,authority_check=authority).__enter__();guard();import native_entry
 asset=native_entry.compile_static_asset(source_root=SOURCE,bundle=SDK,output_model=out,scene_path=W/'inputs/ainav'/C['source_relative_path']/'scene.json',expected_scene_sha256=C['scene_sha256'],guard=guard,enabled=True);need(asset['actual_main_steps']==asset['Actor_forwards']==0 and asset['model_sha256']==sha(out),'Only true cold static model, no task/Actor');result.update(passed=True,asset=asset)
except BaseException as e:result.update(error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc())
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 if lease is not None:
  try:result['final_GPU']=lease.check(force=True)
  except BaseException as e:errors.append(repr(e))
  lease.__exit__()
 result.update(wall_s=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,close_errors=errors,usage_known=True)
 if errors:result['passed']=False
 with(M/'asset-compile-result.json').open('x')as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(result));sys.exit(0 if result['passed']else 1)
