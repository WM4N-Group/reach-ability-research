"""Metadata-only closure; GPU0 quiescence does not require stopping GPU1 bulk.
No native imports, dispatch, retries, lock replacement or signal delivery.
SHA CAS preserves every non-OBS H field, including the live bulk branch.
"""
from pathlib import Path
import sys, os, json, hashlib, fcntl, stat, tempfile, subprocess, datetime, base64
x=json.load(sys.stdin)
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114'); B=R/'workspace'
M=B/'manifests/T-COMPLEX-observability-study-46308-20261115-v1'; H=B/'registry/handoff_current_status_20261115.json'
sha=lambda b:hashlib.sha256(b).hexdigest(); now=lambda:datetime.datetime.now().astimezone().isoformat()
old=H.read_bytes(); assert sha(old)==x['expected']; h=json.loads(old)
assert x['owner']==h['executing_thread_id']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
q=h['active_T_COMPLEX_observation_study_scope']; co=h['T_COMPLEX_observation_study_v1']; pin='9fdd2076cda187b0749f7f294ef362acb954cac4d7fa95a2feec7e1b3529b7ad'
assert q['active'] and q['scope_id']=='data-46308-T-COMPLEX-observability-only-20261115-v1' and q['owner']==x['owner']
assert q['whole_program_freeze_sha256']==q['main_dispatch_program_sha256']==pin and q['zero_dispatch_count']==q['main_dispatch_count']==1
root=R/'runtime/workers'/q['scope_id']; S=root/'main'
v=json.loads((S/'result.json').read_bytes()); L=json.loads((root/'accounting/ledger.json').read_bytes()); a=json.loads((M/'OBS/actual-main-cold-audit-v2.json').read_bytes())
assert v['passed'] and v['observation_qualification_complete'] and not v['task_success'] and not v['AB_comparison'] and not v['close_errors']
assert v['program_sha256']==pin and not Path('/proc/'+str(v['PID'])).exists()
assert len(L['rows'])==2 and all(r['closed'] and r['usage_known']for r in L['rows']) and not L['stopped']
result_sha=sha((S/'result.json').read_bytes()); assert result_sha==L['rows'][1]['report_sha256']==a['source_result_sha256'] and a['passed'] and a['exact_three_boundaries_complete']
freeze=M/'OBS/program-freeze.json'; assert sha(freeze.read_bytes())==pin
frozen=json.loads(freeze.read_bytes())
for name,digest in frozen['files'].items():
 p=Path(name); assert not p.is_symlink() and sha(p.read_bytes())==digest
bulk=h['active_bulk24_collector_scope']; assert bulk['active'] and bulk['owner']==x['owner'] and bulk['main_dispatch_count']==1
bulk_root=R/'runtime/workers'/bulk['scope_id']; bulk_L=json.loads((bulk_root/'accounting/ledger.json').read_bytes()); bulk_pid=bulk_L['rows'][-1]['PID']
assert not bulk_L['rows'][-1]['closed'] and bulk_L['program_sha256']==bulk['whole_program_freeze_sha256'] and Path('/proc/'+str(bulk_pid)).exists()
owned=[]
for p in Path('/proc').glob('[0-9]*'):
 try: args=[v.decode(errors='replace')for v in(p/'cmdline').read_bytes().split(b'\0')if v]
 except OSError: continue
 if any(v.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for v in args): owned.append(int(p.name))
assert owned==[bulk_pid], (owned,bulk_pid)
locks=[]
for kind,ino in [('physics',3428729629),('sdk',3428729630)]:
 p=R/f'resource-locks/native-observer-{kind}-gpu0.lock'; fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  st=os.fstat(fd); assert (st.st_dev,st.st_ino)==(51,ino)==(p.stat().st_dev,p.stat().st_ino)
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); fcntl.flock(fd,fcntl.LOCK_UN); locks.append(dict(path=str(p),device=st.st_dev,inode=st.st_ino,free_snapshot_not_lease=True))
 finally: os.close(fd)
gpu=subprocess.check_output(['nvidia-smi','--id=GPU-297c1146-bcec-a8ee-8437-d9603392a2e1','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=15).strip().split(',')
assert gpu[0].strip()=='0' and gpu[1].strip()=='GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'
owned_bytes=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0])
resources=dict(at=now(),GPU0_owned_native_count=0,other_admitted_GPU1_PID_preserved=bulk_pid,GPU0_free_MiB=int(gpu[2]),owned_bytes=owned_bytes,locks=locks,not_a_new_lease_or_dispatch=True)
d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX); before=f.read(); st=os.fstat(f.fileno()); assert sha(before)==x['expected'] and (H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino)
  out=json.loads(before); q=out['active_T_COMPLEX_observation_study_scope']; co=out['T_COMPLEX_observation_study_v1']; br=co['branches']['OBS']
  q.update(active=False,phase='CLOSED_ACTUAL_MAIN_PASS',zero_dispatch_program_sha256=None,main_dispatch_program_sha256=None,closed_at=now(),actual_result_sha256=result_sha,observation_qualification_complete=True,actual_task_success=False,AB_comparison=False,closure_resource_snapshot=resources)
  br.update(status=q['phase'],actual_result_sha256=result_sha,actual_task_success=False,actual_main_world_sim_s=v['actual_main_world_sim_s'],observation_qualification_complete=True,cold_audit_sha256=sha((M/'OBS/actual-main-cold-audit-v2.json').read_bytes()))
  co.update(status='CLOSED_OBSERVATION_STUDY_COMPLETE_NOT_TASK_SUCCESS'); out['updated_at']=now()
  assert all(out[k]==val for k,val in json.loads(before).items()if k not in ('T_COMPLEX_observation_study_v1','active_T_COMPLEX_observation_study_scope','updated_at'))
  after=(json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode(); fd,tmp=tempfile.mkstemp(prefix='.H-OBS-close-metadata-v2-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as f2:f2.write(after);f2.flush();os.fchmod(f2.fileno(),stat.S_IMODE(st.st_mode));os.fsync(f2.fileno())
   assert H.read_bytes()==before;os.replace(tmp,H);os.fsync(d)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
finally:os.close(d)
receipt=dict(at=now(),before_H_sha256=sha(before),after_H_sha256=sha(after),source_result_sha256=result_sha,frozen_members_reverified=len(frozen['files']),resources=resources,all_other_H_fields_preserved=True,only_metadata_closure_no_physics=True,no_bulk_mutation_or_signal=True)
with(M/'OBS/CAS-close-main-v2.json').open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(dict(receipt=receipt,after_base64=base64.b64encode(after).decode())))
