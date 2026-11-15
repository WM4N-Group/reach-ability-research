from pathlib import Path
import json,base64,hashlib,subprocess,shlex,os,sys
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;W=B/'workers'/M.name;sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror
x=dict(owner=os.environ['CODEX_THREAD_ID'],expected=sha(before),files={str(p.relative_to(W)):base64.b64encode(p.read_bytes()).decode()for p in W.rglob('*')if p.is_file()and '__pycache__'not in p.parts})
code=r'''from pathlib import Path
import json,base64,sys,os,fcntl,stat,tempfile,hashlib,datetime,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='T-COMPLEX-01-v2-camera-components-46308-20261115-v1';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=lambda b:hashlib.sha256(b).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat();assert 'active_T_COMPLEX_v2_camera_component_scope'not in json.loads(H.read_bytes());assert not(B/'registry/T_COMPLEX_V2_CAMERA_COMPONENT_AUTHORITY_20261115_v1.json').exists();W.mkdir(parents=True,exist_ok=True);M.mkdir(parents=True,exist_ok=True)
for rel,v in x['files'].items():
 p=Path(rel);assert not p.is_absolute()and '..'not in p.parts;p=W/p;p.parent.mkdir(parents=True,exist_ok=True)
 raw=base64.b64decode(v)
 if p.exists():assert not p.is_symlink()and p.read_bytes()==raw,'Unfrozen staging retry can only verify identical already-staged source'
 else:
  with p.open('xb')as f:f.write(raw)
config=json.loads((W/'protocol.json').read_bytes());scope=config['scope_id'];old_scope=json.loads(H.read_bytes())['active_T_COMPLEX_component_zero_scope'];assert not old_scope['active']and old_scope['component_zero_dispatch_count']==1 and old_scope['actual_result_sha256']==config['prior_closed_failure_result_sha256'];assert config['allowed_task_main_invocations']==0 and config['allowed_component_zero_invocations']==1;assert not(R/'runtime/workers'/scope).exists();owner=json.loads((W/'inputs/SOURCE_OWNER_NATIVE_COMPONENTS.json').read_bytes());assert owner['code_only_cloud_commit']==config['new_source_owner_commit']
for rel,pin in owner['source_files_sha256'].items():p=W/'inputs/scene'/Path(rel);assert sha(p)==pin
snapshot=json.loads((W/'inputs/SOURCE_SNAPSHOT_SHA256.json').read_bytes())
for rel,pin in snapshot.items():assert sha(W/'inputs/scene'/rel)==pin and sha(Path(owner['remote_root'])/'development/complex_dual_route_v1'/rel)==pin
assert sha(W/'inputs/main-plan.md')=='b2fb786ec002b1e88ed4fc56a0bbfbac21d62cd788dacdda7d9fceb1a774c5a9';assert sha(W/'inputs/TASK_CN.md')=='a3ade42a679dfa86688cb5ce1e0de94899f0f2c3dba0fcaefbfe23db83ae4daa'
source=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav/common-source';assert sha(source/'build_transfer_scene_native.py')=='706c9c7c254e7611526af17e7107ad8a4ba788e6a4e9631d400a7476a1a43abd'and sha(source/'ainav/native/registered_runtime.py')=='ad04b58361e0256e4dc1b95441a38b4b37befe8f31e7d9a6ec9efdae47e202d9'
SDK=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle');sdk=json.loads((SDK/'MANIFEST.json').read_bytes());files={}
for line in(SDK/'SHA256SUMS').read_text().splitlines():
 pin,rel=line.split(None,1);rel=rel.strip().removeprefix('*');p=SDK/rel;assert not Path(rel).is_absolute()and '..'not in Path(rel).parts and p.resolve().is_relative_to(SDK)and not p.is_symlink()and sha(p)==pin;files[str(p)]=pin
for n in('MANIFEST.json','SHA256SUMS'):files[str(SDK/n)]=sha(SDK/n)
for folder in (W,source):
 for p in folder.rglob('*'):
  if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc':assert not p.is_symlink();files[str(p)]=sha(p)
for p in [B/'development/bulk-resource-adapter-46308-20261115-v1/per_gpu_lease.py',B/'development/bulk-resource-adapter-46308-20261115-v1/gpu_observation.py',B/'workers/new-critic-cohort-46308-20261115-v1/raw_third_view.py',R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1',R/'resource-locks/46308-gpu0-bulk-canonical-binding-20261115-v1.json']:
 assert not p.is_symlink();files[str(p)]=sha(p)
assert files[str(R/'resource-locks/46308-gpu0-bulk-canonical-binding-20261115-v1.json')]=='50d6365e40fa07402d6765809b841cd29cc7b0c2a93d00542aecc92879df1bcd'
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit()or int(p.name)==os.getpid():continue
 try:args=[v.decode(errors='replace')for v in(p/'cmdline').read_bytes().split(bytes([0]))if v]
 except(FileNotFoundError,PermissionError,ProcessLookupError):continue
 if any(v.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for v in args):active.append(int(p.name))
assert not active
for kind,inode in [('physics',3428729629),('sdk',3428729630)]:
 p=R/f'resource-locks/native-observer-{kind}-gpu0.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW);s=os.fstat(fd);assert(s.st_dev,s.st_ino)==(51,inode)
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
 finally:os.close(fd)
owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);reserve_old=6*1610612736;assert owned+reserve_old+1073741824<42949672960;gpu=subprocess.check_output(['nvidia-smi','--id=GPU-297c1146-bcec-a8ee-8437-d9603392a2e1','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=20).strip().split(',');assert gpu[0].strip()=='0'and int(gpu[2].strip())>=4096
AUTH=B/'registry/T_COMPLEX_V2_CAMERA_COMPONENT_AUTHORITY_20261115_v1.json';assert not AUTH.exists();a=dict(schema='Data-T-COMPLEX-native-component-zero-one-shot-authority-v1',at=now(),owner=x['owner'],scope_id=scope,allowed_component_zero_invocations=1,allowed_task_main_invocations=0,automatic_retry=False,main_plan_sha256=sha(W/'inputs/main-plan.md'),task_sha256=sha(W/'inputs/TASK_CN.md'),protocol_sha256=sha(W/'protocol.json'),source_owner_record_sha256=sha(W/'inputs/SOURCE_OWNER_NATIVE_COMPONENTS.json'),GPU_UUID=config['GPU_UUID'],GPU_index=0,role=config['purpose'],not_main_A_or_B_or_training=True,does_not_qualify_future_different_program_zero=True,limits={k:config[k]for k in('task_world_steps_allowed','sim_aux_cap_s','wall_cap_s','output_cap_bytes','own_GPU_cap_bytes','own_RSS_cap_bytes','CPU_threads')})
with AUTH.open('x')as f:json.dump(a,f,indent=2);f.write('\n')
files[str(AUTH)]=sha(AUTH);freeze=dict(schema='Data-independent-T-COMPLEX-native-component-program-freeze-v1',at=now(),scope_id=scope,authorization_sha256=sha(AUTH),role=config['purpose'],task_main_invocations=0,component_zero_invocations=1,physical_guards_or_Actor_modified=False,files=files)
with(M/'program-freeze.json').open('x')as f:json.dump(freeze,f,indent=2);f.write('\n')
program=sha(M/'program-freeze.json');d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert digest(old)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(old);saved=json.loads(old);assert h['executing_thread_id']==x['owner']and not h['active_new_critic_cohort_scope']['active']and h['new_critic_cohort_v1']['TRAIN_native_collection_complete'];assert 'active_T_COMPLEX_v2_camera_component_scope'not in h
  h['active_T_COMPLEX_v2_camera_component_scope']=dict(active=True,owner=x['owner'],scope_id=scope,phase='FROZEN_COMPONENT_ZERO_PREPARE_NO_DISPATCH',authorization_sha256=sha(AUTH),whole_program_freeze_sha256=program,component_zero_dispatch_count=0,component_zero_dispatch_program_sha256=None,task_main_dispatch_count=0,automatic_retry=False,source_role=config['purpose'],task_AB_success_or_video_claimed=False)
  assert all(h[k]==v for k,v in saved.items());h['updated_at']=now();raw=(json.dumps(h,indent=2,ensure_ascii=False)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-complex-component-freeze-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as out:out.write(raw);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
   assert H.read_bytes()==old;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(at=now(),before_H_sha256=digest(old),after_H_sha256=digest(raw),program_sha256=program,authorization_sha256=sha(AUTH),frozen_member_count=len(files),component_phase_dispatches=0,task_AB_main_dispatches=0,all_existing_TRAIN_and_heldout_counts_and_gate_flags_preserved=True,owned_allocated_bytes=owned,old_heldout_reserve_bytes=reserve_old,new_component_reserve_bytes=1073741824,provider_quota_unknown=True,GPU0_free_MiB=int(gpu[2].strip()),no_native_by_this_freeze=True)
with(M/'freeze-CAS-receipt.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(raw).decode())))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=240)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('freeze.'+suf)).write_text(t)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['proof']['after_H_sha256'];mirror(raw,sha(before));(M/'freeze-CAS-receipt.json').write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps(v['proof'],indent=2))
