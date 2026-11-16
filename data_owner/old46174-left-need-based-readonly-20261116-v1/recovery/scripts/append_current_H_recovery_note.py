"""Current46308 maintenance metadata only; old UNKNOWN/H/ledger remain immutable."""
from pathlib import Path
import os,json,hashlib,subprocess,shlex,base64,sys
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']==OWNER;P=B/'registry/handoff_46308_current_status_20261115.json';old=P.read_bytes();x=json.loads((M/'recovered-metadata-publication-proof.json').read_bytes());code=r'''
from pathlib import Path
import os,fcntl,json,hashlib,tempfile,stat,datetime,sys,base64
x=json.load(sys.stdin);H=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/registry/handoff_current_status_20261115.json');before=H.read_bytes();assert hashlib.sha256(before).hexdigest()==x['before_sha256'];dfd=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY);key='old46174_left_recovered_metadata_20261116_v1'
try:
 fcntl.flock(dfd,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);raw=f.read();st=os.fstat(f.fileno());assert raw==before and H.stat().st_ino==st.st_ino;h=json.loads(raw);saved=json.loads(raw);assert h['executing_thread_id']==x['owner']and key not in h and not any(v.get('active')for k,v in h.items()if k.startswith('active_')and isinstance(v,dict));assert h['old_46174_administrative_closure']['sha256']=='a312c3e5b596d4c1d02e604cba471c75ca3a6f88f49026b5182172190bd0d866';assert hashlib.sha256(Path(x['remote_release']).read_bytes()).hexdigest()==x['release_sha256']
  h[key]=dict(at=datetime.datetime.now().astimezone().isoformat(),path=x['remote_release'],sha256=x['release_sha256'],old_scope_id='data-native-prefix-left-PUSH-CLIMB-20261114-v1',main_result_sha256='9a879643f89143078dd1fd55f468f16b27ecfd68329faf28b71c1f41088bffc5',final_ledger_sha256='5825aa3d97054de9c4796144bb7ff7de2a6d4d18ebbf3634acd4c34187f1abd1',reported_main_passed=True,reported_requested_semantic_successes=3,recovered_metadata_only_not_full_raw_cold=True,previous_UNKNOWN_snapshot_unchanged=True,no_new_sample_or_old_dispatch_or_old_H_write=True,not_current_compute_or_new_lease=True);h['updated_at']=datetime.datetime.now().astimezone().isoformat();assert all(h[k]==v for k,v in saved.items()if k!='updated_at');after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,tmp=tempfile.mkstemp(prefix='.H-old-recovery-note-',dir=H.parent)
  try:
   os.fchmod(fd,stat.S_IMODE(st.st_mode))
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fsync(out.fileno())
   assert H.read_bytes()==raw;os.replace(tmp,H);os.fsync(dfd)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
finally:os.close(dfd)
print(json.dumps(dict(before_H_sha256=hashlib.sha256(before).hexdigest(),after_H_sha256=hashlib.sha256(after).hexdigest(),after_base64=base64.b64encode(after).decode(),all_prior_fields_unchanged_except_updated_at=True,added_field=key,no_old_server_H_or_scope_or_ledger_mutation=True)))
''';payload=dict(owner=OWNER,before_sha256=hashlib.sha256(old).hexdigest(),**x);r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(payload),capture_output=True,text=True,timeout=45);assert r.returncode==0,r.stderr;proof=json.loads(r.stdout);raw=base64.b64decode(proof.pop('after_base64'));assert hashlib.sha256(raw).hexdigest()==proof['after_H_sha256'];sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror;mirror(raw,hashlib.sha256(old).hexdigest());(M/'current-H-recovery-note-CAS-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False))
