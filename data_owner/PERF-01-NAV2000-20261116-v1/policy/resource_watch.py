"""New-policy cheap hot guard + bounded-staleness external checks, default OFF.
Does NOT replace native collision/FF/QP/FIFO/NN/stop checks or acquire a lease.
"""
import os,threading,time,math
from scoped_io import StopState,PolicyStop
class ResourceWatch:
 def __init__(self,probe,*,state,token,interval_s=1.,max_stale_s=2.,clock=time.monotonic,fast_health=None):
  if not callable(probe)or not 0<interval_s<max_stale_s:raise ValueError('Bounded explicit poll/staleness policy')
  self.probe=probe;self.state=state;self.token=token;self.pid=os.getpid();self.interval=interval_s;self.max_stale=max_stale_s;self.clock=clock;self.fast_health=fast_health;self.last_ok=None;self.last_observation_stamp=None;self.thread=None;self.stop=threading.Event();self.closed=False;self.check_calls=0;self.probe_calls=0;self.probe_wall_s=0.
 def probe_once(self):
  self.state.check();t=time.perf_counter();oldest=self.clock()
  try:
   result=self.probe()
   if result is not None and result is not True:self.state.fail('Probe must succeed explicitly or raise')
   if self.state.sealed:return
   self.state.check();completed=self.clock()
   if not all(math.isfinite(v)for v in(oldest,completed))or not 0<=completed-oldest<=self.max_stale:self.state.fail('External probe already over-age at completion')
   self.last_observation_stamp=(oldest,completed)  # ONE immutable atomic publication.
   self.last_ok=completed  # Legacy metrics only; NEVER freshness authority.
   self.probe_calls+=1
  except BaseException as e:
   if self.state.sealed and self.state.reason is None:return
   self.state.fail('External resource/owner/disk probe failed: '+repr(e))
  finally:self.probe_wall_s+=time.perf_counter()-t
 def check(self,token):
  if self.closed:raise PolicyStop('Supervisor closed; no more execution')
  if token is not self.token or os.getpid()!=self.pid:self.state.fail('Foreign owner token/process')
  self.state.check()
  pair=self.last_observation_stamp;now=self.clock()
  if type(pair)is not tuple or len(pair)!=2:self.state.fail('Successful oldest/completed observation pair required')
  oldest,completed=pair
  if not all(type(v)in(int,float)and math.isfinite(v)for v in(oldest,completed,now))or not oldest<=completed<=now or now-oldest>self.max_stale:self.state.fail('Resource oldest observation stale; stop at next guard boundary')
  if self.fast_health is not None:
   try:
    ok=self.fast_health()
    if ok is not None and ok is not True:self.state.fail('Cheap health check refused')
   except BaseException as e:self.state.fail('Cheap health check failed: '+repr(e))
  self.check_calls+=1
 def __call__(self):return self.check(self.token)
 def start(self):
  if self.closed or self.thread is not None:raise PolicyStop('Supervisor cannot restart')
  self.probe_once()
  def run():
   while not self.stop.wait(self.interval) and not self.state.sealed:
    try:self.probe_once()
    except BaseException:return
  self.thread=threading.Thread(target=run,daemon=True,name='data-periodic-resource-probe');self.thread.start();return self
 def close(self):
  self.closed=True;self.stop.set()
  if self.thread is not None:
   self.thread.join(timeout=.2)
   if self.thread.is_alive():raise PolicyStop('External probe still blocked at shutdown; keep native sealed and record close error')

def make_scope_probe(lease,budget,*,min_free_bytes,disk_free):
 """For the existing held PerGpuLease: it already checks authority/binding/GPU.
 No extra direct owner_guard call here. Must be called only by ResourceWatch.
 """
 if type(min_free_bytes)is not int or min_free_bytes<=0:raise ValueError('Explicit disk reserve')
 def probe():
  lease.check(force=True)  # original held inode + UUID/GPU + authority checks
  free=disk_free(budget.root)
  if type(free)is not int or free<min_free_bytes:budget.state.fail('Disk free unknown/below safety floor')
  budget.reconcile()
 return probe
