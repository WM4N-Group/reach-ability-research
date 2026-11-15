"""Only publish a closed delivery or admit the next UNSTARTED fixed GPU1 slot.
No native subprocess or phase dispatch; old OBS/fit/closed counts never modified.
"""
from pathlib import Path
import os,sys,json,hashlib,base64,subprocess,shlex,time
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror
act=sys.argv[1];assert act in ('publish-first','activate-next');before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();h=json.loads(before);co=h['bulk24_collector_v1'];q=h['active_bulk24_collector_scope'];i=co['order'].index(q['candidate_id']);tag='first-delivery-v2'if act=='publish-first'else('activate-%02d-%d'%(i+2,time.time_ns()));sha=lambda b:hashlib.sha256(b).hexdigest();proof=json.loads((M/'g2-bulk24-v1__bulk-g01_left__original/original-release-proof.json').read_bytes());x=dict(action=act,expected=sha(before),owner=os.environ['CODEX_THREAD_ID'],release=proof['release_path'],release_sha256=proof['release_sha256'],tag=tag);assert x['owner']==os.environ['CODEX_SESSION_ID']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
code=r'''
from pathlib import Path
import os,sys,json,hashlib,base64,fcntl,stat,tempfile,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';M=B/'manifests/bulk24-collector-46308-20261115-v1';W=B/'workers/bulk24-collector-46308-20261115-v1';H=B/'registry/handoff_current_status_20261115.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();resources=None
if x['action']=='activate-next':sys.path.insert(0,str(W));from resource_snapshot import fresh;resources=fresh()
p=Path(x['release']);assert p.is_relative_to(B/'consumer-deliveries')and sha(p)==x['release_sha256'];release=json.loads(p.read_bytes());assert release['actual_summary']['source_result_passed']and not release['actual_summary']['HD']and all(release['actual_summary']['nine_stream_checks'].values())
for rel,pin in release['files'].items():assert sha(p.parent/rel)==pin
d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);old=f.read();st=os.fstat(f.fileno());assert hashlib.sha256(old).hexdigest()==x['expected']and(H.stat().st_dev,H.stat().st_ino)==(st.st_dev,st.st_ino);h=json.loads(old);saved=json.loads(old);assert h['executing_thread_id']==x['owner'];co=h['bulk24_collector_v1'];q=h['active_bulk24_collector_scope'];assert not q['active']and not co['global_stop']
  if x['action']=='publish-first':
   first=co['branches'][co['order'][0]];assert first['status']=='CLOSED_ACTUAL_MAIN_PASS'and first['zero_dispatch_count']==first['main_dispatch_count']==1
   first['actual_public_delivery']=dict(release=x['release'],release_sha256=x['release_sha256'],first_PREPARE_time_s=release['actual_summary']['first_CLIMB_boundary']['first_PREPARE_time_s'],not_current_critic_refit=True)
   co['raw_camera_precision']=dict(actual_direct_raw_resolution_px=[192,128],HD=False,prior_bulk_HD_wording_withdrawn=True,zero_cold_original_HD_label_was_inherited_metadata_not_resolution_gate=True,clarification=str(M/'DIRECT_RAW_RESOLUTION_AND_AUDITOR_ERRATUM.json'),clarification_sha256=sha(M/'DIRECT_RAW_RESOLUTION_AND_AUDITOR_ERRATUM.json'),native_program_and_records_and_counts_not_changed=True)
  else:
   k=co['order'].index(q['candidate_id']);n=k+1;assert n<len(co['order']);previous=co['branches'][co['order'][k]];c=co['order'][n];br=co['branches'][c];assert previous['status'].startswith('CLOSED_ACTUAL_MAIN_')and previous['zero_dispatch_count']==previous['main_dispatch_count']==1 and json.loads((M/co['order'][k]/'actual-main-cold-audit-v2.json').read_bytes())['passed'];assert br['zero_dispatch_count']==br['main_dispatch_count']==0 and not(R/'runtime/workers'/br['scope_id']).exists();assert sha(M/c/'program-freeze.json')==br['whole_program_freeze_sha256']
   h['active_bulk24_collector_scope']=dict(active=True,owner=x['owner'],arm=c,candidate_id=c,scope_id=br['scope_id'],phase='ADMITTED_NEXT_GPU1_PREPARE_NO_DISPATCH',authorization_sha256=co['authorization_sha256'],whole_program_freeze_sha256=br['whole_program_freeze_sha256'],zero_dispatch_count=0,main_dispatch_count=0,zero_dispatch_program_sha256=None,main_dispatch_program_sha256=None,automatic_retry=False,GPU_physical_index=1,resource_snapshot=resources);br['status']='ADMITTED_NEXT_GPU1_PREPARE_NO_DISPATCH';co['status']=br['status'];co['active_index']=n
  assert all(h[k]==v for k,v in saved.items()if k not in ('bulk24_collector_v1','active_bulk24_collector_scope','updated_at'));h['updated_at']=datetime.datetime.now().astimezone().isoformat();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,t=tempfile.mkstemp(prefix='.H-bulk24-metadata-',dir=H.parent)
  try:
   with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
   assert H.read_bytes()==old;os.replace(t,H);os.fsync(d)
  finally:
   if os.path.exists(t):os.unlink(t)
finally:os.close(d)
proof=dict(before_H_sha256=hashlib.sha256(old).hexdigest(),after_H_sha256=hashlib.sha256(after).hexdigest(),action=x['action'],no_native_dispatch=True,old_and_OBS_and_fit_fields_unchanged=True,closed_counts_not_reset=True,current_scope=h['active_bulk24_collector_scope'])
with(M/(x['tag']+'-CAS.json')).open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(dict(proof=proof,after_base64=base64.b64encode(after).decode())))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=180)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/(tag+'-control.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);mirror(raw,sha(before));(M/(tag+'-CAS.json')).write_text(json.dumps(v['proof'],indent=2)+'\n');print(json.dumps(v['proof'],indent=2))
