from pathlib import Path
import json,hashlib,subprocess,base64,shlex,sys,os
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;H=B/'registry/handoff_46308_current_status_20261115.json';old=H.read_bytes();OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']==OWNER;code=r'''
from pathlib import Path
import json,hashlib,base64,sys,os,fcntl,tempfile,datetime,stat
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';M=B/'manifests/E20-prearrival40-direct-live-46308-20261116-v2';S=R/'runtime/workers/data-46308-E20-prearrival40-direct-live-20261116-v2';H=B/'registry/handoff_current_status_20261115.json';KEY='active_E20_prearrival40_v2_scope';raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()==x['before_sha'];h=json.loads(raw);q=h[KEY];assert q['active']and q['zero_dispatch_count']==1 and q['main_dispatch_count']==0;err=(M/'zero.stderr').read_text();ex=json.loads((M/'zero-exit.json').read_bytes());child=json.loads((M/'zero-child.json').read_bytes());claim=json.loads((S/'zero/claim.json').read_bytes());assert 'ModuleNotFoundError: No module named \'private_catalog_boundary\''in err and ex['exit_code']==1 and child['PID']==claim['PID']and not Path('/proc/'+str(child['PID'])).exists();assert not(S/'zero/result.json').exists()and not(S/'zero/ledger.json').exists()and not(S/'main').exists();locks=[]
for kind,ino in [('physics',3428729629),('sdk',3428729630)]:
 p=R/f'resource-locks/native-observer-{kind}-gpu0.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,ino);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN);locks.append(dict(kind=kind,device=st.st_dev,inode=st.st_ino,free=True))
 finally:os.close(fd)
note=dict(at=datetime.datetime.now().astimezone().isoformat(),scope_id=q['scope_id'],program_sha256=q['whole_program_freeze_sha256'],source_commit=q['source_commit'],error='Data deployment omitted original private_catalog_boundary.py; import failed before native try/lease/Runtime',zero_dispatches_consumed=1,main_dispatches=0,Runtime_calls=0,Actor_forwards=0,task_steps=0,aux_sim_s=0.,original_worker_wall_s=None,original_peak_RSS_bytes=None,original_result_and_ledger_missing=True,usage_partial_known_not_free_zero=True,original_exit=ex,original_child=child,original_claim=claim,original_stderr=err,static_asset_compile_pass_not_invalidated=True,static_compile_wall_s=json.loads((M/'asset-compile-result.json').read_bytes())['wall_s'],canonical_locks=locks,no_source_or_old_result_mutation=True,no_retry=True)
with(M/'zero-startup-failure-maintenance-note.json').open('x')as f:json.dump(note,f,ensure_ascii=False,indent=2);f.write('\n')
dfd=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(dfd,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==raw and H.stat().st_ino==st.st_ino;h=json.loads(raw);saved=json.loads(raw);assert h['executing_thread_id']==x['owner'];q=h[KEY];q.update(active=False,phase='CLOSED_DATA_PRIVACY_IMPORT_ZERO_DISPATCH1_NO_RUNTIME_NO_MAIN',closed_at=note['at'],maintenance_note=str(M/'zero-startup-failure-maintenance-note.json'),maintenance_note_sha256=hashlib.sha256((M/'zero-startup-failure-maintenance-note.json').read_bytes()).hexdigest(),worker_result_missing=True,known_Runtime_Actor_task_aux0=True,worker_wall_RSS_unknown_not_zero=True);h['updated_at']=note['at'];assert all(h[k]==v for k,v in saved.items()if k not in(KEY,'updated_at'));after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,tmp=tempfile.mkstemp(prefix='.H-E20-data-startup-close-',dir=H.parent)
  try:
   os.fchmod(fd,stat.S_IMODE(st.st_mode))
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fsync(out.fileno())
   assert H.read_bytes()==raw;os.replace(tmp,H);os.fsync(dfd)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
finally:os.close(dfd)
print(json.dumps(dict(note=note,before_H_sha256=hashlib.sha256(raw).hexdigest(),after_H_sha256=hashlib.sha256(after).hexdigest(),after_base64=base64.b64encode(after).decode(),all_other_fields_unchanged=True)))
''';r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(before_sha=hashlib.sha256(old).hexdigest(),owner=OWNER)),capture_output=True,text=True,timeout=45);assert r.returncode==0,r.stderr;x=json.loads(r.stdout);raw=base64.b64decode(x.pop('after_base64'));assert hashlib.sha256(raw).hexdigest()==x['after_H_sha256'];sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror;mirror(raw,hashlib.sha256(old).hexdigest());(M/'zero-startup-maintenance-close-proof.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(closed=True,note=x['note']),ensure_ascii=False,indent=2))
