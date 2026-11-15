"""Read current one study only; no native imports or dispatch, tolerate append tail."""
from pathlib import Path
import subprocess,shlex,json,datetime
M=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,hashlib,datetime
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';H=B/'registry/handoff_current_status_20261115.json';raw=H.read_bytes();h=json.loads(raw);q=h['active_T_COMPLEX_observation_study_scope'];assert q['arm']=='OBS';root=R/'runtime/workers'/q['scope_id'];phase='main'if q['main_dispatch_count']else'zero';D=root/phase;L=root/'accounting/ledger.json';ledger=json.loads(L.read_bytes())if L.exists()else None;pid=ledger['rows'][-1]['PID']if ledger and ledger['rows']else None;events=[];last='0'*64
if(D/'events.jsonl').exists():
 for line in(D/'events.jsonl').read_text().splitlines():
  try:r=json.loads(line)
  except json.JSONDecodeError:continue
  pin=r.pop('sha256');assert r['sequence']==len(events)and r['previous_sha256']==last and hashlib.sha256(json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()==pin;last=pin;events.append(r['payload'])
v=json.loads((D/'result.json').read_bytes())if(D/'result.json').exists()else None
out=dict(at=datetime.datetime.now().astimezone().isoformat(),H_sha256=hashlib.sha256(raw).hexdigest(),scope=q,phase=phase,PID=pid,PID_exists=bool(pid and Path('/proc/'+str(pid)).exists()),ledger_last=ledger['rows'][-1]if ledger and ledger['rows']else None,journal_complete_rows_verified=len(events),actual_capture_witnesses=[e for e in events if e.get('event')=='complex_actual_cold_capture_completed'],measurement_observations=[e for e in events if e.get('event')=='observability_qualification_actual_public_observation'],fixed_NAV_selections=[e for e in events if e.get('event')=='observability_qualification_fixed_NAV_selected'],actual_NAV_succeeded=[e for e in events if e.get('event')=='observability_qualification_original_NAV_succeeded'],actual_native_terminal_receipts=[e for e in events if e.get('event')=='ainav_native_receipt'and e['receipt']['status']in('succeeded','failed','hard_stop','budget_expired')],actual_NAV_actor_forward_count=sum(e.get('event')=='registered_NAV_actual_actor_forward'for e in events),actual_complete_measurement=[e for e in events if e.get('event')=='observability_qualification_complete_not_task'],result_status=v['status']if v else None,result_error=v.get('error')if v else None,result_passed=v['passed']if v else None,qualification_complete=v.get('observation_qualification_complete')if v else None,task_success=v['task_success']if v else False,AB_comparison=False,old_pair_active=h['active_T_COMPLEX_full_program_scope']['active'],old_pair_stop=h['T_COMPLEX_full_program_v1']['global_stop'],no_Runtime_Actor_Renderer_or_physics_call=True)
print(json.dumps(out,ensure_ascii=False))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],capture_output=True,text=True,timeout=60);assert r.returncode==0,r.stderr;v=json.loads(r.stdout);p=M/('readonly-observation-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json')
with p.open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
(M/'latest-observation-pointer.json').write_text(json.dumps(dict(file=p.name),indent=2)+'\n');print(json.dumps(v,ensure_ascii=False,indent=2))
