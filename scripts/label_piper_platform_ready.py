#!/usr/bin/env python3
"""Attach Reach event/native-outcome receipts to the ONE adopted three-source table.

Reads small original report/READY/boundary/audit receipts, not control trajectories.
No dispatch, model, geometry replay, future-input extraction or registry writes.
"""
import argparse
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

CASES = (('transition-platform-native-v001', 3703),
         ('transition-platform-native-v002', 3701),
         ('transition-platform-native-v002', 3702))
PHASE = 'after_completed_interval_reference_computation_done_before_current_asset_PD_write_and_physics'
READY = 'supported_READY_before_native_blend'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ref(path):
    return {'path': str(Path(path).resolve()), 'sha256': sha(path)}


def same_time(a, b):
    return type(a) in (int, float) and type(b) in (int, float) and abs(a-b) < 1e-8


def native_outcome(report):
    """Known physical failure vetoes even a stale no_failure/final-complete cache."""
    terms = report.get('termination', {})
    require(isinstance(terms, dict) and all(type(v) is bool for v in terms.values()), 'Malformed native termination')
    failures = [k for k, v in terms.items() if v and k not in ('time_out', 'box_settled')]
    details = report.get('platform_final_details', {})
    outcome = report.get('outcome')
    if failures:
        value, reason = False, 'native_physical_failure'
    elif outcome == 'native_termination' and terms.get('time_out'):
        value, reason = False, 'original_timeout_before_verified_native_goal'
    elif outcome == 'nav_climb_nav_platform_target_stable':
        gates = details.get('gates', {})
        complete = (details.get('complete') is True and bool(gates) and
                    all(v is True for v in gates.values()) and details.get('stable_s', 0) >= 1.)
        value, reason = (True, 'original_complete_predicate') if complete else (None, 'incomplete_native_completion_receipt')
    else:
        value, reason = None, 'terminal_missing_or_exception_not_physical_failure'
    return dict(value=value, valid=value is not None, reason=reason,
                native_failure_names=failures, native_termination=terms,
                right_censored=value is None, physical_failure_not_censoring=value is False,
                source_scope='Original fixed bridge/native NAV/capture predicate, not arbitrary whole-chain/SDK safety')


def align_ready(source, table_row, report, ready, boundaries, group_entry):
    key = source['case_key']; join = source['join']
    require(table_row['case_key'] == key and table_row['query_join'] == join,
            'Full source/report/READY join differs; never join by seed alone')
    require(table_row['query_phase_canonical'] == PHASE, 'Admission phase differs')
    require(join['report_sha256'] == group_entry['report_sha256'], 'Producer report identity differs')
    require(report['platform_native_ready'] == ready and
            ready['actual_state']['episode_step'] == join['ready_step'] and
            same_time(ready['time_s'], join['ready_time_s']) and
            same_time(ready['time_s'], group_entry['native_ready_s']), 'READY source/time/step differs')
    events = [e for e in boundaries if e['event'] == READY]
    require(len(events) == 1 and same_time(events[0]['time_s'], ready['time_s']), 'Missing/duplicate first actual READY')
    require(events[0]['identical_physics_queues_and_histories'] is True, 'Original READY boundary is not continuous')
    gates = ready['gates']
    require(len(gates) == 19 and all(v is True for v in gates.values()) and ready['continuous_stable_s'] >= .5,
            'Original READY gate receipt differs')
    view = source['input_view']
    require(view is not None and view['query']['original_READY_gates'] == gates and
            view['query']['original_READY_stable_s'] == ready['continuous_stable_s'], 'Input/READY causal gate binding differs')
    return dict(value=True, valid=True, event_name=READY, event_time_s=ready['time_s'],
                ready_step=join['ready_step'], query_phase_canonical=PHASE,
                original_READY_gates=gates, original_READY_stable_s=ready['continuous_stable_s'],
                scope='Observed READY before current asset PD issuance/physics; private reference computation already done')


def receipt_row(root, source, table_row, entry):
    version, seed = source['source_version'], source['seed_audit_only']
    require((version, seed) in CASES, 'Out-of-scope source version/seed')
    directory = root / version / ('seed'+str(seed))
    paths = {k: directory / v for k, v in dict(report='report.json', ready='platform-native-ready.json',
                                               boundary='platform-boundary-events.jsonl').items()}
    for name, path in paths.items():
        require(sha(path) == source['source_refs'][name]['sha256'], 'Source SHA drift: '+name)
    report, ready = read(paths['report']), read(paths['ready'])
    require(report['seed'] == seed and report['physical_resets_after_initial'] == 0 and
            report['control_sha256'] == source['source_refs']['control']['sha256'], 'Original source identity/reset differs')
    # Reuse the original audited terminal receipt. Do not rerun source/history audit.
    audit_path = (root/version/'audit.json') if version.endswith('v001') else directory/('terminal-aware-audit.json' if seed == 3701 else 'audit.json')
    require(sha(audit_path) == entry['audit_sha256'], 'Original terminal audit identity differs')
    audit = read(audit_path)
    require(audit['seed'] == seed and audit['source_and_control_sha256_verified'] is True and not audit['error'],
            'Original terminal receipt not verified')
    boundaries = [json.loads(line) for line in paths['boundary'].read_text().splitlines()]
    event = align_ready(source, table_row, report, ready, boundaries, entry)
    climb = [e for e in boundaries if e['event'] == 'natural_climb_complete_to_platform_prepare']
    require(len(climb) == 1 and same_time(climb[0]['time_s'], entry['climb_complete_s']), 'Natural CLIMB event binding differs')
    task = native_outcome(report)
    require(task['value'] == table_row['producer_existing_native_terminal_reference']['value'] and
            task['value'] == entry['full_success'], 'Independent native endpoint and existing producer fact disagree')
    require(report['termination'] == entry['termination'] and report['outcome'] == entry['outcome'], 'Native outcome identity differs')
    terminal_s = round(report['steps']*.02, 8)
    require(same_time(terminal_s, entry['completion_s']) and terminal_s >= event['event_time_s'], 'Original terminal total clock differs')
    require(terminal_s <= 420 and terminal_s-climb[0]['time_s'] <= 120, 'Original caller/platform budget differs')
    details = report['platform_final_details']
    if task['value']:
        require(details['raw_native_progress_m'] >= .08 and details['goal_error_m'] <= .035 and
                details['stable_s'] >= 1, 'Original progress/goal/stop predicate receipt differs')
    require(report['platform_native_exact_samples'] == entry['native_exact_samples'] == audit['platform_native_exact_steps'],
            'Original terminal-aware native count differs')
    task.update(observed_terminal_time_s=terminal_s, observed_duration_after_READY_s=terminal_s-ready['time_s'],
                successful_duration_after_READY_s=terminal_s-ready['time_s'] if task['value'] else None,
                native_call_was_entered=report['platform_native_exact_samples'] > 0,
                native_first_action_time_s=None, native_first_action_time_valid=False,
                unknown_alternative_action_outcome=True, alternate_action_success=None)
    return dict(case_key=source['case_key'], source_version=version, seed_audit_only=seed,
        query_join=source['join'], source_refs={**{k: ref(p) for k,p in paths.items()}, 'existing_terminal_audit':ref(audit_path)},
        transition_ready=event, prior_natural_climb_complete=dict(value=True, valid=True,event_time_s=climb[0]['time_s']),
        next_skill_complete=task,
        original_clock=dict(task_budget_s=420, platform_budget_from_climb_s=120,
            task_remaining_at_READY_s=420-ready['time_s'], platform_remaining_at_READY_s=120-(ready['time_s']-climb[0]['time_s']),
            clock_not_restarted_at_READY=True),
        original_goal_semantics=dict(reference_forward_goal_m=.30, minimum_actual_raw_native_progress_m=.08,
            position_radius_m=.035, stable_stop_s=1., note='80mm is a native-progress minimum, NOT the .30m reference goal'),
        terminal_only_diagnostics=dict(original_final_details=details, first_effort_violation=report.get('first_effort_violation'),
            native_issued_samples_terminal_aware=report['platform_native_exact_samples'],
            cached_details_native_samples=details['native18_samples'],
            existing_terminal_phase_adapter=audit.get('audit_only_terminal_phase_correction'),
            stale_final_no_failure_never_overrides_native_termination=True,
            airborne_control_samples=report['airborne_samples'], under_three_support_control_samples=report['under_three_support_samples']),
        input_features_added_by_Reach=0, raw_control_rows_read_by_Reach=0,
        fitting_or_calibration_permission=False, independent_model_validation_permission=False,
        source_role='already_exposed_historical_skill_development_interface_only')


def build(root, inputs_path, interface_path):
    inputs, interface = read(inputs_path), read(interface_path)
    require(sha(inputs_path) == interface['input_ref']['sha256'], 'Shared input/table identity drift')
    group_ref = interface['producer_group_ref']; require(sha(group_ref['path']) == group_ref['sha256'], 'Producer group drift')
    group = read(group_ref['path']); expected={v+'/seed'+str(s) for v,s in CASES}
    for dataset in (inputs, interface):
        require(len(dataset['rows']) == 3 and {r['case_key'] for r in dataset['rows']} == expected, 'Adopted roster differs')
    entries={(e['version'], e['seed']):e for e in group['entries']}
    rows=[]
    for source in inputs['rows']:
        row=next(r for r in interface['rows'] if r['case_key']==source['case_key'])
        rows.append(receipt_row(root,source,row,entries[source['source_version'],source['seed_audit_only']]))
    return dict(schema='reach-platform-READY-native-event-receipts-v1',
        created_at_beijing=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),
        main_decision_anchor='main-platform-ready-interface-adoption-20261017',
        implementation=ref(__file__), shared_inputs=ref(inputs_path), shared_interface_before=ref(interface_path),
        existing_producer_group=group_ref, rows=rows,
        status='three_source_event_and_native_endpoint_receipts_aligned_partial_input_state_preserved',
        scope='Limited historical interface verification; original2success/1physicalfailure are producer facts, not a new experiment or selector result',
        observations=dict(source_rows=3, observed_READY=3, known_native_success=2, known_native_failure=1,
                          missing_terminal=0, verified_alternative_actions=0),
        new_physical_starts=0, model_forward=0, model_fit=0, registry_writes=0,
        unavailable_input_families_unchanged=interface['missing_numeric_families'],
        next_quantity_proposal=interface['minimum_next_prediction_quantity_proposal'])


def attach(interface, labels, labels_ref):
    value=copy.deepcopy(interface)
    require(len(labels['rows']) == len(interface['rows']) == 3, 'Exactly three receipts required')
    by_key={r['case_key']:r for r in labels['rows']}
    require(len(by_key)==3 and set(by_key)=={r['case_key'] for r in interface['rows']}, 'Receipt roster differs')
    for row in value['rows']:
        r=by_key[row['case_key']]
        require(row['query_join'] == r['query_join'] and row['query_phase_canonical']==r['transition_ready']['query_phase_canonical'],
                'Do not silently realign source, READY or phase')
        require(r['next_skill_complete']['value']==row['producer_existing_native_terminal_reference']['value'], 'Known physical result must remain unchanged')
        row['Reach_event_and_censor_receipt']={**labels_ref,'selector':'rows[case_key='+row['case_key']+']'}
        row['Reach_receipt_status']='independent_event_native_endpoint_and_censor_alignment_complete'
    value.update(schema='three-source-platform-ready-interface-v2',
        status='joint_three_source_causal_input_and_native_receipts_formed_partial_internal_state',
        joint_interface_complete=True, joint_completion_scope='Three event/input joins only; missing internal numeric families remain masked, no model/safety/counterfactual qualification',
        Reach_labels_ref=labels_ref)
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--interface',type=Path,required=True);p.add_argument('--labels-output',type=Path,required=True)
    p.add_argument('--joint-output',type=Path,required=True);a=p.parse_args()
    require(a.labels_output.resolve()!=a.joint_output.resolve(),'Outputs must be distinct')
    require(not a.labels_output.exists() and not a.joint_output.exists(),'Refusing to overwrite existing artifacts')
    labels=build(a.source_root,a.inputs,a.interface)
    for dest in (a.labels_output,a.joint_output):dest.parent.mkdir(parents=True,exist_ok=True)
    with a.labels_output.open('x') as f:json.dump(labels,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    joint=attach(read(a.interface),labels,ref(a.labels_output))
    with a.joint_output.open('x') as f:json.dump(joint,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(receipts=3,joint_interface_complete=True,labels=str(a.labels_output),joint=str(a.joint_output))))


if __name__=='__main__':main()
