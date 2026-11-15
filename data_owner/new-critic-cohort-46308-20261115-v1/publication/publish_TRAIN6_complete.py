from pathlib import Path
import json,hashlib,base64,subprocess,shlex,sys,os
M=Path(__file__).resolve().parent;B=M.parents[1];sys.path.insert(0,str(M));from mirror_H import mirror
D=B/'consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-TRAIN6-COMPLETE-20261115-v1';p=json.loads((M/'TRAIN6-complete-original-release-proof.json').read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();x=dict(owner=os.environ['CODEX_THREAD_ID'],expected=sha(before),children=p['child_releases'],release_sha256=p['release_sha256'],files={str(q.relative_to(D)):base64.b64encode(q.read_bytes()).decode()for q in D.rglob('*')if q.is_file()})
code=r'''from pathlib import Path
import sys,json,base64,hashlib,fcntl,os,stat,tempfile,subprocess,datetime
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';M=B/'manifests/new-critic-cohort-46308-20261115-v1';H=B/'registry/handoff_current_status_20261115.json';x=json.load(sys.stdin);sha=lambda b:hashlib.sha256(b).hexdigest()
for c in x['children']:
 p=Path(c['remote_release']);assert p.is_relative_to(B/'consumer-deliveries')and sha(p.read_bytes())==c['release_sha256'];v=json.loads(p.read_bytes());assert v['split']=='TRAIN'and v['ordinal']==c['ordinal'];assert all(sha((p.parent/k).read_bytes())==s for k,s in v['files'].items())
D=B/'consumer-deliveries/AINAV-DATA-NEW-CRITIC-46308-TRAIN6-COMPLETE-20261115-v1';D.mkdir(exist_ok=False)
for rel,v in x['files'].items():
 p=Path(rel);assert not p.is_absolute()and '..'not in p.parts;p=D/p;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(v))
assert sha((D/'release.json').read_bytes())==x['release_sha256'];active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit()or int(p.name)==os.getpid():continue
 try:args=[v.decode(errors='replace')for v in(p/'cmdline').read_bytes().split(bytes([0]))if v]
 except(FileNotFoundError,PermissionError,ProcessLookupError):continue
 if any(a.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for a in args):active.append(int(p.name))
assert not active;locks=[]
for gpu,inodes in [(0,(3428729629,3428729630)),(1,(3428459217,3428459218))]:
 for kind,inode in zip(('physics','sdk'),inodes):
  p=R/f'resource-locks/native-observer-{kind}-gpu{gpu}.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW);st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,inode)
  try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
  finally:os.close(fd)
  locks.append(dict(GPU_index=gpu,kind=kind,device=st.st_dev,inode=st.st_ino,available_not_held=True))
owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True,timeout=20);d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert sha(old)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(old);saved=json.loads(old);assert h['executing_thread_id']==x['owner'];co=h['new_critic_cohort_v1'];q=h['active_new_critic_cohort_scope'];assert not q['active']and q['zero_dispatch_program_sha256']is None and q['main_dispatch_program_sha256']is None;assert not co['TRAIN_gate_passed']and co['training_fit_manifest_sha256']is None and not co['global_stop'];assert co['status']=='TRAIN_SIX_CLOSED_AWAIT_GATE_NO_CAL_VAL_DISPATCH'
  for c in x['children']:
   br=co['branches'][c['condition_id']];assert br['zero_dispatch_count']==br['main_dispatch_count']==1 and br['status'].startswith('CLOSED_ACTUAL_MAIN_');br['actual_public_delivery']=dict(release=c['remote_release'],release_sha256=c['release_sha256'],data_role='NEW_PREREGISTERED_TRAIN',not_a_fit_activation_permit=True,source_clocks_and_bytes_preserved=True)
  assert all(co['branches'][c]['zero_dispatch_count']==co['branches'][c]['main_dispatch_count']==0 for c in co['order'][6:])
  co.update(status='TRAIN6_CLOSED_ORIGINALS_PUBLISHED_AWAIT_REACH_SOURCE_LABEL_FEATURE_GATE',TRAIN_native_collection_complete=True,TRAIN_original_complete_release=dict(release=str(D/'release.json'),release_sha256=x['release_sha256']),TRAIN_actual_outcome_counts=dict(main=6,zero=6,requested_chain_PASS=4,native_error=2,resource_censor=0),CAL_VAL_dispatch_block_preserved=True)
  assert h['active_new_critic_cohort_scope']==saved['active_new_critic_cohort_scope'];assert all(h[k]==v for k,v in saved.items()if k not in('new_critic_cohort_v1','updated_at'));h['updated_at']=datetime.datetime.now().astimezone().isoformat();raw=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-TRAIN6-complete-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as o:o.write(raw);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(st.st_mode));os.fsync(o.fileno())
   assert H.read_bytes()==old;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(at=datetime.datetime.now().astimezone().isoformat(),before_H_sha256=sha(old),after_H_sha256=sha(raw),release=str(D/'release.json'),release_sha256=x['release_sha256'],all_six_counts_and_legacy_scopes_preserved=True,TRAIN_gate_NOT_activated=True,fit_NOT_started=True,CAL_VAL_counts0_preserved=True,active_scope_unchanged_inactive=True,no_owned_native_processes=True,canonical_locks=locks,owned_allocated_bytes=owned,owned_cap_bytes=42949672960,provider_quota_unknown=True,GPU_readonly=gpu,new_physical_dispatches=0)
with(M/'TRAIN6-complete-publication-CAS.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(raw).decode())))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=150)
for suf,t in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:(M/('TRAIN6-complete-publication.'+suf)).write_text(t)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['proof']['after_H_sha256'];mirror(raw,sha(before));(M/'TRAIN6-complete-publication-CAS.json').write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps(v['proof'],indent=2))
