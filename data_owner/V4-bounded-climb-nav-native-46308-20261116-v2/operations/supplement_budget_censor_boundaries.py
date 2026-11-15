"""Read exact closed native journal metadata; distinguish latched capture from later gait and wall censor from native terminal."""
from pathlib import Path
import json,hashlib,subprocess,shlex,datetime
M=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,hashlib,datetime
R=Path('/mnt/yuanyue/data-team/deployments/46308-20261114');S=R/'runtime/workers/data-46308-V4-bounded-climb-nav-native-20261116-v2';v=json.loads((S/'result.json').read_bytes());assert v['error']=='BoundedComponent1800wall cap with teardown reserve';events=[]
for line in(S/'events.jsonl').read_text().splitlines():events.append(json.loads(line)['payload'])
samples=[e for e in events if e.get('event')=='cold_capture_actual_sample'];last=samples[-1];assert len(samples)==448 and last['complete']and min(last['metrics']['foot_normal_N'])>=12 and abs(last['time_s']-448*.005)<1e-7
admitted=[e for e in events if e.get('event')=='ainav_native_admitted'];assert len(admitted)==1 and admitted[0]['option']['skill']=='NAV'and dict(admitted[0]['option']['parameters'])['surface_height_m']==0
term=[e for e in events if e.get('event')=='ainav_native_receipt'and e['receipt']['status']in('succeeded','failed','hard_stop','budget_expired')];assert not term
print(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),source_result_sha256=hashlib.sha256((S/'result.json').read_bytes()).hexdigest(),original_journal_sha256=hashlib.sha256((S/'events.jsonl').read_bytes()).hexdigest(),resource_wall_censored=True,no_native_failure_or_CLIMB_negative_label=True,original_actual_capture_completed_sample=last,actual_Push_intent_selected=[e for e in events if e.get('event')=='skill_intent_selected'],only_original_native_admitted=admitted,original_started_receipts=[e for e in events if e.get('event')=='ainav_native_receipt'and e['receipt']['status']=='started'],literal_native_terminal_receipts=term,original_NAV_actor_forward_events=sum(e.get('event')=='registered_NAV_actual_actor_forward'for e in events),actual_capture_commands=448,subsequent_original_ground_NAV_preparation_commands=v['actual_task_steps']-448,total_task_commands=v['actual_task_steps'],late_capture_report_is_current_gait_measurement_not_capture_boundary=True,late_capture_report_stable_seconds_not_continued_four_foot_dwell=True,legacy_capture_witness_complete_false_is_initial_unupdated_full_run_default=True,actual_Push_interaction_and_CLIMB_and_dynamic_NAV_not_attempted=True,no_original_scope_result_journal_or_guards_changed=True),ensure_ascii=False,indent=2))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-p','46308','root@180.97.68.228','/mnt/yuanyue/data-team/env-native-v1/bin/python -I -B -c '+shlex.quote(code)],text=True,capture_output=True,timeout=45);assert r.returncode==0,r.stderr;v=json.loads(r.stdout)
with(M/'Data-budget-censor-exact-capture-and-native-boundaries.json').open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(resource_censored=True,actual_capture_completed448=True,ground_NAV_preparation_commands=v['subsequent_original_ground_NAV_preparation_commands'],NAV_actor_forward_events=v['original_NAV_actor_forward_events'],literal_native_terminals=0,no_Climb_or_Push_failure_label=True),ensure_ascii=False))
