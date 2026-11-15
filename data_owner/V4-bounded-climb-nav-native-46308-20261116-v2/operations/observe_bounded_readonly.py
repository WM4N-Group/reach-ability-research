"""Scalar journal/process observer, never imports native/model or touches a lifecycle phase."""
from pathlib import Path
import json,subprocess,shlex,datetime
M=Path(__file__).resolve().parent;B=M.parents[1];c=json.loads((B/'workers'/M.name/'protocol.json').read_bytes())
code=r'''from pathlib import Path
import json,datetime
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';h=json.loads((B/'registry/handoff_current_status_20261115.json').read_bytes());q=h['active_V4_bounded_climb_nav_v2_scope'];S=R/'runtime/workers'/q['scope_id'];claim=json.loads((S/'claim.json').read_bytes())if(S/'claim.json').exists()else None;events=[];capture_samples=0;last_capture_time=None
if(S/'events.jsonl').exists():
 for line in(S/'events.jsonl').read_text().splitlines():
  try:r=json.loads(line)
  except json.JSONDecodeError:continue
  e=r['payload'];name=e.get('event','')
  if name=='cold_capture_actual_sample':capture_samples+=1;last_capture_time=e.get('time_s')
  if name in['skill_intent_selected','ainav_native_admitted','ainav_native_receipt','intent_actual_native_outcome','ainav_chain_hard_stop']:events.append(e)
result=json.loads((S/'result.json').read_bytes())if(S/'result.json').exists()else None;print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),scope=q,PID=claim['PID']if claim else None,PID_exists=bool(claim and Path('/proc/'+str(claim['PID'])).exists()),capture_actual_sample_events=capture_samples,last_actual_capture_time_s=last_capture_time,public_or_native_boundary_events=events[-16:],result=result,no_source_Actor_Model_or_Runtime_calls=True),ensure_ascii=False))'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],capture_output=True,text=True,timeout=45);assert r.returncode==0,r.stderr;v=json.loads(r.stdout);p=M/('readonly-progress-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json')
with p.open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
(M/'latest-progress-pointer.json').write_text(json.dumps(dict(file=p.name),indent=2)+'\n');print(json.dumps(dict(at=v['at'],active=v['scope']['active'],phase=v['scope']['phase'],PID=v['PID'],PID_exists=v['PID_exists'],capture_samples=v['capture_actual_sample_events'],last_capture_time_s=v['last_actual_capture_time_s'],boundary_events=len(v['public_or_native_boundary_events']),result_status=None if v['result']is None else v['result']['status']),ensure_ascii=False))
