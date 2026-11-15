"""New fixed24 recipes/programs, rolling ONE GPU1 admission; never old authority edits."""
from pathlib import Path
import os,sys,json,base64,hashlib,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;W=B/'workers'/M.name;sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror
sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();owner=os.environ['CODEX_THREAD_ID'];assert owner==os.environ['CODEX_SESSION_ID']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';x=dict(owner=owner,expected=sha(before),files={str(p.relative_to(W)):base64.b64encode(p.read_bytes()).decode()for p in W.rglob('*')if p.is_file()and '__pycache__'not in p.parts})
code=r'''
from pathlib import Path
import os,sys,json,base64,hashlib,fcntl,stat,tempfile,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='bulk24-collector-46308-20261115-v1';W=B/'workers'/N;M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();digest=lambda b:hashlib.sha256(b).hexdigest();now=lambda:datetime.datetime.now().astimezone().isoformat();assert 'bulk24_collector_v1'not in json.loads(H.read_bytes());W.mkdir(parents=True,exist_ok=True);M.mkdir(parents=True,exist_ok=True)
for rel,v in x['files'].items():
 p=Path(rel);assert not p.is_absolute()and '..'not in p.parts;p=W/p;p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(v)
 if p.exists():assert not p.is_symlink()and p.read_bytes()==raw
 else:
  with p.open('xb')as f:f.write(raw)
C=json.loads((W/'protocol.json').read_bytes());assert C['training_allowed']is False and C['current_critic_refit_allowed']is False and C['automatic_retry']is False and len(C['order'])==24 and list(C['arms'])==C['order'];D=B/'development/bulk24-preconstruction-46308-20261115-v1';assert sha(D/'SOURCE_CUSTODY.json')==C['source_custody_sha256']=='ba932cda090a84f414c563399e521897ad30e49be961c351d9facdc52a087a1a';custody=json.loads((D/'SOURCE_CUSTODY.json').read_bytes())
for rel,pin in custody['files_sha256'].items():assert sha(D/'inputs'/rel)==pin
assert sha(D/'inputs/BULK24_COLLECTION_PROTOCOL.json')==C['Reach_protocol_sha256']=='0f9e0e03a4cdf8263b1c69f69db9697968040023f42d4c1f383a320631d9e57e';report=json.loads((B/'manifests/bulk24-preconstruction-46308-20261115-v1/actual-pure-source-binding.json').read_bytes());assert report['all24_exact_original_protocol_and_requests_verified']and report['remote_probe_H_unchanged'];assert len(report['rows'])==24 and all(r['scope_id']is None and r['physical_program_sha256']is None for r in report['rows'])
for c in C['order']:assert C['arms'][c]['zero_limit']==C['arms'][c]['main_limit']==1 and not(R/'runtime/workers'/C['scopes'][c]).exists()
sys.path.insert(0,str(W));from resource_snapshot import fresh
resources=fresh();SDK=Path('/mnt/yuanyue/ainav-execution-reference-20261112-v1/sdk-bundle');assert sha(SDK/'MANIFEST.json')=='b7669886794092acb6ed17a2f6428b1bf4a9e218de601c860207d6c367ed09be';files={}
for line in(SDK/'SHA256SUMS').read_text().splitlines():
 pin,rel=line.split(None,1);rel=rel.strip().removeprefix('*');p=SDK/rel;assert not Path(rel).is_absolute()and '..'not in Path(rel).parts and not p.is_symlink()and sha(p)==pin;files[str(p)]=pin
for name in('MANIFEST.json','SHA256SUMS'):files[str(SDK/name)]=sha(SDK/name)
for folder in (W,D):
 for p in folder.rglob('*'):
  if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc':assert not p.is_symlink();files[str(p)]=sha(p)
for p in [B/'development/bulk-resource-adapter-46308-20261115-v1/per_gpu_lease.py',B/'development/bulk-resource-adapter-46308-20261115-v1/gpu_observation.py',R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1',R/'resource-locks/46308-canonical-binding-20261115-v1.json']:files[str(p)]=sha(p)
AUTH=B/'registry/BULK24_COLLECTOR_46308_AUTHORITY_20261115_v1.json';a=dict(schema='Data-fixed24-rolling-GPU1-original-chain-collection-authority-v1',at=now(),owner=x['owner'],stage='NEW_PREREGISTERED_HIGH_LEVEL_SUCCESSOR_CRITIC_COLLECTION',candidate_order=C['order'],branches={c:dict(scope_id=C['scopes'][c],allowed_own_zero_invocations=1,allowed_main_invocations=1)for c in C['order']},GPU_UUID=C['GPU_UUID'],physical_GPU_index=1,CPU_affinity=[38,39],protocol_sha256=sha(W/'protocol.json'),source_custody_sha256=C['source_custody_sha256'],training_allowed=False,current_critic_refit_allowed=False,automatic_retry=False,all_old_scopes_remain_closed=True,existing_GPU0_OBS_not_modified=True,full24_capacity_not_reserved=True,per_phase_fresh_rolling_storage_required=True)
with AUTH.open('x')as f:json.dump(a,f,indent=2);f.write('\n')
files[str(AUTH)]=sha(AUTH);programs={}
for c in C['order']:
 P=M/c;P.mkdir();F=P/'program-freeze.json';v=dict(schema='Data-bulk24-one-original-zero-main-program-freeze-v1',at=now(),arm=c,candidate_id=c,method=C['arms'][c]['method'],scope_id=C['scopes'][c],authorization_sha256=sha(AUTH),files=files,physical_safety_or_actor_weights_modified=False,same_zero_and_main_program=True,scope_caps=C['scope_caps'],role='NEW_COLLECTION_NOT_TRAIN_JOB_OR_CURRENT_CRITIC_REFIT',CPU_affinity=[38,39])
 with F.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
 programs[c]=sha(F)
c=C['order'][0];d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert digest(old)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(old);saved=json.loads(old);assert h['executing_thread_id']==x['owner']and'bulk24_collector_v1'not in h
  h['bulk24_collector_v1']=dict(owner=x['owner'],protocol_sha256=sha(W/'protocol.json'),authorization_sha256=sha(AUTH),source_custody_sha256=C['source_custody_sha256'],order=C['order'],status='RECIPES_FROZEN_FIRST_GPU1_SLOT_PREPARE_NO_DISPATCH',global_stop=False,only_one_active_GPU1_slot=True,all24_capacity_not_reserved=True,training_allowed=False,current_critic_refit_allowed=False,branches={key:dict(arm=key,candidate_id=key,scope_id=C['scopes'][key],whole_program_freeze_sha256=programs[key],zero_dispatch_count=0,main_dispatch_count=0,status='REGISTERED_PENDING_ROLLING_ADMISSION')for key in C['order']})
  h['active_bulk24_collector_scope']=dict(active=True,owner=x['owner'],arm=c,candidate_id=c,scope_id=C['scopes'][c],phase='FROZEN_GPU1_FIRST_PREPARE_NO_DISPATCH',authorization_sha256=sha(AUTH),whole_program_freeze_sha256=programs[c],zero_dispatch_count=0,main_dispatch_count=0,zero_dispatch_program_sha256=None,main_dispatch_program_sha256=None,automatic_retry=False,GPU_physical_index=1,resource_snapshot=resources)
  assert all(h[k]==v for k,v in saved.items());h['updated_at']=now();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-bulk24-freeze-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
   assert H.read_bytes()==old;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(at=now(),before_H_sha256=digest(old),after_H_sha256=digest(after),programs=programs,authorization_sha256=sha(AUTH),frozen_members=len(files),resources=resources,all_old_and_OBS_H_fields_preserved=True,all_new_zero_main_counts0=True,not24_root_capacity_reservation=True)
with(M/'freeze-CAS-receipt.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(after).decode())))
'''
assert sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())=='b2fb786ec002b1e88ed4fc56a0bbfbac21d62cd788dacdda7d9fceb1a774c5a9'
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=300)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('freeze.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['proof']['after_H_sha256'];mirror(raw,sha(before));(M/'freeze-CAS-receipt.json').write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps({k:z for k,z in v['proof'].items()if k!='programs'},indent=2))
