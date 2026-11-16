"""Single new E program: technical own-zero, frozen camera, ONE actual E main. No old scope reuse."""
from pathlib import Path
import os,sys,json,hashlib,fcntl,tempfile,stat,subprocess,base64,datetime
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='E20-prearrival40-direct-live-46308-20261116-v2';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';A=B/'registry/E20_PREARRIVAL40_AUTHORITY_20261116_v2.json';KEY='active_E20_prearrival40_v2_scope';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';C=json.loads((W/'protocol.json').read_bytes());S=R/'runtime/workers'/C['scope_id'];SDK=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle');SOURCE=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source';PY='/mnt/yuanyue/data-team/env-native-v1/bin/python';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat()
def record(p,x):
 with p.open('x')as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def fresh():
 h=json.loads(H.read_bytes());assert not h['bulk24_collector_v1']['global_stop'];assert h['executing_thread_id']==OWNER and not any(v['active']for k,v in h.items()if k.startswith('active_')and k!=KEY and isinstance(v,dict)and'active'in v);active=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:args=[s.decode(errors='replace')for s in(p/'cmdline').read_bytes().split(b'\0')if s]
  except OSError:continue
  if any(a.startswith((str(B/'workers')+'/',str(R/'runtime')+'/'))for a in args):active.append(int(p.name))
 assert not active,active
 for kind,ino in [('physics',3428729629),('sdk',3428729630)]:
  p=R/f'resource-locks/native-observer-{kind}-gpu0.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
  try:st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,ino)==(p.stat().st_dev,p.stat().st_ino);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
  finally:os.close(fd)
 gpu=subprocess.check_output(['nvidia-smi','--id='+C['GPU_UUID'],'--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=15).strip().split(',');assert gpu[0].strip()=='0'and gpu[1].strip()==C['GPU_UUID']and int(gpu[2])>=4096;owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);assert owned+8*1024**3+3*1024**3+2*1024**3<40*1024**3
 return dict(at=now(),owned_bytes=owned,limit_bytes=40*1024**3,provider_quota_unknown=True,GPU0_free_MiB=int(gpu[2]),other_Data_workers0=True,canonical_original_inodes_free_not_new_lease=True)
def cas(fn):
 before=H.read_bytes();pin=hashlib.sha256(before).hexdigest();dfd=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:
  fcntl.flock(dfd,fcntl.LOCK_EX)
  with H.open('rb')as f:
   fcntl.flock(f,fcntl.LOCK_EX);raw=f.read();st=os.fstat(f.fileno());assert hashlib.sha256(raw).hexdigest()==pin;h=json.loads(raw);old=json.loads(raw);assert h['executing_thread_id']==OWNER;fn(h);assert all(h[k]==v for k,v in old.items()if k not in(KEY,'updated_at'));h['updated_at']=now();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,tmp=tempfile.mkstemp(prefix='.H-E-first-',dir=H.parent)
   try:
    with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
    assert H.read_bytes()==raw;os.replace(tmp,H);os.fsync(dfd)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
 finally:os.close(dfd)
 return dict(before_H_sha256=pin,after_H_sha256=hashlib.sha256(after).hexdigest(),after_base64=base64.b64encode(after).decode(),all_non_E_H_fields_preserved=True)
def env():return dict(os.environ,LD_PRELOAD=str(R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1'),CUDA_VISIBLE_DEVICES=C['GPU_UUID'],MUJOCO_GL='egl',MUJOCO_EGL_DEVICE_ID='0',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
def collect_files():
 files={}
 for folder in [W,SOURCE]:
  for p in folder.rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':
    assert not p.is_symlink();files[str(p)]=sha(p)
 for line in (SDK/'SHA256SUMS').read_text().splitlines():
  digest,rel=line.split(None,1);p=SDK/rel.strip().removeprefix('*');assert not p.is_symlink()and p.resolve().is_relative_to(SDK)and sha(p)==digest;files[str(p)]=digest
 for p in [SDK/'MANIFEST.json',SDK/'SHA256SUMS',Path(C['model_path']),Path(__file__),R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1',R/'resource-locks/46308-gpu0-bulk-canonical-binding-20261115-v1.json',B/'development/bulk-resource-adapter-46308-20261115-v1/per_gpu_lease.py',B/'development/bulk-resource-adapter-46308-20261115-v1/gpu_observation.py',B/'workers/new-critic-cohort-46308-20261115-v1/raw_third_view.py']:
  assert not p.is_symlink()
  if p==Path(C['model_path'])and C['model_sha256']is None:continue
  files[str(p)]=sha(p)
 for p in (SOURCE.parent/'reach_stow_choice').glob('*.py'):files[str(p)]=sha(p)
 return files
action=sys.argv[1]

if action=='reserve-asset':
 resources=fresh();assert KEY not in json.loads(H.read_bytes())and not S.exists()and not Path(C['model_path']).parent.exists();files=collect_files();files.pop(str(W/'protocol.json'));files.pop(str(Path(C['model_path'])),None);files[str(M/'asset-compile-protocol.json')]=sha(M/'asset-compile-protocol.json');record(M/'asset-compile-authority.json',dict(owner=OWNER,scope_id=C['scope_id'],source_commit=C['source_commit'],compile_max=1,zero_max=1,main_max=1,task_steps_allowed_in_compile=0,no_retry=True,compile_wall_cap_s=C['compile_wall_cap_s']));files[str(M/'asset-compile-authority.json')]=sha(M/'asset-compile-authority.json');record(M/'asset-compile-freeze.json',dict(at=now(),scope_id=C['scope_id'],files=files,phase='STATIC_ASSET_ONLY_NO_RUNTIME',model_output=str(C['model_path'])))
 def change(h):
  assert KEY not in h;h[KEY]=dict(active=True,owner=OWNER,scope_id=C['scope_id'],phase='STATIC_ASSET_RESERVED',source_commit=C['source_commit'],plan_sha256=C['plan_sha256'],asset_compile_freeze_sha256=sha(M/'asset-compile-freeze.json'),asset_compile_dispatch_count=0,zero_dispatch_count=0,main_dispatch_count=0,automatic_retry=False,resources=resources)
 v=cas(change);record(M/'reserve-asset-CAS.json',{k:x for k,x in v.items()if k!='after_base64'});print(json.dumps(v))
elif action=='compile-asset':
 fresh();assert not(M/'asset-compile-launch-once.json').exists()and not Path(C['model_path']).parent.exists()
 def change(h):
  q=h[KEY];assert q['active']and q['phase']=='STATIC_ASSET_RESERVED'and q['asset_compile_dispatch_count']==0;q.update(asset_compile_dispatch_count=1,phase='STATIC_ASSET_DISPATCHED')
 cas(change);record(M/'asset-compile-launch-once.json',dict(at=now(),no_retry=True))
 with(M/'asset-compile.stdout').open('xb')as out,(M/'asset-compile.stderr').open('xb')as err:
  child=subprocess.Popen(['taskset','-c','36,37',PY,'-I','-B',str(W/'compile_asset.py')],env=env(),stdout=out,stderr=err);record(M/'asset-compile-child.json',dict(PID=child.pid,at=now()))
  try:rc=child.wait(timeout=C['compile_wall_cap_s']+30)
  except subprocess.TimeoutExpired:
   child.terminate()
   try:rc=child.wait(timeout=10)
   except subprocess.TimeoutExpired:child.kill();rc=child.wait(timeout=10)
 record(M/'asset-compile-exit.json',dict(exit_code=rc,at=now()));result=json.loads((M/'asset-compile-result.json').read_bytes())if(M/'asset-compile-result.json').exists()else None
 if result and result['passed']:
  assert rc==0 and result['asset']['model_path']==C['model_path']and result['asset']['scene_sha256']==C['scene_sha256'];C['model_sha256']=result['asset']['model_sha256'];p=W/'protocol.json';old=p.read_bytes();tmp=p.with_suffix('.compiled.tmp');assert not tmp.exists()
  with tmp.open('xb')as f:f.write((json.dumps(C,ensure_ascii=False,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
  assert p.read_bytes()==old;os.chmod(tmp,p.stat().st_mode&0o7777);os.replace(tmp,p)
 def finish(h):
  q=h[KEY];assert q['active']and q['phase']=='STATIC_ASSET_DISPATCHED';q.update(phase='STATIC_ASSET_COMPILED'if result and result['passed']else'CLOSED_STATIC_ASSET_FAILED_NO_ZERO_MAIN',active=bool(result and result['passed']),asset_compile_exit=rc,asset_compile_result_sha256=sha(M/'asset-compile-result.json')if result else None)
 v=cas(finish);print(json.dumps(dict(result=result,**v)))
elif action=='inventory':
 resources=fresh();q=json.loads(H.read_bytes())[KEY];assert q['active']and q['phase']=='STATIC_ASSET_COMPILED'and q['asset_compile_dispatch_count']==1 and not S.exists();assert C['model_sha256']==sha(C['model_path']);files=collect_files();files[str(M/'asset-compile-result.json')]=sha(M/'asset-compile-result.json');files[str(M/'asset-compile-freeze.json')]=sha(M/'asset-compile-freeze.json')
 authority=dict(schema='Data-E-own-zero1-then-main1-only-v1',owner=OWNER,scope_id=C['scope_id'],plan_sha256=C['plan_sha256'],source_commit=C['source_commit'],own_zero_max=1,main_max=1,automatic_retry=False,protocol_sha256=sha(W/'protocol.json'));record(A,authority);files[str(A)]=sha(A);record(M/'program-freeze.json',dict(schema='Data-E-complete-program-freeze-v1',at=now(),scope_id=C['scope_id'],authorization_sha256=sha(A),files=files));record(M/'inventory-resources.json',resources);print(json.dumps(dict(program_sha256=sha(M/'program-freeze.json'),authority_sha256=sha(A),members=len(files),resources=resources)))
elif action=='freeze':
 resources=fresh();p=sha(M/'program-freeze.json');freeze=json.loads((M/'program-freeze.json').read_bytes());assert all(sha(n)==s for n,s in freeze['files'].items())
 def change(h):
  assert h[KEY]['phase']=='STATIC_ASSET_COMPILED'and h[KEY]['asset_compile_dispatch_count']==1 and not S.exists();prior=h[KEY];h[KEY]=dict(asset_compile_dispatch_count=1,asset_compile_result_sha256=sha(M/'asset-compile-result.json'),active=True,owner=OWNER,scope_id=C['scope_id'],phase='FROZEN_E_PREPARE',authorization_sha256=sha(A),whole_program_freeze_sha256=p,zero_dispatch_count=0,main_dispatch_count=0,zero_passed=False,camera_sha256=None,source_commit=C['source_commit'],plan_sha256=C['plan_sha256'],automatic_retry=False,resources=resources)
 v=cas(change);record(M/'freeze-CAS.json',{k:x for k,x in v.items()if k!='after_base64'});print(json.dumps(v))
elif action=='prepare':
 p=sha(M/'program-freeze.json');r=subprocess.run(['taskset','-c','36,37',PY,'-I','-B',str(W/'worker.py'),'--phase','prepare','--program-sha256',p],env=env(),capture_output=True,text=True,timeout=90);record(M/'prepare-result.json',dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr;print(json.dumps(dict(prepared=True,no_native=True)))
elif action in('dispatch-zero','dispatch-main'):
 resources=fresh();phase=action.split('-')[1];assert json.loads((M/'prepare-result.json').read_bytes())['exit_code']==0
 def change(h):
  q=h[KEY];assert q['active']and not(S/phase).exists()
  if phase=='zero':assert q['zero_dispatch_count']==q['main_dispatch_count']==0;q['zero_dispatch_count']=1
  else:assert sum(v.get('main_dispatch_count',0)for k,v in h.items()if k.startswith('active_E20_prearrival40_v')and isinstance(v,dict))==0;assert q['zero_dispatch_count']==1 and q['zero_passed']and q['camera_sha256']and q['main_dispatch_count']==0;q['main_dispatch_count']=1
  q.update(phase='CAS_DISPATCHED_E_'+phase.upper(),dispatch_at=now(),resources=resources)
 v=cas(change);record(M/(action+'-CAS.json'),{k:x for k,x in v.items()if k!='after_base64'});print(json.dumps(v))
elif action in('zero','main'):
 phase=action;q=json.loads(H.read_bytes())[KEY];assert q['active']and not(S/phase).exists();assert q['zero_dispatch_count']==1 and(phase=='zero'and q['main_dispatch_count']==0 or phase=='main'and q['main_dispatch_count']==1 and q['zero_passed']);fresh();record(M/(phase+'-launch-once.json'),dict(at=now(),no_retry=True));cap=C['zero_wall_cap_s']if phase=='zero'else C['main_wall_cap_s']
 with(M/(phase+'.stdout')).open('xb')as out,(M/(phase+'.stderr')).open('xb')as err:
  child=subprocess.Popen(['taskset','-c','36,37',PY,'-I','-B',str(W/'worker.py'),'--phase',phase,'--program-sha256',q['whole_program_freeze_sha256']],env=env(),stdout=out,stderr=err);record(M/(phase+'-child.json'),dict(PID=child.pid,at=now()))
  try:rc=child.wait(timeout=cap+30)
  except subprocess.TimeoutExpired:
   child.terminate()
   try:rc=child.wait(timeout=10)
   except subprocess.TimeoutExpired:child.kill();rc=child.wait(timeout=10)
 record(M/(phase+'-exit.json'),dict(exit_code=rc,at=now()));result=json.loads((S/phase/'result.json').read_bytes())if(S/phase/'result.json').exists()else None
 print(json.dumps(dict(result=result,zero_frames={p.name:base64.b64encode(p.read_bytes()).decode()for p in(S/phase).glob('camera-*.png')}if phase=='zero'else{})))
elif action=='qualify-zero':
 choice=int(sys.argv[2]);v=json.loads((S/'zero/result.json').read_bytes());assert v['passed']and v['phase']=='zero'and v['actual_task_steps']==0 and choice in range(len(C['cameras']));spec=C['cameras'][choice];digest=hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':')).encode()).hexdigest();assert(M/'zero-exit.json').exists()
 def change(h):
  q=h[KEY];assert q['active']and q['zero_dispatch_count']==1 and q['main_dispatch_count']==0 and not q['zero_passed'];q.update(zero_passed=True,zero_result_sha256=sha(S/'zero/result.json'),chosen_camera=spec,camera_spec=spec,camera_sha256=digest,phase='ZERO_PASSED_CAMERA_FROZEN_BEFORE_MAIN',camera_selection_is_task0_framing_not_outcome=True)
 v=cas(change);record(M/'zero-qualification-CAS.json',{k:x for k,x in v.items()if k!='after_base64'});print(json.dumps(v))
elif action=='encode':
 p=S/'main/direct-third-view';r=subprocess.run(['taskset','-c','36,37',PY,'-I','-B',str(W/'encode_video.py'),str(p),C['ffmpeg_path'],C['ffmpeg_sha256']],env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2'),capture_output=True,text=True,timeout=300);record(M/'encode-result.json',dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));print(json.dumps(dict(encoded=r.returncode==0,stdout=r.stdout,stderr=r.stderr)))
elif action=='close':
 resources=fresh();h=json.loads(H.read_bytes());q=h[KEY];result=json.loads((S/('main'if q['main_dispatch_count']else'zero')/'result.json').read_bytes());assert not Path('/proc/'+str(result['PID'])).exists()
 def change(h):
  q=h[KEY];assert q['active'];q.update(active=False,phase='CLOSED_E_MAIN'if q['main_dispatch_count']else'CLOSED_TECHNICAL_ZERO_NO_MAIN',closed_at=now(),result_sha256=sha(S/('main'if q['main_dispatch_count']else'zero')/'result.json'),native_task_success=result['full_task_success'],usage_known=result['usage_known'],resource_snapshot=resources)
 v=cas(change);record(M/'close-CAS.json',{k:x for k,x in v.items()if k!='after_base64'});print(json.dumps(dict(result=result,**v)))
else:raise ValueError('Explicit new E lifecycle only')
