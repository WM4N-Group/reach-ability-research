"""Explicit one-shot component control, never AB/task main. No retry action."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,shlex,base64
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;N=M.name
OWNER=os.environ['CODEX_THREAD_ID'];assert OWNER==os.environ['CODEX_SESSION_ID']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
sha=lambda b:hashlib.sha256(b).hexdigest()
sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror
PRELUDE=r'''
from pathlib import Path
import os,sys,json,hashlib,subprocess,fcntl,stat,tempfile,datetime,base64,time
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='T-COMPLEX-01-native-components-46308-20261115-v1';M=B/'manifests'/N;W=B/'workers'/N;H=B/'registry/handoff_current_status_20261115.json';F=M/'program-freeze-api-v2.json';P='d239b27f0e73adf6213eaaadfaa0dee29e3addaa7821f33775657014406147df';C=json.loads((W/'protocol.json').read_bytes());ROOT=R/'runtime/workers'/C['scope_id'];digest=lambda b:hashlib.sha256(b).hexdigest();sha=lambda p:digest(Path(p).read_bytes());now=lambda:datetime.datetime.now().astimezone().isoformat()
assert sha(F)==P
h=json.loads(H.read_bytes());q=h['active_T_COMPLEX_component_zero_scope'];assert h['executing_thread_id']==q['owner']==x['owner'];assert q['whole_program_freeze_sha256']==P and q['task_main_dispatch_count']==0
E=os.environ.copy();E.update(LD_PRELOAD=str(R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1'),CUDA_VISIBLE_DEVICES=C['GPU_UUID'],MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='0',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1');PY='/mnt/yuanyue/data-team/env-native-v1/bin/python'
def record(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n');f.flush();os.fsync(f.fileno())
def active():
 rows=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:args=[v.decode(errors='replace')for v in(p/'cmdline').read_bytes().split(b'\0')if v]
  except(OSError,ProcessLookupError):continue
  if any(v.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for v in args):rows.append(dict(PID=int(p.name),args=args))
 return rows
def resource_check():
 assert not active(),active()
 locks=[]
 for gpu,inos in [(0,(3428729629,3428729630)),(1,(3428459217,3428459218))]:
  bind=R/'resource-locks'/('46308-gpu0-bulk-canonical-binding-20261115-v1.json'if gpu==0 else'46308-canonical-binding-20261115-v1.json');v=json.loads(bind.read_bytes())
  assert [r['inode']for r in v['locks']]==list(inos)
  for row in v['locks']:
   p=Path(row['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
   try:
    st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(row['device'],row['inode']);assert(p.stat().st_dev,p.stat().st_ino)==(st.st_dev,st.st_ino);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(row);fcntl.flock(fd,fcntl.LOCK_UN)
   finally:os.close(fd)
 owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);assert owned+6*1610612736+1073741824<42949672960
 gpu=subprocess.check_output(['nvidia-smi','--id='+C['GPU_UUID'],'--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=15).strip().split(',');assert gpu[0].strip()=='0'and gpu[1].strip()==C['GPU_UUID']and int(gpu[2])>=4096
 return dict(at=now(),owned_bytes=owned,retained_CAL_VAL_reserve_bytes=6*1610612736,component_reserve_bytes=1073741824,provider_quota_unknown=True,GPU0_free_MiB=int(gpu[2]),locks_free_snapshot=locks,no_owned_native=True)
def cas(change):
 d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(d,fcntl.LOCK_EX)
  with H.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);before=f.read();st=os.fstat(f.fileno());assert digest(before)==x['expected'];assert(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);v=json.loads(before);saved=json.loads(before);change(v);assert all(v[k]==val for k,val in saved.items()if k not in('active_T_COMPLEX_component_zero_scope','updated_at'));v['updated_at']=now();after=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-component-control-',dir=H.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert H.read_bytes()==before;os.replace(t,H);os.fsync(d)
   finally:
    if os.path.exists(t):os.unlink(t)
 finally:os.close(d)
 return dict(before_H_sha256=digest(before),after_H_sha256=digest(after),after_base64=base64.b64encode(after).decode())
'''
ACTIONS={
'prepare':r'''
assert q['active']and q['component_zero_dispatch_count']==0 and not ROOT.exists()
with(M/'prepare-api-v2.stdout').open('xb')as out,(M/'prepare-api-v2.stderr').open('xb')as err:
 r=subprocess.run([PY,'-I','-B',str(W/'worker_api_v2.py'),'--phase','prepare','--program-sha256',P],env=E,stdout=out,stderr=err,timeout=90)
record(M/'prepare-api-v2.exit.json',dict(at=now(),exit_code=r.returncode));assert r.returncode==0,(M/'prepare-api-v2.stderr').read_text();assert not ROOT.exists();print(json.dumps(dict(prepared=True,physical_dispatch_count=0,stdout=(M/'prepare-api-v2.stdout').read_text())))
''',
'dispatch':r'''
assert q['active']and q['component_zero_dispatch_count']==0 and not ROOT.exists();assert json.loads((M/'prepare-api-v2.exit.json').read_bytes())['exit_code']==0
resources=resource_check()
def change(v):
 q=v['active_T_COMPLEX_component_zero_scope'];assert q['active']and q['owner']==x['owner']and q['component_zero_dispatch_count']==0 and q['component_zero_dispatch_program_sha256']is None and q['whole_program_freeze_sha256']==P and q['task_main_dispatch_count']==0
 q.update(phase='CAS_DISPATCHED_COMPONENT_ZERO_ONLY',component_zero_dispatch_count=1,component_zero_dispatch_program_sha256=P,dispatch_at=now(),fresh_resource_snapshot=resources)
r=cas(change);record(M/'component-dispatch-CAS.json',{k:v for k,v in r.items()if k!='after_base64'});print(json.dumps(r))
''',
'run':r'''
assert q['active']and q['component_zero_dispatch_count']==1 and q['component_zero_dispatch_program_sha256']==P and not ROOT.exists();resources=resource_check();record(M/'component-launch-once.json',dict(at=now(),program_sha256=P,resources=resources,automatic_retry=False))
cpus=sorted(os.sched_getaffinity(0))[:2]
with(M/'component.stdout').open('xb')as out,(M/'component.stderr').open('xb')as err:
 p=subprocess.Popen(['taskset','-c',','.join(map(str,cpus)),PY,'-I','-B',str(W/'worker_api_v2.py'),'--phase','component-zero','--program-sha256',P],env=E,stdout=out,stderr=err)
 record(M/'component-child-PID.json',dict(at=now(),PID=p.pid,CPUs=cpus))
 try:rc=p.wait(timeout=200)
 except subprocess.TimeoutExpired:
  p.terminate()
  try:rc=p.wait(timeout=15)
  except subprocess.TimeoutExpired:p.kill();rc=p.wait(timeout=10)
record(M/'component.exit.json',dict(at=now(),exit_code=rc));print(json.dumps(dict(exit_code=rc,result_available=(ROOT/'result.json').exists(),stderr=(M/'component.stderr').read_text()[-5000:])))
''',
'close':r'''
assert q['active']and q['component_zero_dispatch_count']==1 and q['component_zero_dispatch_program_sha256']==P
exitv=json.loads((M/'component.exit.json').read_bytes());resources=resource_check();result=json.loads((ROOT/'result.json').read_bytes());ledger=json.loads((ROOT/'ledger.json').read_bytes());assert sha(ROOT/'result.json')==ledger['result_sha256']and result['program_sha256']==P and result['comparison_main_calls']==0;assert not Path('/proc/'+str(result['PID'])).exists()
def change(v):
 q=v['active_T_COMPLEX_component_zero_scope'];assert q['active']and q['owner']==x['owner']and q['component_zero_dispatch_count']==1 and q['component_zero_dispatch_program_sha256']==P and q['task_main_dispatch_count']==0
 q.update(active=False,phase='CLOSED_COMPONENT_ZERO_PASS_NOT_TASK_READY'if result['passed']else'CLOSED_COMPONENT_ZERO_FAILED_NO_RETRY',component_zero_dispatch_program_sha256=None,actual_result_sha256=sha(ROOT/'result.json'),actual_ledger_sha256=sha(ROOT/'ledger.json'),closed_at=now(),closure_resource_snapshot=resources,source_repair_required=not result['passed'])
r=cas(change);record(M/'component-close-CAS.json',{k:v for k,v in r.items()if k!='after_base64'});r.update(result=result,ledger=ledger,small_files={str(p.relative_to(ROOT)):base64.b64encode(p.read_bytes()).decode()for p in ROOT.glob('*.json')if p.stat().st_size<2000000});print(json.dumps(r))
'''}
if __name__=='__main__':
 action=sys.argv[1];assert action in ACTIONS
 before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();x=dict(owner=OWNER,expected=sha(before))
 r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(PRELUDE+ACTIONS[action])],input=json.dumps(x),capture_output=True,text=True,timeout=330)
 for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
  with(M/(action+'-control.'+suffix)).open('x')as f:f.write(text)
 assert r.returncode==0,r.stderr
 v=json.loads(r.stdout)
 if 'after_base64'in v:
  raw=base64.b64decode(v.pop('after_base64'));assert sha(raw)==v['after_H_sha256'];mirror(raw,sha(before))
 if 'small_files'in v:
  D=M/'actual-small';D.mkdir()
  for name,data in v.pop('small_files').items():assert Path(name).name==name;(D/name).write_bytes(base64.b64decode(data))
 with(M/(action+'-control-receipt.json')).open('x')as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
 print(json.dumps(v,indent=2,ensure_ascii=False))
