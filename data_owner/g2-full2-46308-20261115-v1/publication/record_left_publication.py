from pathlib import Path
import json,os,subprocess,shlex,hashlib,base64,sys
M=Path(__file__).resolve().parent;B=M.parents[1];sys.path.insert(0,str(M));from mirror_H import mirror
sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();proof=json.loads((M/'closed-left-release-proof.json').read_bytes())
code=r'''from pathlib import Path
import json,sys,fcntl,os,stat,tempfile,hashlib,base64,datetime
x=json.load(sys.stdin);B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');H=B/'registry/handoff_current_status_20261115.json';sha=lambda b:hashlib.sha256(b).hexdigest();p=Path(x['release']);assert p.is_relative_to(B/'consumer-deliveries')and sha(p.read_bytes())==x['release_sha256'];d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert sha(old)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(old);assert h['executing_thread_id']==x['owner'];preserved=json.loads(old);branch=h['g2_full2_cohort']['branches']['g2_full2_native_NAV_prefix_left'];assert branch['status']=='CLOSED_ACTUAL_MAIN_PASS'and branch['zero_dispatch_count']==branch['main_dispatch_count']==1
  branch['actual_public_delivery']=dict(release=str(p),release_sha256=x['release_sha256'],role='DEV_AUDIT_ONLY_NOT_FIT',original_query_bytes_clocks_and_binding_preserved=True,raw_nine_stream_cold_passed=True)
  assert h['active_g2_full2_scope']==preserved['active_g2_full2_scope']and h['g2_full2_cohort']['branches']['g2_full2_native_NAV_prefix_right']==preserved['g2_full2_cohort']['branches']['g2_full2_native_NAV_prefix_right'];h['updated_at']=datetime.datetime.now().astimezone().isoformat();raw=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-G2-left-public-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as o:o.write(raw);o.flush();os.fchmod(o.fileno(),stat.S_IMODE(st.st_mode));os.fsync(o.fileno())
   assert H.read_bytes()==old;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
print(json.dumps(dict(before=sha(old),after=sha(raw),after_base64=base64.b64encode(raw).decode(),all_old_fields_and_current_phase_preserved=True)))
'''
x=dict(expected=sha(before),owner=os.environ['CODEX_THREAD_ID'],release=proof['release'],release_sha256=proof['release_sha256']);r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=60);(M/'left-publication-cursor.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr
v=json.loads(r.stdout);raw=base64.b64decode(v.pop('after_base64'));assert sha(raw)==v['after'];mirror(raw,sha(before));(M/'left-publication-cursor-CAS.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
