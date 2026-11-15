from pathlib import Path
import os,sys,json,hashlib,base64,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;O=B/'manifests/new-critic-cohort-46308-20261115-v1';sys.path.insert(0,str(O));from mirror_H import mirror
sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();p=json.loads((M/'A/original-release-proof.json').read_bytes());x=dict(owner=os.environ['CODEX_THREAD_ID'],expected=sha(before),release_path=p['release_path'],release_sha256=p['release_sha256'])
code=r'''
from pathlib import Path
import os,sys,json,hashlib,base64,fcntl,stat,tempfile,datetime
x=json.load(sys.stdin);B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');H=B/'registry/handoff_current_status_20261115.json';P=Path(x['release_path']);sha=lambda b:hashlib.sha256(b).hexdigest();assert P.is_relative_to(B/'consumer-deliveries')and sha(P.read_bytes())==x['release_sha256'];release=json.loads(P.read_bytes());assert release['source_result_passed']is False and all(release['nine_stream_checks'].values())
for rel,pin in release['files'].items():assert sha((P.parent/rel).read_bytes())==pin
M=B/'manifests/T-COMPLEX-01-full-program-46308-20261115-v1';eq=json.loads((M/'actual-AB-zero-condition-equality.json').read_bytes());assert eq['passed'];d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert sha(old)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(old);saved=json.loads(old);assert h['executing_thread_id']==x['owner'];co=h['T_COMPLEX_full_program_v1'];a=co['branches']['A'];assert a['status']=='CLOSED_ACTUAL_MAIN_FAILED_NO_RETRY'and a['zero_dispatch_count']==a['main_dispatch_count']==1 and not co['global_stop']
  a['actual_public_delivery']=dict(release=x['release_path'],release_sha256=x['release_sha256'],role=release['role'],original_native_task_options=0,original_task_reconstructions=0,first_query_refusal_not_method_advantage=True);co['actual_zero_initial_condition_equality']=dict(proof=str(M/'actual-AB-zero-condition-equality.json'),sha256=sha((M/'actual-AB-zero-condition-equality.json').read_bytes()),full_integration_state_INPUT8_HD_exact_equal=True,no_state_copy_restore_or_recapture=True);co['A_source_qualification_limit']='Actual original capture passed; first PUSH intent refused at current RGBD association, not executed PUSH or long-horizon planning failure. Ordinary rejection, no detected source integrity/resource stop. B has independent frozen admission; no inferred B result.'
  assert h['active_T_COMPLEX_full_program_scope']==saved['active_T_COMPLEX_full_program_scope']and co['branches']['B']==saved['T_COMPLEX_full_program_v1']['branches']['B'];assert all(h[k]==v for k,v in saved.items()if k not in('T_COMPLEX_full_program_v1','updated_at'));h['updated_at']=datetime.datetime.now().astimezone().isoformat();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-A-first-query-publication-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
   assert H.read_bytes()==old;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(before_H_sha256=sha(old),after_H_sha256=sha(after),A_release_sha256=x['release_sha256'],active_B_scope_counts_and_dispatch_unchanged=True,all_old_and_CAL_VAL_counts_and_fit_unchanged=True,A_not_retried=True,B_result_not_inferred=True)
with(M/'A/first-query-release-publication-CAS.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(after).decode())))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=120)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/'A'/('release-publication.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['proof']['after_H_sha256'];mirror(raw,sha(before));(M/'A/first-query-release-publication-CAS.json').write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps(v['proof'],indent=2))
