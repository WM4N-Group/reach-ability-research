"""OFFLINE repair-demand evidence without assuming a successful time model.

For a DECLARED CLIMB-B snapshot reference a and approach radius r, the distance
to the reference ball is max(0, ||p-a||-r). It is a lower bound on translation
TO THAT FROZEN REFERENCE SET, not a dynamic safety result or seconds estimate.
A box moving later changes the set; missing support/arm/native checks remain.
"""
import hashlib
import json
import math
from pathlib import Path
from .analysis_paths import resolve as analysis_path
from .native_climb_continuation import load_requirements
from .observed_handover_analysis import need,retrospective_compare


def finite(x):return type(x) in (int,float) and math.isfinite(x)


def distance_to_reference_ball(point_xy,reference_xy,radius_m):
    """Standard Euclidean geometry, not a source-binding or safety certificate."""
    need(type(point_xy) in (list,tuple) and len(point_xy)==2 and all(finite(x) for x in point_xy),'Finite measured point')
    need(type(reference_xy) in (list,tuple) and len(reference_xy)==2 and all(finite(x) for x in reference_xy),'Finite EXPLICIT reference point')
    need(finite(radius_m) and radius_m>=0,'Source gate radius required')
    distance=math.hypot(point_xy[0]-reference_xy[0],point_xy[1]-reference_xy[1])
    return max(0.,distance-radius_m)


def repair_snapshot(projection,*,observed_yaw_rad=None):
    if projection is None:
        return dict(status='UNKNOWN_MISSING_MEASURED_EXIT_GEOMETRY',translation_lower_bound_m=None,conditional_geometric_reference_lower_bound_m=None,
                    heading_correction_lower_bound_rad=None,seconds_lower_bound=None,
                    actual_next_ready=None,whole_candidate_infeasible=False,online_input_allowed=False)
    need(projection['role']=='OFFLINE_LABEL_PROJECTION_NOT_PREDICTION_OR_NATIVE_READY'
         and projection['phase']=='AFTER_NORMAL_FINISH','No prediction/PUSH-end/goal as measured exit')
    need(projection.get('source_state_sha256') and projection.get('sample_physical_tick') is not None,
         'Exact verified exit-state evidence required')
    distance=projection['measured_base_to_original_reference_m']
    req=load_requirements();radius=req['limits']['approach_radius_m']
    need(finite(distance) and distance>=0,'Finite measured snapshot distance required')
    # Reusing same source gate, not inventing a target offset or fitted threshold.
    lower=max(0.,distance-radius)
    correction=None
    if observed_yaw_rad is not None:
        need(finite(observed_yaw_rad),'Original world-yaw label in radians required')
        wrapped=math.atan2(math.sin(observed_yaw_rad),math.cos(observed_yaw_rad))
        correction=max(0.,abs(wrapped)-req['limits']['yaw_error_rad'])
    return dict(status='CONDITIONAL_GEOMETRIC_REFERENCE_ONLY_NATIVE_OPTION_GOAL_UNBOUND',
                source_state_sha256=projection['source_state_sha256'],sample_physical_tick=projection['sample_physical_tick'],
                original_reference_world_xy_m=projection['CLIMB_B_original_reference_world_xy_m'],
                snapshot_base_distance_m=distance,source_approach_radius_m=radius,
                translation_lower_bound_m=None,conditional_geometric_reference_lower_bound_m=lower,
                original_selected_CLIMB_goal_xy_available=False,
                native_reference_scope='NativeSceneFactory.native_entry_check reads selected option goal_world_x/y, NOT measured box front',
                heading_correction_lower_bound_rad=correction,
                source_yaw_gate_rad=req['limits']['yaw_error_rad'],
                lower_bound_scope='HYPOTHETICAL future replan from measured exit geometry; not the existing selected native option goal',
                later_box_motion_can_change_reference=True,seconds_lower_bound=None,
                missing_for_actual_preparation=['registered same-support NAV path','posture/arm/profile and common loaded source',
                                                'actual follow-up native entry/seam/Actor checks'],
                actual_next_ready=None,whole_candidate_infeasible=False,online_input_allowed=False,
                fit_norm_training_allowed=False,execution_authorized=False)


def supplement_from_verified_sidecar(observation,*,sidecar,sidecar_pins):
    """Optional same-event yaw only, after the original Data consumer succeeded.

    Rechecks caller-pinned original journal and the exact projection commitment;
    does not open old/private state elsewhere, or take a nearest phase sample.
    """
    projection=observation.get('observed_exit_projection_diagnostic')
    if projection is None:return repair_snapshot(None)
    sidecar=analysis_path(sidecar)
    for n,h in sidecar_pins.items():need(hashlib.sha256((sidecar/n).read_bytes()).hexdigest()==h,'Source sidecar changed')
    events=[json.loads(line) for line in (sidecar/'events.jsonl').read_text().splitlines()]
    exits=[e for e in events if e['kind']=='EXIT_GEOMETRY']
    need(len(exits)==1,'Exactly the source exit observation, not a favorable sampled peak')
    event=exits[0];p=event['payload']
    need(event['role']=='LABEL' and p['sample_physical_tick']==projection['sample_physical_tick']
         and p['private_state_evidence_sha256']==projection['source_state_sha256'],
         'Yaw and geometry must be the same verified exit tick/state')
    return repair_snapshot(projection,observed_yaw_rad=p['robot_yaw_rad'])


def repair_comparison(records,*,comparison_scope):
    """Same immutable records as time-reference comparison, but no time imputation.

    This can remain numerically informative when successor program-end is not
    recorded. It cannot establish a causal policy gain or full task ranking.
    """
    base=retrospective_compare(records,comparison_scope=comparison_scope)
    rows=[]
    for obs in records:
        repair=obs.get('exit_repair_snapshot')
        if repair is None:repair=repair_snapshot(obs.get('observed_exit_projection_diagnostic'))
        eligible=bool(obs['PUSH_and_normal_Finish_complete'] and repair['conditional_geometric_reference_lower_bound_m'] is not None)
        rows.append(dict(distance_m=obs['distance_m'],projection_evidence_available=eligible,
                         translation_lower_bound_m=obs.get('native_option_bound_repair',{}).get('translation_lower_bound_m'),
                         conditional_geometric_reference_lower_bound_m=repair['conditional_geometric_reference_lower_bound_m'] if eligible else None,
                         heading_correction_lower_bound_rad=repair['heading_correction_lower_bound_rad'] if eligible else None,
                         original_entry_check=obs['original_entry_check'],
                         original_categorical_check_details=obs.get('original_entry_check_feedback'),
                         successor_preparation_time_s=obs['receipt_to_successor_preparation_end_s'],
                         actual_next_ready=None,repair_scope=repair.get('lower_bound_scope')))
    available=[r for r in rows if r['projection_evidence_available']]
    min_row=min(available,key=lambda x:(x['conditional_geometric_reference_lower_bound_m'],x['distance_m'])) if available else None
    spread=max(r['conditional_geometric_reference_lower_bound_m'] for r in available)-min(r['conditional_geometric_reference_lower_bound_m'] for r in available) if len(available)>=2 else None
    native_bound=[r for r in rows if r['translation_lower_bound_m'] is not None]
    check_patterns=[dict(distance_m=r['distance_m'],**r['original_categorical_check_details']) for r in rows if r.get('original_categorical_check_details') and r['original_categorical_check_details'].get('status')=='ORIGINAL_NATIVE_CATEGORICAL_RESULT_NOT_FULL_READY']
    return dict(schema='reach-offline-necessary-repair-demand-comparison-v1',scope_basis=base['scope_basis'],
                role=base['result_role'],rows=rows,measured_repair_candidates=len(available),
                conditional_geometric_reference_demand_spread_m=spread,
                minimum_conditional_geometric_reference_demand=None if min_row is None else
                    dict(distance_m=min_row['distance_m'],conditional_lower_bound_m=min_row['conditional_geometric_reference_lower_bound_m']),
                full_success_cost_comparable=base['all_three_observed_complete_endpoints'],
                necessary_translation_not_sufficient_to_rank_total_cost=True,
                meters_and_radians_not_added_to_seconds=True,claim_of_causal_action_effect=False,
                original_check_patterns=check_patterns,
                check_pattern_scope='raw source check is measurable without goal XY; compare only same stage/profile, not full ready',
                native_option_bound_reference_candidates=len(native_bound),
                actual_selected_reference_repair_lower_bound=None if not native_bound else min(native_bound,key=lambda r:(r['translation_lower_bound_m'],r['distance_m'])),
                missing_for_actual_native_repair='original selected next-CLIMB option goal_world_xy joined to its actual option SHA',
                actual_next_ready=None,best_online_action=None,execution_authorized=False)


def repair_against_original_option(exit_payload,option_record,*,checked_option_sha256,purpose):
    """Actual selected-goal repair quantity when the ORIGINAL option is supplied.

    Execute only frozen BehaviorOption validation/digest, not its authority or
    dispatcher. Caller must join this option SHA to the original Data check and
    the exit-state evidence. Here bytes/identity are checked, not native safety.
    """
    need(purpose=='offline_dev_outcome_analysis','No future LABEL input to current planner')
    if option_record is None:
        return dict(status='UNKNOWN_MISSING_ORIGINAL_SELECTED_CLIMB_OPTION',translation_lower_bound_m=None,
                    actual_next_ready=None,execution_authorized=False)
    import ast
    import dataclasses
    from .recorded_v9_diagnostics import DOCS
    from .observed_handover_analysis import read_pinned
    manifest=read_pinned(DOCS/'skill_executor_manifest_v0.json','7b467daf8d6eb895bea48f5a68bb96693bc3a8426f8c3123ee8549193b59c1cb')
    # Owner already published the complete byte-exact source snapshot. No Git,
    # remote operation, authority constructor or runtime import in this API.
    # Locate only the explicit local source snapshot carried by completed A.
    release=read_pinned(DOCS/'common_v9_A_three_candidate_predictions_v4.json',
                        'dab33a0392aa369fa4fc167b5dc711f320464b07ccbbd7265b1ff4e810b80905')
    root=Path(release['source_qualification']['source_snapshot_root'])
    path=analysis_path(root/'mujoco_zyh/behavior_authority.py')
    need(path.is_file(),'Explicit published frozen source path required; no environment scan')
    raw=path.read_bytes();expected=manifest['source_manifest']['mujoco_zyh/behavior_authority.py']
    need(hashlib.sha256(raw).hexdigest()==expected,'Original BehaviorOption source drift')
    tree=ast.parse(raw)
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('digest','finite')]
    nodes += [n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BehaviorOption']
    skills=next(ast.literal_eval(n.value.args[0]) for n in tree.body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='SKILLS' for t in n.targets))
    ns=dict(__name__=__name__,dataclass=dataclasses.dataclass,asdict=dataclasses.asdict,
            math=math,hashlib=hashlib,json=json,SKILLS=frozenset(skills))
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(path)+'[immutable-option-only]','exec'),ns)
    cls=ns['BehaviorOption']
    need(set(option_record)=={f.name for f in dataclasses.fields(cls)},'Exact original serialized option, no omitted default/extra geometry fields')
    kwargs=dict(option_record);kwargs['parameters']=tuple(tuple(v) for v in kwargs['parameters'])
    original=cls(**kwargs)
    need(original.sha256==checked_option_sha256,'Selected goal must join the actual original next-option SHA, not a geometry substitute')
    need(original.skill=='CLIMB' and original.target_ref=='B' and not original.mandatory_protection,'Fixed original CLIMB B only')
    params=dict(original.parameters);goal=[params['goal_world_x_m'],params['goal_world_y_m']]
    need(abs(params['surface_height_m']-.2)<1e-7,'Original CLIMB B target layer')
    need(exit_payload['stage']=='AFTER_NORMAL_FINISH' and exit_payload['frame']=='WORLD_POSITIVE_X'
         and exit_payload['derived_from_requested_goal'] is False,'Same measured after-Finish LABEL state required')
    req=load_requirements();base=exit_payload['robot_base_world_xyz_m']
    need(type(base) in (list,tuple) and len(base)==3 and all(finite(v) for v in base),'Source actual exit base XYZ required')
    lower=distance_to_reference_ball(base[:2],goal,req['limits']['approach_radius_m'])
    return dict(status='SOURCE_OPTION_SHA_MATCHED_FIXED_REFERENCE_REPAIR_BOUND',original_next_option_sha256=original.sha256,
                actual_selected_goal_world_xy_m=goal,source_state_sha256=exit_payload['private_state_evidence_sha256'],
                sample_physical_tick=exit_payload['sample_physical_tick'],translation_lower_bound_m=lower,
                original_approach_radius_m=req['limits']['approach_radius_m'],
                bound_scope='translation to this immutable selected-goal ball; not path feasibility or readiness',
                seconds_lower_bound=None,actual_next_ready=None,online_input_allowed=False,execution_authorized=False)


def original_check_feedback(sidecar,sidecar_pins):
    """Keep original categorical check/reasons even without recorded goal XY.

    Already-verified sidecar only; this does not replace its verifier or grant
    Actor/source-support readiness. Check scope cannot be discarded in a table.
    """
    sidecar=analysis_path(sidecar)
    for n,h in sidecar_pins.items():need(hashlib.sha256((sidecar/n).read_bytes()).hexdigest()==h,'Original closed journal changed')
    events=[json.loads(line) for line in (sidecar/'events.jsonl').read_text().splitlines()]
    rows=[e for e in events if e['kind']=='NEXT_ENTRY_CHECK']
    if not rows:return dict(status='UNKNOWN_NO_ORIGINAL_ENTRY_CHECK',native_next_ready=None)
    need(len(rows)==1,'No picking the most favorable check from several stages')
    event=rows[0];p=event['payload']
    need(event['role']=='LABEL' and p['source_type']=='ORIGINAL_NATIVE_ENTRY_RECHECK'
         and p['skill']=='CLIMB' and p['object_ref']=='B','Original same-successor check only')
    need(type(p['ready']) is bool and type(p['reasons']) is list and (not p['reasons'] if p['ready'] else bool(p['reasons'])), 'Literal original check result/reasons')
    need(p['checked_physical_tick']==event['physical_tick'] and p['final_native_Actor_gate_passed'] is False,'Keep original time/scope, not Actor permission')
    return dict(status='ORIGINAL_NATIVE_CATEGORICAL_RESULT_NOT_FULL_READY',
                check_scope=p['check_scope'],ready=p['ready'],reasons=p['reasons'],entry_profile=p['entry_profile'],
                checked_time_s=event['time_s'],checked_physical_tick=p['checked_physical_tick'],
                next_option_sha256=p['original_next_option_sha256'],source_sha256=event['source_sha256'],
                selected_goal_world_xy=None,full_next_ready=None,native_next_ready=None)
