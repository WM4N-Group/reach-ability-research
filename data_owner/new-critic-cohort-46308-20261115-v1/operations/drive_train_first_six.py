"""One fixed 6-root TRAIN pipeline for exact prospective protocol. No retries/fit/CAL/VAL.
Reuses all existing bounded phase launchers and cold readers; not a scheduler.
"""
from pathlib import Path
import json,subprocess,sys,os,datetime,hashlib
M=Path(__file__).resolve().parent;B=M.parents[1];PIN='2f82530d1f880892c631c7b62cc79bfbd72d57e1b369faf99f542d02d4a53eda';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';H=B/'registry/handoff_46308_current_status_20261115.json';now=lambda:datetime.datetime.now().astimezone().isoformat();sha=lambda b:hashlib.sha256(b).hexdigest()
assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']==OWNER
p=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/new-cohort/FINITE_COHORT_PROTOCOL.json';assert sha(p.read_bytes())==PIN;freeze=json.loads((M/'freeze-CAS-receipt.json').read_bytes());h=json.loads(H.read_bytes());order=h['new_critic_cohort_v1']['order'][:6];assert len(order)==6 and all(h['new_critic_cohort_v1']['branches'][c]['split']=='TRAIN'for c in order)
with(M/'TRAIN_first_six_pipeline_started.json').open('x')as f:json.dump(dict(at=now(),PID=os.getpid(),owner=OWNER,protocol_sha256=PIN,order=order,main_attempts_upper_bound=6,automatic_retry=False,CAL_or_VAL_or_fit=False),f,indent=2);f.write('\n')
def invoke(c,step,script,*args,allow_native_nonzero=False):
 cp=subprocess.run([sys.executable,'-B',str(M/script),c,*args],capture_output=True,text=True,timeout=5700)
 for suffix,text in [('stdout',cp.stdout),('stderr',cp.stderr),('exit',str(cp.returncode)+'\n')]:
  with(M/c/('pipeline-'+step+'.'+suffix)).open('x')as f:f.write(text)
 print(now(),c,step,'EXIT',cp.returncode,flush=True)
 if cp.returncode and not allow_native_nonzero:raise RuntimeError('Stopped at '+c+'/'+step+'; no retry or later scope')
 return cp.returncode
completed=[]
try:
 for i,c in enumerate(order):
  h=json.loads(H.read_bytes());co=h['new_critic_cohort_v1'];assert not co['global_stop'] and not co['TRAIN_gate_passed'];br=co['branches'][c];assert br['zero_dispatch_count']==br['main_dispatch_count']==0 and br['ordinal']==i+1
  if i:invoke(c,'activate','control.py','activate')
  invoke(c,'prepare','run_prepare.py');invoke(c,'zero-CAS','control.py','zero');zrc=invoke(c,'zero','launch_phase.py','zero',allow_native_nonzero=True);invoke(c,'zero-fetch','fetch_result.py','zero');z=json.loads((M/c/'zero-result.json').read_bytes())
  if not z['passed']:
   invoke(c,'zero-failed-close','control.py','zero_failed');raise RuntimeError('Actual zero failure, cohort halted no replacement')
  assert zrc==0;invoke(c,'zero-cold','run_cold.py','zero');invoke(c,'main-CAS','control.py','main');rc=invoke(c,'main','launch_phase.py','main',allow_native_nonzero=True);invoke(c,'main-fetch','fetch_result.py','main');v=json.loads((M/c/'main-result.json').read_bytes());assert v['program_sha256']==freeze['programs'][c]and((rc==0)==bool(v['passed'])),'Inconsistent result/transport, stop without retry'
  invoke(c,'main-cold','run_cold.py','main');invoke(c,'main-close','control.py','close');co=json.loads(H.read_bytes())['new_critic_cohort_v1'];assert co['branches'][c]['zero_dispatch_count']==co['branches'][c]['main_dispatch_count']==1
  completed.append(dict(condition_id=c,passed=v['passed'],error=v.get('error'),program_sha256=v['program_sha256'],actual_main_world_sim_s=v['actual_main_world_sim_s']))
  if co['global_stop']:raise RuntimeError('Recorded zero/integrity/resource stop, no later acquisition')
 with(M/'TRAIN_first_six_pipeline_complete.json').open('x')as f:json.dump(dict(at=now(),protocol_sha256=PIN,completed=completed,TRAIN_gate_not_evaluated_by_Data=True,CAL_VAL_NOT_DISPATCHED=True,fit_not_started=True),f,indent=2);f.write('\n')
 print(now(),'TRAIN6_CLOSED_STOP_AWAIT_REACH_GATE_NO_CAL_VAL_NO_FIT',flush=True)
except BaseException as e:
 with(M/'TRAIN_first_six_pipeline_stopped.json').open('x')as f:json.dump(dict(at=now(),protocol_sha256=PIN,completed=completed,error_class=type(e).__name__,error=str(e),automatic_retry=False,later_scopes_not_dispatched_by_this_pipeline=True,fit_not_started=True),f,indent=2);f.write('\n')
 raise
