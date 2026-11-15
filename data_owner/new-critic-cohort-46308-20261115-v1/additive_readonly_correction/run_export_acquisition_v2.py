from pathlib import Path
import json,hashlib,base64,subprocess,shlex,sys
M=Path(__file__).resolve().parent;B=M.parents[1];C=sys.argv[1];p=M/'export_closed_acquisition_v2.py';rows=json.loads((B/'workers'/M.name/'inputs/new-cohort/FIXED_ACQUISITIONS.json').read_bytes())['conditions'];match=[r for r in rows if r['condition_id']==C];assert len(match)==1;ordinal=match[0]['ordinal'];sha=lambda b:hashlib.sha256(b).hexdigest()
code=r'''from pathlib import Path
import json,sys,hashlib,base64,subprocess
x=json.load(sys.stdin);M=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/new-critic-cohort-46308-20261115-v1');p=M/'export_closed_acquisition_v2.py';raw=base64.b64decode(x['source']);assert hashlib.sha256(raw).hexdigest()==x['source_sha256']
if p.exists():assert p.read_bytes()==raw
else:
 with p.open('xb')as f:f.write(raw)
r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(p),x['condition_id']],capture_output=True,timeout=120);sys.stdout.buffer.write(r.stdout);sys.stderr.buffer.write(r.stderr);sys.exit(r.returncode)
'''
x=dict(condition_id=C,source=base64.b64encode(p.read_bytes()).decode(),source_sha256=sha(p.read_bytes()));r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=150)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(M/C/('original-export-v2.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;out=json.loads(r.stdout);D=B/'consumer-deliveries'/('AINAV-DATA-NEW-CRITIC-46308-ORDINAL-%02d-ACTUAL-20261115-v1'%ordinal);D.mkdir(exist_ok=False)
for name,raw in out['files'].items():
 rel=Path(name);assert not rel.is_absolute()and '..'not in rel.parts;p=D/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(raw))
v=json.loads((D/'release.json').read_bytes());assert sha((D/'release.json').read_bytes())==out['proof']['release_sha256'];assert all(sha((D/n).read_bytes())==s for n,s in v['files'].items());(M/C/'actual-original-release-proof.json').write_text(json.dumps(out['proof'],indent=2)+'\n');print(json.dumps(dict(proof=out['proof'],summary=v['actual_summary']),indent=2))
