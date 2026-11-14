"""Source-bound necessary CLIMB conditions and phase-aware selector adaptation.

PUSH B -> CLIMB B (GROUND -> B) differs from the LATER B -> HIGH seam.
No private native geometry is read; no model/actor/runtime loaded. Point-model
checks never become native readiness, repair infeasibility, or dispatch rights.
"""
import ast
import hashlib
import importlib.util
import sys
from .analysis_paths import resolve as analysis_path
import json
import math
from pathlib import Path
from .discrete_selection import COST_TERMS

DOCS=Path('/home/yuanyue/re-nav/GO2-PIPER/docs')
MANIFEST_SHA='7b467daf8d6eb895bea48f5a68bb96693bc3a8426f8c3123ee8549193b59c1cb'
CONTRACT_SHA='d5cd295c2bc3f2372f459152fc19e345ea001cf50fbb500471825628f48dd0d5'


def read_pinned(path,sha):
    path=analysis_path(path);raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('Requirement source changed; do not silently change thresholds')
    return raw.decode()


def assigned_dict(text,name):
    for node in ast.walk(ast.parse(text)):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
            if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='dict':
                return {kw.arg:ast.literal_eval(kw.value) for kw in node.value.keywords}
            return ast.literal_eval(node.value)
    raise ValueError('Required source assignment missing: '+name)


def policy_scalar(text,name):
    for node in ast.walk(ast.parse(text)):
        if isinstance(node,ast.keyword) and node.arg==name:return ast.literal_eval(node.value)
    raise ValueError('Required native policy scalar missing')


def load_requirements():
    manifest=json.loads(read_pinned(DOCS/'skill_executor_manifest_v0.json',MANIFEST_SHA))
    contract=json.loads(read_pinned(DOCS/'skill_interface_contract_v0_1_1.json',CONTRACT_SHA))
    selected={};refs={}
    for name in ('mujoco_zyh/skill_execution_judge.py','mujoco_zyh/judged_scene_options.py',
                 'mujoco_zyh/native_climb_support_seam.py','mujoco_zyh/integrated_course.py'):
        ref=manifest['frozen_source_excerpts'][name]
        selected[name]=read_pinned(ref['path'],ref['sha256']);refs[name]=ref
    limits=assigned_dict(selected['mujoco_zyh/skill_execution_judge.py'],'NATIVE_LIMITS')
    # Read the original CLIMB catalogue tuple, not a second manually tuned goal.
    catalogue=ast.parse(selected['mujoco_zyh/judged_scene_options.py']);found=None
    for node in ast.walk(catalogue):
        if isinstance(node,ast.For) and isinstance(node.target,ast.Tuple):
            names=[n.id for n in node.target.elts if isinstance(n,ast.Name)]
            if names==['target','base','height','front','stand']:
                for item in node.iter.elts:
                    if ast.literal_eval(item.elts[0])=='B':
                        found=[ast.literal_eval(item.elts[i]) for i in (1,2,4)]
    if found is None:raise ValueError('Source-bound CLIMB B catalogue missing')
    source_height,target_height,stand=found
    seam=selected['mujoco_zyh/native_climb_support_seam.py']
    return dict(schema='reach-native-climb-requirements-v1',executor_version=manifest['executor_version'],
                contract_version=contract['contract_version'],axis='WORLD_X_Y_Z',
                immediate_successor='CLIMB:B',source_support='GROUND',source_height_m=source_height,
                target_height_m=target_height,approach_standoff_m=stand,
                limits=limits,public_source_height_tolerance_m=.05,
                qualified_rise_m=.2,source_loaded_force_strict_gt_N=policy_scalar(seam,'all_four_source_loads_gt_n'),
                later_B_HIGH_docking_tolerance_m=policy_scalar(seam,'original_Terrain_push_ready_dock_tolerance_m'),
                source_refs=refs,source_contract_sha256=CONTRACT_SHA,
                source_ground_does_not_require_B_HIGH_docking=True,
                free_exit_separation_threshold_m=None,
                pending_native_checks=['four loaded top-face contacts on one registered source support',
                                       'actual geometry/compiled foot radii and original source seam check',
                                       'same-world owner/compact profile or original arm gate',
                                       'original ClimbEntry and final Machine Actor gate',
                                       'fresh option/time bound categorical receipt'],
                native_next_ready=None,execution_authorized=False)


def valid(x):return type(x) in (int,float) and math.isfinite(x)


def check(margin,*,strict=False):
    if margin is None:return dict(margin=None,status='UNKNOWN',strict=strict)
    if not valid(margin):raise ValueError('Nonfinite necessary margin')
    return dict(margin=margin,status='PASS_NOMINAL_NECESSARY' if (margin>0 if strict else margin>=0) else 'FAIL_DIRECT_NOMINAL_NECESSARY',strict=strict)


def assess_climb_b(state,requirements):
    """Evaluate supplied nominal state only, at its exact declared phase.

    These are original entry/preparation gate ingredients, not new skill
    thresholds. A direct approach failure can be repaired by registered NAV;
    it is not proof the whole candidate is infeasible.
    """
    L=requirements['limits'];front=state.get('box_front_world_x_m');xy=state.get('robot_xy_world_m')
    lane=state.get('lane_y_m');approach=None;distance=None
    if valid(front) and valid(lane):approach=[front-requirements['approach_standoff_m'],lane]
    if approach is not None and type(xy) in (list,tuple) and len(xy)==2 and all(valid(v) for v in xy):
        distance=math.hypot(xy[0]-approach[0],xy[1]-approach[1])
    rows=dict(approach_radius_m=check(None if distance is None else L['approach_radius_m']-distance))
    numeric=(('yaw_rad','yaw_error_rad','heading_error_rad'),('linear_speed_m_s','linear_speed_m_s','linear_speed_m_s'),
             ('tilt_rad','tilt_rad','tilt_rad'))
    for key,limit,field in numeric:
        value=state.get(field)
        # heading input is already wrapped to [-pi, pi], never blend degrees.
        rows[key]=check(None if not valid(value) else L[limit]-abs(value))
    height=state.get('source_support_height_m')
    rows['source_height_m']=check(None if not valid(height) else requirements['public_source_height_tolerance_m']-abs(height-requirements['source_height_m']))
    loads=state.get('model_source_normal_loads_N')
    rows['four_source_loads_N']=check(None if type(loads) not in (list,tuple) or len(loads)!=4 or not all(valid(v) for v in loads)
                                     else min(loads)-requirements['source_loaded_force_strict_gt_N'],strict=True)
    arm=state.get('max_absolute_arm_q_rad')
    rows['original_zero_arm_profile_rad']=check(None if not valid(arm) else L['arm_absolute_rad']-arm)
    # Loaded values/pose alone do not prove common TOP support or valid owner.
    top=state.get('model_common_loaded_top_ground_support')
    rows['common_top_ground_support']=check(None if type(top) is not bool else (1. if top else -1.))
    missing=[name for name,row in rows.items() if row['status']=='UNKNOWN']
    phase_matched=state.get('phase')=='AFTER_REGISTERED_SUCCESSOR_PREPARATION_BEFORE_CLIMB_ENTRY_CHECK'
    return dict(immediate_successor='CLIMB:B',source_support='GROUND',nominal_approach_world_xy_m=approach,
                nominal_distance_to_approach_m=distance,necessary_margins=rows,
                input_phase=state.get('phase'),phase_matched_for_entry=phase_matched,
                future_gate_values_missing=missing,
                eligible_in_declared_state_model=bool(phase_matched and not missing and all(row['status']=='PASS_NOMINAL_NECESSARY' for row in rows.values())),
                direct_handover_needs_NAV_preparation_if_this_point_were_Finish_state=(distance>L['approach_radius_m']) if distance is not None else None,
                arm_branch='ORIGINAL_ZERO_ARM_OR_SEPARATELY_VERIFIED_COMPACT_MACRO_NOT_POSE_ONLY',
                original_ClimbEntry_and_Actor_gate_still_required=True,
                B_HIGH_docking_required_for_this_immediate_successor=False,
                whole_candidate_infeasible=False,actual_next_ready=None,native_entry_ready=None,
                full_chain_feasibility_proven=False,execution_authorized=False)


def assess_later_B_HIGH(front,length,high_front,requirements):
    if not all(valid(v) for v in (front,length,high_front)):return dict(status='UNKNOWN',gap_m=None)
    gap=high_front-(front+length);tol=requirements['later_B_HIGH_docking_tolerance_m']
    return dict(requirement_scope='LATER_CLIMB:HIGH_FROM_LOADED_B_NOT_IMMEDIATE_CLIMB:B',
                gap_m=gap,symmetric_docking_margin_m=tol-abs(gap),
                status='PASS_POINT_GEOMETRY_ONLY' if abs(gap)<=tol else 'FAIL_POINT_GEOMETRY_ONLY',
                actual_source_support_polygon_and_foot_radius_still_required=True,
                inference_is_not_actual_rejection=True,actual_next_ready=None)


STAGE_BOUNDARIES={
    COST_TERMS[0]:('QUERY','PUSH_NATIVE_ACTIVATION'),
    COST_TERMS[1]:('PUSH_NATIVE_ACTIVATION','PUSH_NATIVE_SUCCEEDED_AFTER_FINISH'),
    COST_TERMS[2]:('PUSH_NATIVE_SUCCEEDED_AFTER_FINISH','CLIMB_FIRST_ACTOR_ACTIVATION'),
}


def phase_cost(segments,*,observation_ref,distance,allow_synthetic=False):
    """Disjoint event coverage; a proven QUERY->PUSH-success span may be combined.

    Unknown option-purpose endpoints are never relabeled. A combined span and
    one of its subspans cannot both enter the sum. Partial source information
    remains visible without supplying a fake total or zero missing duration.
    """
    result=dict(status='UNKNOWN',total_s=None,partial_model_cost_s=None,
                reason=None,native_elapsed_inferred=False,
                covered_terms=[],missing_terms=list(COST_TERMS))
    if not segments:return dict(result,reason='missing_phase_aligned_seconds')
    allowed=dict(STAGE_BOUNDARIES)
    allowed['current_preparation_and_push_including_original_Finish']=('QUERY','PUSH_NATIVE_SUCCEEDED_AFTER_FINISH')
    positions={'QUERY':0,'PUSH_NATIVE_ACTIVATION':1,'PUSH_NATIVE_SUCCEEDED_AFTER_FINISH':2,'CLIMB_FIRST_ACTOR_ACTIVATION':3}
    origins=set();covered=set();total=0.;names=set()
    for row in segments:
        name=row.get('name')
        if name not in allowed or name in names:
            return dict(result,reason='nonoverlapping_known_terms_required_no_extra_Finish')
        names.add(name)
        if row.get('observation_ref')!=observation_ref or row.get('distance_m')!=distance:
            return dict(result,reason='candidate_observation_mismatch')
        if row.get('source_role')=='synthetic_test' and not allow_synthetic:
            return dict(result,reason='synthetic_not_allowed')
        if row.get('source_role') not in ('nominal_phase_model','causal_phase_prediction','synthetic_test'):
            return dict(result,reason='actual_audit_or_unknown_role_not_current_cost')
        ends=(row.get('start_event'),row.get('end_event'))
        if ends!=allowed[name]:
            return dict(result,reason='stage_scope_mismatch_do_not_duplicate_preparation_or_Finish')
        if not valid(row.get('duration_s')) or row['duration_s']<0:
            return dict(result,reason='missing_or_invalid_duration_not_zero')
        origin=row.get('clock_origin_id')
        if not isinstance(origin,str) or not origin:return dict(result,reason='clock_origin_missing')
        origins.add(origin)
        span=set(range(positions[ends[0]],positions[ends[1]]))
        if covered & span:return dict(result,reason='overlapping_intervals_duplicate_preparation_or_Finish')
        covered |= span;total+=row['duration_s']
    if len(origins)!=1:return dict(result,reason='incompatible_clock_origins')
    if not math.isfinite(total):return dict(result,reason='cost_overflow')
    fields=dict(partial_model_cost_s=total,covered_terms=[COST_TERMS[i] for i in sorted(covered)],
                missing_terms=[COST_TERMS[i] for i in range(3) if i not in covered])
    if covered!=set(range(3)):return dict(result,**fields,reason='phase_coverage_incomplete_total_unknown')
    return dict(result,**fields,status='COMPLETE_DECLARED_PHASE_COST_MODEL_ONLY',total_s=total,
                reason='not_actual_time_or_safety_certificate')


def adapt_recorded_rows(public_problem,source_rows,requirements):
    """Real published values only. No fake exit separation/foot loads/costs.

    Source rows already verified by the pinned owner adapter. Keep goal design,
    unaligned forecast diagnostic and actual native readiness separate.
    """
    lane=public_problem['public_reference']['lane_y_m'];length=public_problem['object_geometry']['length_m']
    rows=[]
    for source in source_rows:
        goal=source['requested_goal_geometry'];front=goal['requested_front_world_x_m']
        request_assessment=assess_climb_b(dict(box_front_world_x_m=front,lane_y_m=lane,
                                             phase='REQUEST_GEOMETRY_ONLY_NOT_AFTER_FINISH'),requirements)
        forecast=source['effect'];model=None
        if forecast['status']=='RECORDED_CAUSAL_FORECAST_EXACT_QUERY_ONLY':
            value=forecast['value']
            model=assess_climb_b(dict(box_front_world_x_m=value['box_front_world_x_m'],
                                      robot_xy_world_m=value['robot_xy_world_m'],lane_y_m=lane,
                                      source_support_height_m=value['robot_support_height_m'],
                                      phase='OPTION_PURPOSE_TERMINAL_UNALIGNED_TO_FINISH'),requirements)
            model['later_HIGH_point_diagnostic']=assess_later_B_HIGH(value['box_front_world_x_m'],length,goal['receiving_front_world_x_m'],requirements)
            model['predicted_elapsed_s_not_used_as_native_cost']=value['predicted_elapsed_s']
        rows.append(dict(distance_m=source['push_distance_m'],frame='WORLD_POSITIVE_X',
                         immediate_requested_CLIMB_B=request_assessment,
                         later_requested_B_HIGH=assess_later_B_HIGH(front,length,goal['receiving_front_world_x_m'],requirements),
                         recorded_model_diagnostic=model,
                         phase_cost=phase_cost([],observation_ref=public_problem['input_sha256'],distance=source['push_distance_m']),
                         selector_eligible=False,selector_missing=['phase-aligned exit robot/box state and entry conditions',
                                                                  'current/operation/successor phase cost',
                                                                  'fresh native entry and support witness'],
                         native_next_ready=None,actual_candidate_excluded=False))
    reduced=select_native_assessments(rows)
    return dict(schema='reach-native-climb-selector-adaptation-v1',public_problem_id=public_problem['decision_id'],
                input_sha256=public_problem['input_sha256'],immediate_successor='CLIMB:B',
                later_chain_requirement_separate='CLIMB:HIGH only after B has become loaded source',
                rows=rows,selection_status=reduced['selection_status'],best_candidate=reduced['best_candidate'],
                real_physical_exclusions=[],certified_dominance=[],execution_authorized=False,
                arbitrary_overlap_or_exit_separation_not_injected=True)


def select_native_assessments(rows):
    """Finite numeric reduction of stage-qualified necessary-state models.

    No private gate is invoked and no physical permission follows. Incomplete
    native ingredients never get a default zero or a default eligible flag.
    """
    if sorted(row['distance_m'] for row in rows)!=[.2,.4,.6]:
        raise ValueError('Exactly the three exposed candidates, no interpolation')
    eligible=[];cost_only=[]
    for row in rows:
        assessment=row.get('prepared_successor_state_model')
        cost=row.get('phase_cost',{})
        if cost.get('status')=='COMPLETE_DECLARED_PHASE_COST_MODEL_ONLY' and valid(cost.get('total_s')):
            cost_only.append(dict(distance_m=row['distance_m'],total_model_cost_s=cost['total_s']))
        if (assessment and assessment.get('eligible_in_declared_state_model') is True
            and cost.get('status')=='COMPLETE_DECLARED_PHASE_COST_MODEL_ONLY'
            and valid(cost.get('total_s'))):
            eligible.append(dict(distance_m=row['distance_m'],total_model_cost_s=cost['total_s']))
    best=min(eligible,key=lambda row:(row['total_model_cost_s'],row['distance_m'])) if eligible else None
    return dict(selection_status=('BEST_OF_THREE_DECLARED_NECESSARY_STATE_MODELS' if len(eligible)==3 else
                                  'BEST_OF_EVALUATED_SUBSET_DECLARED_NECESSARY_STATE_MODELS') if best else 'UNKNOWN',
                best_candidate=best,qualifying_candidates=len(eligible),
                cost_only_diagnostic_best=min(cost_only,key=lambda row:(row['total_model_cost_s'],row['distance_m'])) if cost_only else None,
                cost_only_diagnostic_scope='not_a_feasible_candidate_or_native_proposal',
                actual_next_ready=None,execution_authorized=False,global_physical_infeasible=False)


WM_PHASE_V2_SHA='3c09694b512a316510fd9cad00626a9ff6984d51370ca3a24f1ea2c8c15e51fd'
WM_PHASE_ADAPTER_SHA='ad698d3d17b3e5adf4dfec239becbf4eefb084ae28d942a542882ee88987a132'


def consume_wm_phase_v2(public_problem,source_rows):
    """Use owner time semantics and owner cost-admissibility; never its actual ledger."""
    path=DOCS/'common_v9_effect_phase_time_contract_v2.json'
    contract=json.loads(read_pinned(path,WM_PHASE_V2_SHA))
    span=contract['recorded_forecast_event_clock']
    recorded=next(row for row in source_rows if row['push_distance_m']==.6)
    if (contract['schema']!='common-v9-effect-phase-time-contract-v2' or
        contract['skill_contract_version']!='0.1.1' or
        span['query_id']!=public_problem['decision_id'] or
        span['query_input_sha256']!=public_problem['input_sha256'] or
        span['source_forecast_sha256']!=recorded['effect']['source_forecast_sha256']):
        raise ValueError('Owner stage clock cannot transfer to another query/candidate')
    if span['start_event']!='CURRENT_PREDICTION_QUERY' or span['intended_end_event']!='NATIVE_OPTION_TERMINAL_EVENT_SUCCESS_OR_FAILURE':
        raise ValueError('Changed original model event semantics')
    if abs(span['start_time_s']-public_problem['query_time_s'])>1e-9:
        raise ValueError('Image clock is not prediction-query time origin')
    ref=contract['adapter'];code=Path(ref['path'])
    read_pinned(code,WM_PHASE_ADAPTER_SHA)
    scripts=code.parent.parent;old_path=sys.path[:]
    try:
        sys.path.insert(0,str(scripts))
        spec=importlib.util.spec_from_file_location('reach_owner_phase_clock_v2',code)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        admissibility=module.cost_admissibility(span)
    finally:
        sys.path[:]=old_path
    # No offline_phase_ledger, actual timings, new model or terminal logit invoked.
    return dict(source_contract_path=str(path),source_contract_sha256=WM_PHASE_V2_SHA,
                recorded_event_span=span,owner_cost_admissibility=admissibility,
                mapping_to_selector_success_cost=None,successful_phase_total_s=None,
                terminal_success_condition_unknown=True,actual_Finish_state_not_inferred=True,
                actual_outcome_ledger_opened=False,execution_authorized=False)
