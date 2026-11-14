"""Bounded independent JSON-prefix/index and existing-log check. No producer checker."""
import datetime,hashlib,json,re
from pathlib import Path
OUT=Path(__file__).resolve().parent
CTRL=Path('/home/yuanyue/main/work/agent_team_runtime/stage2_joint_gate_20261018/control_dev')
dpath=CTRL/'s2_dev020_offline_prefix_delivery.json';read=lambda p:json.loads(Path(p).read_text());h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
d=read(dpath);c=read(d['comparison'])
for key in ('summary','comparison','evidence_manifest'):assert h(d[key])==d[key+'_sha256']
progress_path=CTRL/'old714_v001r3_run_terminal_20261019/originals/attempt/progress.json'
old_path=Path('/home/yuanyue/re-nav/artifacts/go2-piper-world-model/integrated-course-20261012-v13/full-01/report.json')
log_path=progress_path.parent.parent/'SDK.original.log'
for path in (progress_path,old_path,log_path):assert h(path)==c['inputs'][str(path)]['sha256']
assert h(progress_path)=='726cdf222814be219daa7d734df7e6cca3224dfd30afda10cdc4c5e13c799ed5'
assert h(old_path)=='9c837273663e8a28c00531f1c0b2597a486062a6b09146b3388e36f94bda3a60'
rev019=OUT.parent/'s2_rev_019_old714_firststep_terminal'
assert h(progress_path)==h(rev019/'remote_originals/attempt/progress.json') and h(log_path)==h(rev019/'remote_originals/SDK.original.log')
now=read(progress_path);old=read(old_path);trace=old['trace'][3100]
def same(a,b):
 if type(a) is not type(b):return False
 if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
 return a==b
assert len(now['events'])==95 and same(now['events'],old['events'][:95])
indices=[1,66,67,89,90,92,93,94]
selected=[{'current_pointer':'/events/'+str(i),'old_pointer':'/events/'+str(i),'event':now['events'][i]['event'],'sim_time':now['events'][i]['t'],'full_recorded_event_type_sensitive_equal':same(now['events'][i],old['events'][i])} for i in indices]
keys=['phase','base','box_speed_mps','base_speed_mps','hand_box_contact','platform_feet','climb_diagnostics']
assert set(now)&set(trace)==set(keys)
assert now['step']==15500 and now['time_s']==trace['t']==310.0 and old['step_dt']==.02 and trace['t']/old['step_dt']==15500
assert all(same(now[k],trace[k]) for k in keys)
for index,t,name in [(95,310.02,'four_support_body_plan'),(104,326.2,'climb_exit_body_ready'),(106,329.52,'first_step_platform_reached')]:assert old['events'][index]['t']==t and old['events'][index]['event']==name
lines=log_path.read_text().splitlines()
extract=lambda text:next((i+1,line) for i,line in enumerate(lines) if text in line)
scene_line,scene=extract('Time taken for scene creation');start_line,start=extract('Time taken for simulation start');terrain_line,terrain=extract('Generating terrains randomly took')
duration=lambda line:float(re.search(r':\s*([0-9.]+)\s+seconds',line)[1])
assert duration(scene)==4.003728 and duration(start)==6.034743 and duration(terrain)==.044094
warning_line,warning=extract('18:17:06')
warning_clean=re.sub(r'\x1b\[[0-9;]*m','',warning)
assert warning_clean.startswith('18:17:06 ') and warning_line>start_line
warning_utc=datetime.datetime.fromisoformat('2026-10-19T'+warning_clean.split()[0]+'+08:00').astimezone(datetime.timezone.utc)
stop_line,stop=extract('2026-10-19T10:55:22Z')
window=(datetime.datetime.fromisoformat(stop.split()[0].replace('Z','+00:00'))-warning_utc).total_seconds()
assert window==2296.0 and c['timing']['warning_to_stop_window_s']==window
canonical=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
result={'schema':'rev020-independent-bounded-offline-prefix-v1','at':datetime.datetime.now().astimezone().isoformat(),'decision':'CONFIRMED_RECORDED_PREFIX_MATCH_RUNTIME_BUDGET_PRIORITY','source_SHA_and_indices_verified':True,'current_progress':{'path':str(progress_path),'sha256':h(progress_path),'matches_REV019_independent_remote_copy':True},'old_v13_report':{'path':str(old_path),'sha256':h(old_path)},'current_95_events_vs_old_events_0_to_94':{'type_sensitive_all_JSON_values_equal':True,'event_array_order_and_sim_times_equal':True,'difference_count':0,'current_canonical_prefix_sha256':canonical(now['events']),'old_canonical_prefix_sha256':canonical(old['events'][:95])},'selected_indices':selected,'checkpoint':{'current_step_label':15500,'current_sim_label_s':310.0,'old_pointer':'/trace/3100','common_keys':keys,'all_seven_type_sensitive_equal':True,'diagnostics_null_is_not_extra_state_proof':True},'old_only_suffix_indices_checked':[95,104,106],'current_suffix_or_NAV_success_inferred':False,'continuous_full_state_equivalence_proved':False,'timing':{'scene_creation_s':duration(scene),'scene_line':scene_line,'simulation_start_s':duration(start),'simulation_start_line':start_line,'combined_explicit_nonterrain_time_s':duration(scene)+duration(start),'terrain_nested_s':duration(terrain),'terrain_not_added_again':True,'after_sim_start_warning_line':warning_line,'after_sim_start_warning_UTC':warning_utc.isoformat(),'stop_line':stop_line,'stop_UTC':stop.split()[0],'subsequent_window_s':window,'these_completed_creation_spans_cannot_account_for_later_2296s':True,'entire_2296s_attributed_to_action_loop':False,'CPU_GPU_actor_or_planner_bottleneck_identified':False},'decision_boundary':{'stop_treating_control_wiring_or_physics_parameters_as_established_root_cause':True,'no_control_or_loading_patch_supported_by_this_comparison':True,'prioritize_runtime_wall_budget_and_throughput_question':True,'all_possible_unrecorded_control_problems_ruled_out':False,'success_with_more_wall_proved':False,'bounded_attempt_outcome':'FAILED_WALL_TIMEOUT_BASELINE_NOT_COMPLETED','attempts':1,'successes':0,'included_in_success_rate_denominator':True},'new_framework_or_simulation_designed':False,'producer_script_executed':False,'historical_success_audit_repeated':False,'SDK_or_physics_or_remote_calls':0,'source_or_originals_modified':False,'new_RUN_authorized':False,'input_sha256':{str(path):h(path) for path in (dpath,Path(d['summary']),Path(d['comparison']),Path(d['evidence_manifest']),progress_path,old_path,log_path)}}
(OUT/'comparison_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('selected_indices','input_sha256')},indent=2))
