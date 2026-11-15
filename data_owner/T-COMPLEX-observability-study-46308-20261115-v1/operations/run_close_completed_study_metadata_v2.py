"""Close only terminal OBS metadata while existing GPU1 main is undisturbed."""
from pathlib import Path
import json,os,hashlib,subprocess,shlex,base64,sys
M=Path(__file__).resolve().parent;B=M.parents[1];H=B/'registry/handoff_46308_current_status_20261115.json';old=H.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();source=(M/'close_completed_study_metadata_v2.py').read_bytes();owner=os.environ['CODEX_THREAD_ID'];assert owner==os.environ['CODEX_SESSION_ID'];x=dict(source=base64.b64encode(source).decode(),sha256=sha(source),owner=owner,expected=sha(old))
code=r'''
from pathlib import Path
import sys,os,json,base64,hashlib,subprocess
x=json.load(sys.stdin);M=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/T-COMPLEX-observability-study-46308-20261115-v1');p=M/'close_completed_study_metadata_v2.py';raw=base64.b64decode(x.pop('source'));assert hashlib.sha256(raw).hexdigest()==x.pop('sha256')
with p.open('xb')as f:f.write(raw)
r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(p)],input=json.dumps(x),capture_output=True,text=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable'),timeout=150);sys.stdout.write(r.stdout);sys.stderr.write(r.stderr);sys.exit(r.returncode)
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=200)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/'OBS'/('close-main-metadata-v2.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['receipt']['after_H_sha256'];sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror;mirror(raw,sha(old))
with(M/'OBS/CAS-close-main-v2.json').open('x')as f:json.dump(v['receipt'],f,indent=2);f.write('\n')
print(json.dumps(v['receipt'],indent=2))
