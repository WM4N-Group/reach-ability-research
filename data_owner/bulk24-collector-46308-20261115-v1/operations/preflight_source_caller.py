"""One pre-freeze CPU typed-caller check; no scope, authority or native constructors."""
from pathlib import Path
import subprocess,shlex,json,base64,hashlib
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;W=B/'workers'/M.name;expected=hashlib.sha256((B/'registry/handoff_46308_current_status_20261115.json').read_bytes()).hexdigest();x=dict(expected_H=expected,files={str(p.relative_to(W)):base64.b64encode(p.read_bytes()).decode()for p in W.rglob('*')if p.is_file()and '__pycache__'not in p.parts})
code=r'''
from pathlib import Path
import json,sys,base64,hashlib,os,subprocess
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';H=B/'registry/handoff_current_status_20261115.json';before=H.read_bytes();assert hashlib.sha256(before).hexdigest()==x['expected_H'];W=B/'workers/bulk24-collector-46308-20261115-v1';M=B/'manifests/bulk24-collector-46308-20261115-v1';W.mkdir();M.mkdir()
for rel,v in x['files'].items():
 p=Path(rel);assert not p.is_absolute()and '..'not in p.parts;p=W/p;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(v))
fence=r"""
import sys,json
from pathlib import Path
import torch,mujoco
attempts=[]
def blocked(name):
 def fail(*a,**k):attempts.append(name);raise RuntimeError('NO_NATIVE_PREFLIGHT:'+name)
 return fail
torch.load=blocked('torch.load');torch.jit.load=blocked('torch.jit.load');torch.cuda._lazy_init=blocked('CUDA');torch.nn.Module.__call__=blocked('NN_forward');mujoco.MjSpec=blocked('MjSpec');mujoco.MjData=blocked('MjData');mujoco.Renderer=blocked('Renderer');mujoco.MjModel.from_xml_string=blocked('MjModelXML');mujoco.MjModel.from_xml_path=blocked('MjModelXMLPath');mujoco.mj_step=blocked('mj_step')
sys.path.insert(0,'/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/workers/bulk24-collector-46308-20261115-v1');import prepare_prefix as p
v=p.build_plan(p.IDS[0]);assert not attempts and not torch.cuda.is_initialized()and v['planner_capacity']==v['terminal_exact_successful_semantic_requests']==3 and not v['dispatch'];print(json.dumps(dict(passed=True,candidate=p.IDS[0],protocol=v['new_use_protocol_file_sha256'],source_scene_sha256=v['source_scene_sha256'],original_TYPED_planner_exact3=True,forbidden_attempts=attempts,no_world_Actor_GPU_or_dispatch=True,scope_not_registered=True)))
"""
E=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',LD_PRELOAD=str(R/'dependencies/native-expat-overlay-20261115-v1/lib/libexpat.so.1'));r=subprocess.run(['taskset','-c','38,39','/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B','-c',fence],env=E,capture_output=True,text=True,timeout=150)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('source-caller-preflight.'+suffix)).open('x')as f:f.write(text)
assert H.read_bytes()==before;print(json.dumps(dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,H_unchanged=True)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=200)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('preflight-transport.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
for suffix,text in [('stdout',v['stdout']),('stderr',v['stderr']),('exit',str(v['exit_code'])+'\n')]:
 with(M/('source-caller-preflight.'+suffix)).open('x')as f:f.write(text)
assert v['exit_code']==0,v['stderr'];result=json.loads(v['stdout']);result['H_unchanged']=v['H_unchanged'];(M/'source-caller-preflight.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
