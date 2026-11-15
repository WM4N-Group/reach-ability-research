from pathlib import Path
import subprocess,json,base64,hashlib,shlex
M=Path(__file__).resolve().parent
for name in['audit_closed_B_readonly.py']:
 source=(M/name).read_bytes();code=r'''
from pathlib import Path
import sys,json,base64,hashlib,os,subprocess
x=json.load(sys.stdin);M=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/T-COMPLEX-01-full-program-46308-20261115-v1');p=M/x['name'];raw=base64.b64decode(x['source']);assert hashlib.sha256(raw).hexdigest()==x['sha256']
with p.open('xb')as f:f.write(raw)
E=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',DATA_COMPLEX_ARM='B',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2');r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(p)],env=E,capture_output=True,text=True,timeout=120)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/'B'/(x['name']+'.'+suffix)).open('x')as f:f.write(text)
print(json.dumps(dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr)))
'''
 r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(name=name,source=base64.b64encode(source).decode(),sha256=hashlib.sha256(source).hexdigest())),capture_output=True,text=True,timeout=180);assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
 for suffix,text in[('stdout',v['stdout']),('stderr',v['stderr']),('exit',str(v['exit_code'])+'\n')]:
  with(M/'B'/(name+'.'+suffix)).open('x')as f:f.write(text)
 assert v['exit_code']==0,v['stderr'];out=json.loads(v['stdout']);p=M/'B'/('actual-main-cold-audit.json'if name.startswith('audit')else'unused-no-diagnostic.json');p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:z for k,z in out.items()if k not in('checks','pixel_only_proposal','actual_semantic_intent_selections')},ensure_ascii=False,indent=2)[:5000])
