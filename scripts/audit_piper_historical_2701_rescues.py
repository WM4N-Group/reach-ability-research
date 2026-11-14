#!/usr/bin/env python3
"""Bounded historical audit: only env9/env26 from the two original2701 reports.

No dispatch, prediction, fitting, threshold search, registry write or permission
change. A same-numbered native slow success is NOT a verified paired rescue
without measured first-action-before state/command evidence for both arms.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from label_piper_existing_push_choice import ACTOR, EVALUATORS, TERMS, flags_label

ENVS = (9, 26)
VERSIONS = {'slow': 'push-entry-retreat-v209', 'fast': 'push-direct-approach-v212'}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ref(path):
    return {'path': str(path), 'sha256': sha(path)}


def read(path):
    return json.loads(Path(path).read_text())


def verified(source):
    require(sha(source['path']) == source['sha256'], 'Source SHA differs: ' + source['path'])
    return read(source['path'])


def selected_native(report, env_id):
    """Decode exactly one original env terminal, not an aggregate as one episode."""
    require(env_id in ENVS, 'Only the two adopted historical env selectors are allowed')
    names = report['termination_flag_names']
    require(len(names) == len(set(names)) and set(names) == TERMS, 'Native flag names differ')
    matches = [t for t in report['terminal_states'] if t['env_id'] == env_id]
    require(len(matches) == 1 and matches[0]['episode'] == 1, 'Missing/duplicate/reset env terminal')
    t = matches[0]
    values = t['termination_flags']
    require(len(values) == len(names) and all(type(v) is bool for v in values), 'Native flags malformed')
    label = flags_label(dict(zip(names, values)), t['elapsed_seconds'])
    require(label['valid'], 'Native selected outcome unknown')
    require(report['per_env_completions'][env_id] == 1 and
            report['per_env_successes'][env_id] == int(label['value']), 'Original per-env native counts disagree')
    return t, label


def target_telemetry(report, env_id):
    """Record the provided receipt's support; never treat a late suffix as reset."""
    require(env_id in ENVS, 'Out-of-scope history selector')
    histories = [h for h in report.get('failure_histories', []) if h['env_id'] == env_id]
    require(len(histories) <= 1, 'Ambiguous original failure history')
    samples = histories[0]['pre_step_samples'] if histories else []
    # These exact historic schemas have no initial-state/startup-state receipt.
    # Fail closed if a different schema is supplied: review it, do not silently
    # ignore potentially available t0 evidence or claim it has been verified.
    require(not any(k in report for k in ('initial_states', 'startup_states', 'initial_before')),
            'Unexpected initial-state receipt; this bounded historic audit needs explicit review')
    if samples:
        require(all(float(s['elapsed_seconds']) > 0 for s in samples),
                'Unexpected t0 history: review evidence, do not apply late-suffix assumption')
    return {
        'measured_t0_receipt_in_handed_sources': False,
        'first_action_before_physics_joint_state': 'missing',
        'first_action_before_pd_targets_torques_and_action_history': 'missing',
        'target_env_history_count': len(samples),
        'target_env_history_first_s': samples[0]['elapsed_seconds'] if samples else None,
        'target_env_history_last_s': samples[-1]['elapsed_seconds'] if samples else None,
        'history_phase': report.get('failure_history_sample_phase'),
        'other_env_trace_not_used': 'trace_env0 is not env9/env26 and cannot substitute for their reset',
        'decision_time_features_or_between_arm_t0_difference_verified': False,
    }


def audit(pointers_path, reports_root):
    pointers = read(pointers_path)
    require(pointers['schema'] == 'owner-existing-2701-provenance-pointers-v1' and
            pointers['shared_env_selectors'] == list(ENVS) and
            pointers['maximum_episode_evidence_units'] == 4 and pointers['whole_batch_report_files'] == 2,
            'Adopted scope differs')
    catalog = verified(pointers['catalog'])
    require(len(pointers['sources']) == 2 and {s['arm'] for s in pointers['sources']} == set(VERSIONS),
            'Only the two adopted whole reports are supported')
    sources, reports = {}, {}
    for s in pointers['sources']:
        arm = s['arm']; p = reports_root / (arm + '-report.json')
        require(s['skill_version'] == VERSIONS[arm] and sha(p) == s['remote_report']['sha256'], 'Original arm/report drift')
        raw = read(p)
        require(raw['seed'] == 2701 and raw['num_envs'] == raw['requested_episodes'] == 32 and
                raw['episodes_per_env'] == 1 and raw['episode_length_s'] == 48 and
                raw['box_mass'] == 1 and raw['box_friction'] == .15, 'Original domain/window differs')
        require(raw['checkpoint_sha256'] == ACTOR == catalog['common']['checkpoint_sha256'] and
                raw['evaluation_sha256'] == EVALUATORS[arm], 'Original actor/evaluator differs')
        summary = verified(s['local_summary']); startup = verified(s['local_startup_physics_metadata'])
        require(summary['report_sha256'] == sha(p) and summary['returncode'] == 0 and summary['valid'], 'Original receipt differs')
        require(not any(k in startup for k in ('initial_states', 'initial_before', 'startup_states')),
                'Unexpected measured startup; review new evidence explicitly')
        version = next(v for v in catalog['versions'] if v['version'] == VERSIONS[arm])
        root = Path(s['local_summary']['path']).parent
        batch_plan = read(root / 'plan.json')
        evaluator = root.parent / 'train/scripts/evaluate_residual_push.py'
        require(sha(evaluator) == EVALUATORS[arm] and batch_plan['source_plan_sha256'] == version['plan_sha256'] and
                batch_plan['checkpoint_sha256'] == ACTOR, 'Frozen source plan/evaluator differs')
        for name in ('completed_episodes', 'successful_episodes', 'incomplete_episodes', 'termination_reasons'):
            require(summary[name] == raw[name], 'Original batch summary/report disagree: ' + name)
        sources[arm] = dict(original_remote_report=s['remote_report'], local_report=ref(p),
            original_summary=s['local_summary'], startup_metadata=s['local_startup_physics_metadata'],
            batch_plan=ref(root / 'plan.json'), frozen_evaluator=ref(evaluator),
            original_source_plan_sha256=batch_plan['source_plan_sha256'],
            original_batch_denominator={k: raw[k] for k in ('requested_episodes', 'completed_episodes',
                'successful_episodes', 'incomplete_episodes', 'termination_reasons')},
            batch_physical_diagnostics_not_target_env_attributed=raw['physical_safety_control_samples'])
        reports[arm] = raw
    rows = []
    for env_id in ENVS:
        arms = {}
        for arm, raw in reports.items():
            t, label = selected_native(raw, env_id)
            arms[arm] = dict(native_outcome=label,
                terminal_observations={k: t.get(k) for k in ('elapsed_seconds', 'safe_approach_index',
                    'safe_approach_complete', 'box_displacement', 'box_goal_error', 'settle_duration',
                    'hand_contact_valid', 'hand_contact_position_valid', 'hand_contact_position', 'hand_position', 'hand_force')},
                visibility_and_missing=target_telemetry(raw, env_id))
        static_equal = all(reports['slow']['actual_physics'][k] == reports['fast']['actual_physics'][k]
                           for k in reports['slow']['actual_physics'] if k != 'controller_contract')
        rows.append(dict(original_env_id=env_id, original_batch_seed_audit_only=2701, arms=arms,
            static_physical_configuration_equal=static_equal,
            measured_t0_comparable=None, actual_paired_rescue_verified=None, paired_time_gain_s=None,
            reason='Same seed/env and matching static metadata do not prove the absent measured t0 state/commands; later failure history is explanatory only.',
            native_failure_not_credited_as_faster=True))
    return dict(schema='reach-historical-2701-rescue-audit-v1',
        created_at_beijing=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),
        main_decision_anchor='main-choice-pilot-close-and-historical-check-20261017',
        implementation=ref(__file__), native_label_semantics=ref(Path(__file__).with_name('label_piper_existing_push_choice.py')),
        owner_source_pointers=ref(pointers_path), catalog=pointers['catalog'],
        scope=dict(original_role='already_exposed_skill_development2701', report_files=2,
                   inspected_episode_evidence_units=4, reported_case_rows=2,
                   selected_env_ids=list(ENVS), new_independent_groups_claimed=0),
        sources=sources, rows=rows,
        conclusion='Both original fast failures are invalid_hand_contact, with same-env slow native successes. '
                   'Original t0 receipts are absent from the handed evidence; fast suffixes start long after reset and slow target-env history is absent. '
                   'The two native outcome contrasts are confirmed, but matched-reset rescues and pre-action observable preference are unverified. '
                   'Close this historical evidence path with a missing matrix; do not use it to fit a selector or fill gaps by rerunning old cases.',
        research_branch='Only post-action explanation/insufficient t0: stop this evidence path per main13:18. No same-domain expansion or selector training.',
        missing_data_policy='Completed limited audit with explicit missing evidence, not an open request to recover or recollect old startup.',
        mutations=dict(new_physical_starts=0, model_forward=0, model_fits=0, model_rescoring=0,
                       registry_writes=0, roles_or_permissions_changed=0))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pointers', type=Path, required=True)
    p.add_argument('--reports-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('Refusing to overwrite an audit artifact')
    value = audit(a.pointers, a.reports_root)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False); f.write('\n')
    print(value['conclusion'])


if __name__ == '__main__':
    main()
