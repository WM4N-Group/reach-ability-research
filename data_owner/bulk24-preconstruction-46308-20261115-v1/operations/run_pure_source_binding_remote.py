"""Stage a new CODE-only snapshot and do one fenced CPU source-binding probe.
Does not allocate scope/authority/lease, use GPU/Actor or modify in-flight roots.
"""
from pathlib import Path
import subprocess,shlex,json,base64,hashlib
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;D=B/'development'/M.name;x=dict(expected_H=hashlib.sha256((B/'registry/handoff_46308_current_status_20261115.json').read_bytes()).hexdigest(),files={str(p.relative_to(D)):base64.b64encode(p.read_bytes()).decode()for p in D.rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc'})
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,os,subprocess,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';H=B/'registry/handoff_current_status_20261115.json';before=H.read_bytes();assert hashlib.sha256(before).hexdigest()==x['expected_H'];D=B/'development/bulk24-preconstruction-46308-20261115-v1';M=B/'manifests/bulk24-preconstruction-46308-20261115-v1';D.mkdir();M.mkdir()
for rel,encoded in x['files'].items():
 p=Path(rel);assert not p.is_absolute()and '..'not in p.parts;p=D/p;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(encoded))
E=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1',LD_PRELOAD=str(R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1'));r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(D/'prepare_bulk24.py'),'--enable-pure-source-binding'],env=E,capture_output=True,text=True,timeout=120)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('pure-source-binding.'+suffix)).open('x')as f:f.write(text)
assert H.read_bytes()==before
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,H_unchanged=True,no_scope_allocated=True,no_native_dispatch=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=180)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('pure-binding-transport.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
for suffix,text in [('stdout',v['stdout']),('stderr',v['stderr']),('exit',str(v['exit_code'])+'\n')]:
 with(M/('pure-source-binding.'+suffix)).open('x')as f:f.write(text)
assert v['exit_code']==0,v['stderr'];report=json.loads(v['stdout']);report['remote_probe_H_unchanged']=v['H_unchanged']
with(M/'actual-pure-source-binding.json').open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:z for k,z in report.items()if k!='rows'},ensure_ascii=False,indent=2))
