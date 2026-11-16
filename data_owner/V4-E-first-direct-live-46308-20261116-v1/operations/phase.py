from pathlib import Path
import sys,json,subprocess,base64,hashlib,datetime,os
M=Path(__file__).resolve().parent;B=M.parents[1];assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';action=sys.argv[1];suffix='-'.join(sys.argv[1:]);H=B/'registry/handoff_46308_current_status_20261115.json';old=H.read_bytes();C=json.loads((B/'workers'/M.name/'protocol.json').read_bytes());cmd='/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B /mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/'+M.name+'/control.py '+' '.join(sys.argv[1:]);r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228',cmd],capture_output=True,text=True,timeout=(C['main_wall_cap_s']+120 if action=='main'else 420))
for name,s in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
 with(M/(suffix+'.'+name)).open('x')as f:f.write(s)
assert r.returncode==0,r.stderr;x=json.loads(r.stdout)
if'after_base64'in x:
 raw=base64.b64decode(x.pop('after_base64'));assert hashlib.sha256(raw).hexdigest()==x['after_H_sha256'];sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror;mirror(raw,hashlib.sha256(old).hexdigest())
frames=x.pop('zero_frames',{})
for name,b64 in frames.items():
 with(M/name).open('xb')as f:f.write(base64.b64decode(b64))
with(M/(suffix+'-proof.json')).open('x')as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(action=action,result=x.get('result'),program=x.get('program_sha256'),frames=list(frames)),ensure_ascii=False))
