"""Stage exact41+7 immutable source closure and new distinct own-zero; no H/physics."""
from pathlib import Path
import json,subprocess,hashlib,base64,shlex,datetime
M=Path(__file__).resolve().parent;B=M.parents[1];W=B/'workers'/M.name;req=json.loads((M/'PARALLEL_CURRENT_FULL_PATH_GUARD.original.json').read_bytes());sha=lambda b:hashlib.sha256(b).hexdigest();files={p.name:p.read_bytes()for p in[W/'worker.py',W/'protocol.json',W/'engineering_policy.py',W/'private_catalog_boundary.py']};files['inputs/main-plan.md']=Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes();files['inputs/PARALLEL_CURRENT_FULL_PATH_GUARD.json']=(M/'PARALLEL_CURRENT_FULL_PATH_GUARD.original.json').read_bytes()
assert json.loads(files['protocol.json'])['main_plan_sha256']==sha(files['inputs/main-plan.md'])
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,shutil,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='V4-parallel-guard-bounded-native-46308-20261116-v1';W=B/'workers'/N;M=B/'manifests'/N;assert not W.exists()and not M.exists();W.mkdir();M.mkdir();source=x['request'];owner=Path(source['remote_code_root']);V=owner/'development/complex_v4_four_arm_v1';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();out={}
base={'native_construction.py':'6c3ee245cd54bfeeec0c64a53627ec2efbebba34775afcac7aab794a286b18cf','complex_scene.py':'613a18e735addf31edfe448e6f46e58ad0c130f4066c9b4393a8720d686d78c0','camera_abi.py':'3969490e368f47d944471f77c103e11cf369e9ff90726c2fbca9cf9dadad7617','semantic_factory.py':'52f2eb52dcda837067ad027782ec35465ac44b90aae4c09b4865c28877a869a2','multi_goal_factory.py':'afbe3326015db0544a8714a565d53795f3cfd0f72a891529dd4d1b852f2e7070','terminal_stop.py':'461d4146aeed1622be01f1952a1b4d582eab631cbf14f9defbdc3e0a78099196'}
base['scene_driver.py']=sha(owner/'development/complex_dual_route_v1/scene_driver.py')
for directory,pins in[(V,source['source_files_sha256']),(owner/'development/complex_dual_route_v1',base)]:
 for rel,pin in pins.items():
  p=directory/rel;assert not p.is_symlink()and sha(p)==pin;dest=W/'inputs/ainav/development'/directory.name/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);out[str(dest.relative_to(W))]=base64.b64encode(dest.read_bytes()).decode()
for rel,row in x['files'].items():
 p=Path(rel);assert not p.is_absolute()and'..'not in p.parts;raw=base64.b64decode(row['source']);assert hashlib.sha256(raw).hexdigest()==row['sha256'];dest=W/p;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb')as f:f.write(raw)
 if p.suffix=='.py':compile(raw,str(dest),'exec')
raw=base64.b64decode(x['control']);assert hashlib.sha256(raw).hexdigest()==x['control_sha256'];p=M/'component_control_remote.py'
with p.open('xb')as f:f.write(raw)
compile(raw,str(p),'exec')
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),source41_and_parent7_verified=True,small_files=out,no_H_or_native_dispatch=True)))
'''
control=(M/'component_control_remote.py').read_bytes();r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(request=req,files={rel:dict(source=base64.b64encode(raw).decode(),sha256=sha(raw))for rel,raw in files.items()},control=base64.b64encode(control).decode(),control_sha256=sha(control))),capture_output=True,text=True,timeout=90)
for suf,data in[('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
 with(M/('source-stage.'+suf)).open('x')as f:f.write(data)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
for rel,data in v.pop('small_files').items():
 p=W/rel;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(data))
for rel,data in files.items():
 if rel in['worker.py','protocol.json','engineering_policy.py','private_catalog_boundary.py']:continue
 p=W/rel;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(data)
with(M/'source-stage-proof.json').open('x')as f:json.dump(v,f,indent=2);f.write('\n')
print(json.dumps(v))
