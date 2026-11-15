from pathlib import Path
import os,sys,json,hashlib,subprocess,shlex,base64
M=Path(__file__).resolve().parent;B=M.parents[1];O=B/'manifests/new-critic-cohort-46308-20261115-v1';sys.path.insert(0,str(O));from mirror_H import mirror
c,action=sys.argv[1:];before=(B/'registry/handoff_46308_current_status_20261115.json').read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();freeze=json.loads((M/'CAL-gate-admission-CAS.json').read_bytes());x=dict(candidate=c,action=action,expected_H_sha256=sha(before),owner=os.environ['CODEX_THREAD_ID'],phase_freeze_sha256=freeze['phase_freeze_sha256']);assert x['owner']==os.environ['CODEX_SESSION_ID']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480'
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote((M/'phase_control_cal_remote.py').read_text())],input=json.dumps(x),text=True,capture_output=True,timeout=180)
D=M/c;D.mkdir(exist_ok=True)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode)+'\n')]:
 with(D/('control-'+action+'.'+suffix)).open('x')as f:f.write(text)
assert r.returncode==0,r.stderr;v=json.loads(r.stdout);raw=base64.b64decode(v['after_base64']);assert sha(raw)==v['receipt']['after_H_sha256'];mirror(raw,sha(before));(D/('CAS-'+action+'.json')).write_text(json.dumps(v['receipt'],indent=2)+'\n');print(json.dumps(v['receipt'],indent=2))
