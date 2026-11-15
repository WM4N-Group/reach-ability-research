"""Copy only immutable completed 19..20 public queries and small evidence."""
from pathlib import Path
import subprocess,shlex,json,hashlib,base64,datetime
M=Path(__file__).resolve().parent;B=M.parents[1];source=(M/'export_closed_ordinals19to20_originals.py').read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest()
with(M/'closed19to20-original-export-once.json').open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),no_physics_no_H_mutation=True,ordinals=[19,20]),f,indent=2);f.write('\n')
code=r'''
from pathlib import Path
import sys,json,base64,hashlib,subprocess,os
x=json.load(sys.stdin);M=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/bulk24-collector-46308-20261115-v1');p=M/'export_closed_ordinals19to20_originals.py';raw=base64.b64decode(x['source']);assert hashlib.sha256(raw).hexdigest()==x['sha256']
with p.open('xb')as f:f.write(raw)
protocol=json.loads((M.parents[1]/'workers'/M.name/'protocol.json').read_bytes());releases=[]
for ordinal in(19,20):
 candidate=protocol['order'][ordinal-1];r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(p),candidate],env=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable'),capture_output=True,text=True,timeout=120)
 for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
  with(M/candidate/('original-export-fixed-v4.'+suffix)).open('x')as f:f.write(text)
 if r.returncode:sys.stderr.write(r.stderr);sys.exit(r.returncode)
 releases.append(json.loads(r.stdout))
print(json.dumps(dict(releases=releases)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(source=base64.b64encode(source).decode(),sha256=sha(source))),capture_output=True,text=True,timeout=420)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/('closed19to20-original-export.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;out=json.loads(r.stdout)
for v in out['releases']:
 D=B/'consumer-deliveries'/Path(v['release_path']).parent.name;D.mkdir()
 for name,data in v.pop('small_files').items():
  p=Path(name);assert not p.is_absolute()and'..'not in p.parts;p=D/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(data))
 assert sha((D/'release.json').read_bytes())==v['release_sha256'];release=json.loads((D/'release.json').read_bytes())
 for name,pin in release['files'].items():assert sha((D/name).read_bytes())==pin
 candidate=release['attempt_key']
 with(M/candidate/'original-release-proof.json').open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
with(M/'closed19to20-original-release-index.json').open('x')as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps([dict(release_path=v['release_path'],release_sha256=v['release_sha256'],passed=v['summary']['source_result_passed'],public_queries=v['summary']['public_query_count'],CLIMB_boundary=v['summary']['first_CLIMB_boundary'])for v in out['releases']],ensure_ascii=False,indent=2))
