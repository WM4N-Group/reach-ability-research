"""Finite read-only OS/CPU separation; NOT held lease/old-failure replay or repair.
Two pairs of the original GPU0 NVML queries, no GPU/Runtime/Actor/lease creation.
The one synthetic GIL hold affects only THIS diagnostic Python process.
"""
import argparse,ctypes,hashlib,json,os,subprocess,sys,threading,time
from pathlib import Path
UUID='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'
QUERIES=[['nvidia-smi','--id='+UUID,'--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],
         ['nvidia-smi','--id='+UUID,'--query-compute-apps=pid,used_gpu_memory,gpu_uuid','--format=csv,noheader,nounits']]
CHILD='''import hashlib,json,subprocess,time
queries=json.loads(__import__('sys').argv[1]);started=time.monotonic();print("READY",flush=True);rows=[]
for args in queries:
 s=time.monotonic();p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10);e=time.monotonic()
 if len(p.stdout)>65536 or len(p.stderr)>8192:raise ValueError("Bounded original NVML metadata output")
 rows.append(dict(args=args,started=s,completed=e,wall_s=e-s,returncode=p.returncode,stdout_bytes=len(p.stdout),stdout_sha256=hashlib.sha256(p.stdout).hexdigest(),stderr_bytes=len(p.stderr)))
 if p.returncode:break
print(json.dumps(dict(started=started,completed=time.monotonic(),queries=rows,not_owner_observation=True),sort_keys=True),flush=True)
'''

def run_pair(hold_s):
    ready=threading.Event();result={};error=[]
    def probe():
        result['parent_started']=time.monotonic();p=None
        try:
            p=subprocess.Popen([sys.executable,'-I','-B','-c',CHILD,json.dumps(QUERIES)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            if p.stdout.readline(16)!=b'READY\n':raise RuntimeError('Bounded query subprocess readiness')
            result['parent_received_ready']=time.monotonic();ready.set()
            raw,err=p.communicate(timeout=25)
            if len(raw)>65536 or len(err)>8192 or p.returncode:raise RuntimeError('Bounded readonly query helper failed')
            result['child']=json.loads(raw)
        except BaseException as exc:
            error.append(type(exc).__name__);ready.set()
            if p is not None and p.poll()is None:p.kill();p.wait(timeout=5)
        finally:result['parent_completed']=time.monotonic()
    thread=threading.Thread(target=probe,daemon=True);thread.start()
    if not ready.wait(10):raise TimeoutError('No readiness; no repeat')
    hold_start=hold_end=None
    if hold_s:
        # PyDLL deliberately retains THIS process GIL across a sleeping libc call.
        # No CPU busy-loop/peer process/environment/runtime/physics interaction.
        lib=ctypes.PyDLL('libc.so.6');sleep=lib.usleep;sleep.argtypes=[ctypes.c_uint];sleep.restype=ctypes.c_int
        hold_start=time.monotonic();ret=sleep(int(hold_s*1000000));hold_end=time.monotonic()
        if ret!=0:raise RuntimeError('Synthetic own-process GIL hold interrupted')
    thread.join(timeout=35)
    if thread.is_alive():raise TimeoutError('Bounded readonly thread did not finish')
    result.update(error_types=error,synthetic_own_process_GIL_hold_requested_s=hold_s,
                  hold_started=hold_start,hold_completed=hold_end,
                  parent_elapsed_s=result['parent_completed']-result['parent_started'],
                  synthetic_not_actual_D3_constructor=True,owner_stamp_or_GPU_lease=False)
    child=result.get('child')
    if child:
        result['child_query_total_s']=sum(x['wall_s']for x in child['queries'])
        result['parent_completion_after_child_completed_s']=result['parent_completed']-child['completed']
        result['child_completed_during_own_GIL_hold']=(hold_start is not None and hold_start<=child['completed']<=hold_end)
    return result

def measure(*,enabled=False):
    if enabled is not True:return None
    os.nice(15)
    started=time.monotonic()
    rows=[run_pair(0.),run_pair(2.3)]
    return dict(schema='Data-two-readonly-pairs-parent-vs-independent-child-timing-v1',
        runs=rows,total_wall_s=time.monotonic()-started,actual_NVML_query_count=sum(len(r.get('child',{}).get('queries',[]))for r in rows),
        maximum_NVML_queries=4,original_1s_2s_policy_unchanged=True,ResourceWatch_not_run=True,
        Runtime_Actor_CUDA_context_or_GPU_lease_or_API_or_physics_calls=0,
        actual_D3_zero_leaf_cause_recovered=False,closed_scope_not_reopened=True,
        does_not_qualify_native_or_prove_resource_fix=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--enabled',action='store_true');a=p.parse_args()
    if a.enabled:print(json.dumps(measure(enabled=True),sort_keys=True,indent=2))
