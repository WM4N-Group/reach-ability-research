from pathlib import Path
import subprocess,json,hashlib,base64,shlex
M=Path(__file__).resolve().parent;B=M.parents[1];raw=(M/'export_component_readonly.py').read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest()
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,subprocess,os
x=json.load(sys.stdin);M=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/V4-native-components-46308-20261116-v1');p=M/'export_component_readonly.py';raw=base64.b64decode(x['source']);assert hashlib.sha256(raw).hexdigest()==x['sha256']
with p.open('xb')as f:f.write(raw)
r=subprocess.run(['taskset','-c','36,37','/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(p)],env=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2'),capture_output=True,text=True,timeout=90);sys.stdout.write(r.stdout);sys.stderr.write(r.stderr);sys.exit(r.returncode)
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(source=base64.b64encode(raw).decode(),sha256=sha(raw))),capture_output=True,text=True,timeout=130)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('component-original-export.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);D=B/'consumer-deliveries'/Path(v['release_path']).parent.name;D.mkdir()
for name,data in v.pop('small_files').items():
 p=Path(name);assert not p.is_absolute()and'..'not in p.parts;p=D/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(data))
assert sha((D/'release.json').read_bytes())==v['release_sha256'];(M/'component-original-release-proof.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps(v,ensure_ascii=False,indent=2))
