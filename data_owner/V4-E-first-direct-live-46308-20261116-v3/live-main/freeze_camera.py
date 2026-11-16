"""Pre-main parameter CAS only: choose PREDECLARED task0 view1; do not change source/caps."""
from pathlib import Path
import json,subprocess,shlex,hashlib,base64,sys
M=Path(__file__).resolve().parent;B=M.parents[1];H=B/'registry/handoff_46308_current_status_20261115.json';old=H.read_bytes()
code=r'''
from pathlib import Path
import json,os,fcntl,tempfile,stat,base64,hashlib,datetime
B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');H=B/'registry/handoff_current_status_20261115.json';N='V4-E-first-direct-live-46308-20261116-v3';M=B/'manifests'/N;W=B/'workers'/N;KEY='active_V4_E_first_main_v3_scope';C=json.loads((W/'protocol.json').read_bytes());S=B.parent/'runtime/workers'/C['scope_id'];z=json.loads((S/'zero/result.json').read_bytes());assert z['passed']and z['actual_task_steps']==0 and z['close_errors']==[] and not Path('/proc/'+str(z['PID'])).exists();spec=C['cameras'][1];assert spec==C['camera_candidates'][1]==z['camera_frames'][1]['spec'];digest=hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':')).encode()).hexdigest();before=H.read_bytes();pin=hashlib.sha256(before).hexdigest();dfd=os.open(H.parent,os.O_RDONLY|os.O_DIRECTORY)
try:
 fcntl.flock(dfd,fcntl.LOCK_EX)
 with H.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_EX);raw=f.read();st=os.fstat(f.fileno());assert hashlib.sha256(raw).hexdigest()==pin;h=json.loads(raw);saved=json.loads(raw);q=h[KEY];assert q['active']and q['zero_dispatch_count']==1 and q['main_dispatch_count']==0 and not q['zero_passed']and q['camera_sha256']is None;q.update(zero_passed=True,zero_result_sha256=hashlib.sha256((S/'zero/result.json').read_bytes()).hexdigest(),chosen_camera=spec,camera_spec=spec,camera_sha256=digest,phase='ZERO_PASSED_PREDECLARED_CAMERA1_FROZEN_BEFORE_MAIN',camera_selection_reason='Actual task0 frames: view0 clips goal deck; view1 covers dog/three boxes/deck/full arena. Dog remains small in wide shot; no task outcome used.');assert all(h[k]==v for k,v in saved.items()if k not in(KEY,'updated_at'));h['updated_at']=datetime.datetime.now().astimezone().isoformat();after=(json.dumps(h,ensure_ascii=False,indent=2)+'\n').encode();fd,tmp=tempfile.mkstemp(prefix='.H-E-camera-',dir=H.parent)
  with os.fdopen(fd,'wb')as out:out.write(after);out.flush();os.fchmod(out.fileno(),stat.S_IMODE(st.st_mode));os.fsync(out.fileno())
  assert H.read_bytes()==raw;os.replace(tmp,H);os.fsync(dfd)
finally:os.close(dfd)
print(json.dumps(dict(before_H_sha256=pin,after_H_sha256=hashlib.sha256(after).hexdigest(),after_base64=base64.b64encode(after).decode(),camera_sha256=digest,camera_spec=spec,predeclared_camera_index=1,zero_result_sha256=q['zero_result_sha256'],no_frozen_source_or_cap_change=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr;x=json.loads(r.stdout);raw=base64.b64decode(x.pop('after_base64'));sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror;mirror(raw,hashlib.sha256(old).hexdigest())
with(M/'camera-freeze-proof.json').open('x')as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(x,ensure_ascii=False))
