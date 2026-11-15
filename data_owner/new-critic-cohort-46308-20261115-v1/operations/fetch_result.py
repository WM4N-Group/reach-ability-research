from pathlib import Path
import sys,json,base64,subprocess,shlex
M=Path(__file__).parent;c,phase=sys.argv[1:]
code='''from pathlib import Path
import os,sys,json,base64
x=json.load(sys.stdin);B=Path('/mnt/yuanyue/data-team/deployments/46308-20261114/workspace');W=B/'workers/new-critic-cohort-46308-20261115-v1';sys.path.insert(0,str(W));from prepare_prefix import SCOPES
root=B.parent/'runtime/workers'/SCOPES[x['candidate']];D=root/x['phase'];files={x['phase']+'-result.json':D/'result.json','final-ledger.json':root/'accounting/ledger.json'}
for name in ('construction.json','prefix-common-choice-binding.json','actual-model-identity.json','actual-config.json','new-purpose-acquisition-manifest.json'):
 p=D/name
 if p.exists():files[x['phase']+'-'+name]=p
for name in ('metadata.json','closure.json'):
 p=D/'raw-third-view'/name
 if p.exists():files[x['phase']+'-camera-'+name]=p
print(json.dumps({name:base64.b64encode(p.read_bytes()).decode() for name,p in files.items()}))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ControlMaster=auto','-o','ControlPersist=120','-o','ControlPath=/tmp/data-team-46308-01a1d3aa-ssh','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],input=json.dumps(dict(candidate=c,phase=phase)),capture_output=True,text=True,timeout=60);assert r.returncode==0,r.stderr
for n,b in json.loads(r.stdout).items():(M/c/n).write_bytes(base64.b64decode(b))
x=json.loads((M/c/(phase+'-result.json')).read_bytes());print(json.dumps({k:x.get(k) for k in ('status','passed','task_physics_steps','actual_main_world_sim_s','wall_s','error','actual_auxiliary_calibration','close_errors','raw_third_view_closure')},ensure_ascii=False,indent=2)[:3500])
