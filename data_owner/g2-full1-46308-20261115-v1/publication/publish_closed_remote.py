from pathlib import Path
import json,sys,fcntl,hashlib,base64,os,stat,tempfile,datetime,subprocess
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';M=B/'manifests/g2-full1-46308-20261115-v1';H=B/'registry/handoff_current_status_20261115.json';x=json.load(sys.stdin);sha=lambda b:hashlib.sha256(b).hexdigest()
for c in x['children']:
 p=Path(c['remote_release']);assert p.is_relative_to(B/'consumer-deliveries')and sha(p.read_bytes())==c['release_sha256'];v=json.loads(p.read_bytes());assert all(sha((p.parent/k).read_bytes())==s for k,s in v['files'].items())
for row in x['actual_configs']:
 p=Path(row['remote_path']);assert p.is_relative_to(R/'runtime/workers')and sha(p.read_bytes())==row['sha256']
D=B/'consumer-deliveries/AINAV-DATA-G2-46308-REGISTERED-SCENE-SOURCE-HANDOFF-20261115-v1';D.mkdir(exist_ok=False)
for rel,v in x['files'].items():
 path=Path(rel);assert not path.is_absolute()and '..'not in path.parts;p=D/path;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(v))
assert sha((D/'release.json').read_bytes())==x['source_handoff_release_sha256'];p=Path(x['full1_release']);assert sha(p.read_bytes())==x['full1_release_sha256']
active=[]
for q in Path('/proc').iterdir():
 if not q.name.isdigit()or int(q.name)==os.getpid():continue
 try:args=[a.decode(errors='replace')for a in(q/'cmdline').read_bytes().split(bytes([0]))if a]
 except(FileNotFoundError,ProcessLookupError,PermissionError):continue
 if any(a.startswith((str(R/'runtime')+'/',str(B/'workers')+'/'))for a in args):active.append(int(q.name))
assert not active
for kind,inode in [('physics',3428459217),('sdk',3428459218)]:
 p=R/f'resource-locks/native-observer-{kind}-gpu1.lock';fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW);st=os.fstat(fd);assert(st.st_dev,st.st_ino)==(51,inode)
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(fd,fcntl.LOCK_UN)
 finally:os.close(fd)
owned=int(subprocess.check_output(['du','-sx','-B1','/mnt/yuanyue/data-team'],text=True,timeout=90).split()[0]);d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert sha(old)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(old);preserved=json.loads(old);assert h['executing_thread_id']==x['owner'];q=h['active_g2_full1_scope'];assert not q['active']and q['zero_dispatch_program_sha256']is None and q['main_dispatch_program_sha256']is None;c=h['g2_full1_cohort'];br=c['branches']['g2_full1_native_NAV_prefix_left'];assert br['zero_dispatch_count']==br['main_dispatch_count']==1 and br['status']=='CLOSED_ACTUAL_MAIN_PASS'
  br['actual_public_delivery']=dict(release=x['full1_release'],release_sha256=x['full1_release_sha256'],role='DEV_AUDIT_ONLY_NOT_FIT',raw_nine_stream_cold_passed=True,original_query_clock_and_binding_preserved=True)
  c.update(status='CLOSED_SINGLE_REGISTERED_FULL1_CHAIN_PASS_PENDING_CONSUMER_INFORMATION_NOT_FIT',complete_release=dict(release=x['full1_release'],release_sha256=x['full1_release_sha256']),no_repeat_or_retry=True)
  assert all(h[k]==v for k,v in preserved.items()if k not in('g2_full1_cohort','updated_at'));assert 'g2_registered_source_handoff_20261115'not in h
  h['g2_registered_source_handoff_20261115']=dict(release=str(D/'release.json'),release_sha256=x['source_handoff_release_sha256'],status='THREE_REGISTERED_SOURCE_SCENES_FIVE_DEV_ATTEMPTS_NOT_TRAINING_PROTOCOL',training_rows=0,training_scopes_allocated=False,physical_dispatch=False,next_owned_item='Reach prospective NEW-use finite whole-scene cohort protocol/source selection/size-and-stop rules; no budget reapproval or old DEV fit')
  h['updated_at']=datetime.datetime.now().astimezone().isoformat();raw=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-full1-closed-source-handoff-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as o:o.write(raw);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(st.st_mode));os.fsync(o.fileno())
   assert H.read_bytes()==old;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(at=datetime.datetime.now().astimezone().isoformat(),before_H_sha256=sha(old),after_H_sha256=sha(raw),all_prior_scopes_and_dispatch_counts_and_failures_preserved=True,current_inactive_scope_unchanged=True,no_owned_native_processes=True,canonical_locks_available_not_leased=True,owned_allocated_bytes=owned,provider_quota_unknown=True,new_training_scopes_or_dispatch=False,full1_release_sha256=x['full1_release_sha256'],source_handoff_release_sha256=x['source_handoff_release_sha256'])
with(M/'closed-publication-and-source-handoff-CAS.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(raw).decode())))
