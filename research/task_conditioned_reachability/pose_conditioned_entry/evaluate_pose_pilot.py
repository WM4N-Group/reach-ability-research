"""Eight-cell descriptive pilot at fixed world goal. Missing NEVER filled.

Typed final-preview refusal is an observed failed task, not a successful safety
certificate. The old16 cells remain in their old evaluation, not replaced here.
"""
import argparse,json,math
from pathlib import Path


def refusal_verified(r):
    f=r.get('entry_final_preview_refusal',{});v=r.get('measured_final_support_verification',{});preview=v.get('box_approach_preview',{})
    return (r.get('outcome')=='entry_final_preview_refused' and f.get('criterion')=='COMMON_original_full_cloud_fixed_yz'
        and f.get('physics_advanced') is False and f.get('command_issued') is False
        and v.get('shift_m',0)>0 and f.get('required_shift_m')==v['shift_m']
        and preview.get('evaluation_role')=='final_actual' and preview.get('criterion')=='COMMON_original_full_cloud_fixed_yz'
        and not r.get('error') and not any(e.get('event')=='push_activated' for e in r.get('control_events',[])))


def classify(r,item):
    value=dict(seed=item['seed'],arm=item['arm'],native_outcome=None,primary_success=None,protocol_valid=None)
    if r is None:return dict(value,unknown_reason='missing_report')
    value['native_outcome']=r.get('outcome')
    if (r.get('seed')!=item['seed'] or r.get('study_arm')!=item['arm'] or r.get('study_global_goal_se2')!=[-.25,0.,0.] or r.get('physical_resets_after_initial')!=0):
        return dict(value,protocol_valid=False,unknown_reason='case_arm_goal_or_reset_mismatch')
    if r.get('physics_samples',0)<=0:return dict(value,unknown_reason='no_actual_physics_coverage')
    value['protocol_valid']=True
    if r.get('outcome')=='entry_final_preview_refused':
        if not refusal_verified(r):return dict(value,protocol_valid=False,unknown_reason='unverified_typed_refusal')
        return dict(value,primary_success=False,typed_refusal=True)
    if r.get('outcome')!='nav_push_stow_nav_target_stable':return dict(value,primary_success=False)
    v=r.get('measured_final_support_verification',{});preview=v.get('box_approach_preview',{})
    if v.get('shift_m')!=0 or preview.get('evaluation_role')!='final_actual' or preview.get('criterion')!='COMMON_original_full_cloud_fixed_yz':
        return dict(value,protocol_valid=False,unknown_reason='common_actual_verifier_not_proven')
    event=next((e for e in r.get('control_events',[]) if e.get('event')=='return_nav_requested_after_stowed_ready'),None)
    final=r.get('return_nav_final_state')
    if event is None or final is None:return dict(value,unknown_reason='missing_actual_goal_or_final_pose')
    if event.get('goal',[])[:2]!=[-.25,0.]:return dict(value,protocol_valid=False,unknown_reason='wrong_actual_world_goal')
    p=final['root_position'];q=final['root_quaternion'];xy=math.hypot(p[0]+.25,p[1]);heading=abs(2*math.atan2(q[3],q[0]))
    gates=final.get('exit_stable_gates',{})
    passed=(xy<.05 and heading<.12 and final.get('return_nav_stable_seconds',0)>=.5 and final.get('retracted_ready') is True and bool(gates) and all(gates.values()))
    if not passed:return dict(value,protocol_valid=False,unknown_reason='raw_native_goal_gates_not_satisfied')
    return dict(value,primary_success=True,xy_error_m=xy,native_heading_error_rad=heading)


def summarize(protocol,ledger,reports):
    entries={} if ledger is None else {(e['seed'],e['arm']):e for e in ledger.get('entries',[])}
    active=None if ledger is None else ledger.get('active');rows=[]
    for item in protocol['schedule']:
        key=item['seed'],item['arm']
        if key in entries:row=dict(classify(reports.get(key),item),status='recorded_start')
        else:row=dict(seed=key[0],arm=key[1],primary_success=None,status='in_flight' if active and (active['seed'],active['arm'])==key else 'not_run')
        rows.append(row)
    complete=all(r['primary_success'] is not None for r in rows);arms={}
    for arm in protocol['arms']:
        group=[r for r in rows if r['arm']==arm];known=sum(r['primary_success'] is not None for r in group);wins=sum(r['primary_success'] is True for r in group);n=len(group)
        arms[arm]=dict(registered=n,known=known,verified_successes=wins,unknown=n-known,complete_rate=wins/n if known==n else None,registered_success_bounds=[wins/n,(wins+n-known)/n])
    effects={}
    for left,right in [('P0','P1'),('P2','P3'),('P0','P2'),('P1','P3')]:
        effects[right+'_minus_'+left]=(sum(int(next(r for r in rows if r['seed']==seed and r['arm']==right)['primary_success'])-int(next(r for r in rows if r['seed']==seed and r['arm']==left)['primary_success']) for seed in protocol['seeds'])/len(protocol['seeds'])) if complete else None
    return dict(schema='pose-factorial-eight-cell-evaluation-v1',starts=0 if ledger is None else ledger['starts'],rows=rows,arms=arms,effects=effects,
        effect_status='descriptive_development_only' if complete else 'NOT_ESTIMABLE_incomplete_registered_cells',
        full_obstacle_navigation_claim=False,independent_generalization_claim=False,old16_cells_replaced=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    protocol=json.loads((a.root/'source/protocol.json').read_text());f=a.root/'physical_ledger.json';ledger=json.loads(f.read_text()) if f.exists() else None
    reports={}
    for item in protocol['schedule']:
        file=a.root/'runs'/item['output_name']/'report.json'
        if file.exists():reports[item['seed'],item['arm']]=json.loads(file.read_text())
    with a.output.open('x') as f:json.dump(summarize(protocol,ledger,reports),f,indent=2);f.write('\n')

if __name__=='__main__':main()
