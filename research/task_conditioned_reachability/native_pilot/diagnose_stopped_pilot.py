"""Read-only stopped-pilot evaluation and logged-cloud diagnosis. No FK/App/actor.

Counterfactual scalar calculations on recorded clouds are NOT unstarted E2/E3
physical outcomes. Ex-post pose errors are NOT predecision uncertainty bounds.
"""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from evaluate_pilot import summarize
from pose_tube_standoff import robust_request
from runtime_tip_envelope import choose_request,rotation


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def records(p):
    with p.open() as stream:return [json.loads(line) for line in stream]


def verify_raw(root, ledger, source):
    manifest=load(source/'manifest.json')
    if sha(source/'manifest.json') != ledger['source_manifest_sha256']:raise ValueError('Ledger/source manifest mismatch')
    for name,digest in manifest['files'].items():
        if sha(source/name)!=digest:raise ValueError('Frozen source changed: '+name)
    if sha(source/'box_approach_standoff.py')!=sha(Path(__file__).with_name('runtime_tip_envelope.py')):
        raise ValueError('Offline scalar replay differs from executed runtime math')
    for entry in ledger['entries']:
        out=root/'runs'/entry['output_name']
        for name,key in [('report.json','report_sha256'),('control.jsonl','control_sha256'),('entry_geometry.jsonl','geometry_sha256')]:
            if sha(out/name)!=entry[key]:raise ValueError('Raw terminal evidence hash mismatch: '+str(out/name))


def scalar_replay(q):
    points=np.array(q['tip_cloud_box_m']);ids=np.array(q['nominal_indices']);half=np.array(q['box_size_m'])/2
    output={}
    for arm in ('E0','E1','E2','E3'):
        shift,maximum,count=choose_request(points,ids,half,np.array(q['world_x_in_box']),.015+q['forecast_margin_m'],arm)
        output[arm]=dict(request_m=shift,maximum_x_m=maximum,selected_points=count)
    return dict(step=q['step'],time_s=q['time_s'],requests=output,
                scope='Counterfactual scalar replay at this logged query, NOT another physical episode or future outcome')


def planned_orientation_shadow(query, same_step_control):
    """Post-exposure candidate using an EXISTING same-query orientation target.

    Only point transforms; no FK, future cloud, learned parameters or source edit.
    It predicts a reference, not actual tracking or a prospective error bound.
    """
    if query['step'] != same_step_control['step'] or query['time_s'] != same_step_control['time_s']:
        raise ValueError('Orientation reference is not from the same query')
    target=np.asarray(same_step_control['stance_orientation_target'],dtype=float)
    current=np.asarray(query['root_quaternion_wxyz'],dtype=float)
    if target.shape!=(4,) or not np.isfinite(target).all() or abs(np.linalg.norm(target)-1)>1e-5:
        raise ValueError('Invalid recorded orientation target')
    rb=rotation(query['box_quaternion_wxyz']);rr=rotation(current/np.linalg.norm(current));rt=rotation(target/np.linalg.norm(target))
    root=np.asarray(query['root_position_w']);box=np.asarray(query['box_position_w']);translation=np.asarray(query['nominal_translation_w'])
    points=np.asarray(query['tip_cloud_box_m'])
    world=points@np.linalg.inv(rb.T).T+box
    root_local=(world-root-translation)@rr
    forecast=(root_local@rt.T+root+translation-box)@rb
    copy=dict(query,tip_cloud_box_m=forecast.tolist())
    requests=scalar_replay(copy)
    grids={}
    for arm,request in requests['requests'].items():
        eligible=next((j*.005 for j in range(9) if j*.005>=request['request_m']-1e-9),None)
        grids[arm]=dict(first_eligible_grid_m=eligible,
            requested_with_original_reserve_IF_first_grid_feasible_m=None if eligible is None else (0. if eligible==0 else min(.04,eligible+.005)),
            support_feasibility_evaluated=False)
    return dict(scope='Post-exposure candidate development shadow, NOT executed episode or forecast tracking guarantee',
        input_query_step=query['step'],input_control_step=same_step_control['step'],
        reference_quaternion_wxyz=same_step_control['stance_orientation_target'],
        used_future_measured_pose_or_cloud=False,new_FK_or_physics=False,
        candidate_requests=requests,conditional_grid_quantization=grids,
        pose_error_bound_status='UNKNOWN: no externally justified prospective tracking tube; do not treat reference as actual pose',
        runtime_control_authority=False)


def diagnose_cloud_change(forecast, measured):
    if forecast['nominal_indices']!=measured['nominal_indices'] or forecast['residual_corner_indices']!=measured['residual_corner_indices']:
        raise ValueError('Cannot match cloud sample identities')
    p=np.array(forecast['tip_cloud_box_m']);actual=np.array(measured['tip_cloud_box_m']);delta=actual-p
    half=np.array(measured['box_size_m'])/2;inflation=.015+measured['forecast_margin_m']
    valid=(np.abs(actual[:,1:])<=half[1:]+inflation).all(1)
    valid &= np.array(measured['nominal_indices'])==40
    selected=np.flatnonzero(valid)
    if not len(selected):raise ValueError('No endpoint witness in actual measured cloud')
    i=int(selected[np.argmax(actual[selected,0])]);fhalf=np.array(forecast['box_size_m'])/2
    f_inflation=.015+forecast['forecast_margin_m']
    eps=np.max(np.abs(delta),axis=0)
    # Reconstruct root-rotation effect using only stored point coordinates, no FK.
    rb0=rotation(forecast['box_quaternion_wxyz']);rb1=rotation(measured['box_quaternion_wxyz'])
    qr0=np.array(forecast['root_quaternion_wxyz']);qr1=np.array(measured['root_quaternion_wxyz'])
    r0=rotation(qr0/np.linalg.norm(qr0));r1=rotation(qr1/np.linalg.norm(qr1))
    root0=np.array(forecast['root_position_w']);root1=np.array(measured['root_position_w'])
    t=np.array(forecast['nominal_translation_w']);box0=np.array(forecast['box_position_w']);box1=np.array(measured['box_position_w'])
    predicted_world=p@np.linalg.inv(rb0.T).T+box0
    local=(predicted_world-root0-t)@r0
    reconstructed=(local@r1.T+root1-box1)@rb1
    residual=np.linalg.norm(reconstructed-actual,axis=1)
    rotation_only=(local@(r1-r0).T)@rb1
    origin_error=root1-(root0+t)
    rotation_angle=2*math.acos(min(1.,abs(float(np.dot(qr0,qr1)/(np.linalg.norm(qr0)*np.linalg.norm(qr1))))))
    bound=robust_request(p,half,forecast['world_x_in_box'],.015,eps.tolist())
    bound['usage']='EX_POST_DIAGNOSTIC_only; epsilon uses the observed final cloud and was NOT available as a justified planning bound'
    return dict(matched_cloud_point_count=len(p),observed_axiswise_displacement_m=eps.tolist(),
        observed_max_point_displacement_m=float(np.linalg.norm(delta,axis=1).max()),
        root_rotation_change_rad=rotation_angle,root_origin_forecast_error_w_m=origin_error.tolist(),
        rigid_pose_reconstruction_max_residual_m=float(residual.max()),
        rigid_root_rotation_component_axiswise_max_m=np.abs(rotation_only).max(0).tolist(),
        witness=dict(sample_index=i,phase=forecast['nominal_indices'][i],corner=forecast['residual_corner_indices'][i],
            forecast_point_box_m=p[i].tolist(),measured_point_box_m=actual[i].tolist(),difference_m=delta[i].tolist(),
            in_original_forecast_yz=bool((np.abs(p[i,1:])<=fhalf[1:]+f_inflation).all()),
            forecast_z_excess_outside_inflated_band_m=float(abs(p[i,2])-fhalf[2]-f_inflation),
            in_measured_yz=bool((np.abs(actual[i,1:])<=half[1:]+inflation).all())),
        ex_post_pose_tube_result=bound,
        limitation='Logged point transformation diagnosis, not new FK/physics or a prospective pose-tube guarantee')


def analyze(root):
    source=root/'revisions/sdk-report-r2/source';ledger=load(root/'physical_ledger.json');protocol=load(source/'protocol.json')
    verify_raw(root,ledger,source)
    reports={(e['seed'],e['arm']):load(root/'runs'/e['output_name']/'report.json') for e in ledger['entries']}
    primary=summarize(protocol,ledger,reports)
    q={};control={}
    for arm in ('E0','E1'):
        out=root/'runs'/('seed120401-'+arm)
        q[arm]=[r for r in records(out/'entry_geometry.jsonl') if r['event']=='finite_tip_query']
        control[arm]=records(out/'control.jsonl')
    n=min(len(rows) for rows in control.values())
    mismatches=[i for i in range(n) if control['E0'][i]!=control['E1'][i]]
    keys=['root_position_w','root_quaternion_wxyz','box_position_w','box_quaternion_wxyz','tip_cloud_box_m','nominal_indices',
          'residual_corner_indices','q_rad','dq_rad_s','nominal_translation_w','forecast_margin_m']
    matching_queries=len(q['E0'])==len(q['E1']) and all(all(a[k]==b[k] for k in keys) for a,b in zip(q['E0'],q['E1']))
    failed=reports[120401,'E1'];plan=failed['prospective_support_plan'];final=failed['measured_final_support_verification']
    return dict(schema='stopped-native-pilot-terminal-diagnosis-v1',source_manifest_sha256=ledger['source_manifest_sha256'],
        no_new_App_physics_actor_or_FK=True,raw_hashes_verified=True,primary_evaluation=primary,
        budget=dict(original_physical_allocation=16,starts=ledger['starts'],unspent_starts=16-ledger['starts'],
                    stopped_status=ledger['status'],active=ledger['active'],total_SDK_consumed=2,automatic_resume_authorized=False),
        observed_prefix=dict(compared_control_rows=n,last_step=control['E1'][n-1]['step'],
            last_sim_s=control['E1'][n-1]['time_s'],all_recorded_rows_value_equal=not mismatches,
            first_recorded_value_difference_row=None if not mismatches else mismatches[0],query_inputs_and_clouds_equal=matching_queries,
            scope='Equality of recorded values only; no assertion about unrecorded full world/hidden state'),
        forecast_then_measured=dict(initial_tip_request_m=plan['box_approach_preview']['minimum_shift_m'],initial_selected_support_shift_m=plan['shift_m'],
            final_tip_request_m=final['box_approach_preview']['minimum_shift_m'],final_support_only_shift_m=final['support_only_shift_m'],
            final_first_accepted_grid_m=final['checks'][0]['shift_m'],final_grid_plus_original_reserve_m=final['shift_m'],
            refusal_error=failed.get('error'),push_activated=any(e['event']=='push_activated' for e in failed['control_events']),
            classification='original final measured preview refusal surfaced as runtime_error; NOT observed invalid contact/effort failure'),
        counterfactual_scalar_queries=[scalar_replay(query) for query in q['E1']],
        cloud_change=diagnose_cloud_change(q['E1'][0],q['E1'][1]),
        planned_orientation_candidate=planned_orientation_shadow(q['E1'][0],next(row for row in control['E1'] if row['step']==q['E1'][0]['step'])),
        observed_single_seed_contrast=dict(seed=120401,E1_minus_E0_success=-1,scope='This observed pair only; not the registered four-seed mean or generalization'),
        conclusions=['E0 common-goal completion verified separately from native label',
            'E1 real failure remains in denominator; E2/E3 and other14 physical outcomes remain unknown',
            'One observed E0/E1 seed pair, but no complete registered four-seed ablation; no full-sample point rates or effect',
            'All active tip arms yield same request at these logged queries; no evidence that swept-retreat membership alone fixes pose evolution',
            'Do not tune original5mm margin from this known failure or erase/relabel/retry this source'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    value=analyze(args.root)
    with args.output.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':main()
