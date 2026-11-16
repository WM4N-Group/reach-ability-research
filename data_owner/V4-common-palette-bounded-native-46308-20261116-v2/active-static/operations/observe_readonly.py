"""Read this NEW scope only; never signal a worker, touch a lease or invoke once/control."""
from pathlib import Path
import json,subprocess,shlex,datetime,hashlib
M=Path(__file__).resolve().parent;B=M.parents[1]
code=r'''
from pathlib import Path
import os,json,hashlib,datetime,subprocess
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';N='V4-common-palette-bounded-native-46308-20261116-v2';M=B/'manifests'/N;H=B/'registry/handoff_current_status_20261115.json';raw=H.read_bytes();h=json.loads(raw);assert h['executing_thread_id']=='01a1d3aa-a0d5-7de0-b886-9d92ed5f1480';q=h.get('active_V4_palette_bounded_v2_scope');root=R/'runtime/workers/data-46308-V4-common-palette-bounded-native-20261116-v2'
assert not h['active_V4_bounded_climb_nav_scope']['active']and not h['active_V4_bounded_climb_nav_v2_scope']['active']and not h['active_V4_parallel_guard_bounded_scope']['active']and not h['active_V4_palette_bounded_scope']['active']
def tail(p,n=32768):
 if not p.exists():return ''
 with p.open('rb')as f:
  f.seek(max(0,p.stat().st_size-n));return f.read(n).decode(errors='replace')
rows=[]
for line in tail(root/'software-phase-timing.jsonl').splitlines():
 try:rows.append(json.loads(line))
 except json.JSONDecodeError:pass
small={}
for name in ['new-common-appearance-static-delta-proof.json','actual-supported-capture-completion-boundary.json','result.json','ledger.json']:
 p=root/name
 if p.exists():small[name]=json.loads(p.read_bytes())
child=json.loads((M/'component-child.json').read_bytes())if(M/'component-child.json').exists()else None
process=None
if child and Path('/proc/'+str(child['PID'])).exists():
 p=Path('/proc/'+str(child['PID']));status=(p/'status').read_text();process=dict(PID=child['PID'],status=[x for x in status.splitlines()if x.split(':')[0]in('State','VmRSS','Threads','Cpus_allowed_list')],wchan=(p/'wchan').read_text(),stat=(p/'stat').read_text())
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),H_sha256=hashlib.sha256(raw).hexdigest(),H_scope=q,program_sha256=hashlib.sha256((M/'program-freeze.json').read_bytes()).hexdigest()if(M/'program-freeze.json').exists()else None,process=process,child=child,last_timing_checkpoint=rows[-1]if rows else None,actual_small=small,event_tail=tail(root/'events.jsonl',12000),source50_new_asset_and_old_closed_brown_samples_not_conflated=True,read_only_no_dispatch_or_lease=True),ensure_ascii=False))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],capture_output=True,text=True,timeout=60);assert r.returncode==0,r.stderr;x=json.loads(r.stdout);x['local_H_mirror_matches_at_observation']=hashlib.sha256((B/'registry/handoff_46308_current_status_20261115.json').read_bytes()).hexdigest()==x['H_sha256'];p=M/('readonly-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json')
with p.open('x')as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
with(M/'latest-readonly-pointer.json').open('w')as f:json.dump(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()),f,indent=2);f.write('\n')
print(json.dumps(dict(path=str(p),phase=None if x['H_scope']is None else x['H_scope']['phase'],program=x['program_sha256'],process=x['process'],checkpoint=x['last_timing_checkpoint'],result=x['actual_small'].get('result.json'),local_H_mirror_matches=x['local_H_mirror_matches_at_observation']),ensure_ascii=False,indent=2))
