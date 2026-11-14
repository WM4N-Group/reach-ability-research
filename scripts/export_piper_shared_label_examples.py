"""Export historical label-alignment examples; not a v212 batch adapter or sampler."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from audit_piper_source_transition_trace import audit, sha256


def label(value, reason, observed_until, source_event=None, censor=None):
    return dict(value=value, valid=value is not None, invalid_reason=reason,
                source_event=source_event, observed_until_s=observed_until,
                censor_time_s=censor)


def clearance_window(rows, query_step, dt, horizon, threshold=0.035):
    """Rows must be one audited episode with provenance-verified actual geometry.

    The minimum includes query and endpoint. A missing/nonfinite sample masks the
    full window. No interpolation or terminal-state padding is performed.
    """
    if not 0 <= query_step < len(rows) or not math.isfinite(dt) or dt <= 0:
        raise ValueError('Invalid query or sample period')
    ratio = horizon / dt
    if not math.isfinite(ratio) or ratio <= 0 or not math.isclose(ratio, round(ratio), abs_tol=1e-8):
        raise ValueError('Horizon must be a positive integer number of sample periods')
    q = rows[query_step]['time_s']
    count = round(ratio) + 1
    selected = rows[query_step:query_step + count]
    prefix = []
    reason = None
    for offset, row in enumerate(selected):
        if (row.get('step') != query_step + offset
                or not math.isclose(row.get('time_s', -1), q + offset * dt, abs_tol=1e-8)):
            reason = 'missing_sample_or_episode_boundary'
            break
        c = row.get('clearance_m')
        if type(c) not in (int, float) or not math.isfinite(c):
            reason = 'missing_or_nonfinite_actual_geometry'
            break
        prefix.append(row)
    if reason is None and len(prefix) != count:
        reason = 'episode_observation_ended_before_horizon'
    end = prefix[-1]['time_s'] if prefix else None
    minimum = min((r['clearance_m'] - threshold for r in prefix), default=None)
    result = label(minimum if reason is None else None, reason, end,
                   'actual_state_control_samples', end if reason else None)
    result.update(requested_horizon_s=horizon, horizon_complete=reason is None,
                  actual_sample_period_s=dt, expected_sample_count=count,
                  observed_sample_count=len(prefix), observed_prefix_min=minimum,
                  constant_reference_m=(prefix[0]['clearance_m'] - threshold) if prefix else None,
                  sampling_semantics='recorded_control_sample_minimum_not_physics_substeps')
    return result


def native_event_window(rows, q, horizon, native_failure):
    """An observed terminal breach is known even when the rest of H is censored."""
    end = rows[-1]['time_s']
    if native_failure and q <= end <= q + horizon + 1e-8:
        return label(True, None, end, 'native_terminal', end if end < q + horizon else None)
    if q + horizon <= end + 1e-8:
        return label(False, None, q + horizon, 'no_native_terminal_in_complete_window')
    return label(None, 'incomplete_horizon_without_observed_breach', end, censor=end)


def stage_labels(report, rows):
    end = rows[-1]['time_s']
    controls = {e['event']: e['time_s'] for e in report['control_events']}
    runtime = report['outcome'] == 'runtime_error'
    native = report['outcome'] == 'native_termination_during_push'
    ready = report['events'][-1]['time_s']
    contact = next((r['time_s'] for r in rows
                    if r.get('push', {}).get('legal_hand_contact') is True), None)
    settled = controls.get('native_push_settled_exit_requested')
    stowed = controls.get('return_nav_requested_after_stowed_ready')
    nav_start = controls.get('return_nav_activated_after_three_real_history_frames')
    final = end if report['outcome'] == 'nav_push_stow_nav_target_stable' else None

    def stage(entered, achieved, event):
        if entered is None:
            out = label(None, 'not_entered', end)
        elif achieved is not None:
            out = label(True, None, achieved, event)
        elif runtime:
            out = label(None, 'runtime_error_before_observed_stage_outcome', end, censor=end)
        elif native:
            out = label(False, None, end, 'native_terminal')
        else:
            out = label(None, 'outcome_unobserved', end, censor=end)
        out.update(entry_time_s=entered, event_time_s=achieved if achieved is not None
                   else end if out['value'] is False else None)
        return out

    return dict(transition_complete=stage(0., ready, 'transition_ready'),
                contact_established=stage(ready, contact, 'first_recorded_legal_hand_contact'),
                push_complete=stage(ready, settled, 'native_push_settled_exit_requested'),
                exit_complete=stage(settled, stowed, 'stowed_ready'),
                next_skill_complete=stage(nav_start, final, 'return_nav_target_stable'))


def export(source_root, contract_path):
    contract = json.loads(contract_path.read_text())
    if contract['label_schema_version'] != 'reach-wm-v212-v1':
        raise ValueError('Unsupported contract')
    if contract['auxiliary_target']['threshold_m'] != 0.035:
        raise ValueError('Unexpected geometry threshold')
    source_plan = source_root / 'push-direct-approach-v212/plan.json'
    plan = json.loads(source_plan.read_text())
    selected_sources = [
        'scripts/rsl_rl/safe_retraining.py',
        'source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp/box_push_geometry.py',
    ]
    provenance = []
    for rel in selected_sources:
        p = source_root / 'push-direct-approach-v212/train' / rel
        if sha256(p) != plan['source_hashes'][rel]:
            raise ValueError(f'Source drift: {p}')
        provenance.append(dict(path=str(p), sha256=sha256(p)))
    manifest_path = source_root.parent.parent.parent / 'GO2-PIPER-SIM2REAL/docs/push-v212-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    geometry_entries = [e for e in manifest['files'] if '/runtime-push-detour-v1/mujoco/' in e['path']]
    if not geometry_entries:
        raise ValueError('Missing geometry inventory')
    for e in geometry_entries:
        p = source_root.parent / e['path'].split('/artifacts/go2-piper/', 1)[1]
        if sha256(p) != e['sha256']:
            raise ValueError(f'Geometry drift: {p}')
    provenance.append(dict(path=str(manifest_path), sha256=sha256(manifest_path),
                           matched_geometry_files=len(geometry_entries)))
    examples = []
    for version, seed in ((272, 3701), (268, 3702), (272, 3706)):
        root = source_root / f'transition-arm-entry-v{version}'
        run = root / f'seed{seed}-native-entry'
        report_path, trace_path = run/'report.json', run/'control.jsonl'
        checked = audit(report_path, trace_path)
        report = json.loads(report_path.read_text())
        rows = [json.loads(s) for s in trace_path.read_text().splitlines()]
        candidate = json.loads((root/'plan.json').read_text())
        if candidate['source_plan_sha256'] != sha256(source_plan):
            raise ValueError('Candidate has a different underlying PUSH source')
        if sha256(root/'probe.py') != candidate['files']['probe.py']:
            raise ValueError('Historical recorder source drift')
        dt, last = report['control_dt'], rows[-1]['time_s']
        native = report['outcome'] == 'native_termination_during_push'
        runtime = report['outcome'] == 'runtime_error'
        query_steps = [report['events'][-1]['step'], len(rows)-11]
        queries = []
        for index in query_steps:
            q = rows[index]['time_s']
            queries.append(dict(
                query_time_s=q,
                query_event='transition_ready' if index == query_steps[0] else 'observed_control_sample',
                query_selection='predeclared_ready' if index == query_steps[0] else 'retrospective_tail_for_mask_test_only',
                inputs=dict(actual_clearance_m=rows[index]['clearance_m']),
                targets=[dict(name=contract['auxiliary_target']['name'],
                              **clearance_window(rows, index, dt, h)) for h in (0.4, 1.0)],
                native_safety_event_targets=[dict(requested_horizon_s=h,
                            **native_event_window(rows, q, h, native)) for h in (0.4, 1.0)],
            ))
        examples.append(dict(
            episode_id=f'historical-v{version}-seed{seed}', skill_version=f'transition-arm-entry-v{version}',
            source_path=str(trace_path), source_sha256=checked['control_trace_sha256'],
            report_path=str(report_path), report_sha256=checked['report_sha256'],
            candidate_plan_sha256=sha256(root/'plan.json'), recorder_sha256=sha256(root/'probe.py'),
            skill_bundle_hash=None, bundle_status='historical_source_references_not_new_v212_bundle_acceptance',
            group_id=f'historical-used-start-{seed}', group_split_version=None,
            task_scope='historical_nav_push_stow_nav', dataset_role='historical_semantics_alignment_only',
            execution_status='runtime_error' if runtime else 'native_termination' if native else 'normal_completion',
            verified_task_success=report['outcome']=='nav_push_stow_nav_target_stable',
            native_success_flags={k:v for k,v in report['terminal'].items() if k=='box_settled'},
            native_failure_flags={k:v for k,v in report['terminal'].items() if k!='box_settled'},
            exception_type='ValueError' if runtime else None,
            exception_time_s=None, exception_time_note='Not timestamped; last complete observation is only a lower bound' if runtime else None,
            last_valid_observation_time_s=last, stages=stage_labels(report, rows), queries=queries,
        ))
    return dict(label_schema_version=contract['label_schema_version'],
                exporter_version='historical-examples-v1', exporter_sha256=sha256(Path(__file__)),
                trace_auditor_sha256=sha256(Path(__file__).with_name('audit_piper_source_transition_trace.py')),
                contract_path=str(contract_path), contract_sha256=sha256(contract_path),
                sample_origin='physical_sample(actual joints, current common_step_counter); snapshot after env.step and before reset; initial sample at step zero',
                geometry_scope=contract['auxiliary_target']['geometry_pairs'], provenance=provenance,
                physical_episode_count_added=0, v212_new_domain_coverage_claimed=False,
                cross_group_alignment='pending_world_model_review', examples=examples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite versioned labels')
    result = export(args.source_root, args.contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(f'Wrote {len(result["examples"])} historical examples; zero new physical episodes')


if __name__ == '__main__':
    main()
