"""Reviewed continuation of ONLY never-dispatched phases after readonly auditor bug.
NOT restart of one-shot original pipeline; no new zero for03, no rerun of01/02.
"""
from pathlib import Path
import json,subprocess,sys,os,datetime,hashlib
M=Path(__file__).resolve().parent;B=M.parents[1];H=B/'registry/handoff_46308_current_status_20261115.json';now=lambda:datetime.datetime.now().astimezone().isoformat();OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';PIN='2f82530d1f880892c631c7b62cc79bfbd72d57e1b369faf99f542d02d4a53eda';assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']==OWNER
stopped=json.loads((M/'TRAIN_first_six_pipeline_stopped.json').read_bytes());assert stopped['error']=='Stopped at new_critic_03_full4_left_lateral_plus_0p04/zero-cold; no retry or later scope';h=json.loads(H.read_bytes());co=h['new_critic_cohort_v1'];order=co['order'];assert len(order)==12 and not co['global_stop']and not co['TRAIN_gate_passed']and co['protocol_sha256']==PIN
assert all(co['branches'][c]['status']=='CLOSED_ACTUAL_MAIN_PASS'and co['branches'][c]['zero_dispatch_count']==co['branches'][c]['main_dispatch_count']==1 for c in order[:2]);c=order[2];br=co['branches'][c];assert br['zero_dispatch_count']==1 and br['main_dispatch_count']==0 and h['active_new_critic_cohort_scope']['candidate_id']==c
cold=json.loads((M/c/'actual-zero-cold-validation.json').read_bytes());assert cold['passed']and cold['readonly_auditor_revision']==2 and cold['program_sha256']==br['whole_program_freeze_sha256'];assert all(co['branches'][c]['zero_dispatch_count']==co['branches'][c]['main_dispatch_count']==0 for c in order[3:])
with(M/'TRAIN03_06_reviewed_continuation_started.json').open('x')as f:json.dump(dict(at=now(),PID=os.getpid(),owner=OWNER,protocol_sha256=PIN,original_pipeline_stopped_evidence=str(M/'TRAIN_first_six_pipeline_stopped.json'),readonly_correction_sha256=hashlib.sha256((M/'READONLY_ZERO_CANDIDATE_AUDITOR_CORRECTION_v2.json').read_bytes()).hexdigest(),remaining_main_order=order[2:6],no_zero_repeat_for03=True,no_main_repeat_or_old_scope_reopen=True,after06_STOP_no_CAL_VAL_fit=True),f,indent=2);f.write('\n')
def invoke(c,step,script,*args,allow_nonzero=False):
 r=subprocess.run([sys.executable,'-B',str(M/script),c,*args],capture_output=True,text=True,timeout=5700)
 for suf,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
  with(M/c/('reviewed-continuation-'+step+'.'+suf)).open('x')as f:f.write(text)
 print(now(),c,step,'EXIT',r.returncode,flush=True)
 if r.returncode and not allow_nonzero:raise RuntimeError('Stop without retry at '+c+'/'+step)
 return r.returncode
completed=[]
try:
 for i,c in enumerate(order[2:6],3):
  h=json.loads(H.read_bytes());co=h['new_critic_cohort_v1'];assert not co['global_stop']and not co['TRAIN_gate_passed'];br=co['branches'][c];assert br['main_dispatch_count']==0 and br['ordinal']==i
  if i>3:
   assert br['zero_dispatch_count']==0;invoke(c,'activate','control.py','activate');invoke(c,'prepare','run_prepare.py');invoke(c,'zero-CAS','control.py','zero');rc=invoke(c,'zero','launch_phase.py','zero',allow_nonzero=True);invoke(c,'zero-fetch','fetch_result.py','zero');z=json.loads((M/c/'zero-result.json').read_bytes())
   if not z['passed']:invoke(c,'zero-failed-close','control.py','zero_failed');raise RuntimeError('Actual zero failure; no later scope')
   assert rc==0;invoke(c,'zero-cold-exact-candidate-v2','run_zero_cold_candidate_v2.py')
  invoke(c,'main-CAS','control.py','main');rc=invoke(c,'main','launch_phase.py','main',allow_nonzero=True);invoke(c,'main-fetch','fetch_result.py','main');v=json.loads((M/c/'main-result.json').read_bytes());assert((rc==0)==bool(v['passed']))and v['program_sha256']==br['whole_program_freeze_sha256'];invoke(c,'main-cold','run_cold.py','main');invoke(c,'main-close','control.py','close');co=json.loads(H.read_bytes())['new_critic_cohort_v1'];completed.append(dict(condition_id=c,passed=v['passed'],error=v.get('error'),program_sha256=v['program_sha256'],actual_main_world_sim_s=v['actual_main_world_sim_s']))
  if co['global_stop']:raise RuntimeError('Recorded shared resource/integrity failure; no later scope')
 with(M/'TRAIN03_06_reviewed_continuation_complete.json').open('x')as f:json.dump(dict(at=now(),protocol_sha256=PIN,completed=completed,prior_01_02_not_repeated=True,TRAIN_gate_not_evaluated_by_Data=True,CAL_VAL_NOT_DISPATCHED=True,fit_not_started=True),f,indent=2);f.write('\n')
 print(now(),'TRAIN6_CLOSED_STOP_AWAIT_REACH_GATE_NO_CAL_VAL_NO_FIT',flush=True)
except BaseException as e:
 with(M/'TRAIN03_06_reviewed_continuation_stopped.json').open('x')as f:json.dump(dict(at=now(),protocol_sha256=PIN,completed=completed,error=str(e),automatic_retry=False,later_scopes_not_dispatched_by_this_continuation=True),f,indent=2);f.write('\n')
 raise
