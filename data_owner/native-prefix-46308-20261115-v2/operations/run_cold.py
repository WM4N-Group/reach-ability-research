from pathlib import Path
import json,sys,hashlib,base64,subprocess,shlex
M=Path(__file__).parent;B=M.parents[1];c,phase=sys.argv[1:];assert phase in ('zero','main')
# Only new output readers and pinned immutable bridge. No physics in this tool.
files=[M/('zero_cold_readonly.py' if phase=='zero' else 'audit_main_readonly.py')]
if phase=='main':files += [M/n for n in ('adopted_optional_journal_bridge.py','JOURNAL_RECORD_BRIDGE_RELEASE_v1.json')]
rows=[dict(name=p.name,bytes=base64.b64encode(p.read_bytes()).decode(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
code='''from pathlib import Path
import os,sys,json,base64,hashlib,subprocess
B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');M=B/'manifests/native-prefix-46308-20261115-v2';x=json.load(sys.stdin);C=x['candidate'];phase=x['phase'];D=M/C
for row in x['rows']:
 p=(M/row['name'] if row['name'].endswith('readonly.py') else D/row['name']);raw=base64.b64decode(row['bytes']);assert hashlib.sha256(raw).hexdigest()==row['sha256']
 if p.exists():assert p.read_bytes()==raw
 else:
  with p.open('xb') as f:f.write(raw)
script=M/('zero_cold_readonly.py' if phase=='zero' else 'audit_main_readonly.py')
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2',DATA_PREFIX_CONDITION=C)
r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(script)],capture_output=True,env=env,timeout=240)
for suffix,raw in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode).encode()+b'\\n')]:
 with (D/(phase+'-cold.'+suffix)).open('xb') as f:f.write(raw)
name='actual-zero-cold-validation.json' if phase=='zero' else 'actual-main-cold-audit.json';out=dict(exit=r.returncode,stdout=r.stdout.decode(),stderr=r.stderr.decode())
if (D/name).exists():out['report']=json.loads((D/name).read_bytes())
print(json.dumps(out))
'''
x=dict(candidate=c,phase=phase,rows=rows);r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ControlMaster=auto','-o','ControlPersist=120','-o','ControlPath=/tmp/data-team-46308-01a1d3aa-ssh','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=270);assert r.returncode==0,r.stderr
out=json.loads(r.stdout)
for key in ('stdout','stderr'):(M/c/(phase+'-cold.'+key)).write_text(out[key])
(M/c/(phase+'-cold.exit')).write_text(str(out['exit'])+'\n')
if 'report' in out:(M/c/('actual-zero-cold-validation.json' if phase=='zero' else 'actual-main-cold-audit.json')).write_text(json.dumps(out['report'],ensure_ascii=False,indent=2)+'\n')
print(out['stdout']);print(out['stderr'],file=sys.stderr);sys.exit(out['exit'])
