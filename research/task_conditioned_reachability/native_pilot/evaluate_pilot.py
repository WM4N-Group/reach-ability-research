"""Evaluation of registered starts at a common world goal; never fill missing.

Reported native outcome is preserved separately from verified common-goal
completion and method delivery. SDK fixtures are not physical episodes.
"""
import argparse,json,math
from pathlib import Path


def classify(report,entry):
    out=dict(seed=entry['seed'],arm=entry['arm'],native_outcome=None,primary_success=None,
             protocol_valid=None,method_delivery_verified=False,unknown_reason=None)
    if report is None:return dict(out,unknown_reason='missing_actual_episode_report_NOT_success_or_native_failure')
    out['native_outcome']=report.get('outcome')
    if (report.get('seed')!=entry['seed'] or report.get('study_arm')!=entry['arm']
            or report.get('study_global_goal_se2')!=[-.25,0.,0.] or report.get('physical_resets_after_initial')!=0):
        return dict(out,protocol_valid=False,unknown_reason='source_case_arm_goal_or_reset_mismatch')
    if not report.get('physics_samples',0):
        return dict(out,unknown_reason='no_recorded_actual_physics_coverage')
    out['protocol_valid']=True
    preview=report.get('prospective_support_plan',{}).get('box_approach_preview',{})
    out['method_delivery_verified']=preview.get('study_arm')==entry['arm'] and bool(preview.get('query_id'))
    if report.get('outcome')!='nav_push_stow_nav_target_stable':
        out['primary_success']=False
        return out
    event=next((e for e in report.get('control_events',[]) if e['event']=='return_nav_requested_after_stowed_ready'),None)
    final=report.get('return_nav_final_state')
    if event is None or final is None:
        return dict(out,unknown_reason='native_success_without_actual_goal_or_final_state_evidence')
    if event.get('goal',[])[:2]!=[-.25,0.]:
        return dict(out,protocol_valid=False,unknown_reason='state_relative_or_wrong_goal_NOT_registered_world_goal')
    p=final['root_position'];q=final['root_quaternion']
    position_error=math.hypot(p[0]+.25,p[1]);heading_error=abs(2*math.atan2(q[3],q[0]))
    gates=final.get('exit_stable_gates')
    satisfied=(position_error<.05 and heading_error<.12 and final.get('return_nav_stable_seconds',0)>=.5
               and final.get('retracted_ready') is True and isinstance(gates,dict) and bool(gates) and all(gates.values()))
    out.update(actual_goal_xy_error_m=position_error,actual_goal_heading_error_rad=heading_error)
    if not satisfied:return dict(out,protocol_valid=False,unknown_reason='native_success_not_supported_by_raw_common_goal_native_gate_evidence')
    out['primary_success']=True
    return out


def summarize(protocol,ledger,reports):
    entries={} if ledger is None else {(e['seed'],e['arm']):e for e in ledger.get('entries',[])}
    active=None if ledger is None else ledger.get('active')
    rows=[]
    for item in protocol['schedule']:
        key=item['seed'],item['arm'];entry=entries.get(key)
        if entry is None:
            row=dict(seed=key[0],arm=key[1],primary_success=None,status='not_run' if not active or (active['seed'],active['arm'])!=key else 'in_flight')
        else:
            row=classify(reports.get(key),entry);row['status']='recorded_start'
            row['end_sim_s']=entry.get('end_sim_s');row['wall_s']=entry.get('wall_s')
        rows.append(row)
    arms={}
    for arm in ['E0','E1','E2','E3']:
        group=[r for r in rows if r['arm']==arm];known=[r for r in group if r['primary_success'] is not None]
        wins=sum(r['primary_success'] is True for r in group)
        arms[arm]=dict(registered=4,known_outcomes=len(known),verified_successes=wins,
                       unknown_or_not_run=4-len(known),registered_success_bounds=[wins/4,(wins+4-len(known))/4],
                       complete_point_rate=wins/4 if len(known)==4 else None)
    complete=all(r['primary_success'] is not None for r in rows)
    effects={}
    for a,b in [('E0','E1'),('E1','E2'),('E2','E3')]:
        effects[b+'_minus_'+a]=(sum(int(next(r for r in rows if r['seed']==seed and r['arm']==b)['primary_success'])-
                                     int(next(r for r in rows if r['seed']==seed and r['arm']==a)['primary_success']) for seed in protocol['seeds'])/4) if complete else None
    return dict(schema='common-goal-native-pilot-evaluation-v1',starts=0 if ledger is None else ledger['starts'],
                primary='actual fixed-world-goal completion, NOT static/SDK/model validity',
                paired_effect_status='descriptive_pilot_only_NOT_confirmatory' if complete else 'NOT_ESTIMABLE_incomplete_pairs',
                rows=rows,arms=arms,paired_effects=effects,independent_generalization_claim=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    protocol=json.loads((a.root/'source/protocol.json').read_text())
    ledger_path=a.root/'physical_ledger.json';ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else None
    reports={}
    for s in protocol['schedule']:
        f=a.root/'runs'/s['output_name']/'report.json'
        if f.exists():reports[s['seed'],s['arm']]=json.loads(f.read_text())
    with a.output.open('x') as f:json.dump(summarize(protocol,ledger,reports),f,indent=2);f.write('\n')

if __name__=='__main__':main()
