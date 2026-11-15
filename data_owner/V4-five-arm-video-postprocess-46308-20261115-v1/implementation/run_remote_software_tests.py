"""One isolated synthetic CPU check, no existing actual run is replayed."""
from pathlib import Path
import subprocess,base64,hashlib,json,shlex,datetime
D=Path(__file__).resolve().parent;B=D.parents[1];M=B/'manifests/V4-five-arm-video-postprocess-46308-20261115-v1';M.mkdir();files={n:(D/n).read_bytes()for n in ['encode_five_arm_originals.py','test_five_arm_originals.py']}
code=r'''
from pathlib import Path
import json,sys,base64,hashlib,os,subprocess,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');D=R/'workspace/development/V4-five-arm-video-postprocess-46308-20261115-v1';D.mkdir();pins={}
for name,row in x['files'].items():
 assert Path(name).name==name and name.endswith('.py');raw=base64.b64decode(row['source']);assert hashlib.sha256(raw).hexdigest()==row['sha256']
 with(D/name).open('xb')as f:f.write(raw)
 pins[name]=row['sha256']
E=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2');r=subprocess.run(['taskset','-c','36,37','/mnt/yuanyue/data-team/env-native-v1/bin/python','-B','-m','unittest','-v','test_five_arm_originals'],cwd=D,env=E,capture_output=True,text=True,timeout=180)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(D/('software-fixture-test.'+suffix)).open('x')as f:f.write(text)
assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==p for n,p in pins.items());print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,source_pins=pins,synthetic_fixture_only=True,no_actual_source_or_four_method_evidence_used=True,no_native_Actor_Renderer_WM_API_or_physics_calls=True,temporary_fixture_videos_not_delivered_or_retained=True)))
'''
x=dict(files={n:dict(source=base64.b64encode(v).decode(),sha256=hashlib.sha256(v).hexdigest())for n,v in files.items()});r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=220)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('software-fixture-transport.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
with(M/'software-fixture-test-result.json').open('x')as f:json.dump(v,f,indent=2);f.write('\n')
assert v['exit_code']==0,v['stderr'];print(json.dumps(v,indent=2))
