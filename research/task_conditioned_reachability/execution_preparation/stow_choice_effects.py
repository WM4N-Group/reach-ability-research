"""Post-close, audit-only effects of the frozen v1 stow selector.

No planner/fit input or prediction. A chosen schedule is not an issued motor
command, measured completion saving, or a novel solver. Missing evidence stays
None; literal owner failures and original success flags are never relabelled.
"""
import math
import re
from .stow_path_choice import all_subsequences, path_sum, vector


def need(ok, message):
    if not ok: raise ValueError(message)


def finite(v):
    return type(v) in (int, float) and math.isfinite(v)


def close(a, b):
    return finite(a) and finite(b) and math.isclose(a, b, rel_tol=0., abs_tol=1e-9)


def audit_choice(value):
    """Recompute the SAME finite graph objective, never re-evaluate past guard."""
    if value.get('status') == 'GUARD_UNKNOWN_ORIGINAL_FOR_NATIVE_RECHECK':
        need(value.get('changed') is False, 'Unknown guard cannot change path')
        return dict(classification='GUARD_UNKNOWN_ORIGINAL_FOR_NATIVE_RECHECK', changed=False,
                    waypoint_count=None, expected_completed_waypoints=None, schedule_reduction_s=None,
                    novel_solver=False, native_geometry_rechecked=False)
    need(value.get('schema') == 'reach-native-terminal-preserving-stow-path-choice-v1', 'Frozen selector schema')
    rows=value['edge_witnesses'];need(rows, 'Complete nonempty DAG witness')
    n=max(e['target'] for e in rows)
    need(type(n) is int and 1 <= n <= 16, 'Bounded original domain')
    edges={}
    for e in rows:
        i,j=e['source'],e['target']
        need(type(i) is int and type(j) is int and 0 <= i < j <= n and (i,j) not in edges, 'Unique ordered graph edge')
        need(type(e['guard_pass']) is bool, 'Literal guard decision, not unknown')
        reasons=e['guard_reasons']
        need(isinstance(reasons,list) and all(type(r) is str and r for r in reasons), 'Explicit original guard reasons')
        need(e['guard_pass'] == (not reasons), 'Guard pass/reasons disagree')
        t=e['timing'];lo,nom,hi=(t[k] for k in ('lower_s','nominal_s','upper_s'))
        need(all(finite(x) for x in (lo,nom,hi)) and .6 <= lo <= nom <= hi, 'Ordered finite assigned timing only')
        need(t['source_reference_origin_tolerance_rad'] == (0. if i==0 else .002), 'Original origin tolerance')
        need(t.get('actual_completion_time_upper_s') is None, 'Do not substitute a measured completion guarantee')
        edges[i,j]=e
    need(set(edges)=={(i,j) for i in range(n) for j in range(i+1,n+1)}, 'Complete same-domain graph')
    need(value['finite_DAG_edges']==len(edges), 'Graph cardinality mismatch')
    original=tuple(range(n+1));chosen=tuple(value['chosen_path_indices'])
    need(all(type(i) is int for i in chosen) and chosen==tuple(sorted(set(chosen))) and
         chosen[0]==0 and chosen[-1]==n, 'Ordered terminal-preserving chosen path')
    eligible=[(path_sum(p,edges)['upper_s'],p) for p in all_subsequences(n) if path_sum(p,edges) is not None]
    optimum=min(eligible) if eligible else None
    need(type(value['guarded_candidate_found']) is bool and value['guarded_candidate_found'] == (optimum is not None), 'Graph feasibility claim mismatch')
    changed=chosen!=original
    need(value['changed'] is changed, 'Changed flag contradicts actual indices')
    selected=path_sum(chosen,edges)
    if optimum is None:
        need(not changed and value['chosen_reference_duration_interval_s'] is None, 'No route must retain original for native recheck')
    else:
        need(selected is not None and close(selected['upper_s'],optimum[0]), 'Chosen path is not same-domain optimum')
        need(all(close(selected[k],value['chosen_reference_duration_interval_s'][k]) for k in selected), 'Chosen interval mismatch')
    original_interval={k:sum(edges[i,i+1]['timing'][k] for i in range(n)) for k in ('lower_s','nominal_s','upper_s')}
    need(all(close(v,value['original_reference_duration_interval_s'][k]) for k,v in original_interval.items()), 'Original interval mismatch')
    ws=value['chosen_waypoints'];endpoint=vector(value['same_original_compact_endpoint'])
    need(len(ws)==len(chosen)-1 and vector(ws[-1])==endpoint, 'Materialized terminal/path length mismatch')
    direct=changed and chosen==(0,n)
    need(not changed or n>2 or direct, 'Two-waypoint domain cannot contain a third strategy')
    need(value['unchanged_original_final_verify_min_s']==4., 'Original final verification cannot be removed')
    need(value['actual_total_completion_cost_s'] is None and value['actual_successor_repair_cost_s'] is None,
         'Schedule evidence is not actual completion/successor prediction')
    return dict(classification=('DIRECT_BASELINE_EQUIVALENT' if direct else
                'INTERMEDIATE_ORIGINAL_SUBSEQUENCE' if changed else 'ORIGINAL_PATH_UNCHANGED'),
        changed=changed,waypoint_count=n,ordered_subsequence_count=2**(n-1),
        domain_contains_any_strategy_beyond_original_and_direct=n>2,
        expected_completed_waypoints=len(ws),schedule_reduction_s=(original_interval['upper_s']-selected['upper_s']
            if selected is not None and path_sum(original,edges) is not None else None),
        novel_solver=False,native_geometry_rechecked=False,
        actual_completion_or_successor_cost_inferred=False)


def _single_time(events, name):
    found=[e.get('time') for e in events if e.get('event')==name]
    if not found:return None
    need(len(found)==1 and finite(found[0]) and found[0]>=0, 'Unique finite original event: '+name)
    return found[0]


def _span(a,b):
    if a is None or b is None:return None
    need(a<=b, 'Ordered actual event clocks');return b-a


def audit_effect(raw_result, records):
    decisions=[r for r in records if r['payload'].get('event')=='reach_selected_ground_confirmed_stow_path_choice']
    need(len(decisions)<=1, 'Do not silently select one of multiple interventions')
    if 'stow_choice_records' in raw_result:
        need(raw_result['stow_choice_records']==[r['payload'] for r in decisions], 'Result/journal selector records disagree')
        need(raw_result.get('actual_selection_recorded') is bool(decisions), 'Result selection flag disagrees with journal')
        need(raw_result.get('actual_choice_changed') is any(r['payload'].get('changed') is True for r in decisions),
             'Result control-change flag disagrees with actual selector record')
    decision=decisions[0] if decisions else None
    choice=audit_choice(decision['payload']) if decision else None
    pushes=[r for r in raw_result.get('actual_native_results',[]) if r.get('skill')=='push' and
            isinstance(r.get('finish',{}).get('protected_stow'),dict)]
    need(len(pushes)<=1, 'Evaluator covers one selected ground PUSH, not arbitrary routes')
    stow=pushes[0]['finish']['protected_stow'] if pushes else None
    events=stow.get('events',[]) if stow else []
    capture=_single_time(events,'actual_unloaded_supported_retreat_and_full_path_checked')
    compact=_single_time(events,'actual_arm_compact_safe_pose_reached')
    terminal=_single_time(events,'failed_PUSH_stow_1s_plus3s_verified_NO_NAV')
    waypoints=[e for e in events if re.fullmatch(r'actual_safe_arm_waypoint_\d+',e.get('event',''))]
    indices=[int(e['event'].rsplit('_',1)[1]) for e in waypoints]
    need(indices==list(range(len(indices))), 'Original completed waypoint sequence inconsistent')
    verify=_span(compact,terminal)
    if verify is not None:need(verify>=4.-1e-8, 'Observed final verification shorter than original 4s')
    consumption=None
    if choice and choice['expected_completed_waypoints'] is not None and terminal is not None:
        consumption=choice['expected_completed_waypoints']==len(waypoints)
        need(consumption, 'Selected waypoint count does not match original terminal consumption events')
    times=[r['payload'].get('time_s') for r in records if r['payload'].get('event')=='placement_original_native_clock_confirmed']
    nn=times[0] if len(times)==1 and finite(times[0]) else None
    bindings=[r['payload'] for r in records if r['payload'].get('event')=='intent_native_execution_bound']
    climb=[b for b in bindings if b.get('native_option',{}).get('skill')=='CLIMB']
    climb_start=climb_end=None
    if len(climb)==1:
        receipts=[r['payload']['receipt'] for r in records if r['payload'].get('event')=='ainav_native_receipt' and
                  r['payload']['receipt']['option_sha256']==climb[0]['native_option_sha256']]
        starts=[r['time_s'] for r in receipts if r['status']=='started']
        ends=[r['time_s'] for r in receipts if r['status']=='succeeded']
        climb_start=starts[0] if len(starts)==1 else None;climb_end=ends[0] if len(ends)==1 else None
    selection_time=decision['payload'].get('time_s') if decision else None
    confirmations=[r for r in records if r['payload'].get('event')=='placement_original_native_clock_confirmed']
    if decision is not None and len(confirmations)==1:
        need(confirmations[0]['sequence']<decision['sequence'], 'Selector must follow original genuine NN confirmation')
    if selection_time is not None:
        need(finite(selection_time), 'Finite explicit selector time if supplied')
        if capture is not None:need(close(selection_time,capture), 'Selector and original same-update capture clock differ')
    status='NO_REACH_DECISION_OBSERVED' if decision is None else choice['classification']
    if decision is None and raw_result.get('passed') is False and raw_result.get('error')=='Selected ground placement owner/runtime identity mismatch':
        status='BINDING_IDENTITY_REFUSED_BEFORE_SELECTION'
    return dict(schema='reach-closed-stow-control-effect-v1',role='AUDIT_ONLY_NOT_PLANNER_INPUT_OR_FIT',
        scope_id=raw_result.get('scope_id'),program_sha256=raw_result.get('program_sha256'),selected_requests=raw_result.get('selected_requests'),
        owner_literal_task_passed=raw_result.get('passed'),choice=choice,
        owner_result_storage_closed=raw_result.get('episode_closure',{}).get('storage_complete'),
        owner_result_close_errors=raw_result.get('close_errors'),
        intervention_status=status,owner_literal_status=raw_result.get('status'),
        owner_error_class=raw_result.get('error_class'),owner_error=raw_result.get('error'),
        selector_journal_sequence=decision['sequence'] if decision else None,
        explicit_selector_time_s=selection_time,original_native_capture_boundary_s=capture,
        selector_same_update_boundary_inferred_from_pinned_call_order=decision is not None and capture is not None and selection_time is None,
        completed_original_waypoint_count=len(waypoints) if compact is not None else None,
        selected_count_matches_terminal_events=consumption,
        original_stow_verified_literal=stow.get('stow_verified') if stow else None,
        actual_costs_s=dict(capture_to_compact=_span(capture,compact),compact_verification=verify,
            capture_to_stow=_span(capture,terminal),NN_to_stow=_span(nn,terminal),
            stow_to_CLIMB_first_motor=_span(terminal,climb_start),stow_to_CLIMB_success=_span(terminal,climb_end),
            capture_to_CLIMB_success=_span(capture,climb_end)),
        claimed_schedule_saving_is_not_a_measured_task_saving=True,
        actual_command_array_prefix_or_full_native_safety_independently_audited=False,
        causal_task_benefit_proven=False,novel_algorithm_proven=False)


def compare_effects(baseline, candidate, *, prefix_match=None, source_delta_verified=None):
    """Descriptive deltas only until distinct scope, task, prefix AND source match.

    prefix_match must be normalized from owner array evidence bound to THESE
    two results by the calling pinned-file reader, not from earlier P1/P2 proof.
    """
    need((prefix_match is None or type(prefix_match) is bool) and
         (source_delta_verified is None or type(source_delta_verified) is bool), 'Explicit evidence state')
    same=baseline['selected_requests'] is not None and baseline['selected_requests']==candidate['selected_requests']
    distinct=baseline['scope_id'] is not None and candidate['scope_id'] is not None and baseline['scope_id']!=candidate['scope_id']
    both=baseline['owner_literal_task_passed'] is True and candidate['owner_literal_task_passed'] is True
    changed=candidate.get('choice') is not None and candidate['choice']['changed'] is True
    native_consumption=(candidate.get('selected_count_matches_terminal_events') is True and
        baseline.get('original_stow_verified_literal') is True and candidate.get('original_stow_verified_literal') is True and
        all(finite(r['actual_costs_s']['compact_verification']) and r['actual_costs_s']['compact_verification']>=4.-1e-8
            and r.get('owner_result_storage_closed') is True and r.get('owner_result_close_errors')==[]
            for r in (baseline,candidate)))
    comparable=same and distinct and both and changed and native_consumption and prefix_match is True and source_delta_verified is True
    deltas={}
    for k,a in baseline['actual_costs_s'].items():
        b=candidate['actual_costs_s'][k]
        deltas[k]=b-a if finite(a) and finite(b) and same and distinct else None
    total=-deltas['capture_to_CLIMB_success'] if comparable and deltas['capture_to_CLIMB_success'] is not None else None
    local=-deltas['capture_to_stow'] if comparable and deltas['capture_to_stow'] is not None else None
    penalty=deltas['stow_to_CLIMB_success'] if comparable else None
    if total is not None and local is not None and penalty is not None:
        need(close(total,local-penalty), 'Local and successor costs do not decompose to same total')
    return dict(same_requests=same,distinct_scope=distinct,both_literal_success=both,
        terminal_native_consumption_and_closed_storage_evidence=native_consumption,
        prefix_match=prefix_match,source_delta_verified=source_delta_verified,
        observed_candidate_minus_baseline_s=deltas,
        single_development_pair_attribution_eligible=comparable,
        successful_capture_to_CLIMB_reduction_s=total,
        attributed_local_capture_to_stow_reduction_s=local,
        attributed_successor_penalty_s=penalty,
        local_gain_erased_by_successor=(local>0 and total<=0 if local is not None and total is not None else None),
        novel_algorithm_proven=False,independent_generalization_proven=False,
        direct_baseline_equivalence=candidate.get('intervention_status')=='DIRECT_BASELINE_EQUIVALENT')


# Exact owner programs independently consumed in this worktree, not permits or
# a whitelist for arbitrary descendants. Other source pairs remain UNKNOWN.
REVIEWED_PROGRAM_PAIR=(
    'd149701b7d843e8dd7ea657cebd0ea7815b4548d7f1c0d09e3d950bf368c2dd6',
    'd7d42515dc564556ae54ba91551b76927ebb2766750b5aec2425a3dca3f341d7')


def compare_with_bound_prefix(baseline,candidate,prefix_receipt,*,source_pair_evidence=None):
    """Never reuse a true prefix result from P1/P2 for this new candidate."""
    need(prefix_receipt.get('schema')=='reach-owner-closed-stow-intervention-prefix-v1', 'Narrow recorded-array prefix receipt')
    for role,run in (('baseline',baseline),('candidate',candidate)):
        need(run.get('input_result_sha256') is not None and
             prefix_receipt.get(role+'_result_sha256')==run['input_result_sha256'], 'Prefix receipt belongs to a different result pair')
    matched=prefix_receipt.get('prefix_match')
    need(matched is None or type(matched) is bool, 'Unknown prefix is not pass')
    if matched is True:
        tick=prefix_receipt['capture_boundary_physics_tick']
        need(type(tick) is int and tick>0 and prefix_receipt['compared_common_physics_steps']>=tick,'Actual prefix through intervention')
        for i,run in enumerate((baseline,candidate)):
            capture=run['original_native_capture_boundary_s']
            need(close(prefix_receipt['original_capture_times_s'][i],capture) and
                 finite(capture) and abs(capture-tick*.005)<1e-7, 'Prefix intervention boundary differs from original report')
        need(prefix_receipt.get('same_requests') is True and prefix_receipt.get('same_numeric_model') is True,
             'Prefix pair task/model evidence missing')
        fields=('issued','delayed','q_before','dq_before','raw_torque','torque')
        need(set(prefix_receipt['bitwise_equal_through_capture_by_field'])==set(fields) and
             all(prefix_receipt['bitwise_equal_through_capture_by_field'][k] is True and
                 (prefix_receipt['first_bitwise_difference_tick'][k] is None or prefix_receipt['first_bitwise_difference_tick'][k]>tick)
                 for k in fields), 'Actual per-field prefix evidence inconsistent')
    source=None
    if source_pair_evidence is not None:
        if source_pair_evidence.get('source_pair_verified') is True:
            need(source_pair_evidence.get('schema')=='reach-exact-v2-declared-source-pair-qualification-v1', 'Explicit v2 declared-source qualification')
            for role,run in (('baseline',baseline),('candidate',candidate)):
                need(source_pair_evidence.get(role+'_result_sha256')==run.get('input_result_sha256') and
                     source_pair_evidence.get(role+'_program_sha256')==run.get('program_sha256'), 'Source evidence belongs to a different result/program pair')
            source=True
        else:
            need(source_pair_evidence.get('source_pair_verified') is False, 'Unknown source is not pass')
    elif (baseline.get('program_sha256'),candidate.get('program_sha256'))==REVIEWED_PROGRAM_PAIR:
        source=True  # Legacy exact v1 pair only; does not qualify any successor.
    result=compare_effects(baseline,candidate,prefix_match=matched,source_delta_verified=source)
    result['prefix_receipt_bound_to_exact_results']=True
    result['different_motor_commands_observed']=prefix_receipt.get('different_motor_commands_observed')
    result['source_program_pair_is_exact_independently_reviewed_pair']=source is True
    return result
