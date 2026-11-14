"""Task-conditioned cost accounting from ONE owner-published AINav index.

Historical EVIDENCE-only: no replay, planner input, fit, missing-label creation,
or causal action comparison. Native started != semantic query or Actor start.
"""
import math


def need(value, message):
    if not value:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def span(start, end):
    need(start is None or (finite(start) and start >= 0), 'Finite original start if supplied')
    need(end is None or (finite(end) and end >= 0), 'Finite original end if supplied')
    if start is None or end is None:
        return None
    need(start <= end, 'Ordered finite original native clock')
    return end-start


def summarize(index, *, selected_manifest_sha256, allow_unverified_source=False):
    need(index.get('schema') == 'Data-AINav-intent-native-evidence-index-v1'
         and index.get('role') == 'EVIDENCE_NOT_PLANNER_INPUT', 'Original evidence index, not forecasts')
    need(type(allow_unverified_source) is bool, 'Explicit diagnostic source mode')
    recorded_source = index.get('historical_source_manifest_sha256', index.get('source_manifest_sha256'))
    source_matches = recorded_source == selected_manifest_sha256
    need(source_matches or (recorded_source is None and allow_unverified_source),
         'Same selected source version, or explicitly UNKNOWN diagnostic; known version mismatch rejected')
    need(type(index.get('decisions')) is list, 'Explicit original decision list')
    rows = []; decisions = []; seen = set(); intervals = []
    for i, decision in enumerate(index['decisions']):
        executions = decision['native_executions']; own = []
        for j, e in enumerate(executions):
            ident = e['native_option_sha256']
            need(ident not in seen, 'No duplicate native option/double accounting'); seen.add(ident)
            start=e['first_started_time_s']; end=e['literal_terminal_time_s']
            elapsed=span(start,end)
            role=e['execution_role']; need(role in ('preparation','interaction'), 'Original execution role')
            status=e['literal_terminal_status']
            need(status in (None,'succeeded','failed','protected_exit_complete'), 'Keep original terminal namespace')
            literal=[r['status'] for r in e['receipts']]
            if elapsed is not None: intervals.append((start,end,ident))
            row=dict(decision_order=i+1, execution_in_decision=j+1,
                     semantic_intent_sha256=decision['intent_sha256'],
                     semantic_skill=decision['selected_intent']['skill'],
                     semantic_target=decision['selected_intent']['target_ref'],
                     public_intent_parameters=decision['selected_intent']['parameters'],
                     native_option_sha256=ident, native_skill=e['native_option']['skill'],
                     role=role, native_started_s=start,native_terminal_s=end,
                     literal_terminal_status=status, literal_receipt_statuses=literal,
                     observed_native_window_s=elapsed,
                     successful_native_window_s=elapsed if status=='succeeded' else None,
                     execution_evidence=e['execution_evidence'],
                     independently_observed_Finish_s=None, independently_observed_stow_s=None,
                     Actor_activation_time_s=None, query_start_s=None)
            rows.append(row); own.append(row)
        known=[r['observed_native_window_s'] for r in own if r['observed_native_window_s'] is not None]
        decisions.append(dict(order=i+1,semantic_skill=decision['selected_intent']['skill'],
            semantic_target=decision['selected_intent']['target_ref'],
            semantic_intent_sha256=decision['intent_sha256'],native_options=len(own),
            known_native_window_sum_s=sum(known),known_native_window_sum_complete=len(known)==len(own),
            known_preparation_native_window_sum_s=sum(r['observed_native_window_s'] for r in own if r['role']=='preparation' and r['observed_native_window_s'] is not None),
            preparation_native_window_coverage_complete_for_bound_options=all(r['observed_native_window_s'] is not None for r in own if r['role']=='preparation'),
            query_to_intent_completion_s=None,query_start_s=None))
    sorted_windows=sorted(intervals)
    for a,b in zip(sorted_windows,sorted_windows[1:]):
        need(a[1] <= b[0], 'Overlapping native windows; cannot sum as disjoint')
    complete=len(intervals)==len(rows)
    known_sum=sum(end-start for start,end,_ in intervals)
    prep_known=sum(r['observed_native_window_s'] for r in rows if r['role']=='preparation' and r['observed_native_window_s'] is not None)
    interaction_known=sum(r['observed_native_window_s'] for r in rows if r['role']=='interaction' and r['observed_native_window_s'] is not None)
    chains=[]
    for i,decision in enumerate(index['decisions'][:-1]):
        if decision['selected_intent']['skill']!='PUSH': continue
        current=[r for r in rows if r['decision_order']==i+1 and r['role']=='interaction' and r['native_skill']=='PUSH']
        after=[r for r in rows if r['decision_order']==i+2 and r['role']=='preparation']
        entry=dict(push_intent_sha256=decision['intent_sha256'],push_target=decision['selected_intent']['target_ref'],
            observed_next_intent_sha256=index['decisions'][i+1]['intent_sha256'],
            observed_next_skill=index['decisions'][i+1]['selected_intent']['skill'],
            observed_next_target=index['decisions'][i+1]['selected_intent']['target_ref'],
            source='observed adjacent decisions only, not a required successor policy',
            own_push_native_window_s=None, observed_next_preparation_windows_s=None,
            push_terminal_to_next_preparation_end_s=None,
            push_native_start_to_next_preparation_end_s=None,
            query_to_next_preparation_end_s=None, actual_Actor_ready_at_preparation_end=None,
            alternative_action_effects=None, causal_method_gain=None)
        if len(current)==1:
            push=current[0];entry['own_push_native_window_s']=push['successful_native_window_s']
            if after:
                known=[r['observed_native_window_s'] for r in after]
                entry['observed_next_preparation_windows_s']=sum(known) if all(v is not None for v in known) else None
                # A recorded literal success is needed for each included stage.
                if push['literal_terminal_status']=='succeeded' and all(r['literal_terminal_status']=='succeeded' for r in after):
                    ends=[r['native_terminal_s'] for r in after]
                    starts=[r['native_started_s'] for r in after]
                    if all(v is not None for v in ends+starts) and push['native_terminal_s'] is not None:
                        need(push['native_terminal_s'] <= min(starts), 'Adjacent preparation predates PUSH completion')
                        endpoint=max(ends)
                        entry['push_terminal_to_next_preparation_end_s']=span(push['native_terminal_s'],endpoint)
                        entry['push_native_start_to_next_preparation_end_s']=span(push['native_started_s'],endpoint)
        chains.append(entry)
    return dict(schema='reach-retrospective-AINav-native-phase-cost-v1',
        role=('HISTORICAL_AUDIT_ONLY_NOT_PLANNER_INPUT_OR_FIT'
              if 'historical_source_manifest_sha256' in index else 'OFFLINE_OUTCOME_EVIDENCE_NOT_PLANNER_INPUT_OR_FIT'),
        source_manifest_sha256=recorded_source, expected_selected_manifest_sha256=selected_manifest_sha256,
        selected_executor_source_matches=source_matches if recorded_source is not None else None,
        source_scope='VERIFIED_OWNER_INDEX_DECLARATION' if source_matches else 'UNKNOWN_SOURCE_COST_DIAGNOSTIC_ONLY',
        rows=rows,per_intent=decisions,push_chains=chains,
        denominators=dict(selected_intents=len(index['decisions']),bound_native_options=len(rows),
            started_receipt_observed=sum(r['native_started_s'] is not None for r in rows),
            literal_succeeded=sum(r['literal_terminal_status']=='succeeded' for r in rows),
            literal_failed=sum(r['literal_terminal_status']=='failed' for r in rows),
            unobserved_terminal=sum(r['literal_terminal_status'] is None for r in rows)),
        accounting=dict(known_disjoint_native_window_sum_s=known_sum,window_coverage_complete_for_bound_options=complete,
            known_preparation_window_sum_s=prep_known,known_interaction_window_sum_s=interaction_known,
            preparation_share_of_known_native_windows=prep_known/known_sum if known_sum>0 else None,
            first_started_to_last_terminal_s=(sorted_windows[-1][1]-sorted_windows[0][0]) if complete and sorted_windows else None,
            interwindow_gap_sum_s=(sum(b[0]-a[1] for a,b in zip(sorted_windows,sorted_windows[1:])) if complete else None)),
        accounting_ablation=dict(kind='same recorded execution, remove terms on paper only',
            native_interaction_only_account_s=interaction_known,
            with_observed_preparation_windows_account_s=known_sum,
            omitted_known_preparation_s=prep_known,actual_runtime_saved_s=None,
            different_policy_executed=False,method_benefit_proven=False),
        matched_alternative_candidates=0, online_method_ranking=None,
        full_query_successor_cost_s=None,new_physical_samples_created_by_analysis=0,training_admission=False,dispatch=False)
