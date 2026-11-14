"""Independent read-only full-course acceptance, including actual robot crossing."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from .audit import audit as data_audit
from .review_capture import state_records,load_display_model
from .integrated_course import layout


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit(root,output):
    import mujoco
    root=Path(root);p=json.loads((root/'protocol.json').read_text());r=json.loads((root/'report.json').read_text())
    errors=[]
    def check(ok,message):
        if not ok:errors.append(message)
    freeze=json.loads((root/'freeze.json').read_text())
    for path,digest in freeze['inputs'].items():check(sha(root/path)==digest,'frozen input changed:'+path)
    data=data_audit(root/'episode');errors.extend(data['errors'])
    full=r.get('integrated_course',{});prefix=full.get('prefix',{});abort=prefix.get('abort')
    check(bool(r['task_success']) and r['error'] is None,'collector did not report successful full completion')
    check(full.get('stage')=='FAR_BANK_COMPLETE' and full.get('complete'),'full stage graph incomplete')
    check(bool(full.get('endpoint',{}).get('passed')),'actual far-bank endpoint not passed')
    check(bool(abort) and abort.get('native_goal_success') is False,'actual failed A attempt absent')
    if abort:
        check(abort['box_dx_contact_window_m']<.002 and abort['contact_window_s']>=.06-1e-7,'A original60ms stall not measured')
        check(full['endpoint']['A_failed_goal_retained']==abort['original_goal'],'retired A goal changed')
    recovery=prefix.get('recovery') or {}
    check(bool(recovery.get('stow_verified')),'A protected recovery not verified')
    check(bool((prefix.get('selected_B',{}).get('result') or {}).get('native_PUSH_goal_reached')),'B native push goal absent')
    results=r['native_results'];unique=[];seen=set();duplicate_results=[]
    for row in results:
        if row['skill']=='push':key=('push',(row.get('finish') or {}).get('started'))
        elif row['skill']=='climb':key=('climb',(row.get('stop') or {}).get('handoff_time'))
        else:key=('nav',len(unique))
        if key in seen:duplicate_results.append(key);continue
        seen.add(key);unique.append(row)
    successful=[x['skill'] for x in unique if x.get('successful')]
    check(successful.count('push')==2,'both B and C native push/finish completions required')
    check(successful.count('climb')==3,'B step, high platform and C deck native climb completions required')
    ledger=[json.loads(x) for x in (root/'integrated-stage-events.jsonl').read_text().splitlines()]
    names=[x['event'] for x in ledger]
    required=['B_native_goal_and_original_finish_complete','actual_high_platform_reached','explicit_C_bound_on_high_platform','bridge_actual_docked_and_stowed','full_integrated_sequence_complete']
    positions=[]
    for name in required:
        check(names.count(name)==1,'missing or duplicate phase:'+name)
        if name in names:positions.append(names.index(name))
    check(positions==sorted(positions),'stage graph executed out of order')
    if p.get('causal_model_policy'):
        check(r['reset_after_initial']==0 and r['WM_control']==1 and r['WM_forwards']>=3 and r['training_runs']==0,'causal no-reset model execution accounting differs')
        from .causal_policy_audit import audit as policy_audit
        model_audit=policy_audit(root,r);errors.extend(model_audit['errors'])
    else:
        check(r['reset_after_initial']==0 and r['WM_control']==0 and r['WM_forwards']==0 and r['training_runs']==0,'reset/model execution counters changed')
    check((full.get('C_binding') or {}).get('candidate')=='heavy','bridge did not bind actual C')
    check((full.get('C_binding') or {}).get('actual_shared_world_and_queue') is True,'C did not share original world/queue')
    c=p['integrated_case'];g=layout(c);cross=[];min_base=1e9
    model=load_display_model(root/'review-state');display=mujoco.MjData(model)
    first_cross_time=next((x['time'] for x in ledger if x['event']=='bridge_actual_docked_and_stowed'),1e12)
    state_count=0
    for tick,time,state in state_records(root/'review-state'):
        mujoco.mj_setState(model,display,state,mujoco.mjtState.mjSTATE_INTEGRATION)
        mujoco.mj_forward(model,display);state_count+=1
        base=display.qpos[:3]
        if time>=first_cross_time and g['near_edge']<=base[0]<=g['far_front']:
            cross.append(dict(time_s=time,base_xyz_m=base.tolist()))
            min_base=min(min_base,float(base[2]))
            check(abs(base[1]-c['lane_y_m'])<c['bridge_width_m']/2-.15,'robot left bridge lane over gap')
            check(base[2]>.65,'robot traversed gap at lower-ground height instead of bridge deck')
    check(state_count==r['frames'],'complete world-state count mismatch')
    check(len(cross)>0,'no actual recorded robot traversal over the real gap')
    closure=r.get('private_failure_capsules') or {}
    check(closure.get('all_required_captures_complete') is True,'required exact failure capsule incomplete')
    for row in closure.get('files',[]):check(sha(root/'private-failure-capsules'/row['path'])==row['sha256'],'private capsule changed')
    result=dict(schema='continuous-full-integrated-course-independent-audit-v1',passed=not errors,errors=errors,
        root=str(root),case=c,report_sha256=sha(root/'report.json'),freeze_sha256=sha(root/'freeze.json'),
        native_completed_skills=successful,duplicate_summary_results_not_counted=duplicate_results,A_actual_abort=abort,actual_gap_crossing_samples=cross,
        min_recorded_base_height_over_gap_m=None if not cross else min_base,
        original_motor_and_visual_audit=data,raw_full_state_frames=state_count,
        full_endpoint=full.get('endpoint'),original_joint_excursions_retained=r.get('angle_violation_rad'),
        original_speed_exceeded_diagnostics_retained=r.get('speed_exceeded_physics_steps'),
        physical_steps_started_by_audit=0,recomputed_force_used_as_measured_support=False,
        engineering_task_acceptance=True,hardware_safety_certification=False)
    with Path(output).open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(passed=result['passed'],errors=errors,crossing_samples=len(cross),output=str(output))))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=audit(a.root,a.output);raise SystemExit(0 if r['passed'] else 2)
