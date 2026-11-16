"""One explicit new bounded component lifecycle. No old-driver pause, no closed retry or five-arm dispatch."""
from pathlib import Path
import os,json,subprocess,base64,hashlib,datetime,sys,time
M=Path(__file__).resolve().parent;B=M.parents[1];H=B/'registry/handoff_46308_current_status_20261115.json';OWNER='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';assert os.environ['CODEX_THREAD_ID']==os.environ['CODEX_SESSION_ID']==OWNER;sha=lambda b:hashlib.sha256(b).hexdigest();cfg=json.loads((B/'workers'/M.name/'protocol.json').read_bytes());assert cfg['main_plan_sha256']==sha(Path('/home/yuanyue/main/汇总/各小组下一步研究计划.md').read_bytes())
with(M/'lifecycle-once-claim.json').open('x')as f:json.dump(dict(at=datetime.datetime.now().astimezone().isoformat(),owner=OWNER,PID=os.getpid(),scope_id=cfg['scope_id'],no_automatic_retry=True,old_bulk_driver_closed_not_signaled=True),f,indent=2);f.write('\n')
phases=[]
for action in ['inventory','freeze','prepare','dispatch','run','close']:
 old=H.read_bytes();begin=time.monotonic();cmd='/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B /mnt/yuanyue/data-team/deployments/46308-20261114/workspace/manifests/'+M.name+'/component_control_remote.py '+action;r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228',cmd],text=True,capture_output=True,timeout=cfg['wall_cap_s']+120 if action=='run'else 180)
 for suf,data in [('stdout',r.stdout),('stderr',r.stderr),('exit',str(r.returncode))]:
  with(M/(action+'-control.'+suf)).open('x')as f:f.write(data)
 assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
 if 'after_base64'in v:
  raw=base64.b64decode(v.pop('after_base64'));assert sha(raw)==v['after_H_sha256'];sys.path.insert(0,str(B/'manifests/new-critic-cohort-46308-20261115-v1'));from mirror_H import mirror;mirror(raw,sha(old))
 if 'small_files'in v:
  D=M/'actual-small';D.mkdir()
  for name,data in v.pop('small_files').items():assert Path(name).name==name;(D/name).write_bytes(base64.b64decode(data))
 with(M/(action+'-control-proof.json')).open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
 phases.append(dict(action=action,control_wall_s=time.monotonic()-begin,at=datetime.datetime.now().astimezone().isoformat()))
 with(M/('lifecycle-through-'+action+'.json')).open('x')as f:json.dump(dict(phases=phases,no_native_retry=True,no_closed_scope_or_other_owner_process_changes=True),f,indent=2);f.write('\n')
print(json.dumps(dict(lifecycle_closed=True,result=v.get('result'),ledger=v.get('ledger'),not_C_or_E_or_five_arm_main=True),ensure_ascii=False,indent=2))
