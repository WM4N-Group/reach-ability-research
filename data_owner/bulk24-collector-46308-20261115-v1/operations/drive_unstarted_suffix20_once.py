"""Bounded remaining20 previously-unstarted ordinal05..24 only.
The original22 driver STOPPED after a preserved metadata SHA-CAS rejection when
OBS closure won; original ordinal04 native FF failure is retained and NOT retried.
This suffix begins only after terminal04 metadata reconciliation and raw audit.
No recurring automation, no native source/cap change, no existing phase recovery.
"""
from pathlib import Path
import os,json,subprocess,sys,datetime,tempfile
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;H=B/'registry/handoff_46308_current_status_20261115.json';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']==OWNER
claim=M/'unstarted-suffix20-driver-once-claim.json'
prior=json.loads((M/'remaining-unstarted-driver-status.json').read_bytes());assert prior['status']=='STOPPED_NO_RETRY_NO_FIT' and not Path('/proc/'+str(prior['driver_PID'])).exists()
assert not json.loads((B/'registry/handoff_46308_current_status_20261115.json').read_bytes())['active_T_COMPLEX_observation_study_scope']['active']
with claim.open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),driver_PID=os.getpid(),owner=OWNER,first_four_physical_mains_closed_not_repeated=True,previous_native_FF_failure_and_CAS_rejection_preserved=True,only_fresh_zero0_main0_suffix20=True,max_registered_mains=24,no_refit_no_new_automation=True),f,indent=2)
def state():
 h=json.loads(H.read_bytes());assert h['executing_thread_id']==OWNER;return h,h['bulk24_collector_v1'],h['active_bulk24_collector_scope']
def record(status,**extra):
 h,co,q=state();v=dict(at=datetime.datetime.now().astimezone().isoformat(),driver_PID=os.getpid(),status=status,current_candidate=q['candidate_id'],current_scope=q['scope_id'],current_phase=q['phase'],global_stop=co['global_stop'],registered24=len(co['order']),zero_dispatches=sum(r['zero_dispatch_count']for r in co['branches'].values()),main_dispatches=sum(r['main_dispatch_count']for r in co['branches'].values()),closed_main=sum(r['status'].startswith('CLOSED_ACTUAL_MAIN_')for r in co['branches'].values()),closed_native_failed=sum(r['status']=='CLOSED_ACTUAL_MAIN_FAILED_NO_RETRY'for r in co['branches'].values()),conditional_PASS=sum(r['status']=='CLOSED_ACTUAL_MAIN_PASS'for r in co['branches'].values()),remaining_not_started=sum(r['zero_dispatch_count']==r['main_dispatch_count']==0 for r in co['branches'].values()),no_refit=True,no_closed_scope_reopened=True,**extra);fd,t=tempfile.mkstemp(prefix='.rollout-status-',dir=M)
 with os.fdopen(fd,'w')as f:json.dump(v,f,indent=2);f.write('\n')
 os.replace(t,M/'unstarted-suffix20-driver-status.json')
def call(script,args,tag,c):
 record('RUNNING_'+tag);D=M/c;D.mkdir(exist_ok=True)
 with(D/('suffix20-driver-'+tag+'.stdout')).open('xb')as out,(D/('suffix20-driver-'+tag+'.stderr')).open('xb')as err:
  r=subprocess.run([sys.executable,str(M/script),*args],cwd=B,stdout=out,stderr=err)
 with(D/('suffix20-driver-'+tag+'.exit')).open('x')as f:f.write(str(r.returncode)+'\n')
 if r.returncode:raise RuntimeError('Stopped without retry: '+c+'/'+tag+' exit'+str(r.returncode))
try:
 h,co,q=state();assert not q['active']and not co['global_stop'];assert co['order'].index(q['candidate_id'])==3
 assert all(co['branches'][c]['zero_dispatch_count']==co['branches'][c]['main_dispatch_count']==1 and co['branches'][c]['status'].startswith('CLOSED_ACTUAL_MAIN_') for c in co['order'][:4])
 assert co['branches'][co['order'][3]]['status']=='CLOSED_ACTUAL_MAIN_FAILED_NO_RETRY' and json.loads((M/co['order'][3]/'actual-main-cold-audit-v2.json').read_bytes())['passed']
 for _ in range(20):
  h,co,q=state()
  if co['global_stop']:record('SOURCE_STOP_REMAINING_NOT_STARTED');break
  assert not q['active'];idx=co['order'].index(q['candidate_id'])+1
  if idx>=len(co['order']):record('FIXED24_CLOSED_NO_REFIT');break
  c=co['order'][idx];br=co['branches'][c];assert br['zero_dispatch_count']==br['main_dispatch_count']==0
  call('metadata_and_next_slot_v2.py',['activate-next'],'activate',c)
  for action in ('prepare','zero-dispatch','zero-run','fetch-zero'):call('control_bulk24_v2.py',[c,action],action,c)
  z=json.loads((M/c/'zero-result.json').read_bytes())
  if z['passed']:call('control_bulk24_v2.py',[c,'zero-cold'],'zero-cold',c)
  call('control_bulk24_v2.py',[c,'close-zero'],'close-zero',c)
  if not z['passed']:record('OWN_ZERO_FAILED_STOP_SOURCE_NO_RETRY');break
  for action in ('main-dispatch','main-run','fetch-main','close-main'):call('control_bulk24_v2.py',[c,action],action,c)
  call('run_main_cold_v2.py',[c],'main-cold-v2',c);record('CLOSED_CANDIDATE_ORIGINAL_STREAMS_AUDITED')
 else:record('FIXED24_CLOSED_NO_REFIT')
except BaseException as error:
 record('STOPPED_NO_RETRY_NO_FIT',error=repr(error));raise
