from pathlib import Path
import json,sys,os,fcntl,stat,tempfile,hashlib,base64,datetime,subprocess
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';M=B/'manifests/g2-full2-46308-20261115-v1';H=B/'registry/handoff_current_status_20261115.json';x=json.load(sys.stdin);sha=lambda b:hashlib.sha256(b).hexdigest()
for child in x['children']:
 p=Path(child['remote_release']);assert p.is_relative_to(B/'consumer-deliveries')and sha(p.read_bytes())==child['release_sha256'];v=json.loads(p.read_bytes());assert all(sha((p.parent/n).read_bytes())==s for n,s in v['files'].items())
D=B/'consumer-deliveries/AINAV-DATA-G2-46308-FULL2-TWO-PREFIX-ACTUAL-20261115-v1';D.mkdir(exist_ok=False)
for rel,v in x['files'].items():
 p=Path(rel);assert not p.is_absolute()and '..'not in p.parts;p=D/p;p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(v)
 with p.open('xb')as f:f.write(raw)
assert sha((D/'release.json').read_bytes())==x['release_sha256']
for kind,inode in [('physics',3428459217),('sdk',3428459218)]:
 p=R/f'resource-locks/native-observer-{kind}-gpu1.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW);st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,inode)
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
 finally:os.close(fd)
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit()or int(p.name)==os.getpid():continue
 try:args=[a.decode(errors='replace')for a in(p/'cmdline').read_bytes().split(b'\0')if a]
 except(FileNotFoundError,ProcessLookupError,PermissionError):continue
 if any(a.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for a in args):active.append(int(p.name))
assert not active
owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert sha(old)==x['expected_H_sha256']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(old);preserved=json.loads(old);assert h['executing_thread_id']==x['owner'];q=h['active_g2_full2_scope'];assert not q['active']and q['zero_dispatch_program_sha256']is None and q['main_dispatch_program_sha256']is None;cohort=h['g2_full2_cohort'];assert all(b['zero_dispatch_count']==b['main_dispatch_count']==1 and b['status'].startswith('CLOSED_ACTUAL_MAIN_')for b in cohort['branches'].values())
  for child in x['children']:
   c='g2_full2_native_NAV_prefix_'+child['side'];cohort['branches'][c]['actual_public_delivery']=dict(release=child['remote_release'],release_sha256=child['release_sha256'],role='DEV_AUDIT_ONLY_NOT_FIT',original_query_bytes_clocks_and_binding_preserved=True,raw_nine_stream_cold_passed=True)
  cohort.update(status='CLOSED_DEV_SOURCE_GATE_ONE_CHAIN_PASS_ONE_PREDECESSOR_ERROR_NO_RETRY',actual_complete_release=dict(release=str(D/'release.json'),release_sha256=x['release_sha256']),actual_attempt_counts=dict(main=2,zero=2,whole_chain_PASS=1,predecessor_execution_error=1,first_CLIMB_PREPARE_observed=1,first_CLIMB_PREPARE_unreached=1),no_repeat_or_retry=True)
  assert h['active_g2_full2_scope']==preserved['active_g2_full2_scope'];assert all(h[k]==v for k,v in preserved.items()if k not in('g2_full2_cohort','updated_at'));h['updated_at']=datetime.datetime.now().astimezone().isoformat();raw=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-G2-pair-complete-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as o:o.write(raw);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(st.st_mode));os.fsync(o.fileno())
   assert H.read_bytes()==old;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(at=datetime.datetime.now().astimezone().isoformat(),before_H_sha256=sha(old),after_H_sha256=sha(raw),release=str(D/'release.json'),release_sha256=x['release_sha256'],all_prior_scope_counts_and_failures_and_inactive_scope_preserved=True,no_owned_native_processes=not active,canonical_locks_free_not_leased=True,owned_allocated_bytes=owned,provider_quota_unknown=True,no_new_physics_or_training=True)
with(M/'complete-G2-publication-CAS.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(raw).decode())))
