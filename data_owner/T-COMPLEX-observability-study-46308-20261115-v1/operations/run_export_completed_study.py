from pathlib import Path
import subprocess,shlex,json,hashlib,base64
M=Path(__file__).resolve().parent;B=M.parents[1];s=(M/'export_completed_study_readonly.py').read_bytes();code=r'''
from pathlib import Path
import sys,json,base64,hashlib,subprocess,os
x=json.load(sys.stdin);M=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/T-COMPLEX-observability-study-46308-20261115-v1');p=M/'export_completed_study_readonly.py';raw=base64.b64decode(x['source']);assert hashlib.sha256(raw).hexdigest()==x['sha256']
with p.open('xb')as f:f.write(raw)
r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(p)],env=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2'),capture_output=True,text=True,timeout=240);sys.stdout.write(r.stdout);sys.stderr.write(r.stderr);sys.exit(r.returncode)
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(source=base64.b64encode(s).decode(),sha256=hashlib.sha256(s).hexdigest())),capture_output=True,text=True,timeout=300)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('completed-study-export.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);D=B/'consumer-deliveries'/Path(v['release_path']).parent.name;D.mkdir()
for name,data in v.pop('small_files').items():
 p=Path(name);assert not p.is_absolute()and '..'not in p.parts;p=D/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(data))
assert hashlib.sha256((D/'release.json').read_bytes()).hexdigest()==v['release_sha256'];(M/'completed-study-original-release-proof.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps(v,ensure_ascii=False,indent=2))
