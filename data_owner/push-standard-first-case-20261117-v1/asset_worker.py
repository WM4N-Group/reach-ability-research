"""One opt-in original-standard static asset worker; NOT a skill test/own-zero."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from standard_asset import CASE, QUESTION, build, declaration

OWNER='01a1e4e1-3037-7333-9019-a3f37effe5da'
UUID='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'
SCOPE='data-46308-PUSH-standard-static-asset-20261117-v1'


def need(ok,message):
    if not ok:raise RuntimeError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(config_path=None,pin=None,*,enabled=False):
    if enabled is not True:return None
    c=json.loads(Path(config_path).read_bytes())
    need(c['scope_id']==SCOPE and c['owner']==OWNER and c['question']==QUESTION and c['case']==CASE,'One new explicit standard asset case')
    need(c['static_asset_max']==1 and c['world_constructor_max']==1 and c['main_max']==c['own_zero_max']==c['retry_max']==0,'Only one static constructor, never physics/own-zero/retry')
    need((c['wall_cap_s'],c['RSS_cap_bytes'],c['GPU_cap_bytes'])==(120,4<<30,3<<30),'Original finite memory caps')
    need((c['interval_s'],c['max_oldest_age_s'])==(1,2),'Original probe/oldest policy unchanged')
    need(c['output_cap_bytes']==256<<20 and c['reserve_bytes']==32<<20 and c['model_buffer_cap_bytes']==128<<20 and c['disk_floor_bytes']==2<<30,'Bound asset, transient RAM buffer and disk floor')
    need(sha(c['freeze_path'])==pin,'New complete static program freeze')
    f=json.loads(Path(c['freeze_path']).read_bytes())
    need(f['question']==QUESTION and f['scope_id']==SCOPE,'No old program/authority borrowing')
    for p,d in f['files'].items():need(not Path(p).is_symlink()and sha(p)==d,'Frozen source drift: '+p)
    need(sys.prefix=='/mnt/yuanyue/data-team/env-native-v1'and sys.version_info[:3]==(3,11,16),'Actual private interpreter')
    need(os.environ.get('CUDA_VISIBLE_DEVICES')==UUID and os.environ.get('MUJOCO_GL')=='egl'and os.environ.get('MUJOCO_EGL_DEVICE_ID')=='0'and os.environ.get('LD_PRELOAD')==c['LD_PRELOAD'],'Original UUID/EGL/loader environment')
    sys.path[:0]=c['import_paths']
    import torch,mujoco
    from plugins import Plugin
    from ainav.native import scene_registry
    from mujoco_zyh.source_bundle import verify_bundle
    from camera_abi import install_original_camera,verify_compiled_camera
    reg=declaration(scene_registry,enabled=True)
    need(list(reg.objects)==['sdk_box']and reg.objects['sdk_box'].size_m==(1.2,1.2,.2),'Actual generic registry accepts standard box without weakening V4')
    need(not torch.cuda.is_initialized(),'CPU prepare cannot initialize CUDA')
    need(build(enabled=False)is None,'Default-OFF new static constructor')
    return c


def run(config_path=None,pin=None,*,enabled=False):
    if enabled is not True:return None
    started=time.monotonic();c=prepare(config_path,pin,enabled=True)
    from scoped_io import ScopeIO
    from runner_outputs import write_json,finish_accounting
    from fd_capture import FDCapture
    from fast_health import make_original_fast_health
    from resource_watch import ResourceWatch
    from timed_probe import make_timed_scope_probe
    from per_gpu_lease import PerGpuLease
    import torch,shutil
    H,A=Path(c['handoff']),Path(c['authority']);auth_sha=sha(A)
    def authority():
        h=json.loads(H.read_bytes());q=h[c['key']]
        need(h['executing_thread_id']==q['owner']==OWNER and q['active'],'Actual live owner/scope')
        need(q['scope_id']==SCOPE and q['asset_PID']==os.getpid()and q['phase']=='STANDARD_STATIC_ASSET_ONLY_NO_ACTOR_OR_STEPS','Actual static asset PID/phase')
        need(q['static_asset_dispatch_count']==1 and q['zero_dispatch_count']==q['main_dispatch_count']==0 and q['program_sha256']==pin,'One asset count only, no own-zero/main reuse')
        need(q['authorization_sha256']==auth_sha==sha(A),'Exact new static authority')
        need(not h['bulk24_collector_v1']['global_stop']and not q.get('stop_requested',False),'Original stop latch')
        need(all(not row.get('active',False)for k,row in h.items()if k!=c['key']and isinstance(row,dict)),'No competing Data physical authority')
    gate=time.monotonic()
    while json.loads(H.read_bytes())[c['key']]['asset_PID']is None:
        need(time.monotonic()-gate<3,'Actual PID must be bound before original lease');time.sleep(.01)
    authority();root=Path(c['output']);need(not root.exists(),'Never reuse a static asset root');root.mkdir(parents=True)
    budget=ScopeIO(root,cap_bytes=c['output_cap_bytes'],reserve_bytes=c['reserve_bytes']);state=budget.state
    lease=watch=capture=producer=None;errors=[]
    counters=dict(world_constructors_started=0,world_constructors_completed=0,additional_static_compiles_completed=0)
    result=dict(scope_id=SCOPE,question=QUESTION,program_sha256=pin,PID=os.getpid(),passed=False,
        zero_dispatch_count=0,main_dispatch_count=0,Actor_load_forward_Runtime_Renderer_physics_commands=0,
        actual_task_sim_s=None,asset=None,automatic_retry=False,static_asset_not_skill_result_or_own_zero=True)
    def timeout(*_):raise RuntimeError('Original bounded asset wall deadline')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,c['wall_cap_s']-10)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.nice(15)
    health=make_original_fast_health(torch,state=state,start_mono=started,wall_cap_s=c['wall_cap_s'],rss_cap_bytes=c['RSS_cap_bytes'],gpu_cap_bytes=c['GPU_cap_bytes'])
    try:
        capture=FDCapture(budget,stdout_path=root/'stdout.bin',stderr_path=root/'stderr.bin',enabled=True)
        lease=PerGpuLease(physical_index=0,authority_check=authority).__enter__()
        producer=make_timed_scope_probe(lease,budget,min_free_bytes=c['disk_floor_bytes'],disk_free=lambda p:shutil.disk_usage(p).free,enabled=True)
        watch=ResourceWatch(producer,state=state,token=object(),interval_s=1,max_stale_s=2,fast_health=health).start()
        result['asset']=build(c,budget,watch,counters,enabled=True)
        result['actual_task_sim_s']=result['asset']['actual_original_constructor_task_sim_s']
        watch();need(not torch.cuda.is_initialized(),'Static model never initializes CUDA');result['passed']=True
    except BaseException as exc:
        result.update(error_type=type(exc).__name__,error_message=str(exc),resource_failure=state.reason)
    finally:
        budget.begin_finalization()
        if watch is not None:
            try:watch.close()
            except BaseException as exc:errors.append(dict(stage='watch_close',error_type=type(exc).__name__))
        if producer is not None and producer.last_attempt is not None:result['last_original_producer_attempt']=asdict(producer.last_attempt)
        if watch is not None:result['original_watch']=dict(interval_s=watch.interval,max_oldest_age_s=watch.max_stale,successful_probe_calls=watch.probe_calls,oldest_completed_pair=watch.last_observation_stamp,probe_wall_s=watch.probe_wall_s)
        if lease is not None:
            result['last_original_GPU_observation']=lease.last_gpu
            try:lease.__exit__()
            except BaseException as exc:errors.append(dict(stage='lease_close',error_type=type(exc).__name__))
        if capture is not None:
            try:result['FD_capture']=capture.close()
            except BaseException as exc:errors.append(dict(stage='FD_close',error_type=type(exc).__name__))
        signal.setitimer(signal.ITIMER_REAL,0)
        result.update(counters=counters,close_errors=errors,wall_s=time.monotonic()-started,RSS_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            original_fast_health=health.metrics,resource_failure=state.reason,CUDA_initialized=torch.cuda.is_initialized())
        if errors or state.reason is not None:result['passed']=False
        write_json(budget,root/'result.json',result);finish_accounting(budget,root/'final-output-accounting.json')
    return 0 if result['passed']else 3


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--enabled',action='store_true');p.add_argument('--prepare',action='store_true');p.add_argument('--config');p.add_argument('--pin');a=p.parse_args()
    if a.enabled:
        if a.prepare:
            prepare(a.config,a.pin,enabled=True);print(json.dumps(dict(stage='STANDARD_ASSET_ACTUAL_CPU_PREPARE_NO_WORLD_OR_ACTOR',program_sha256=a.pin,CUDA_initialized=False,Runtime_world_lease_API_calls=0)))
        else:raise SystemExit(run(a.config,a.pin,enabled=True))
