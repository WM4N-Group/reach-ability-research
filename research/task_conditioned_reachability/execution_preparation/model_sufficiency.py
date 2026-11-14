"""Four-level sufficiency analysis, not a producer or native controller.

Accepts WM candidate-source rows or explicitly mapped producer rows. Missing
rows stay missing. Extra raw means can establish action response but cannot
repair a model's missing successful-phase/state/uncertainty semantics.
"""
import math
from .native_climb_continuation import assess_climb_b,assess_later_B_HIGH,select_native_assessments

DISTANCES=(.2,.4,.6)


def finite(x):return type(x) in (float,int) and math.isfinite(x)


def interval(value):
    if type(value) not in (list,tuple) or len(value)!=2 or not all(finite(x) for x in value) or value[0]>value[1]:
        raise ValueError('Finite ordered interval required; std is not an interval')
    return list(map(float,value))


def scope_interval_diagnostic(bound,requirements):
    """Use legitimate MODEL intervals only; never a global physical cut.

    A failed direct CLIMB-B approach means registered NAV may be needed. A
    later-HIGH docking failure applies only to that fixed chain mode/phase.
    """
    base=dict(status='UNKNOWN',scope=None,exclude_PUSH_candidate=False,physical_exclusion=False)
    if not bound:return base
    if bound.get('kind') not in ('ANALYTIC_VALID_MODEL_INTERVAL','INDEPENDENT_VALIDATED_CURRENT_MODEL_BOUND'):
        return dict(base,reason='no_valid_interval_bound; hypothetical/std not promoted')
    if not bound.get('source_ref') or bound.get('phase') not in ('AFTER_FINISH','BEFORE_HIGH_ENTRY'):
        return dict(base,reason='missing_bound_source_or_phase')
    if bound.get('frame')!='WORLD_X_Y':return dict(base,reason='wrong_coordinate_frame')
    f=interval(bound['box_front_world_x_m'])
    if bound['phase']=='BEFORE_HIGH_ENTRY':
        H=bound['high_front_m'];L=bound['box_length_m'];tol=requirements['later_B_HIGH_docking_tolerance_m']
        if not all(finite(x) for x in (H,L)):raise ValueError('Bounded stage geometry required')
        gap=[H-f[1]-L,H-f[0]-L]
        separated=gap[1]<-tol or gap[0]>tol
        return dict(base,status='LATER_HIGH_MODE_NECESSARY_CONDITION_EXCLUDED_IN_MODEL' if separated else 'NOT_EXCLUDED',
                    scope='CLIMB_HIGH_FROM_B_AT_BOUND_PHASE_ONLY',gap_interval_m=gap,
                    source_ref=bound['source_ref'],exclude_fixed_HIGH_chain_mode_in_model=separated)
    xr=interval(bound['robot_x_world_m']);yr=interval(bound['robot_y_world_m']);lane=bound['lane_y_m']
    stand=requirements['approach_standoff_m']
    dx=[xr[0]-f[1]+stand,xr[1]-f[0]+stand];dy=[yr[0]-lane,yr[1]-lane]
    def nearest(v):return 0. if v[0]<=0<=v[1] else min(abs(x) for x in v)
    minimum=math.hypot(nearest(dx),nearest(dy))
    excluded=minimum>requirements['limits']['approach_radius_m']
    return dict(base,status='DIRECT_CLIMB_B_APPROACH_EXCLUDED_IN_MODEL' if excluded else 'NOT_EXCLUDED',
                scope='DIRECT_CLIMB_B_ONLY_NAV_REPAIR_NOT_EXCLUDED',minimum_approach_distance_m=minimum,
                source_ref=bound['source_ref'],registered_NAV_repair_possible='UNKNOWN')


def analyze(public,rows,requirements,*,allow_synthetic=False):
    if public['candidate_distances_m']!=list(DISTANCES):raise ValueError('Exact finite domain required')
    if len(rows)!=3 or sorted(r['push_distance_m'] for r in rows)!=list(DISTANCES):raise ValueError('Exactly 3 rows, explicit missing effects allowed')
    details=[];responses=[];qualified=[];cost_rows=[]
    for row in sorted(rows,key=lambda x:x['push_distance_m']):
        if row.get('executor_version')!=public.get('executor_version') or row.get('contract_version')!='0.1.1':raise ValueError('Same frozen executor/coordinate contract required')
        d=row['push_distance_m']
        if row.get('query_input_sha256')!=public['input_sha256'] or row.get('decision_id')!=public['decision_id']:
            raise ValueError('All alternatives share one immutable public query')
        if row.get('object_ref')!=public['object_ref'] or row.get('frame')!='WORLD_POSITIVE_X':raise ValueError('Object/frame mismatch')
        effect=row['effect'];value=effect.get('value');role=effect.get('source_role','RECORDED_CAUSAL_FORECAST')
        if role=='SYNTHETIC_TEST' and not allow_synthetic:raise ValueError('Synthetic producer fixture not a real output')
        if role not in ('RECORDED_CAUSAL_FORECAST','AUTHORIZED_CAUSAL_PRODUCER_OUTPUT','SYNTHETIC_TEST'):
            raise ValueError('Actual future/private evaluation cannot enter model analysis')
        known=type(value) is dict and bool(value)
        vector=value.get('motion_mean_anchor_body_m') if known else None
        raw_vector=type(vector) is list and len(vector)==6 and all(finite(x) for x in vector)
        if raw_vector:responses.append(dict(distance_m=d,mean=vector,elapsed_event_s=value.get('predicted_elapsed_s') if finite(value.get('predicted_elapsed_s')) else None))
        phase=effect.get('actual_predicted_endpoint_phase','UNKNOWN_SUCCESS_OR_FAILURE')
        eligible_success=effect.get('successful_after_Finish_state_qualified') is True
        model=row.get('prepared_successor_state_model')
        if model and model.get('eligible_in_declared_state_model') is True:qualified.append(d)
        cost=row.get('phase_cost',dict(status='UNKNOWN',total_s=None))
        cost_rows.append(dict(distance_m=d,prepared_successor_state_model=model,phase_cost=cost))
        bound=row.get('valid_model_bound')
        if bound and (bound.get('query_input_sha256')!=public['input_sha256'] or bound.get('distance_m')!=d):
            diagnostics=dict(status='UNKNOWN',reason='bound_query_action_identity_missing_or_mismatch',physical_exclusion=False)
        else:
            diagnostics=scope_interval_diagnostic(bound,requirements)
        nominal=None
        if known and finite(value.get('box_front_world_x_m')):
            nominal=assess_climb_b(dict(box_front_world_x_m=value['box_front_world_x_m'],
                robot_xy_world_m=value.get('robot_xy_world_m'),source_support_height_m=value.get('robot_support_height_m'),
                lane_y_m=public['public_reference']['lane_y_m'],phase=phase),requirements)
        details.append(dict(distance_m=d,requested_geometry=row.get('requested_goal_geometry'),
                            model_response_available=raw_vector,model_terminal_point=nominal,
                            terminal_phase=phase,successful_after_Finish_state_qualified=eligible_success,
                            uncertainty_bound_status='VALID_SUPPLIED_MODEL_INTERVAL' if (row.get('valid_model_bound') or {}).get('kind') in ('ANALYTIC_VALID_MODEL_INTERVAL','INDEPENDENT_VALIDATED_CURRENT_MODEL_BOUND') else 'UNKNOWN_NOT_STD',
                            necessary_interval_diagnostic=diagnostics,phase_cost=cost,
                            complete_exit_state_missing=not eligible_success,
                            actual_next_ready=None))
    reduced=select_native_assessments(cost_rows)
    pairwise=[]
    for i,a in enumerate(responses):
        for b in responses[i+1:]:
            delta=b['distance_m']-a['distance_m']
            pairwise.append(dict(from_distance_m=a['distance_m'],to_distance_m=b['distance_m'],
                raw_motion_mean_difference_m=[y-x for x,y in zip(a['mean'],b['mean'])],
                discrete_secant_m_per_m_NOT_continuous_gradient=[(y-x)/delta for x,y in zip(a['mean'],b['mean'])],
                native_terminal_event_time_difference_s=b['elapsed_event_s']-a['elapsed_event_s'] if a['elapsed_event_s'] is not None and b['elapsed_event_s'] is not None else None,
                time_difference_is_not_successful_completion_cost=True))
    all_raw=len(responses)==3
    stage_missing=[x['distance_m'] for x in details if not x['successful_after_Finish_state_qualified']]
    structural=[]
    if stage_missing:structural += ['unconditioned success-or-failure terminal outputs do not identify successful Finish state',
                                    'six translation means omit arm/posture/loads/common support and actual native witnesses']
    complete_time=[r['distance_m'] for r in cost_rows if r['phase_cost'].get('status')=='COMPLETE_DECLARED_PHASE_COST_MODEL_ONLY']
    if len(complete_time)<3:structural.append('terminal event time is not disjoint successful preparation/operation/successor cost')
    return dict(schema='reach-four-level-model-sufficiency-v1',query_input_sha256=public['input_sha256'],rows=details,
                levels=dict(model_response_comparison=dict(available_candidates=[r['distance_m'] for r in responses],
                              pairwise_comparison_possible=len(responses)>=2,all_three_available=all_raw,pairwise_numeric_response=pairwise),
                            necessary_condition_exclusion=dict(scoped_model_conclusions=[r['necessary_interval_diagnostic'] for r in details if 'EXCLUDED_IN_MODEL' in r['necessary_interval_diagnostic']['status']],
                                                              physical_PUSH_exclusions=[]),
                            successful_time_comparison=dict(available_candidates=complete_time,all_three_comparable=len(complete_time)==3),
                            executable_selection=dict(sufficient=False,nominal_model_best=reduced['best_candidate'],native_ready=None,dispatch=False)),
                cost_only_comparison=reduced['cost_only_diagnostic_best'],
                dominance_in_supplied_model_only=model_dominance(rows,public),
                structural_insufficiency=structural,
                more_same_kind_raw_forecasts_alone_can_fix_structure=False,
                next_required_capabilities=['success/stage-qualified exit state or an explicitly scoped nominal state model',
                    'nonoverlapping comparable successful cost or a different explicitly defined decision objective',
                    'independent native readiness/support validation at execution; model fields do not replace it'],
                hypothetical_results_are_not_calibrated=True,execution_authorized=False,
                result_role='SYNTHETIC_TEST' if allow_synthetic else 'CAUSAL_SOURCE_ANALYSIS_NOT_ACTUAL_OUTCOME')


def model_dominance(rows,public):
    """Strict upper(A)<lower(B), same explicitly feasible MODEL/success scope.

    The source must independently justify intervals; this routine never turns
    standard deviations or output labels into validated physical intervals.
    """
    eligible=[]
    for row in rows:
        e=row.get('dominance_evidence')
        if not e or e.get('kind') not in ('ANALYTIC_VALID_MODEL_INTERVAL','INDEPENDENT_VALIDATED_CURRENT_MODEL_BOUND'):continue
        if (e.get('query_input_sha256')!=public['input_sha256'] or e.get('distance_m')!=row['push_distance_m']
            or e.get('success_cost_scope')!='SUCCESSFUL_CURRENT_AND_SUCCESSOR_PREPARATION'
            or e.get('feasible_in_declared_model') is not True or not e.get('source_ref')
            or not e.get('same_constraint_scope_id')):continue
        c=interval(e['cost_s'])
        if c[0]<0:raise ValueError('Nonnegative seconds required')
        eligible.append((row['push_distance_m'],e,c))
    return [dict(dominating_distance_m=a,dominated_distance_m=b,scope=ea['same_constraint_scope_id'],
                 upper_a_s=ca[1],lower_b_s=cb[0],actual_physical_dominance=False)
            for a,ea,ca in eligible for b,eb,cb in eligible
            if a!=b and ea['same_constraint_scope_id']==eb['same_constraint_scope_id'] and ca[1]<cb[0]]


def declared_producer_sufficiency(metadata):
    """Analyze actual published capability declarations without loading a model."""
    mapping=metadata['input_mapping'];spec=mapping['output_spec']
    if metadata['contract_version']!='0.1.1' or metadata['executor_version']!='go2-piper-mission-v9-ae1c724-full4':
        raise ValueError('Incompatible real producer specification')
    return dict(schema='reach-producer-capability-sufficiency-v1',
                source_role='PUBLISHED_CAPABILITY_NOT_NEW_FORECAST',
                raw_motion_fields=spec['motion_fields'],
                substage_durations_available=spec['substage_durations_output'],
                native_next_ready_output=spec['next_ready_output'],
                calibrated_error_bound_available=spec['calibrated_error_bound_output'],
                standoff_action_channel=spec['standoff_action_channel'],
                declared_terminal=spec['intended_terminal'],
                action_response_diagnostic_potential=True,
                successful_stage_cost_supported=False,
                complete_exit_state_supported=False,
                three_extra_translation_rows_cannot_supply_missing_state_dimensions=True,
                no_need_to_wait_for_same_output_type_to_decide_structural_insufficiency=True,
                real_forward_executed=metadata['producer_state']['forward_executed'],
                nominal_decision_requires_more_than_raw_elapsed_and_mean=True)


def rows_from_raw_batch(public,source_rows,payload,*,allow_synthetic=False):
    """Explicit internal mapping for a pinned producer result, not a WM ABI fork.

    A caller verifies the actual artifact/adapter version before supplying this
    layout. World projection is NOT guessed from raw body-anchor translations;
    only the raw-response comparison level is enabled by the 6-vector.
    """
    if payload.get('query_input_sha256')!=public['input_sha256']:raise ValueError('Raw batch query mismatch')
    role=payload.get('source_role')
    if role=='SYNTHETIC_TEST' and not allow_synthetic:raise ValueError('Synthetic batch is not a real forward')
    if role not in ('SYNTHETIC_TEST','AUTHORIZED_CAUSAL_PRODUCER_OUTPUT'):raise ValueError('Unqualified batch role')
    if role!='SYNTHETIC_TEST' and payload.get('forward_executed') is not True:raise ValueError('No result before actual authorized execution')
    if payload.get('candidate_distances_m')!=list(DISTANCES):raise ValueError('Exact batch candidate identity required')
    means=payload['mean'];elapsed=payload['elapsed_s']
    if len(means)!=3 or len(elapsed)!=3 or any(len(v)!=6 or not all(finite(x) for x in v) for v in means):
        raise ValueError('Batch [3,6] motion and [3] clock arrays required')
    if not all(finite(t) and t>0 for t in elapsed):raise ValueError('Positive native-terminal-event times only')
    from copy import deepcopy
    rows=deepcopy(source_rows)
    for row,v,t in zip(rows,means,elapsed):
        row['effect']=dict(status='RAW_PRODUCER_OUTPUT_EXPLICIT_MAPPING',source_role=role,
            value=dict(motion_mean_anchor_body_m=v,predicted_elapsed_s=t),
            actual_predicted_endpoint_phase='UNKNOWN_SUCCESS_OR_FAILURE',
            successful_after_Finish_state_qualified=False)
    return rows
