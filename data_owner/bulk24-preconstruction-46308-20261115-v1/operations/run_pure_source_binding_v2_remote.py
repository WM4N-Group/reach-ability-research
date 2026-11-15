"""Fix own not-frozen Data metadata verifier only, then fenced source probe v2.
This is not physical retry; no runtime scope, authority, lease or native call.
"""
from pathlib import Path
import subprocess,shlex,json,base64,hashlib
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;D=B/'development'/M.name;fix=json.loads((M/'declared-source-note-preconstruction-fix.json').read_bytes());x=dict(expected_H=hashlib.sha256((B/'registry/handoff_46308_current_status_20261115.json').read_bytes()).hexdigest(),files={rel:dict(expected=row['before_sha256'],data=base64.b64encode((D/rel).read_bytes()).decode())for rel,row in fix['changed_files'].items()})
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,os,subprocess,datetime,fcntl,stat,tempfile
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';H=B/'registry/handoff_current_status_20261115.json';before=H.read_bytes();assert hashlib.sha256(before).hexdigest()==x['expected_H'];D=B/'development/bulk24-preconstruction-46308-20261115-v1';M=B/'manifests/bulk24-preconstruction-46308-20261115-v1'
for rel,row in x['files'].items():
 assert rel in('inputs/AINav/explicit_preparation_consumer.py','SOURCE_CUSTODY.json','prepare_bulk24.py');p=D/rel;new=base64.b64decode(row['data']);d=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with p.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert hashlib.sha256(old).hexdigest()==row['expected']and(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino)
   with(M/(p.name+'.before-declared-note-fix')).open('xb')as backup:backup.write(old)
   fd,t=tempfile.mkstemp(prefix='.preconstruction-note-fix-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(new);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert p.read_bytes()==old;os.replace(t,p);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
E=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1',LD_PRELOAD=str(R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1'));r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(D/'prepare_bulk24.py'),'--enable-pure-source-binding'],env=E,capture_output=True,text=True,timeout=120)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('pure-source-binding-v2.'+suffix)).open('x')as f:f.write(text)
assert H.read_bytes()==before
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,H_unchanged=True,no_scope_allocated=True,no_native_dispatch=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=180)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('pure-binding-v2-transport.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
for suffix,text in [('stdout',v['stdout']),('stderr',v['stderr']),('exit',str(v['exit_code'])+'\n')]:
 with(M/('pure-source-binding-v2.'+suffix)).open('x')as f:f.write(text)
assert v['exit_code']==0,v['stderr'];report=json.loads(v['stdout']);report['remote_probe_H_unchanged']=v['H_unchanged']
with(M/'actual-pure-source-binding.json').open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:z for k,z in report.items()if k!='rows'},ensure_ascii=False,indent=2))
