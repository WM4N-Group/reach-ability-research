"""Only the new V4 component lifecycle; no old scope or GPU1 mutations."""
from pathlib import Path
import sys,os,json,hashlib,base64,subprocess,fcntl,stat,tempfile,datetime
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='V4-common-palette-bounded-native-46308-20261116-v2';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';AUTH=B/'registry/V4_COMMON_PALETTE_BOUNDED_AUTHORITY_20261116_v2.json';PY='/mnt/yuanyue/data-team/env-native-v1/bin/python';SDK=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle');SOURCE=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source';KEY='active_V4_palette_bounded_v2_scope';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';C=json.loads((W/'protocol.json').read_bytes());ROOT=R/'runtime/workers'/C['scope_id'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=lambda raw:hashlib.sha256(raw).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat()
def record(p,v):
 with p.open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def fresh():
 h=json.loads(H.read_bytes());assert h['executing_thread_id']==OWNER and not h['bulk24_collector_v1']['global_stop'];assert all(not h[k]['active']for k in ['active_V4_palette_bounded_scope','active_V4_parallel_guard_bounded_scope','active_V4_bounded_climb_nav_scope','active_V4_bounded_climb_nav_v2_scope','active_V4_capture_execution_scope','active_V4_native_component_scope','active_new_critic_cohort_scope','active_T_COMPLEX_component_zero_scope','active_T_COMPLEX_v2_camera_component_scope','active_T_COMPLEX_observation_study_scope','active_T_COMPLEX_full_program_scope'])
 q=h['active_bulk24_collector_scope'];allowed=[]
 if q['active']:
  p=R/'runtime/workers'/q['scope_id']/'accounting/ledger.json'
  if p.exists():
   l=json.loads(p.read_bytes())
   if l['rows']and Path('/proc/'+str(l['rows'][-1]['PID'])).exists():allowed=[l['rows'][-1]['PID']]
 active=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:args=[x.decode(errors='replace')for x in(p/'cmdline').read_bytes().split(b'\0')if x]
  except OSError:continue
  if any(x.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for x in args):active.append(int(p.name))
 assert sorted(active)==sorted(allowed),(active,allowed)
 locks=[]
 for kind,ino in [('physics',3428729629),('sdk',3428729630)]:
  p=R/f'resource-locks/native-observer-{kind}-gpu0.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
  try:
   st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,ino)==(p.stat().st_dev,p.stat().st_ino);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN);locks.append(dict(path=str(p),device=51,inode=ino,free_snapshot_not_lease=True))
  finally:os.close(fd)
 gpu=subprocess.check_output(['nvidia-smi','--id='+C['GPU_UUID'],'--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=15).strip().split(',');assert gpu[0].strip()=='0'and gpu[1].strip()==C['GPU_UUID']and int(gpu[2])>=4096
 owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);reserve=8053063680+3221225472+1073741824+C['output_cap_bytes'];assert owned+reserve<40*1024**3
 available=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:'));assert available>=8*1024**3
 return dict(at=now(),GPU0_free_MiB=int(gpu[2]),canonical_GPU0_locks=locks,owned_bytes=owned,conservative_reserve_bytes=reserve,owned_limit_bytes=40*1024**3,provider_quota_unknown=True,available_RAM_bytes=available,legitimate_GPU1_native_PIDs_preserved=allowed,no_owned_GPU0_native=True,no_new_lease_from_snapshot=True)
def cas(change):
 # Read fresh immediately before the locked SHA CAS. Bulk parent is held at a
 # non-mutating main-run/fetch boundary by the local one-shot orchestration gate.
 before=H.read_bytes();expected=digest(before);dfd=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with H.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);raw=f.read();st=os.fstat(f.fileno());assert digest(raw)==expected and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);v=json.loads(raw);saved=json.loads(raw);assert v['executing_thread_id']==OWNER;change(v);assert all(v[k]==val for k,val in saved.items()if k not in(KEY,'updated_at'));v['updated_at']=now();after=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode();fd,tmp=tempfile.mkstemp(prefix='.H-V4-component-',dir=H.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert H.read_bytes()==raw;os.replace(tmp,H);os.fsync(dfd)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 finally:os.close(dfd)
 return dict(before_H_sha256=digest(before),after_H_sha256=digest(after),after_base64=base64.b64encode(after).decode(),all_non_component_H_fields_preserved=True)
def env():
 return dict(os.environ,LD_PRELOAD=str(R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1'),CUDA_VISIBLE_DEVICES=C['GPU_UUID'],MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='0',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
action=sys.argv[1]
if action=='inventory':
 resources=fresh();assert not ROOT.exists()and KEY not in json.loads(H.read_bytes());files={}
 for line in(SDK/'SHA256SUMS').read_text().splitlines():
  pin,rel=line.split(None,1);rel=rel.strip().removeprefix('*');p=SDK/rel;assert not Path(rel).is_absolute()and'..'not in Path(rel).parts and not p.is_symlink()and p.resolve().is_relative_to(SDK)and sha(p)==pin;files[str(p)]=pin
 for name in('MANIFEST.json','SHA256SUMS'):files[str(SDK/name)]=sha(SDK/name)
 for folder in(W,SOURCE):
  for p in folder.rglob('*'):
   if p.is_file()and'__pycache__'not in p.parts and p.suffix!='.pyc':assert not p.is_symlink();files[str(p)]=sha(p)
 for p in (SOURCE.parent/'reach_stow_choice').glob('*.py'):files[str(p)]=sha(p)
 for p in [Path(C['static_MJB_input']),Path(__file__),B/'development/bulk-resource-adapter-46308-20261115-v1/per_gpu_lease.py',B/'development/bulk-resource-adapter-46308-20261115-v1/gpu_observation.py',B/'workers/new-critic-cohort-46308-20261115-v1/raw_third_view.py',R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1',R/'resource-locks/46308-gpu0-bulk-canonical-binding-20261115-v1.json']:
  assert not p.is_symlink();files[str(p)]=sha(p)
 assert files[str(R/'resource-locks/46308-gpu0-bulk-canonical-binding-20261115-v1.json')]=='50d6365e40fa07402d6765809b841cd29cc7b0c2a93d00542aecc92879df1bcd'
 authority=dict(schema='Data-V4-component-zero-only-authority-v1',at=now(),owner=OWNER,scope_id=C['scope_id'],allowed_component_zero_invocations=1,allowed_task_main_invocations=0,automatic_retry=False,main_plan_sha256=C['main_plan_sha256'],protocol_sha256=sha(W/'protocol.json'),source_request_sha256=C['source_request_sha256'],GPU_UUID=C['GPU_UUID'],GPU_index=0,not_E_or_A_B_C_D_or_training=True,limits={k:C[k]for k in ['task_world_steps_allowed','task_world_sim_cap_s','sim_aux_cap_s','wall_cap_s','output_cap_bytes','own_GPU_cap_bytes','own_RSS_cap_bytes','CPU_threads','metadata_path_read_threads']});record(AUTH,authority);files[str(AUTH)]=sha(AUTH)
 freeze=dict(schema='Data-V4-complete-component-program-freeze-v1',at=now(),scope_id=C['scope_id'],authorization_sha256=sha(AUTH),component_zero_max=1,task_main_max=0,files=files);record(M/'program-freeze.json',freeze);record(M/'pre-authority-resource-snapshot.json',resources);print(json.dumps(dict(program_sha256=sha(M/'program-freeze.json'),authorization_sha256=sha(AUTH),members=len(files),resources=resources,no_H_write=True)))
elif action=='freeze':
 p=sha(M/'program-freeze.json');f=json.loads((M/'program-freeze.json').read_bytes());assert all(sha(n)==s for n,s in f['files'].items());resources=fresh()
 def change(h):
  assert KEY not in h and not ROOT.exists();h[KEY]=dict(active=True,owner=OWNER,scope_id=C['scope_id'],phase='FROZEN_COMPONENT_PREPARE_NO_DISPATCH',authorization_sha256=sha(AUTH),whole_program_freeze_sha256=p,component_zero_dispatch_count=0,component_zero_dispatch_program_sha256=None,task_main_dispatch_count=0,automatic_retry=False,source_commit=C['new_source_owner_commit'],source_role=C['purpose'],fresh_resource_snapshot=resources)
 v=cas(change);record(M/'freeze-CAS.json',{k:x for k,x in v.items()if k!='after_base64'});print(json.dumps(v))
elif action=='prepare':
 h=json.loads(H.read_bytes());q=h[KEY];assert q['active']and q['component_zero_dispatch_count']==0 and not ROOT.exists();p=q['whole_program_freeze_sha256']
 r=subprocess.run(['taskset','-c','36,37',PY,'-I','-B',str(W/'worker.py'),'--phase','prepare','--program-sha256',p],env=env(),capture_output=True,text=True,timeout=90)
 for suffix,text in [('stdout',r.stdout),('stderr',r.stderr)]:
  with(M/('prepare.'+suffix)).open('x')as f:f.write(text)
 record(M/'prepare-exit.json',dict(exit_code=r.returncode));assert r.returncode==0,r.stderr;assert not ROOT.exists();print(json.dumps(dict(prepared=True,physical_dispatches=0,stdout=r.stdout)))
elif action=='dispatch':
 assert json.loads((M/'prepare-exit.json').read_bytes())['exit_code']==0;resources=fresh();p=sha(M/'program-freeze.json')
 def change(h):
  q=h[KEY];assert q['active']and q['owner']==OWNER and q['component_zero_dispatch_count']==q['task_main_dispatch_count']==0 and q['whole_program_freeze_sha256']==p and not ROOT.exists();q.update(phase='CAS_DISPATCHED_COMPONENT_ZERO_ONLY',component_zero_dispatch_count=1,component_zero_dispatch_program_sha256=p,dispatch_at=now(),fresh_resource_snapshot=resources)
 v=cas(change);record(M/'dispatch-CAS.json',{k:x for k,x in v.items()if k!='after_base64'});print(json.dumps(v))
elif action=='run':
 q=json.loads(H.read_bytes())[KEY];p=q['whole_program_freeze_sha256'];assert q['active']and q['component_zero_dispatch_count']==1 and q['component_zero_dispatch_program_sha256']==p and q['task_main_dispatch_count']==0 and not ROOT.exists();resources=fresh();record(M/'component-launch-once.json',dict(at=now(),program_sha256=p,resources=resources,automatic_retry=False))
 with(M/'component.stdout').open('xb')as out,(M/'component.stderr').open('xb')as err:
  child=subprocess.Popen(['taskset','-c','36,37',PY,'-I','-B',str(W/'worker.py'),'--phase','component-zero','--program-sha256',p],env=env(),stdout=out,stderr=err);record(M/'component-child.json',dict(PID=child.pid,at=now(),CPUs=[36,37]))
  try:rc=child.wait(timeout=C['wall_cap_s']+40)
  except subprocess.TimeoutExpired:
   child.terminate()
   try:rc=child.wait(timeout=10)
   except subprocess.TimeoutExpired:child.kill();rc=child.wait(timeout=10)
 record(M/'component-exit.json',dict(exit_code=rc,at=now()));print(json.dumps(dict(exit_code=rc,result_available=(ROOT/'result.json').exists(),stderr=(M/'component.stderr').read_text()[-3000:])))
elif action=='close':
 q=json.loads(H.read_bytes())[KEY];assert q['active']and q['component_zero_dispatch_count']==1 and q['task_main_dispatch_count']==0;assert(M/'component-exit.json').exists();resources=fresh();p=sha(M/'program-freeze.json');result=ledger=None
 if(ROOT/'result.json').exists():
  result=json.loads((ROOT/'result.json').read_bytes());ledger=json.loads((ROOT/'ledger.json').read_bytes());assert not Path('/proc/'+str(result['PID'])).exists()and ledger['closed']and ledger['result_sha256']==sha(ROOT/'result.json')and result['program_sha256']==p and result['comparison_main_calls']==0
 def change(h):
  q=h[KEY];assert q['active']and q['component_zero_dispatch_count']==1 and q['component_zero_dispatch_program_sha256']==p and q['task_main_dispatch_count']==0;q.update(active=False,phase='CLOSED_COMPONENT_PASS_NOT_TASK_READY'if result and result['passed']else'CLOSED_COMPONENT_FAILED_OR_UNKNOWN_NO_RETRY',component_zero_dispatch_program_sha256=None,closed_at=now(),actual_result_sha256=sha(ROOT/'result.json')if result else None,actual_ledger_sha256=sha(ROOT/'ledger.json')if ledger else None,source_repair_required=not(result and result['passed']),usage_known=bool(ledger and ledger['usage_known']),closure_resource_snapshot=resources)
 v=cas(change);record(M/'close-CAS.json',{k:x for k,x in v.items()if k!='after_base64'});v.update(result=result,ledger=ledger,small_files={p.name:base64.b64encode(p.read_bytes()).decode()for p in ROOT.glob('*.json')if p.stat().st_size<2*1024**2});print(json.dumps(v))
else:raise ValueError('Only the explicit new component lifecycle actions are accepted')
