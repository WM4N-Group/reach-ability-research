"""Metadata-only SHA-CAS of closed B/pair original delivery; never clears stop."""
from pathlib import Path
import os,sys,json,hashlib,base64,subprocess,shlex
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;O=B/'manifests/new-critic-cohort-46308-20261115-v1';sys.path.insert(0,str(O));from mirror_H import mirror
sha=lambda b:hashlib.sha256(b).hexdigest();before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();p=json.loads((M/'B/original-release-proof.json').read_bytes());x=dict(owner=os.environ['CODEX_THREAD_ID'],expected=sha(before),release_path=p['release_path'],release_sha256=p['release_sha256']);assert x['owner']==os.environ['CODEX_SESSION_ID']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
code=r'''
from pathlib import Path
import os,sys,json,hashlib,base64,fcntl,stat,tempfile,datetime
x=json.load(sys.stdin);B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');H=B/'registry/handoff_current_status_20261115.json';P=Path(x['release_path']);sha=lambda b:hashlib.sha256(b).hexdigest();assert P.is_relative_to(B/'consumer-deliveries')and sha(P.read_bytes())==x['release_sha256'];release=json.loads(P.read_bytes());assert all(release['nine_stream_checks'].values())
for rel,pin in release['files'].items():assert sha((P.parent/rel).read_bytes())==pin
M=B/'manifests/T-COMPLEX-01-full-program-46308-20261115-v1';d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert sha(old)==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(old);saved=json.loads(old);assert h['executing_thread_id']==x['owner'];co=h['T_COMPLEX_full_program_v1'];b=co['branches']['B'];q=h['active_T_COMPLEX_full_program_scope'];assert not q['active']and q['arm']=='B'and b['zero_dispatch_count']==b['main_dispatch_count']==1 and b['actual_result_sha256']==release['source_result_sha256']
  if release['resource_censored']:assert co['global_stop']is True
  b['actual_public_delivery']=dict(release=x['release_path'],release_sha256=x['release_sha256'],role=release['role'],resource_censored=release['resource_censored'],native_terminal_receipts_count=len(release['actual_native_terminal_receipts']),actual_task_reconstructions=release['actual_task_reconstructions'],not_method_failure_or_advantage_inferred=True)
  co['closed_pair_diagnostic_delivery']=dict(release=x['release_path'],release_sha256=x['release_sha256'],direct_video_manifest=str(M/'closed-pair-direct-video-evidence-v1/manifest.json'),direct_video_manifest_sha256=release['files']['closed-pair-direct-video-manifest.json'],same_actual_predecision_input_and448_command_prefix=True,raw_originals_not_rerendered=True,not_full_success_master_or_algorithm_advantage=True,stop_not_cleared=True,no_scope_reopened=True)
  assert h['active_T_COMPLEX_full_program_scope']==saved['active_T_COMPLEX_full_program_scope']and co['branches']['A']==saved['T_COMPLEX_full_program_v1']['branches']['A']and co['global_stop']==saved['T_COMPLEX_full_program_v1']['global_stop'];assert all(h[k]==v for k,v in saved.items()if k not in('T_COMPLEX_full_program_v1','updated_at'));h['updated_at']=datetime.datetime.now().astimezone().isoformat();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-B-closed-pair-publication-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
   assert H.read_bytes()==old;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(before_H_sha256=sha(old),after_H_sha256=sha(after),B_release_sha256=x['release_sha256'],scope_inactive_counts_unchanged=True,all_old_CAL_VAL_fit_counts_and_A_unchanged=True,global_stop_not_cleared=True,no_new_physics_or_retry=True)
with(M/'B/closed-pair-release-publication-CAS.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(after).decode())))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=120)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/'B'/('closed-pair-release-publication.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['proof']['after_H_sha256'];mirror(raw,sha(before));(M/'B/closed-pair-release-publication-CAS.json').write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps(v['proof'],indent=2))
