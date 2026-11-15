"""Copy exact released19+3 source closure, stage a default-off new worker only."""
from pathlib import Path
import json,hashlib,base64,subprocess,shlex,datetime
M=Path(__file__).resolve().parent;B=M.parents[1];W=B/'workers'/M.name;sha=lambda b:hashlib.sha256(b).hexdigest();req=json.loads((M/'AINav-NATIVE_ASSET_COLD_COMPONENT_REQUEST.json').read_bytes());cfg=json.loads((W/'protocol.json').read_bytes());assert req['own_zero_max_proposed']==1 and req['main_max_proposed']==0;assert cfg['main_plan_sha256']==sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())
files={'worker.py':(W/'worker.py').read_bytes(),'protocol.json':(W/'protocol.json').read_bytes(),'inputs/main-plan.md':Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes(),'inputs/NATIVE_ASSET_COLD_COMPONENT_REQUEST.json':(M/'AINav-NATIVE_ASSET_COLD_COMPONENT_REQUEST.json').read_bytes()}
code=r'''
from pathlib import Path
import sys,json,hashlib,base64,shutil,datetime
x=json.load(sys.stdin);R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='V4-native-components-46308-20261116-v1';W=B/'workers'/N;M=B/'manifests'/N;assert not W.exists()and not M.exists();W.mkdir();M.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();source=x['request']['source'];owner=Path(source['remote_code_root']);V=owner/source['source_relative_path'];allfiles={}
for rel,pin in source['source_files_sha256'].items():
 p=V/rel;assert not p.is_symlink()and sha(p)==pin;dest=W/'inputs/ainav/development/complex_v4_four_arm_v1'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);allfiles[str(dest.relative_to(W))]=base64.b64encode(dest.read_bytes()).decode()
base={'native_construction.py':'6c3ee245cd54bfeeec0c64a53627ec2efbebba34775afcac7aab794a286b18cf','complex_scene.py':'613a18e735addf31edfe448e6f46e58ad0c130f4066c9b4393a8720d686d78c0','camera_abi.py':'3969490e368f47d944471f77c103e11cf369e9ff90726c2fbca9cf9dadad7617'}
for rel,pin in base.items():
 p=owner/'development/complex_dual_route_v1'/rel;assert not p.is_symlink()and sha(p)==pin;dest=W/'inputs/ainav/development/complex_dual_route_v1'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);allfiles[str(dest.relative_to(W))]=base64.b64encode(dest.read_bytes()).decode()
for rel,row in x['files'].items():
 p=Path(rel);assert not p.is_absolute()and'..'not in p.parts;raw=base64.b64decode(row['source']);assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=W/p;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(raw)
 c=p.suffix
 if c=='.py':compile(raw,str(p),'exec')
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),released_source_members=len(source['source_files_sha256']),exact_base_members=len(base),all_released_pins_match=True,not_imported_native_or_models=True,no_H_or_physical_dispatch=True,small_files=allfiles)))
'''
x=dict(request=req,files={rel:dict(source=base64.b64encode(raw).decode(),sha256=sha(raw))for rel,raw in files.items()});r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=90)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('source-stage.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
for rel,data in v.pop('small_files').items():
 p=W/rel;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb')as f:f.write(base64.b64decode(data))
for rel,raw in files.items():
 if rel not in('worker.py','protocol.json'):
  p=W/rel;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb')as f:f.write(raw)
(M/'source-stage-proof.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v,indent=2))
