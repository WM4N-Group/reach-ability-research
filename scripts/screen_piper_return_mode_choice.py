"""Zero-new-physics decision-opportunity screen over two executed return modes.

This is a retrospective development ceiling, NOT learned selection, fresh
validation or an SDK/native-action safety claim. Reads only the explicit plan's
historical v317/v319 files; never the world-model registry or reserved raw data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

QUERY_EVENT = 'return_nav_requested_after_stowed_ready'
SUCCESS = 'nav_push_stow_nav_target_stable'
PREFIX_FIELDS = ('step', 'time_s', 'root_position', 'root_quaternion', 'root_velocity',
                 'root_angular_velocity', 'q', 'dq', 'pd_target', 'torque', 'foot_forces',
                 'body_forces', 'gates', 'clearance_m', 'torque_ratio', 'history_valid_frames')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def reference(path):
    return dict(path=str(Path(path).resolve()), sha256=digest(path))


def verify(ref):
    require(digest(ref['path']) == ref['sha256'], 'Source SHA differs: ' + ref['path'])


def finite(value):
    if type(value) in (int, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite(v) for v in value.values())
    if isinstance(value, list):
        return all(finite(v) for v in value)
    return value is None or type(value) in (bool, str)


def same_typed(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same_typed(v, right[k]) for k, v in left.items())
    if isinstance(left, list):
        return len(left) == len(right) and all(same_typed(x, y) for x, y in zip(left, right))
    return left == right


def query_event(report):
    events = [e for e in report['control_events'] if e['event'] == QUERY_EVENT]
    require(len(events) == 1, 'Exactly one declared return query event required')
    event = events[0]
    require(type(event['step']) is int and event['step'] >= 0 and finite(event), 'Invalid query event')
    require(len(event['goal']) == 3, 'Return goal must have original xyz identity')
    return event


def outcome(report, checked):
    require(report['outcome'] == checked['outcome'], 'Outcome differs from original source audit')
    require(report['samples'] == checked['samples'] and report['samples'] > 0, 'Original sample count differs')
    require(type(checked['end_time_s']) in (int, float) and math.isfinite(checked['end_time_s']), 'Invalid source observation end')
    require(math.isclose(checked['end_time_s'], (report['samples'] - 1) * report['control_dt'], abs_tol=1e-8, rel_tol=0),
            'Source end/sample clock differs')
    if checked['status'] == 'success' and report['outcome'] == SUCCESS:
        require(not any(report.get('terminal', {}).values()), 'Success conflicts with native termination flags')
        success, reason = True, None
    elif checked['status'] == 'failure' and report['outcome'].startswith('native_termination') and any(report.get('terminal', {}).values()):
        success, reason = False, 'observed_native_termination'
    elif checked['status'] == 'failure' and report['outcome'] in ('return_nav_timeout', 'exit_timeout'):
        success, reason = False, 'observed_original_budget_timeout'
    else:
        success, reason = None, 'unsupported_or_unobserved_task_outcome'
    return dict(task_completed=success, original_outcome=report['outcome'], source_audit_status=checked['status'],
                observed_end_s=checked['end_time_s'], successful_completion_time_s=checked['end_time_s'] if success is True else None,
                native_flags=report.get('terminal', {}), unknown_reason=reason if success is None else None)


def prefix_comparison(path_a, path_b, step, dt):
    """Compare actual causal histories, not just seed IDs or terminal reports."""
    rows_checked = 0
    with Path(path_a).open() as a, Path(path_b).open() as b:
        for index in range(step + 1):
            raw_a, raw_b = a.readline(), b.readline()
            require(raw_a and raw_b, 'Missing control observation before decision')
            left, right = json.loads(raw_a), json.loads(raw_b)
            for row in (left, right):
                require(row.get('step') == index and math.isclose(row.get('time_s', -1), index * dt, abs_tol=1e-8, rel_tol=0),
                        'Control clock gap before decision')
                require(all(k in row for k in PREFIX_FIELDS) and finite(row), 'Missing/nonfinite causal field')
            require(left.keys() == right.keys(), 'Recorded causal field set differs before decision')
            for key in left:
                if not same_typed(left[key], right[key]):
                    return dict(passed=False, rows_checked=rows_checked, first_different_step=index,
                                first_different_field=key, decision_observation=None)
            rows_checked += 1
        # Contains only information already observed before return request. IDs and
        # seed never become predictor inputs. Deployment sensor access is not claimed.
        observation = {key: left[key] for key in PREFIX_FIELDS}
    return dict(passed=True, rows_checked=rows_checked, first_different_step=None,
                first_different_field=None, decision_observation=observation,
                all_recorded_fields_compared=True, decision_recorded_field_count=len(left),
                native_action_and_applied_command_available=all(k in left for k in ('native_action', 'applied_joint_command')))


def preferred(a, b):
    """Completion first, completed time second. Failure never earns speed credit."""
    sa, sb = a['task_completed'], b['task_completed']
    if sa is None or sb is None:
        return None
    if sa is not sb:
        return 'A' if sa else 'B'
    if sa is False:
        return 'tie_both_failed'
    ta, tb = a['successful_completion_time_s'], b['successful_completion_time_s']
    require(all(type(t) in (int, float) and math.isfinite(t) for t in (ta, tb)), 'Completed task time missing')
    if math.isclose(ta, tb, abs_tol=1e-8, rel_tol=0):
        return 'tie'
    return 'A' if ta < tb else 'B'


def summarize(pairs):
    eligible = [p for p in pairs if p['pair_eligible']]
    known = [p for p in eligible if p['preference'] is not None]
    all_supported = bool(pairs) and len(known) == len(pairs)
    b_wins = [p['seed_audit_only'] for p in known if p['preference'] == 'B']
    dominated = all_supported and not b_wins and any(p['preference'] == 'A' for p in known)
    def complete(which):
        return sum(p[which]['task_completed'] is True for p in known)
    return dict(requested_pairs=len(pairs), eligible_pairs=len(eligible), fully_observed_rankable_pairs=len(known),
                ineligible_pair_ids=[p['seed_audit_only'] for p in pairs if not p['pair_eligible']],
                unknown_outcome_pair_ids=[p['seed_audit_only'] for p in eligible if p['preference'] is None],
                always_A_completed=complete('A'), always_B_completed=complete('B'),
                hindsight_oracle_completed=sum(p['A']['task_completed'] is True or p['B']['task_completed'] is True for p in known),
                B_better_pair_ids=b_wins, B_empirically_dominated_for_original_task_completion_time=dominated,
                all_pairs_supported=all_supported,
                oracle_added_successes_vs_A=0 if dominated else None,
                oracle_completed_time_gain_vs_A_s=0. if dominated else None,
                no_model_fit_or_new_physics_recommended_for_this_observed_pair=dominated,
                caveat='Empirical post-exposure development ceiling under original final-stop task only; not a theorem for fresh states or native18-axis SDK fidelity. No runtime late-switch API or safety guarantee established.')


def screen(plan_path):
    plan = read(plan_path)
    require(plan['schema'] == 'reach-return-mode-decision-opportunity-screen-plan-v1', 'Wrong screen plan')
    require(plan['candidate_versions'] == [317, 319] and plan['paired_seeds'] == [3701, 3703, 3705, 3706], 'Explicit immutable version/pair scope required')
    for key in ('dispatch_enabled', 'training_enabled', 'model_forward_enabled', 'reference_fitting_enabled'):
        require(plan[key] is False, 'This screen cannot execute a new experiment or fitting')
    require(plan['minimum_budget']['new_physical_episodes'] == 0, 'Zero-physical screen only')
    base = Path(plan['source_root'])
    registries, source_refs = {}, []
    for version in plan['candidate_versions']:
        refs = plan['source_refs'][str(version)]
        for ref in refs.values():
            verify(ref)
            source_refs.append(ref)
        candidate, audit = read(refs['plan']['path']), read(refs['audit']['path'])
        require(audit['plan_sha256'] == digest(refs['plan']['path']), 'Original audit plan binding differs')
        by_seed = {x['seed']: x for x in audit['runs']}
        require(len(by_seed) == len(audit['runs']), 'Duplicate source audit seed')
        for name, wanted in candidate['files'].items():
            path = base / f'transition-arm-entry-v{version}' / name
            require(digest(path) == wanted, 'Candidate implementation drift: ' + name)
        registries[version] = candidate, by_seed
    require(registries[317][0]['source_plan_sha256'] == registries[319][0]['source_plan_sha256'], 'Different frozen PUSH source')
    source_plan = base / 'push-direct-approach-v212/plan.json'
    require(digest(source_plan) == registries[317][0]['source_plan_sha256'], 'Frozen PUSH plan drift')
    source_refs.append(reference(source_plan))
    # Select exactly every actually run B case, not just favorable outcomes.
    actual_b = {seed for seed, x in registries[319][1].items() if x['status'] not in ('not_run', 'missing_terminal')}
    require(actual_b == set(plan['paired_seeds']), 'All-run B source set differs; no favorable subset permitted')
    pairs = []
    for seed in plan['paired_seeds']:
        reports, traces, results, events = {}, {}, {}, {}
        item = dict(seed_audit_only=seed, pair_eligible=False, eligibility_reason=None, preference=None)
        try:
            for version, key in ((317, 'A'), (319, 'B')):
                source = base / f'transition-arm-entry-v{version}' / f'seed{seed}-native-entry'
                report_path, trace_path = source / 'report.json', source / 'control.jsonl'
                checked = registries[version][1][seed]
                require(digest(report_path) == checked['report_sha256'] and digest(trace_path) == checked['control_sha256'],
                        'Original report/control bytes differ')
                report = read(report_path)
                require(report['seed'] == seed and report['control_dt'] == .02 and report['physical_resets_after_initial'] == 0,
                        'Source reset/clock/seed identity differs')
                reports[key], traces[key] = report, trace_path
                results[key] = outcome(report, checked)
                events[key] = query_event(report)
                item[key] = dict(**results[key], report=reference(report_path), control=reference(trace_path),
                                 original_safety_metrics={k: report[k] for k in ('minimum_clearance_m', 'max_substep_arm_torque_ratio',
                                    'airborne_samples', 'under_three_support_samples')})
            require(reports['A']['source'] == reports['B']['source'] and reports['A']['nav_sha256'] == reports['B']['nav_sha256'] and
                    reports['A']['robot_initial_position'] == reports['B']['robot_initial_position'] and
                    reports['A']['joint_names'] == reports['B']['joint_names'], 'Initial/controller identity differs; seed is not enough')
            require(events['A'] == events['B'], 'Decision event/goal differs')
            require(math.isclose(events['A']['time_s'], events['A']['step'] * .02, abs_tol=1e-8, rel_tol=0), 'Query event clock mismatch')
            prefix = prefix_comparison(traces['A'], traces['B'], events['A']['step'], .02)
            item.update(decision_event=events['A'], actual_prefix=prefix)
            require(prefix['passed'], 'Actual state/issued-target/history prefix differs')
            item['pair_eligible'] = True
            item['preference'] = preferred(results['A'], results['B'])
            item['completed_B_minus_A_s'] = (results['B']['successful_completion_time_s'] - results['A']['successful_completion_time_s']
                                             if results['A']['task_completed'] is True and results['B']['task_completed'] is True else None)
            for key in ('A', 'B'):
                item[key]['successful_post_query_duration_s'] = (results[key]['successful_completion_time_s'] - events[key]['time_s']
                                                               if results[key]['task_completed'] is True else None)
        except (ValueError, KeyError, OSError) as error:
            item['eligibility_reason'] = str(error)
        pairs.append(item)
    # Never change or charge shared registries; verify they remained byte-identical.
    for ref in plan['current_shared_registry'].values():
        verify(ref)
    return dict(schema='reach-return-mode-decision-opportunity-screen-v2', plan=reference(plan_path),
                implementation=reference(__file__), source_refs=source_refs,
                scope=plan['classification'], source_outcomes_known_before_registration=True,
                objective=plan['utility'], candidate_decision_event=QUERY_EVENT, pairs=pairs, summary=summarize(pairs),
                model_inference_runs=0, new_model_fits=0, new_physical_episodes=0,
                shared_registry_roles_labels_permissions_or_budget_changed=False,
                actual_dynamic_switch_api_validated=False,
                full_simulator_hidden_state_equality_not_certified=True,
                implementation_scope='v2 checks every recorded prefix field with exact types, including native actions/applied commands; v1 core-field result retained. No new execution or utility changed.',
                causal_fields_are_simulation_audit_only_not_hardware_interface=True,
                no_data_from_original_world_model_reserved_5311_5312_read=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('Refusing to overwrite a decision screen result')
    result = screen(args.plan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(result['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
