"""Exactly one existing CAL root per explicit invocation, stop before next/VAL.
Native code/programs unchanged; new separate research-gate admission controller.
"""
from pathlib import Path
import sys,os,json,subprocess,datetime,hashlib
M=Path(__file__).resolve().parent;B=M.parents[1];O=B/'manifests/new-critic-cohort-46308-20261115-v1';c=sys.argv[1];h=json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes());co=h['new_critic_cohort_v1'];assert c in co['order'][6:9]and co['TRAIN_gate_passed']and co['branches'][c]['zero_dispatch_count']==co['branches'][c]['main_dispatch_count']==0;D=M/c;D.mkdir(exist_ok=True);now=lambda:datetime.datetime.now().astimezone().isoformat()
with(D/'single-CAL-driver-started.json').open('x')as f:json.dump(dict(at=now(),PID=os.getpid(),candidate=c,allowed_roots=[c],next_roots_and_VAL_not_dispatched=True,automatic_retry=False,fit_or_refit=False),f,indent=2);f.write('\n')
def invoke(step,script,*args,allow_nonzero=False,new=False):
 r=subprocess.run([sys.executable,'-B',str((M if new else O)/script),c,*args],text=True,capture_output=True,timeout=5700)
 for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
  with(D/(step+'.'+suffix)).open('x')as f:f.write(text)
 print(now(),c,step,'EXIT',r.returncode,flush=True)
 if r.returncode and not allow_nonzero:raise RuntimeError('Stop without retry at '+step)
 return r.returncode
try:
 invoke('activate','control.py','activate',new=True);invoke('prepare','run_prepare.py');invoke('zero-CAS','control.py','zero',new=True);rc=invoke('zero','launch_phase.py','zero',allow_nonzero=True);invoke('zero-fetch','fetch_result.py','zero');z=json.loads((O/c/'zero-result.json').read_bytes())
 if not z['passed']:invoke('zero-failed-close','control.py','zero_failed',new=True);raise RuntimeError('Own zero failed; no main/retry/replacement')
 assert rc==0;invoke('zero-cold','run_zero_cold_candidate_v2.py');invoke('main-CAS','control.py','main',new=True);rc=invoke('main','launch_phase.py','main',allow_nonzero=True);invoke('main-fetch','fetch_result.py','main');v=json.loads((O/c/'main-result.json').read_bytes());assert(rc==0)==bool(v['passed']);invoke('main-cold','run_cold.py','main');invoke('main-close','control.py','close',new=True)
 with(D/'single-CAL-driver-complete.json').open('x')as f:json.dump(dict(at=now(),candidate=c,main_passed=v['passed'],error=v.get('error'),actual_main_sim_s=v['actual_main_world_sim_s'],next_roots_and_VAL_not_dispatched=True,fit_or_refit=False,closed_no_retry=True),f,indent=2);f.write('\n')
except BaseException as e:
 with(D/'single-CAL-driver-stopped.json').open('x')as f:json.dump(dict(at=now(),candidate=c,error=str(e),automatic_retry=False,next_roots_and_VAL_not_dispatched=True),f,indent=2);f.write('\n')
 raise
