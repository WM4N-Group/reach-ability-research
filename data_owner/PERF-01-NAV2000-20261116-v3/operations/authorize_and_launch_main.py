from pathlib import Path
import json,hashlib,os,fcntl,tempfile,datetime,subprocess,sys,time
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='perf-NAV2000-indexed-46308-20261116-v3';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';A=B/'registry/PERF01_NAV2000_INDEXED_AUTHORITY_20261116_v3.json';KEY='active_PERF01_NAV2000_indexed_v3_scope';SCOPE='data-46308-perf-NAV2000-indexed-20261116-v3';OWNER='01a1e4e1-3037-7333-9019-a3f37effe5da';PIN=hashlib.sha256((M/'program-freeze.json').read_bytes()).hexdigest();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat();start=time.monotonic()
assert sha(M/'program-freeze.json')==PIN;assert (R/'runtime/workers'/SCOPE/'zero/result.json').is_file() and not(R/'runtime/workers'/SCOPE/'main').exists();c=json.loads((W/'protocol.json').read_bytes());auth=json.loads(A.read_bytes());assert auth['own_zero_max']==auth['main_max']==1
used=int(subprocess.check_output(['du','-s','-B1','/mnt/yuanyue/data-team'],text=True).split()[0]);reservation=(1<<30)+524288;assert used+reservation<40*1024**3
stats={name:[(R/'resource-locks'/name).stat().st_dev,(R/'resource-locks'/name).stat().st_ino]for name in ['native-observer-physics-gpu0.lock','native-observer-sdk-gpu0.lock']};assert list(stats.values())==[[51,3428729629],[51,3428729630]]
kernel_locks=Path('/proc/locks').read_text().splitlines()
assert not any(len(line.split())>5 and line.split()[5].split(':')[-1]in {'3428729629','3428729630'}for line in kernel_locks),'GPU0 canonical locks already held'
gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True);assert 'GPU-297c1146-bcec-a8ee-8437-d9603392a2e1'in gpu
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
 except OSError:continue
 assert not any(s in cmd for s in [str(B/'workers')+'/',str(R/'runtime/workers')+'/',str(R/'runtime/diagnostics')+'/']),(proc.name,cmd[:500])
raw=H.read_bytes();before=json.loads(raw);assert before['executing_thread_id']==OWNER and not before['bulk24_collector_v1']['global_stop'];q=before[KEY];assert q['owner']==OWNER and q['active']and q['zero_passed']and q['zero_dispatch_count']==1 and q['main_dispatch_count']==0 and q['whole_program_freeze_sha256']==PIN;assert all(not v.get('active',False)for k,v in before.items()if isinstance(v,dict)and k!=KEY);assert sha(R/'runtime/workers'/SCOPE/'zero/result.json')==q['zero_result_sha256'];assert before['active_E20_prearrival40_v3_scope']['main_dispatch_count']==1 and not before['active_E20_prearrival40_v3_scope']['active']
after=json.loads(raw);after[KEY].update(main_dispatch_count=1,phase='PERF01_MAIN_AUTHORIZED_ONCE',main_authorized_at=now())
dfd=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(dfd,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==raw and H.stat().st_ino==st.st_ino
  fd,tmp=tempfile.mkstemp(prefix='.PERF01-zero-',dir=H.parent)
  try:
   os.fchmod(fd,st.st_mode&0o7777)
   with os.fdopen(fd,'wb')as out:out.write((json.dumps(after,ensure_ascii=False,indent=2)+'\n').encode());out.flush();os.fsync(out.fileno())
   assert H.read_bytes()==raw;os.replace(tmp,H);os.fsync(dfd)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
finally:os.close(dfd)
proof=dict(at=now(),before_H_SHA=hashlib.sha256(raw).hexdigest(),after_H_SHA=sha(H),program_sha256=PIN,old_all_fields_semantically_unchanged=all(after[k]==v for k,v in before.items()if k!=KEY),own_zero1_main_authorized1=True,scope_id=SCOPE)
(M/'main-dispatch-CAS-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');(M/'H-before-main-CAS.json').write_bytes(raw)
# Separate bounded launch diagnostics, fully pre-reserved outside native S root.
# Child counters own ONLY S; parent owns ONLY this disjoint launch-root. Never fork-share.
sys.path.insert(0,str(W/'policy'));from scoped_io import ScopeIO
from controlled_process import ControlledProcess
from runner_outputs import write_json,finish_accounting
L=M/'launcher-main';L.mkdir();budget=ScopeIO(L,cap_bytes=262144,reserve_bytes=65536,max_open=4,text_buffer_bytes=8192)
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=c['GPU_UUID'],MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='0',LD_PRELOAD=c['LD_PRELOAD'])
child=ControlledProcess(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(W/'worker/worker.py'),'--enabled','--phase','main','--config',str(W/'protocol.json'),'--program-sha256',PIN],budget,stdout_path='startup.stdout',stderr_path='startup.stderr',env=env,cwd=str(W),enabled=True)
(M/'main-controller-PID.json').write_text(json.dumps(dict(at=now(),PID=child.process.pid,program_sha256=PIN,phase='main',launcher_has_disjoint_bounded_budget=True))+'\n')
try:receipt=child.finish(timeout_s=1230.)
except BaseException as e:receipt=getattr(e,'receipt',dict(error=repr(e),returncode=child.process.poll()))
budget.begin_finalization();write_json(budget,L/'launcher-result.json',dict(at=now(),capture=receipt,wall_s=time.monotonic()-start,main_result_exists=(R/'runtime/workers'/SCOPE/'main/result.json').exists()));finish_accounting(budget,L/'final-accounting.json')
print(json.dumps(dict(CAS=proof,child_PID=child.process.pid,capture=receipt,main_result_exists=(R/'runtime/workers'/SCOPE/'main/result.json').exists(),wall_s=time.monotonic()-start)))
