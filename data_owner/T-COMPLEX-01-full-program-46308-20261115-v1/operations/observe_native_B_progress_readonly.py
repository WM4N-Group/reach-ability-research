from pathlib import Path
import subprocess,shlex,json,datetime
M=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,hashlib,datetime
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');B=R/'workspace';H=B/'registry/handoff_current_status_20261115.json';raw=H.read_bytes();h=json.loads(raw);q=h['active_T_COMPLEX_full_program_scope'];assert q['arm']=='B';D=R/'runtime/workers'/q['scope_id']/'main';ledger=json.loads((D.parent/'accounting/ledger.json').read_bytes());pid=ledger['rows'][-1]['PID'];events=[];last='0'*64
for line in(D/'events.jsonl').read_text().splitlines():
 try:r=json.loads(line)
 except json.JSONDecodeError:continue
 digest=r.pop('sha256');encoded=json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode();assert r['sequence']==len(events)and r['previous_sha256']==last and hashlib.sha256(encoded).hexdigest()==digest;last=digest;events.append(r['payload'])
result=json.loads((D/'result.json').read_bytes())if(D/'result.json').exists()else None
v=dict(at=datetime.datetime.now().astimezone().isoformat(),H_sha256=hashlib.sha256(raw).hexdigest(),PID=pid,PID_exists=Path('/proc/'+str(pid)).exists(),scope=q,ledger_last=ledger['rows'][-1],complete_journal_rows_verified=len(events),selected_intents=[e for e in events if e.get('event')=='skill_intent_selected'],native_admissions=[e for e in events if e.get('event')=='ainav_native_admitted'],actual_intent_outcomes=[e for e in events if e.get('event')=='intent_actual_native_outcome'],terminal_native_receipts=[e for e in events if e.get('event')=='ainav_native_receipt'and e['receipt']['status']in('succeeded','failed','hard_stop','budget_expired')],capture_witnesses=[e for e in events if e.get('event')=='complex_actual_cold_capture_completed'],actual_NAV_actor_forward_count=sum(e.get('event')=='registered_NAV_actual_actor_forward'for e in events),public_bundle_decisions=sum(e.get('event')=='reach_complex_public_decision'for e in events),original_completed_placements=sum(e.get('event')=='completed_placement_boundary_latched'for e in events),result_status=result['status']if result else None,result_error=result.get('error')if result else None,not_task_success_or_three_meaningful_choices_inferred=True,no_physics_Renderer_Actor_or_live_state_calls=True)
print(json.dumps(v,ensure_ascii=False))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],capture_output=True,text=True,timeout=60);assert r.returncode==0,r.stderr;v=json.loads(r.stdout);p=M/('B-native-progress-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'.json');p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');(M/'latest-native-B-progress-pointer.json').write_text(json.dumps(dict(file=p.name),indent=2)+'\n');print(json.dumps(v,ensure_ascii=False,indent=2))
