"""Bounded deterministic CPU reproduction; not a lease/native/runtime test."""
from pathlib import Path
import argparse,hashlib,json,sys
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root',type=Path,default=Path('/home/yuanyue/main/work/data-team/consumer-deliveries/AINAV-DATA-PERF-CONTROLLED-IO-PERIODIC-GUARD-CPU-QUALIFIED-NOT-NATIVE-20261116-v1/code'))
root=parser.parse_args().source_root.resolve(strict=True)
expected={'resource_watch.py':'0c0eb1412b738496cd64bf527cede45afc1a06b16f7d0ec91c9e3f6812397815','scoped_io.py':'3409293c6bc45749e28fb06e968e76317862e512bd081820d6b7286835a68ae2'}
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in expected.items())
sys.path.insert(0,str(root))
from resource_watch import ResourceWatch
from scoped_io import StopState,PolicyStop
assert Path(sys.modules['resource_watch'].__file__).resolve()==root/'resource_watch.py'
assert Path(sys.modules['scoped_io'].__file__).resolve()==root/'scoped_io.py'
class Clock:
 def __init__(self):self.t=0.
 def __call__(self):return self.t

def run(check_during_stall):
 clock=Clock();state=StopState();token=object();reads=[];slow=[False];watch=None
 def probe():
  reads.append(clock.t)  # Fake lease/owner sample is taken BEFORE the slow reconciliation.
  if slow[0]:
   clock.t+=3.
   if check_during_stall:watch.check(token)
 watch=ResourceWatch(probe,state=state,token=token,clock=clock,interval_s=1.,max_stale_s=2.)
 watch.probe_once();assert watch.last_ok==0.
 clock.t=1.;slow[0]=True;probe_error=None
 try:watch.probe_once()
 except PolicyStop as e:probe_error=str(e)
 accepted=True;check_error=None
 try:watch.check(token)
 except PolicyStop as e:accepted=False;check_error=str(e)
 return dict(check_during_stall=check_during_stall,earliest_probe_sample_s=reads[-1],
  completion_s=clock.t,published_last_ok_s=watch.last_ok,max_stale_s=watch.max_stale,
  earliest_sample_age_on_next_check_s=clock.t-reads[-1],
  next_check_accepted=accepted,probe_error=probe_error,check_error=check_error)
without=run(False);with_check=run(True)
assert without['next_check_accepted'] and without['earliest_sample_age_on_next_check_s']>without['max_stale_s']
assert not with_check['next_check_accepted']
print(json.dumps(dict(role='EXPLICIT_SOFTWARE_FAKE_CLOCK_PROBE_AGE_BOUNDARY_NOT_REAL_OWNER_REVOCATION',source_sha256=expected,
 cases=[without,with_check],finding='Completion-time last_ok is not the earliest composite resource observation time when guard checks are delayed; continuous hot checks do stop the stalled probe case.',
 risk_scope='Policy already allows blocked-IO extra delay: owner must define/retain oldest observation age or explicitly qualify the combined bound. Not a claim of a live exploit or that existing continuous staleness protection is absent.',
 suggested_owner_action='Data: conservatively publish probe-start/oldest observation stamp, reject over-age or over-budget completion, or explicitly provide per-signal observation/deadline semantics before native use.',
 real_lease_GPU_probe_thread_native_Runtime_model_physics_API_fit_calls=0,peer_source_modified=False),ensure_ascii=False,indent=2))
