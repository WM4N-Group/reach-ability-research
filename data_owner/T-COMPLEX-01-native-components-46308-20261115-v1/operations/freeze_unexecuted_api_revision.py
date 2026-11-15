from pathlib import Path
import json,subprocess,shlex,hashlib,base64,sys,os
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;W=B/'workers'/M.name;sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror
sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();p=W/'worker_api_v2.py';x=dict(owner=os.environ['CODEX_THREAD_ID'],expected=sha(before),source=base64.b64encode(p.read_bytes()).decode(),source_sha256=sha(p.read_bytes()),review=base64.b64encode((M/'PRELAUNCH_API_CORRECTION_NO_PHYSICAL_ATTEMPT.json').read_bytes()).decode())
code=r'''from pathlib import Path
import json,sys,base64,hashlib,os,fcntl,stat,tempfile,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='T-COMPLEX-01-native-components-46308-20261115-v1';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=lambda b:hashlib.sha256(b).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat();oldfreeze=json.loads((M/'program-freeze.json').read_bytes());old_program=sha(M/'program-freeze.json');assert old_program=='7ac90d41b23d213abc8cee48a9a836f74bab381160a7972657ba5934240f0c90';assert not(R/'runtime/workers'/oldfreeze['scope_id']).exists()
for p,pin in oldfreeze['files'].items():assert sha(p)==pin
p=W/'worker_api_v2.py';assert not p.exists();raw=base64.b64decode(x['source']);assert digest(raw)==x['source_sha256']
with p.open('xb')as f:f.write(raw)
with(M/'PRELAUNCH_API_CORRECTION_NO_PHYSICAL_ATTEMPT.json').open('xb')as f:f.write(base64.b64decode(x['review']))
oldauth=B/'registry/T_COMPLEX_NATIVE_COMPONENT_ZERO_AUTHORITY_20261115_v1.json';a=json.loads(oldauth.read_bytes());a.update(at=now(),revision=2,withdrawn_unexecuted_program_sha256=old_program,reason='RegisteredObserver public acquisition method capture, not nonexistent acquire; found before physical claim. Old worker/freeze unchanged.',same_scope_total_component_zero_limit=1,previous_physical_dispatches=0);AUTH=B/'registry/T_COMPLEX_NATIVE_COMPONENT_ZERO_API_v2_AUTHORITY_20261115.json';assert not AUTH.exists()
with AUTH.open('x')as f:json.dump(a,f,indent=2);f.write('\n')
freeze=dict(oldfreeze,at=now(),revision=2,authorization_sha256=sha(AUTH),withdrawn_unexecuted_program_sha256=old_program,files=dict(oldfreeze['files'],**{str(p):sha(p),str(AUTH):sha(AUTH),str(M/'PRELAUNCH_API_CORRECTION_NO_PHYSICAL_ATTEMPT.json'):sha(M/'PRELAUNCH_API_CORRECTION_NO_PHYSICAL_ATTEMPT.json')}));F=M/'program-freeze-api-v2.json'
with F.open('x')as f:json.dump(freeze,f,indent=2);f.write('\n')
program=sha(F);d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);before=f.read();st=os.fstat(f.fileno());assert digest(before)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(before);q=h['active_T_COMPLEX_component_zero_scope'];assert h['executing_thread_id']==x['owner']and q['component_zero_dispatch_count']==q['task_main_dispatch_count']==0 and q['component_zero_dispatch_program_sha256']is None and q['whole_program_freeze_sha256']==old_program
  q.update(whole_program_freeze_sha256=program,authorization_sha256=sha(AUTH),revision=2,withdrawn_unexecuted_program_sha256=old_program,unexecuted_revision_not_physical_retry=True);h['updated_at']=now();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-unexecuted-component-api-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
   assert H.read_bytes()==before;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(at=now(),before_H_sha256=digest(before),after_H_sha256=digest(after),old_unexecuted_program_preserved=old_program,program_sha256=program,authorization_sha256=sha(AUTH),all_physical_dispatch_counts_remain0=True,original_frozen_members_unchanged=True,new_scope_or_retry_not_created=True)
with(M/'unexecuted-api-v2-CAS.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(after).decode())))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=120)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('unexecuted-api-v2.'+suf)).write_text(t)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['proof']['after_H_sha256'];mirror(raw,sha(before));(M/'unexecuted-api-v2-CAS.json').write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps(v['proof'],indent=2))
