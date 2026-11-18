"""Bounded original lease-site observer; one enter, NEVER a new lease primitive.

No H/AUTH/claim here. The native caller retains original PerGpuLease and closes
via its existing finally. Errors are original objects; observer cannot retry,
change open/flock/binding or produce an OwnerStamp. CPU fixtures are not leases.
"""
from pathlib import Path
import datetime,os,sys,time
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114')
now=lambda:datetime.datetime.now().astimezone().isoformat()

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

def enter_once(lease,events):
    if sys.gettrace() is not None:raise ValueError('No ambient trace replacement')
    if type(events)is not list or events:raise ValueError('One fresh bounded observer list; no repeated enter')
    target=type(lease).__enter__.__code__
    calls=0
    def observer(frame,event,arg):
        nonlocal calls
        if frame.f_code is target and frame.f_locals.get('self')is lease:
            if event=='call':calls+=1
            elif event=='exception'and len(events)<2:
                try:events.append(dict(event='ORIGINAL_LEASE_EXCEPTION_BEFORE_ORIGINAL_CLEANUP',error_type=arg[0].__name__,errno=getattr(arg[1],'errno',None),site=snapshot_fd_site(lease,frame)))
                except BaseException as e:events.append(dict(event='LEASE_OBSERVER_METADATA_ERROR',error_type=type(e).__name__,does_not_replace_original_error=True))
            elif event=='return'and arg is lease and len(events)<2:
                try:events.append(dict(event='ORIGINAL_LEASE_RETURN_SUCCESS_OWN_FDS_RETAINED',site=snapshot_fd_site(lease,frame)))
                except BaseException as e:events.append(dict(event='LEASE_OBSERVER_METADATA_ERROR',error_type=type(e).__name__))
        return observer if frame.f_code is target else None
    try:
        sys.settrace(observer)
        return lease.__enter__() # ONE unmodified original own-process acquisition/check.
    finally:
        sys.settrace(None)
        # No new exception may mask an original enter error. Original lease
        # __exit__ stays in the native caller's existing finally lifecycle.
        if len(events)<3:events.append(dict(event='ORIGINAL_ENTER_INVOCATION_COUNT',calls=calls,source_trace_observer_not_lease_retry=True))
