"""Use source-owner exact immutable remote release, never drifting working tree."""
from pathlib import Path
import json,hashlib,subprocess,shlex,base64,datetime
B=Path('/home/yuanyue/main/work/data-team');M=Path(__file__).resolve().parent;W=B/'workers'/M.name;S=Path('/home/yuanyue/main/work/ainav/development/complex_dual_route_v1');P=Path('/home/yuanyue/main/work/ainav/manifests/T_COMPLEX_01_source_20261115_v1/CAMERA_ABI_REPAIR_AND_SOURCE_BOUND_PLANNER_DEPLOYED_NOT_NATIVE_QUALIFIED.json');raw=P.read_bytes();v=json.loads(raw);sha=lambda b:hashlib.sha256(b).hexdigest();drift={n:dict(expected=pin,actual=sha((S/n).read_bytes()))for n,pin in v['source_files_sha256'].items()if sha((S/n).read_bytes())!=pin};(M/'local-working-source-drift-rejected-before-stage.json').write_text(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),drift=drift,physical_dispatches=0,using_exact_released_remote_snapshot_instead=True),indent=2)+'\n')
code=r'''
from pathlib import Path
import json,sys,base64,hashlib
v=json.load(sys.stdin);S=Path(v['remote_root'])/'development/complex_dual_route_v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert S.is_dir()
for name,pin in v['source_files_sha256'].items():assert not(S/name).is_symlink()and sha(S/name)==pin
files={}
for p in S.rglob('*'):
 if p.is_file()and '__pycache__'not in p.parts and p.suffix in('.py','.md','.json'):
  assert not p.is_symlink();files[str(p.relative_to(S))]=dict(data=base64.b64encode(p.read_bytes()).decode(),sha256=sha(p))
print(json.dumps(files))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(v),capture_output=True,text=True,timeout=60);(M/'remote-source-intake.stderr').write_text(r.stderr);assert r.returncode==0,r.stderr;files=json.loads(r.stdout);I=W/'inputs';D=I/'scene';D.mkdir(parents=True);pins={}
for name,row in files.items():
 p=Path(name);assert not p.is_absolute()and '..'not in p.parts;p=D/p;p.parent.mkdir(parents=True,exist_ok=True);b=base64.b64decode(row['data']);assert sha(b)==row['sha256'];p.write_bytes(b);pins[name]=row['sha256']
(I/'SOURCE_OWNER_NATIVE_COMPONENTS.json').write_bytes(raw);(I/'SOURCE_SNAPSHOT_SHA256.json').write_text(json.dumps(pins,indent=2)+'\n');(M/'released-source-intake.json').write_text(json.dumps(dict(source_owner_commit=v['code_only_cloud_commit'],remote_source_root=v['remote_root'],source_owner_record_sha256=sha(raw),files_sha256=pins,old_closed_scope_unchanged=True,no_physical_calls=True),indent=2)+'\n');print('Exact released remote source received: '+str(len(pins))+' code-only members; local working tree drift not adopted')
