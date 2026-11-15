"""One explicit CPU-only encoding of immutable closed A/B raw RGB; no native."""
from pathlib import Path
import subprocess,json,base64,hashlib,shlex
M=Path(__file__).resolve().parent;name='encode_closed_pair_direct_raw_readonly.py';source=(M/name).read_bytes()
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,os,subprocess
x=json.load(sys.stdin);M=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/T-COMPLEX-01-full-program-46308-20261115-v1');p=M/x['name'];raw=base64.b64decode(x['source']);assert hashlib.sha256(raw).hexdigest()==x['sha256']
with p.open('xb')as f:f.write(raw)
E=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2');r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(p)],env=E,capture_output=True,text=True,timeout=180)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('closed-pair-video.'+suffix)).open('x')as f:f.write(text)
v=dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr)
if r.returncode==0:
 manifest=M/'closed-pair-direct-video-evidence-v1/manifest.json';v['manifest_base64']=base64.b64encode(manifest.read_bytes()).decode();preview=manifest.parent/'preview-first-and-last.png';assert preview.stat().st_size<1024**2;v['preview_base64']=base64.b64encode(preview.read_bytes()).decode()
print(json.dumps(v))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(name=name,source=base64.b64encode(source).decode(),sha256=hashlib.sha256(source).hexdigest())),capture_output=True,text=True,timeout=240)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('closed-pair-video-transport.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);assert v['exit_code']==0,v['stderr'];raw=base64.b64decode(v.pop('manifest_base64'));p=M/'closed-pair-direct-video-manifest.json'
with p.open('xb')as f:f.write(raw)
preview=base64.b64decode(v.pop('preview_base64'));
with(M/'closed-pair-preview-first-and-last.png').open('xb')as f:f.write(preview)
print(v['stdout'])
