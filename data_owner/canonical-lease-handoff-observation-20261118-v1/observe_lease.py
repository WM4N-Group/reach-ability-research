"""Finite ORIGINAL PerGpuLease ownership observation ONLY; no world/Actor/zero/main.

One enter, no retry, no primitive/binding/flags modification or FD passing. A
source-level exception observer captures bounded actual-site FD/proc evidence
BEFORE original __exit__ closes the failing FD. Success is immediately released
by original __exit__; it is never borrowed as a future simulation lease.
"""
from pathlib import Path
import datetime,fcntl,hashlib,json,os,resource,signal,subprocess,sys,tempfile,time
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace'
H=B/'registry/handoff_current_status_20261115.json';OWNER='01a1e4e1-3037-7333-9019-a3f37effe5da'
QUESTION='CANONICAL_GPU0_ORIGINAL_LEASE_SINGLE_HANDOFF_OBSERVATION_NO_WORLD'
KEY='active_Data_canonical_lease_handoff_observation_20261118_v1_scope'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
now=lambda:datetime.datetime.now().astimezone().isoformat()
def need(ok,msg):
 if not ok:raise ValueError(msg)
def cas(change):
 raw=H.read_bytes();before=json.loads(raw);after=change(json.loads(raw));need({k:v for k,v in after.items()if k!=KEY}=={k:v for k,v in before.items()if k!=KEY},'All old/peer H fields retained')
 d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with H.open('rb')as stream:
   fcntl.flock(stream,fcntl.LOCK_EX);st=os.fstat(stream.fileno());need(stream.read()==raw and H.stat().st_ino==st.st_ino,'H SHA/inode CAS')
   fd,tmp=tempfile.mkstemp(prefix='.Data-lease-observation-',dir=H.parent)
   try:
    os.fchmod(fd,st.st_mode&0o7777)
    with os.fdopen(fd,'wb')as out:out.write((json.dumps(after,ensure_ascii=False,indent=2)+'\n').encode());out.flush();os.fsync(out.fileno())
    need(H.read_bytes()==raw,'H CAS race');os.replace(tmp,H);os.fsync(d)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 finally:os.close(d)
 return dict(before_H_SHA256=hashlib.sha256(raw).hexdigest(),after_H_SHA256=sha(H),directory_file_flock_SHA_inode_CAS_atomic_replace=True,old_peer_values_preserved=True,mode_preserved=(H.stat().st_mode&0o7777)==(st.st_mode&0o7777))
def proc_scripts():
 rows=[]
 for d in Path('/proc').iterdir():
  if not d.name.isdigit()or int(d.name)==os.getpid():continue
  try:argv=(d/'cmdline').read_bytes().split(b'\0')
  except OSError:continue
  scripts=[x.decode(errors='replace')for x in argv if x.startswith(b'/mnt/yuanyue/')and x.endswith(b'.py')and len(x)<512]
  if any('/v-jepa/collection/'in x or str(B/'workers')+'/'in x or str(R/'runtime/workers')+'/'in x for x in scripts):rows.append(dict(PID=int(d.name),script_paths=scripts))
 return rows

def snapshot_fd_site(lease,frame=None):
 """Bounded proc metadata, not argv/env/credentials; no acquire/check/unlock."""
 started=time.monotonic();out=dict(at=now(),PID=os.getpid(),own_fds=[],proc_locks=[],canonical_open_refs=[],proc_scan_complete=False)
 for fd in lease.fds[:2]:
  try:out['own_fds'].append(dict(FD=fd,fdinfo=Path(f'/proc/self/fdinfo/{fd}').read_text()[:2048],metadata_only_not_passed_FDs=True))
  except OSError as e:out['own_fds'].append(dict(FD=fd,error_type=type(e).__name__))
 if frame is not None:
  row=frame.f_locals.get('row');fd=frame.f_locals.get('fd')
  out['actual_site_row']=dict(row)if type(row)is dict else None;out['actual_site_fd']=fd if type(fd)is int else None
  out['line']=frame.f_lineno;out['instruction_offset']=frame.f_lasti
  spans=list(frame.f_code.co_positions());i=frame.f_lasti//2
  if 0<=i<len(spans):out['source_position']=spans[i]
 inos={'3428729629','3428729630','3428459217','3428459218'}
 try:out['proc_locks']=[s for s in Path('/proc/locks').read_text().splitlines()if len(s.split())>5 and s.split()[5].split(':')[-1]in inos][:16]
 except OSError as e:out['proc_lock_read_error']=type(e).__name__
 # Bounded 0.25s/128 processes/16 refs; absence is NOT global idle/ownership proof.
 for count,p in enumerate(Path('/proc').iterdir()):
  if count>=512 or time.monotonic()-started>.25 or len(out['canonical_open_refs'])>=16:break
  if not p.name.isdigit():continue
  try:
   for n,fd in enumerate((p/'fd').iterdir()):
    if n>=128 or time.monotonic()-started>.25:break
    try:
     target=os.readlink(fd)
     if target not in {str(R/f'resource-locks/native-observer-{kind}-gpu{g}.lock')for kind in ('physics','sdk')for g in (0,1)}:continue
     info=(p/'fdinfo'/fd.name).read_text();out['canonical_open_refs'].append(dict(PID=int(p.name),FD=int(fd.name),canonical_path=target,fdinfo_lock_lines=[s for s in info.splitlines()if s.startswith('lock:')],open_reference_not_ownership=True))
    except OSError:continue
  except OSError:continue
 else:out['proc_scan_complete']=True
 out['read_wall_s']=time.monotonic()-started;out['absence_not_idle_or_failed_holder_proof']=True
 # Source/fs options are omitted: record only non-secret filesystem type/device.
 try:
  candidates=[]
  for line in Path('/proc/self/mountinfo').read_text().splitlines():
   left,right=line.split(' - ',1);a=left.split();b=right.split()
   if str(R).startswith(a[4].rstrip('/')+'/')or str(R)==a[4]:candidates.append((len(a[4]),dict(mountpoint=a[4],device=a[2],fstype=b[0])))
  out['canonical_filesystem']=max(candidates,key=lambda x:x[0])[1]if candidates else None
 except BaseException as e:out['mount_metadata_error']=type(e).__name__
 return out

def prepare(config,pin):
 c=json.loads(Path(config).read_bytes());need(c['question']==QUESTION and c['owner']==OWNER and c['max_enter_attempts']==1,'Exact finite resource-only question')
 need(c['scope_id']=='data-46308-canonical-lease-handoff-observation-20261118-v1' and Path(c['output'])==R/'runtime/resource-observations'/c['scope_id'],'Exact new resource-only identity/root; no closed root reuse')
 f=Path(c['freeze']);need(sha(f)==pin,'Whole resource program freeze')
 freeze=json.loads(f.read_bytes())
 need(freeze['question']==QUESTION and freeze['scope_id']==c['scope_id'] and freeze['files'].get(str(Path(__file__)))==sha(__file__),'Exact actual resource worker in full freeze')
 auth=Path(c['authorization']);a=json.loads(auth.read_bytes())
 need(freeze['files'].get(str(auth))==sha(auth) and a['owner']==OWNER and a['scope_id']==c['scope_id'] and a['question']==QUESTION and a['max_enter_attempts']==1 and a['world_Actor_model_allowed'] is False,'New frozen resource-only authorization, not old physics/zero')
 for p,digest in freeze['files'].items():need(not Path(p).is_symlink()and sha(p)==digest,'Frozen resource helper/source drift')
 sys.path[:0]=[str(B/'development/bulk-resource-adapter-46308-20261115-v1')]
 import per_gpu_lease
 need(sha(per_gpu_lease.__file__)=='d44b3176255d177d432a4243da2b4a9a472881222fc1079224c82a9140dd9857','Original unchanged own-process lease')
 need('torch'not in sys.modules and 'mujoco'not in sys.modules,'No Actor/world/renderer import')
 need(sys.prefix=='/mnt/yuanyue/data-team/env-native-v1'and sys.version_info[:3]==(3,11,16),'Existing private interpreter')
 return c,per_gpu_lease

def run(config,pin):
 c,module=prepare(config,pin);need(sys.gettrace()is None,'No existing trace observer to replace')
 need(sha(H)==c['expected_H_SHA256'],'Fresh expected H before any authority')
 peer=json.loads(Path(c['peer_safe_phase_proof']).read_bytes());need(peer['audit_scope_closed']and peer['all_own_processes_exited']and peer['all_original_FDs_closed']and all(r['independent_nonblocking_reacquire_and_close']for r in peer['original_canonical_lock_checks']),'Actual peer terminal/release proof, NOT idle alone')
 need(proc_scripts()==[],'An actual Data/J collector phase is in flight; STOP before H/enter')
 gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=10)
 apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_gpu_memory','--format=csv,noheader,nounits'],text=True,timeout=10)
 need(any(s.split(',')[0].strip()=='0'and'GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'in s for s in gpu.splitlines()),'Exact target UUID')
 need(not any('GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'in s for s in apps.splitlines()),'Foreign target compute; no preemption/switch')
 root=Path(c['output']);need(not root.exists(),'Never reopen output/scope');root.mkdir()
 budget=0
 def report(name,value):
  nonlocal budget
  raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode();need(budget+len(raw)<=65536,'Bounded metadata output')
  p=root/name;need(not p.exists(),'No result overwrite');p.write_bytes(raw);budget+=len(raw)
 def claim(h):
  need(h['executing_thread_id']==OWNER and KEY not in h and not h['bulk24_collector_v1']['global_stop'],'Current unique owner/new scope')
  need(not any(v.get('active')for v in h.values()if isinstance(v,dict)),'No second Data execution')
  h[KEY]=dict(active=True,owner=OWNER,scope_id=c['scope_id'],question=QUESTION,PID=os.getpid(),program_sha256=pin,
   authorization_sha256=sha(c['authorization']),resource_attempt_authorized=1,zero_dispatch_count=0,main_dispatch_count=0,
   physical_simulation_admission=False,world_Actor_model_allowed=False,automatic_retry=False,phase='RESOURCE_ONLY_SINGLE_ORIGINAL_ENTER')
  return h
 report('claim-CAS-proof.json',cas(claim))
 def authority():
  h=json.loads(H.read_bytes());q=h[KEY]
  need(h['executing_thread_id']==q['owner']==OWNER and q['active']and q['PID']==os.getpid()and q['program_sha256']==pin,'Actual resource scope/PID authority')
  need(not h['bulk24_collector_v1']['global_stop']and not q.get('stop_requested',False),'Original global stop authority')
  return q
 started=time.monotonic();lease=module.PerGpuLease(physical_index=0,authority_check=authority)
 events=[];entered=False;error=None;calls=0;released_fd_numbers=[]
 target=module.PerGpuLease.__enter__.__code__
 def observer(frame,event,arg):
  nonlocal calls
  if frame.f_code is target and frame.f_locals.get('self')is lease:
   if event=='call':calls+=1
   elif event=='exception'and len(events)<2:
    try:events.append(dict(event='ORIGINAL_ENTER_EXCEPTION_BEFORE_ORIGINAL_CLEANUP',error_type=arg[0].__name__,errno=getattr(arg[1],'errno',None),site=snapshot_fd_site(lease,frame)))
    except BaseException as e:events.append(dict(event='OBSERVER_METADATA_ERROR',error_type=type(e).__name__,cannot_replace_primary_exception=True))
   elif event=='return'and arg is lease and len(events)<2:
    try:events.append(dict(event='ORIGINAL_ENTER_SUCCESS_WHILE_OWN_FDS_RETAINED',site=snapshot_fd_site(lease,frame)))
    except BaseException as e:events.append(dict(event='OBSERVER_METADATA_ERROR',error_type=type(e).__name__))
  return observer if frame.f_code is target else None
 def timeout(*args):raise TimeoutError('Finite resource-only wall deadline')
 signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,30.)
 try:
  sys.settrace(observer)
  try:lease.__enter__();entered=True
  except BaseException as e:error=e
  finally:sys.settrace(None)
 finally:
  released_fd_numbers=list(lease.fds);lease.__exit__();signal.setitimer(signal.ITIMER_REAL,0.)
 closed=[]
 for fd in released_fd_numbers:
  try:os.fstat(fd);closed.append(False)
  except OSError:closed.append(True)
 result=dict(at=now(),question=QUESTION,scope_id=c['scope_id'],PID=os.getpid(),program_sha256=pin,
  original_enter_invocations=calls,entered_original_lease=entered,original_error_type=None if error is None else type(error).__name__,original_errno=None if error is None else getattr(error,'errno',None),
  original_source_body_binding_flags_unchanged=True,trace_observer_never_replaces_primitive_or_retries=True,
  actual_site_events=events,completed_rows=list(lease.rows),last_original_gpu_check=lease.last_gpu,
  original_exit_called_FDs_released=all(closed)and not lease.fds,FD_numbers_metadata_only_not_passed=True,
  wall_sample_s=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
  no_Model_MjData_Actor_Torch_or_GPU_context=True,zero=0,main=0,physical_admission=False,
  actual_resource_lease_only_not_a_future_zero_or_borrowable_lease=True,other_peer_phase_was_terminal_and_released=True,
  holder_unknown_if_no_direct_lock_metadata=True,old_f073_b7_failure_causes_not_retrofilled=True)
 report('result.json',result)
 def close(h):
  q=h[KEY];need(q['active']and q['PID']==os.getpid()and q['program_sha256']==pin,'Original resource scope closes once')
  q.update(active=False,phase='RESOURCE_ONLY_CLOSED_NO_RETRY',closed_at=now(),original_enter_invocations=calls,lease_entered=entered,all_own_FDs_released=result['original_exit_called_FDs_released'],result_SHA256=sha(root/'result.json'),error_type=result['original_error_type'],errno=result['original_errno'],no_simulation_permission=True)
  return h
 report('close-CAS-proof.json',cas(close))
 print(json.dumps(dict(at=now(),original_enter_invocations=calls,entered_original_lease=entered,original_error_type=result['original_error_type'],original_errno=result['original_errno'],FDs_released=result['original_exit_called_FDs_released'],H_SHA256=sha(H),metadata_bytes=budget,scope_active=False)))

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--enabled',action='store_true');p.add_argument('--phase',choices=('prepare','run'));p.add_argument('--config');p.add_argument('--program-sha256');a=p.parse_args()
 if a.enabled:
  if a.phase=='prepare':
   c,m=prepare(a.config,a.program_sha256);print(json.dumps(dict(stage='RESOURCE_ONLY_COMPLETE_PROGRAM_ACTUAL_CPU_PREPARE_PASS',program_sha256=a.program_sha256,no_world_Actor_GPU_or_lease_calls=True)))
  else:run(a.config,a.program_sha256)
