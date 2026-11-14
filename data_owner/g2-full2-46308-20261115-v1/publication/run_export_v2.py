from pathlib import Path
import subprocess,sys,shlex,json,base64,hashlib
M=Path(__file__).resolve().parent;B=M.parents[1];side=sys.argv[1];assert side in('left','right');p=M/'export_closed_condition_v2.py'
code='''from pathlib import Path
import json,sys,base64,subprocess,hashlib
x=json.load(sys.stdin);M=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/g2-full2-46308-20261115-v1');p=M/'export_closed_condition_v2.py';raw=base64.b64decode(x['source']);assert hashlib.sha256(raw).hexdigest()==x['sha256']
if p.exists():assert p.read_bytes()==raw
else:
 with p.open('xb')as f:f.write(raw)
r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(p),x['side']],capture_output=True,timeout=120);sys.stdout.buffer.write(r.stdout);sys.stderr.buffer.write(r.stderr);sys.exit(r.returncode)
'''
x=dict(source=base64.b64encode(p.read_bytes()).decode(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),side=side)
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=150)
for name,raw in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/(side+'-public-export-v2.'+name)).open('x')as f:f.write(raw)
assert r.returncode==0,r.stderr
out=json.loads(r.stdout);D=B/'consumer-deliveries'/('AINAV-DATA-G2-46308-FULL2-'+side.upper()+'-ACTUAL-20261115-v1');D.mkdir(exist_ok=False)
for name,raw in out['files'].items():
 rel=Path(name);assert not rel.is_absolute()and '..'not in rel.parts;p=D/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(raw))
v=json.loads((D/'release.json').read_bytes());assert hashlib.sha256((D/'release.json').read_bytes()).hexdigest()==out['proof']['release_sha256']
assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==s for n,s in v['files'].items())
(M/('closed-'+side+'-release-proof.json')).write_text(json.dumps(out['proof'],indent=2)+'\n')
print(json.dumps(dict(proof=out['proof'],summary=v['actual_summary']),indent=2))
