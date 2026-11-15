from pathlib import Path
import os,sys,json,base64,hashlib,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;W=B/'workers'/M.name;sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror
sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();owner=os.environ['CODEX_THREAD_ID'];assert owner==os.environ['CODEX_SESSION_ID']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';x=dict(owner=owner,expected=sha(before),files={str(p.relative_to(W)):base64.b64encode(p.read_bytes()).decode()for p in W.rglob('*')if p.is_file()and '__pycache__'not in p.parts})
code=r'''
from pathlib import Path
import os,sys,json,base64,hashlib,fcntl,stat,tempfile,datetime,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='T-COMPLEX-observability-study-46308-20261115-v1';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=lambda b:hashlib.sha256(b).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat();assert 'T_COMPLEX_observation_study_v1'not in json.loads(H.read_bytes());W.mkdir(parents=True,exist_ok=True);M.mkdir(parents=True,exist_ok=True)
for rel,v in x['files'].items():
 p=Path(rel);assert not p.is_absolute()and '..'not in p.parts;p=W/p;p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(v)
 if p.exists():assert not p.is_symlink()and p.read_bytes()==raw
 else:
  with p.open('xb')as f:f.write(raw)
C=json.loads((W/'protocol.json').read_bytes());owner=json.loads((W/'inputs/SOURCE_OWNER_RECORD.json').read_bytes());assert C['source_owner_commit']==owner['cloud_commit']and C['training_allowed']is False and C['automatic_retry']is False and list(C['arms'])==['OBS']and C['purpose']=='OBSERVABILITY_QUALIFICATION_ONLY'
for name,pin in json.loads((W/'inputs/SOURCE_FILES_SHA256.json').read_bytes()).items():assert sha(W/'inputs/scene'/name)==pin and sha(Path(owner['remote_code_root'])/'development/complex_dual_route_v1'/name)==pin
assert sha(W/'inputs/main-plan.md')=='b2fb786ec002b1e88ed4fc56a0bbfbac21d62cd788dacdda7d9fceb1a774c5a9';h=json.loads(H.read_bytes());assert h['executing_thread_id']==x['owner']and not h['active_T_COMPLEX_full_program_scope']['active']and not h['active_T_COMPLEX_component_zero_scope']['active']and not h['active_new_critic_cohort_scope']['active']and not h['active_T_COMPLEX_v2_camera_component_scope']['active'];assert h['active_T_COMPLEX_v2_camera_component_scope']['component_zero_dispatch_count']==1
for a,row in C['arms'].items():assert row['zero_limit']==row['main_limit']==1 and not(R/'runtime/workers'/row['scope_id']).exists()
active=[]
for p in Path('/proc').glob('[0-9]*'):
 try:args=[v.decode(errors='replace')for v in(p/'cmdline').read_bytes().split(b'\0')if v]
 except OSError:continue
 if any(v.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for v in args):active.append(int(p.name))
assert not active
for kind,ino in[('physics',3428729629),('sdk',3428729630)]:
 p=R/f'resource-locks/native-observer-{kind}-gpu0.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,ino)and(p.stat().st_dev,p.stat().st_ino)==(51,ino);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
 finally:os.close(fd)
owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);assert owned+C['remaining_CAL_VAL_reserve_bytes']+C['pair_root_storage_reserve_bytes']<40*1024**3;gpu=subprocess.check_output(['nvidia-smi','--id='+C['GPU_UUID'],'--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=20).strip().split(',');assert gpu[0].strip()=='0'and gpu[1].strip()==C['GPU_UUID']and int(gpu[2])>=4096
SDK=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle');assert sha(SDK/'MANIFEST.json')=='b7669886794092acb6ed17a2f6428b1bf4a9e218de601c860207d6c367ed09be';files={}
for line in(SDK/'SHA256SUMS').read_text().splitlines():
 pin,rel=line.split(None,1);rel=rel.strip().removeprefix('*');p=SDK/rel;assert not Path(rel).is_absolute()and '..'not in Path(rel).parts and not p.is_symlink()and sha(p)==pin;files[str(p)]=pin
for name in('MANIFEST.json','SHA256SUMS'):files[str(SDK/name)]=sha(SDK/name)
A=B/'workers/new-critic-cohort-46308-20261115-v1/inputs/AINav'
for folder in[W,A]:
 for p in folder.rglob('*'):
  if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc':assert not p.is_symlink();files[str(p)]=sha(p)
for p in[B/'development/bulk-resource-adapter-46308-20261115-v1/per_gpu_lease.py',B/'development/bulk-resource-adapter-46308-20261115-v1/gpu_observation.py',B/'workers/new-critic-cohort-46308-20261115-v1/raw_third_view.py',B/'workers/new-critic-cohort-46308-20261115-v1/model_identity.py',R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1',R/'resource-locks/46308-gpu0-bulk-canonical-binding-20261115-v1.json']:files[str(p)]=sha(p)
AUTH=B/'registry/T_COMPLEX_OBSERVATION_STUDY_AUTHORITY_20261115_v1.json';a=dict(schema='Data-one-shot-independent-observation-study-authority-v1',at=now(),owner=x['owner'],arms=C['arms'],GPU_UUID=C['GPU_UUID'],source_owner_commit=C['source_owner_commit'],scene_sha256=C['scene_sha256'],protocol_sha256=sha(W/'protocol.json'),training_allowed=False,automatic_retry=False,old_closed_scopes_unchanged=True,component_zero_not_transferable=True,shared_original_control_and_success_gates=True,purpose='OBSERVABILITY_QUALIFICATION_ONLY',task_success_can_be_claimed=False,AB_comparison=False,old_pair_stop_and_caps_unchanged=True,measurement_termination_not_host_complete=True,DEV_not_confirmatory_or_advantage_claim=True,main_requires_own_full_program_zero_cold_and_fresh_lease=True)
with AUTH.open('x')as f:json.dump(a,f,indent=2);f.write('\n')
files[str(AUTH)]=sha(AUTH);programs={}
for arm,row in C['arms'].items():
 D=M/arm;D.mkdir();F=D/'program-freeze.json';freeze=dict(schema='Data-T-complex-source-bound-full-DEV-program-freeze-v1',at=now(),arm=arm,method=row['method'],scope_id=row['scope_id'],authorization_sha256=sha(AUTH),files=files,same_zero_and_main_program=True,physical_rules_or_Actor_modified=False,scope_caps=C['scope_caps'])
 with F.open('x')as f:json.dump(freeze,f,indent=2);f.write('\n')
 programs[arm]=sha(F)
d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);before=f.read();st=os.fstat(f.fileno());assert digest(before)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(before);saved=json.loads(before);assert h['executing_thread_id']==x['owner']and'T_COMPLEX_observation_study_v1'not in h
  h['T_COMPLEX_observation_study_v1']=dict(owner=x['owner'],protocol_sha256=sha(W/'protocol.json'),authorization_sha256=sha(AUTH),order=['OBS'],status='OBSERVATION_ONLY_FROZEN_PREPARE_NO_PHYSICAL_DISPATCH',global_stop=False,purpose='OBSERVABILITY_QUALIFICATION_ONLY',original_task_success=False,AB_comparison=False,measurement_complete=False,branches={arm:dict(arm=arm,method=row['method'],scope_id=row['scope_id'],whole_program_freeze_sha256=programs[arm],zero_dispatch_count=0,main_dispatch_count=0,status='FROZEN_PENDING_FULL_HOST_PREPARE')for arm,row in C['arms'].items()})
  h['active_T_COMPLEX_observation_study_scope']=dict(active=True,owner=x['owner'],arm='OBS',scope_id=C['arms']['OBS']['scope_id'],phase='FROZEN_FULL_PROGRAM_PREPARE_NO_DISPATCH',authorization_sha256=sha(AUTH),whole_program_freeze_sha256=programs['OBS'],zero_dispatch_count=0,main_dispatch_count=0,zero_dispatch_program_sha256=None,main_dispatch_program_sha256=None,automatic_retry=False)
  assert all(h[k]==v for k,v in saved.items());h['updated_at']=now();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-full-T-complex-freeze-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
   assert H.read_bytes()==before;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(at=now(),before_H_sha256=digest(before),after_H_sha256=digest(after),programs=programs,authorization_sha256=sha(AUTH),frozen_members=len(files),owned_allocated_bytes=owned,remaining_CAL_VAL_reserve_bytes=C['remaining_CAL_VAL_reserve_bytes'],pair_reserve_bytes=C['pair_root_storage_reserve_bytes'],GPU0_free_MiB=int(gpu[2]),no_owned_native_processes=True,all_old_H_fields_and_counts_preserved=True,all_new_zero_main_counts0=True,source_dynamic_unknown_not_promoted=True)
with(M/'freeze-CAS-receipt.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(after).decode())))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),text=True,capture_output=True,timeout=240)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('freeze.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['proof']['after_H_sha256'];mirror(raw,sha(before));(M/'freeze-CAS-receipt.json').write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps(v['proof'],indent=2))
