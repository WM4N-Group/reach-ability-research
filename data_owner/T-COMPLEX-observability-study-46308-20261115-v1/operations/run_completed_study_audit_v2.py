"""One readonly audit of terminal original OBS, no dispatch or H mutation."""
from pathlib import Path
import sys,subprocess,shlex,json,base64,hashlib
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;C='OBS';source=(M/'audit_completed_study_readonly_v2.py').read_bytes();x=dict(candidate=C,source=base64.b64encode(source).decode(),sha256=hashlib.sha256(source).hexdigest())
code=r'''
from pathlib import Path
import sys,json,hashlib,base64,subprocess,os
x=json.load(sys.stdin);M=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/T-COMPLEX-observability-study-46308-20261115-v1');p=M/'audit_completed_study_readonly_v2.py';raw=base64.b64decode(x['source']);assert hashlib.sha256(raw).hexdigest()==x['sha256']
if p.exists():assert p.read_bytes()==raw
else:
 with p.open('xb')as f:f.write(raw)
D=M/x['candidate'];E=dict(os.environ,DATA_OBSERVATION_ARM=x['candidate'],CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2');r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(p)],env=E,capture_output=True,text=True,timeout=150)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(D/('completed-study-cold-v2.'+suffix)).open('x')as f:f.write(text)
print(json.dumps(dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=200)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/C/('completed-study-cold-v2-transport.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);assert v['exit_code']==0,v['stderr'];report=json.loads(v['stdout'])
with(M/C/'actual-main-cold-audit-v2.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:z for k,z in report.items()if k in('passed','source_result_passed','actual_commands','visual_frames','direct_raw_resolution_px','HD_camera_metadata_verified','exact_three_boundaries_complete')},indent=2))
