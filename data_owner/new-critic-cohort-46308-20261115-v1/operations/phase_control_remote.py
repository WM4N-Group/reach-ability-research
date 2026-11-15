"""Exact SHA-CAS control for one branch; command never starts physical process."""
from pathlib import Path
import os,sys,json,base64,hashlib,fcntl,stat,tempfile,datetime,subprocess
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='new-critic-cohort-46308-20261115-v1';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json'
x=json.load(sys.stdin);sha=lambda b:hashlib.sha256(b).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat()
sys.path.insert(0,str(W));from prepare_prefix import SCOPES,IDS
c=x['candidate'];action=x['action'];assert c in IDS
program=sha((M/c/'program-freeze.json').read_bytes());root=R/'runtime/workers'/SCOPES[c]
# No present workers or held canonical locks. A check is NOT a future lease.
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:args=[a.decode(errors='replace') for a in (p/'cmdline').read_bytes().split(b'\0') if a]
 except (FileNotFoundError,PermissionError,ProcessLookupError):continue
 if any(a.startswith((str(R/'runtime')+'/',str(B/'workers')+'/')) for a in args):active.append(int(p.name))
assert not active,('OWN_WORKERS_ACTIVE',active)
for kind,inode in [('physics', 3428459217), ('sdk', 3428459218)]:
 path=R/f'resource-locks/native-observer-{kind}-gpu1.lock';st=path.stat();assert (st.st_dev,st.st_ino)==(51,inode);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
 finally:os.close(fd)
# For a new phase, freeze/prepare is checked before any ledger/root is created.
if action in ('zero','main'):
 assert (M/c/'fenced-prepare.exit').read_text().strip()=='0'
 fr=json.loads((M/c/('fenced-prepare-'+program+'.json')).read_bytes());assert fr['prepared'] and not fr['constructor_or_physics_started'] and not fr['forbidden_attempts']
 GPU=subprocess.check_output(['nvidia-smi','--id=GPU-6d66aa68-9a3f-fdcf-89b7-f98d4106fa39','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=20).strip().split(',')
 assert GPU[0].strip()=='1' and int(GPU[2].strip())>=4096,('INSUFFICIENT_GPU_HEADROOM_NO_DISPATCH',GPU)
 owned=int(subprocess.check_output(['du','-sx','--block-size=1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);assert owned+1610612736<40*1024**3
 if action=='zero':assert not root.exists()
 else:
  z=json.loads((root/'zero/result.json').read_bytes());ledger=json.loads((root/'accounting/ledger.json').read_bytes());cold=json.loads((M/c/'actual-zero-cold-validation.json').read_bytes())
  assert z['passed'] and z['program_sha256']==program and cold['passed'] and cold['program_sha256']==program
  assert len(ledger['rows'])==1 and ledger['rows'][0]['closed'] and ledger['rows'][0]['report_sha256']==sha((root/'zero/result.json').read_bytes()) and not ledger['stopped']
  assert not (root/'main').exists()
d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with H.open('rb') as f:
  fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);before=f.read();st=os.fstat(f.fileno());assert sha(before)==x['expected_H_sha256'];assert (H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino)
  h=json.loads(before);assert h['executing_thread_id']==x['owner'];cohort=h['new_critic_cohort_v1'];q=h['active_new_critic_cohort_scope'];branch=cohort['branches'][c]
  for k in ('active_full_host_execution_scope','active_full_host_continuation_scope','active_stow_choice_execution_scope','active_stow_choice_v2_execution_scope','active_climb_preparation_stageB_scope','active_native_prefix_condition_scope','active_native_prefix_condition_v2_scope','active_g2_full2_scope','active_g2_full1_scope'):
   old=h[k];assert not old['active'] and old['zero_dispatch_program_sha256'] is None and old['main_dispatch_program_sha256'] is None
  assert not cohort['global_stop'],'Cohort already stopped, no replacement/continuation'
  ordinal=list(IDS).index(c)+1
  if action in ('activate','zero','main'):
   assert ordinal<=6,'CAL/VAL requires separate reviewed TRAIN gate + actual fit; this collection controller cannot enable it'
  if action=='activate':
   assert not q['active'] and branch['zero_dispatch_count']==branch['main_dispatch_count']==0 and not root.exists()
   previous=list(IDS).index(c)-1;assert previous>=0 and cohort['branches'][IDS[previous]]['status'].startswith('CLOSED_')
   q=dict(active=True,owner=x['owner'],scope_id=SCOPES[c],candidate_id=c,phase='FROZEN_CPU_PREPARE_NO_PHYSICAL_PHASE_DISPATCH',authorization_sha256=cohort['authorization_sha256'],whole_program_freeze_sha256=program,zero_dispatch_count=0,main_dispatch_count=0,zero_dispatch_program_sha256=None,main_dispatch_program_sha256=None,physical_retry_allowed=False);h['active_new_critic_cohort_scope']=q
  elif action in ('zero','main'):
   assert q['active'] and q['candidate_id']==c and q['scope_id']==SCOPES[c] and q['whole_program_freeze_sha256']==program and q[action+'_dispatch_count']==0 and branch[action+'_dispatch_count']==0
   q.update(phase='CAS_DISPATCHED_'+action.upper(),**{action+'_dispatch_program_sha256':program,action+'_dispatch_count':1});branch[action+'_dispatch_count']=1;branch['status']='DISPATCHED_'+action.upper();cohort['status']='IN_PROGRESS_ONE_CURRENT_BRANCH'
  elif action in ('close','zero_failed'):
   phase='main' if action=='close' else 'zero';v=json.loads((root/phase/'result.json').read_bytes());ledger=json.loads((root/'accounting/ledger.json').read_bytes())
   assert q['candidate_id']==c and q['active'] and v['program_sha256']==program and all(r['closed'] for r in ledger['rows']) and ledger['rows'][-1]['report_sha256']==sha((root/phase/'result.json').read_bytes())
   assert not Path('/proc/'+str(v['PID'])).exists()
   if action=='zero_failed' or v.get('resource_censored')is True or v.get('owner_guard_or_contract_stop')is True or (not v['passed'] and any(s in str(v.get('error','')).lower() for s in ('immutable','identity','drift','canonical','source mismatch','binding mismatch'))):cohort.update(global_stop=True,status='STOPPED_INTEGRITY_ZERO_OR_RESOURCE_NO_REPLACEMENT')
   status='CLOSED_ACTUAL_'+phase.upper()+('_PASS' if v['passed'] else '_FAILURE_NO_RETRY')
   q.update(active=False,phase=status,zero_dispatch_program_sha256=None,main_dispatch_program_sha256=None,actual_result_sha256=sha((root/phase/'result.json').read_bytes()),closed_at=now(),physical_retry_allowed=False)
   branch.update(status=status,result_sha256=q['actual_result_sha256'],actual_result_path=str(root/phase/'result.json'),final_ledger_sha256=sha((root/'accounting/ledger.json').read_bytes()),actual_main_world_sim_s=v['actual_main_world_sim_s'],actual_passed=v['passed'],primary_error=v.get('error'))
   if all(cohort['branches'][k]['status'].startswith('CLOSED_')for k in IDS[:6]):cohort['status']='TRAIN_SIX_CLOSED_AWAIT_GATE_NO_CAL_VAL_DISPATCH'
  else:raise ValueError('Unknown explicit action')
  h['updated_at']=now();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();mode=stat.S_IMODE(st.st_mode)
  receipt=dict(at=now(),candidate=c,action=action,before_H_sha256=sha(before),after_H_sha256=sha(after),program_sha256=program,phase=q['phase'],active=q['active'],GPU_lease_not_acquired_by_CAS=True,all_old_scopes_unchanged=True)
  fd,tmp=tempfile.mkstemp(prefix='.'+H.name+'.StageB-phase-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb') as out:out.write(after);out.flush();os.fchmod(out.fileno(),mode);os.fsync(out.fileno())
   assert H.read_bytes()==before;os.replace(tmp,H);os.fsync(d)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
  with (M/c/('CAS-'+action+'.json')).open('x') as out:json.dump(receipt,out,indent=2);out.write('\n')
  print(json.dumps(dict(receipt=receipt,after_base64=base64.b64encode(after).decode())))
finally:os.close(d)
