"""Record actual result after own child exit; close only this new scope on failure/main."""
from pathlib import Path
import json,os,hashlib,fcntl,tempfile,datetime,sys
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='perf-NAV2000-indexed-46308-20261116-v5';M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';S=R/'runtime/workers/data-46308-perf-NAV2000-indexed-20261116-v5';KEY='active_PERF01_NAV2000_indexed_v5_scope';OWNER='01a1e4e1-3037-7333-9019-a3f37effe5da';phase=sys.argv[1];assert phase in ['zero','main'];sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
raw=H.read_bytes();old=json.loads(raw);q=old[KEY];assert old['executing_thread_id']==q['owner']==OWNER and q['active']
result=json.loads((S/phase/'result.json').read_bytes());assert result['program_sha256']==q['whole_program_freeze_sha256']and result['phase']==phase
assert not Path('/proc/'+str(result['PID'])).exists(),'Wait for actual worker exit before closure'
locks=[]
for name,ino in [('physics',3428729629),('sdk',3428729630)]:
 p=R/f'resource-locks/native-observer-{name}-gpu0.lock';s=p.stat();assert(s.st_dev,s.st_ino)==(51,ino);holders=[x for x in Path('/proc/locks').read_text().splitlines()if len(x.split())>5 and x.split()[5].split(':')[-1]==str(ino)];assert not holders;locks.append(dict(path=str(p),device=s.st_dev,inode=s.st_ino,holders=holders))
final=json.loads((S/phase/'final-output-accounting.json').read_bytes());h=json.loads(raw);q=h[KEY];at=datetime.datetime.now().astimezone().isoformat()
q[phase+'_result_sha256']=sha(S/phase/'result.json');q[phase+'_actual_result']=dict(passed=result['passed'],PID=result['PID'],PID_exited=True,wall_s=result['wall_s'],actual_task_steps=result.get('actual_task_steps'),actual_task_sim_s=result.get('actual_task_sim_s'),actual_auxiliary_calibration=result.get('actual_auxiliary_calibration'),usage_known=result['usage_known'],peak_RSS_bytes=result['peak_RSS_bytes'],final_GPU=result.get('final_GPU'),status=result['status'],error=result.get('error'),close_errors=result['close_errors'],controlled_logical_bytes=final['final_controlled_logical_bytes'])
if phase=='zero'and result['passed']:
 image=result['own_zero_camera'];assert sha(S/'zero/camera.png')==image['image_sha256'];q.update(zero_passed=True,camera_sha256=image['spec_sha256'],camera_spec=image['spec'],phase='OWN_ZERO_PASSED_MAIN_NOT_YET_DISPATCHED',zero_qualified_at=at)
else:q.update(active=False,phase='CLOSED_'+phase.upper()+'_ACTUAL_'+('PASS'if result['passed']else'FAILED'),closed_at=at,automatic_retry=False,main_forbidden_after_failed_zero=(phase=='zero'))
assert all(h[k]==v for k,v in old.items()if k!=KEY)
d=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(d,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);st=os.fstat(f.fileno());assert f.read()==raw and H.stat().st_ino==st.st_ino;fd,tmp=tempfile.mkstemp(prefix='.PERF01-v2-phase-',dir=H.parent)
  try:
   os.fchmod(fd,st.st_mode&0o7777)
   with os.fdopen(fd,'wb')as out:out.write((json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode());out.flush();os.fsync(out.fileno())
   assert H.read_bytes()==raw;os.replace(tmp,H);os.fsync(d)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
finally:os.close(d)
proof=dict(at=at,phase=phase,before_H_SHA=hashlib.sha256(raw).hexdigest(),after_H_SHA=sha(H),all_non_scope_fields_preserved=True,scope=q,original_locks=locks,directory_file_flock_SHA_CAS_atomic_replace=True,mode_preserved=True)
(M/(phase+'-close-proof.json')).write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False))
