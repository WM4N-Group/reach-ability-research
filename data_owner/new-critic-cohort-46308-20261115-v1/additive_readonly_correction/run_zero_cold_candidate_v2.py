from pathlib import Path
import json,subprocess,shlex,base64,hashlib,sys
M=Path(__file__).resolve().parent;c=sys.argv[1];p=M/'zero_cold_candidate_readonly_v2.py';x=dict(condition_id=c,source=base64.b64encode(p.read_bytes()).decode(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),release=base64.b64encode((M/'READONLY_ZERO_CANDIDATE_AUDITOR_CORRECTION_v2.json').read_bytes()).decode())
code=r'''from pathlib import Path
import json,sys,base64,hashlib,subprocess,os
x=json.load(sys.stdin);M=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/new-critic-cohort-46308-20261115-v1');D=M/x['condition_id'];p=M/'zero_cold_candidate_readonly_v2.py';raw=base64.b64decode(x['source']);assert hashlib.sha256(raw).hexdigest()==x['source_sha256'];rel=M/'READONLY_ZERO_CANDIDATE_AUDITOR_CORRECTION_v2.json';rr=base64.b64decode(x['release'])
for path,data in [(p,raw),(rel,rr)]:
 if path.exists():assert path.read_bytes()==data
 else:
  with path.open('xb')as f:f.write(data)
assert not(D/'actual-zero-cold-validation.json').exists(),'Do not replace an existing passed or failed cold report'
env=dict(os.environ,CUDA_VISIBLE_DEVICES='',MUJOCO_GL='disable',OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2',DATA_PREFIX_CONDITION=x['condition_id']);r=subprocess.run(['/mnt/yuanyue/data-team/env-native-v1/bin/python','-I','-B',str(p)],env=env,capture_output=True,timeout=240)
for suf,raw in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode).encode()+b'\n')]:
 with(D/('zero-cold-candidate-v2.'+suf)).open('xb')as f:f.write(raw)
report=D/'actual-zero-cold-validation.json';print(json.dumps(dict(exit=r.returncode,stdout=r.stdout.decode(),stderr=r.stderr.decode(),report=json.loads(report.read_bytes())if report.exists()else None)))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(x),capture_output=True,text=True,timeout=270);assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
for suf,t in [('stdout',v['stdout']),('stderr',v['stderr']),('exit',str(v['exit'])+'\n')]:
 with(M/c/('zero-cold-candidate-v2.'+suf)).open('x')as f:f.write(t)
if v['report']is not None:(M/c/'actual-zero-cold-validation.json').write_text(json.dumps(v['report'],indent=2)+'\n')
print(v['stdout']);print(v['stderr'],file=sys.stderr);sys.exit(v['exit'])
