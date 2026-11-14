"""Read-only native-event/paired-efficiency evaluation for the adopted v209/v212 pilot.

No sampler, controller, model, fitting, registry mutation or permissions release.
The reset-before-first-action is the only decision point: post-action prefixes
MUST NOT be required equal for two different full calls. Old studies stay intact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

STUDY = 'existing-push-choice-20261017-v1'
ROLE = 'skill_choice_development'
ARM_VERSIONS = {'slow': 'push-entry-retreat-v209', 'fast': 'push-direct-approach-v212'}
EVALUATORS = {'slow': '75965d73b0addd17a58fadc8e0f80b54f7d2bca3a9f44469bd378c176782cee1',
              'fast': '5a801de358b1ccc86e0c23c2cb1db187e1b6407b43e3d93e3503e314039df049'}
ACTOR = '4d1a4616928b4d06002285e870a1d6dd114e27b8cafcdd9a41dbdae1aceed419'
TERMS = {'time_out', 'base_contact', 'bad_orientation', 'box_settled', 'box_contact',
         'invalid_hand_contact', 'box_tipped', 'low_posture', 'arm_body_clearance',
         'actual_surface_clearance', 'arm_effort_safety'}
INITIAL_KEYS = ('root_position_xyz', 'root_quaternion_wxyz', 'root_linear_velocity_world_mps',
                'root_angular_velocity_world_radps', 'joint_position_rad', 'joint_velocity_radps',
                'box_position_xyz', 'box_quaternion_wxyz', 'box_linear_velocity_world_mps',
                'box_angular_velocity_world_radps', 'feet_position_xyz', 'foot_force_world_n',
                'previous_joint_position_target_rad', 'last_substep_applied_torque_nm')
CLOCK_TOL = 1e-4  # serialization tolerance <1/100 of a20ms control step; no added physics


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk := f.read(1024 * 1024): h.update(chunk)
    return h.hexdigest()


def ref(path):
    return dict(path=str(Path(path).resolve()), sha256=sha(path))


def verified(ref):
    require(sha(ref['path']) == ref['sha256'], 'Source byte drift: ' + ref['path'])
    return read(ref['path'])


def same(a, b):
    if type(a) is not type(b): return False
    if isinstance(a, dict): return a.keys() == b.keys() and all(same(v, b[k]) for k, v in a.items())
    if isinstance(a, list): return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def flags_label(flags, seconds, program_returncode=0):
    """Match original evaluator779-783: failures veto, time_out alone does not veto goal."""
    require(set(flags) == TERMS and all(type(v) is bool for v in flags.values()), 'Complete bool native flags required')
    require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0, 'Invalid original terminal clock')
    require(type(program_returncode) is int, 'Return code must be explicit integer')
    failure = [k for k, value in flags.items() if value and k not in ('box_settled', 'time_out')]
    in_window = seconds <= 48. + CLOCK_TOL
    if not in_window:
        value, reason = None, 'terminal_outside_original48s_protocol'
    elif failure:
        value, reason = False, 'native_failure'
    elif flags['box_settled']:
        value, reason = True, None
    elif flags['time_out']:
        value, reason = False, 'native_timeout_without_verified_goal'
    else:
        value, reason = None, 'no_native_outcome_observed'
    return dict(value=value, valid=value is not None, invalid_reason=reason if value is None else None,
                execution_status='normal_completion' if value is True else 'native_termination' if failure else
                    'normal_timeout' if value is False else 'outcome_unobserved',
                native_flags=flags, native_failure_names=failure,
                observed_terminal_seconds=seconds, successful_completion_seconds=seconds if value is True else None,
                program_returncode=program_returncode, program_error=program_returncode != 0,
                original48s_clock_compatible=in_window,
                failure_is_never_time_saving=True)


def report_label(report, arm, program_returncode=0):
    require(arm in ARM_VERSIONS, 'Only the two adopted arms are supported')
    require(report['evaluation_sha256'] == EVALUATORS[arm] and report['checkpoint_sha256'] == ACTOR, 'Arm evaluator/actor drift')
    require(all(type(report[k]) is int and report[k] == 1 for k in ('num_envs','episodes_per_env','requested_episodes')),
            'This adopted recorder/report is one full-reset attempt, not an aggregate batch')
    require(all(type(report[k]) in (int,float) and report[k] == v for k,v in (('episode_length_s',48),('box_mass',1),('box_friction',.15))),
            'Original task domain/window differs')
    terminals = report.get('terminal_states', [])
    require(len(terminals) <= 1, 'Multiple terminals/reset bridge in one charged attempt')
    if not terminals:
        return dict(value=None, valid=False, invalid_reason='runtime_or_missing_native_terminal',
                    execution_status='runtime_or_recording_failure', native_flags=None, native_failure_names=[],
                    observed_terminal_seconds=None, successful_completion_seconds=None,
                    program_returncode=program_returncode, program_error=program_returncode != 0,
                    original48s_clock_compatible=True, failure_is_never_time_saving=True)
    names = report['termination_flag_names']; terminal = terminals[0]
    require(len(names) == len(set(names)) and set(names) == TERMS, 'Native term mapping drift')
    values = terminal['termination_flags']
    require(len(values) == len(names) and all(type(v) is bool for v in values), 'Terminal native flag mapping invalid')
    require(terminal.get('env_id') == 0 and terminal.get('episode', 1) == 1, 'Terminal identity/reset differs')
    label = flags_label(dict(zip(names, values)), terminal['elapsed_seconds'], program_returncode)
    require(type(report['completed_episodes']) is int and report['completed_episodes'] == 1 and
            type(report['incomplete_episodes']) is int and report['incomplete_episodes'] == 0, 'Native terminal/report counters conflict')
    if label['valid']:
        require(type(report['successful_episodes']) is int and report['successful_episodes'] == int(label['value']), 'Native predicate and report success count conflict')
    return label


def reset_fingerprint(domain):
    initial = domain['initial_states'][0]
    fields = ('root_position_xyz', 'root_quaternion_wxyz', 'joint_position_rad', 'joint_velocity_radps',
              'box_position_xyz', 'box_quaternion_wxyz')
    measured = {key: initial[key] for key in fields}
    measured.update({key: domain[key] for key in ('robot_body_masses_kg', 'box_mass_kg', 'box_material_properties')})
    return hashlib.sha256(json.dumps(measured, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def sequence_events(path, metadata):
    """Optional stage observations; a bad suffix never fabricates a stage negative."""
    require(metadata['num_envs'] == 1 and math.isclose(metadata['control_dt_s'], .02, abs_tol=1e-10), 'Recorder clock/env drift')
    events = dict(first_approach_flag_s=None, first_legal_contact_s=None, observed_until_s=None,
                  initial_before=None, valid_prefix_intervals=0, prefix_stop_reason=None)
    last_terminal = False
    with Path(path).open() as f:
        for line in f:
            row = json.loads(line); i = events['valid_prefix_intervals']
            if last_terminal or row.get('index') != i or row.get('env_id') != 0 or not math.isclose(row.get('interval_start_s', -1), i * .02, abs_tol=1e-7):
                events['prefix_stop_reason'] = 'gap_or_continuation_after_terminal'; break
            if i == 0: events['initial_before'] = row['before']
            observations = [(row['before'], i * .02)]
            if row.get('terminal') is True and row.get('after_captured_before_reset') is True:
                observations.append((row['after'], (i + 1) * .02))
            for state, t in observations:
                if state.get('controller_observed', {}).get('safe_approach_complete') is True and events['first_approach_flag_s'] is None:
                    events['first_approach_flag_s'] = t
                if state.get('legal_hand_contact') is True and state.get('invalid_hand_contact') is False and state.get('forbidden_box_contact') is False and events['first_legal_contact_s'] is None:
                    events['first_legal_contact_s'] = t
                events['observed_until_s'] = t
            events['valid_prefix_intervals'] += 1
            last_terminal = row.get('terminal') is True
    return events


def summarize(records, planned_cases):
    require(len(planned_cases) == 4 and len({c['episode_id'] for c in planned_cases}) == 4, 'Exactly four explicit adopted pair slots')
    seeds = sorted({c['seed'] for c in planned_cases})
    require(len(seeds) == 2 and all({c['arm'] for c in planned_cases if c['seed'] == seed} == {'slow', 'fast'} for seed in seeds), 'Two reset slots and both full calls required')
    require(len({r['episode_id'] for r in records}) == len(records) and {r['episode_id'] for r in records} == {c['episode_id'] for c in planned_cases}, 'Every planned slot must stay in full denominator')
    by_id = {r['episode_id']: r for r in records}; pairs = []
    for c in planned_cases:
        row=by_id[c['episode_id']]
        require(row['arm']==c['arm'] and row['seed_audit_only']==c['seed'] and type(row['started']) is bool,
                'Reported slot arm/seed/started identity differs')
    for seed in seeds:
        pair = {arm: by_id[next(c['episode_id'] for c in planned_cases if c['seed'] == seed and c['arm'] == arm)] for arm in ('slow', 'fast')}
        a, b = pair['slow'], pair['fast']
        initial_match = bool(a.get('initial_before')) and bool(b.get('initial_before')) and bool(a.get('joint_names')) and a.get('joint_names')==b.get('joint_names') and all(
            key in a['initial_before'] and key in b['initial_before'] and same(a['initial_before'][key], b['initial_before'][key]) for key in INITIAL_KEYS)
        group_match = bool(a.get('group_id')) and a.get('group_id') == b.get('group_id')
        comparable = bool(initial_match and group_match and a.get('source_valid') and b.get('source_valid'))
        known = comparable and all(r['task']['valid'] for r in (a,b))
        both = known and a['task']['value'] is True and b['task']['value'] is True
        pairs.append(dict(seed_audit_only=seed, slow_episode=a['episode_id'], fast_episode=b['episode_id'],
            measured_group_id=a.get('group_id') if group_match else None, actual_initial_match=initial_match,
            comparable=comparable, both_outcomes_known=bool(known), slow_success=a['task']['value'], fast_success=b['task']['value'],
            both_success=bool(both), fast_time_gain_s=a['task']['successful_completion_seconds']-b['task']['successful_completion_seconds'] if both else None,
            slow_rescues_fast_failure=bool(known and a['task']['value'] is True and b['task']['value'] is False),
            reason=None if comparable else 'missing_or_nonidentical_reset/source; kept_in_full_attempt_denominator'))
    paired_known = [p for p in pairs if p['both_outcomes_known']]
    gains = [p['fast_time_gain_s'] for p in pairs if p['both_success']]
    arm_counts = {}
    for arm in ('slow', 'fast'):
        rows = [r for r in records if r['arm'] == arm]
        arm_counts[arm] = dict(planned=2, actual_started=sum(r['started'] for r in rows),
            native_success=sum(r['task']['value'] is True for r in rows), native_failure=sum(r['task']['value'] is False for r in rows),
            unknown=sum(r['started'] and r['task']['value'] is None for r in rows), not_started=sum(not r['started'] for r in rows),
            program_errors=sum(r['task'].get('program_error', False) for r in rows),
            recording_or_postprocessing_errors=sum(r.get('owner_status')=='runtime_or_recording_failure' or bool(r.get('canonical_source',{}).get('postprocessing_error')) for r in rows))
    best = max(sum(p['slow_success'] is True for p in paired_known), sum(p['fast_success'] is True for p in paired_known)) if paired_known else None
    oracle = sum(p['slow_success'] is True or p['fast_success'] is True for p in paired_known) if paired_known else None
    return dict(planned_slots=4, actual_started=sum(r['started'] for r in records), arms=arm_counts, pairs=pairs,
        comparable_known_pairs=len(paired_known), distinct_measured_pair_groups=len({p['measured_group_id'] for p in paired_known}),
        common_success_pairs=len(gains), paired_fast_time_gain_s=gains,
        median_fast_gain_common_success_s=statistics.median(gains) if gains else None,
        best_fixed_completed_on_known_pairs=best, hindsight_oracle_completed_on_known_pairs=oracle,
        hindsight_added_completions_over_best_fixed=oracle-best if oracle is not None else None,
        fast_faster_common_success_pairs=sum(g > 0 for g in gains), slow_rescue_pairs=sum(p['slow_rescues_fast_failure'] for p in pairs),
        success_reversal_is_not_required_for_this_adopted_efficiency_pilot=True,
        interpretation='Known paired completion and conditional successful time are separate; unknown/unrun/invalid groups stay in full denominator. Two groups cannot prove noninferiority, safety, stable preferences or learned policy benefit.')


def evaluate(shared, protocol_path):
    protocol = read(protocol_path)
    paths={name:Path(shared)/name for name in ('batch_manifest.json','group_split.json','collection_ledger.jsonl')}
    payloads={name:path.read_bytes() for name,path in paths.items()}
    checksums={name:hashlib.sha256(raw).hexdigest() for name,raw in payloads.items()}
    manifest=json.loads(payloads['batch_manifest.json']);split=json.loads(payloads['group_split.json'])
    require(protocol['study_id'] == STUDY and protocol['role'] == ROLE and protocol['decision_event'] == 'original_reset_before_first_skill_action', 'Wrong adopted study/decision/role')
    require(protocol['maximum_new_attempts'] == 6 and protocol['automatic_retry'] is False and protocol['training_enabled'] is False and protocol['model_action_authority'] is False, 'Scope/authority differs')
    registration = manifest.get('skill_choice_studies', {}).get(STUDY)
    require(registration and registration['protocol']['sha256'] == sha(protocol_path), 'Owner study registration missing or differs')
    require(manifest['group_split']['sha256'] == checksums['group_split.json'], 'Canonical split drift')
    by_id = {r['episode_id']: r for r in manifest['physical_episodes']}
    require(len(by_id) == len(manifest['physical_episodes']), 'Duplicate canonical episode')
    slots={r['episode_id']:r for r in manifest['planned_episodes']}
    records = []
    for case in protocol['cases']:
        item = by_id.get(case['episode_id']); arm = case['arm']; config = protocol['arms'][arm]
        require(config['skill_version'] == ARM_VERSIONS[arm] and config['evaluator_sha256'] == EVALUATORS[arm] and config['actor_sha256'] == ACTOR, 'Arm identity drift')
        slot=slots.get(case['episode_id'],{})
        require(slot.get('study_id')==STUDY and slot.get('role')==ROLE and slot.get('arm')==arm, 'Owner planned slot differs')
        started=item is not None or slot.get('status')=='started'
        row = dict(episode_id=case['episode_id'], arm=arm, seed_audit_only=case['seed'], started=started,
                   owner_status=item.get('status') if item else slot.get('status','not_started'), group_id=item.get('group_id') if item else None,
                   source_valid=False, initial_before=None, joint_names=None, task=dict(value=None,valid=False,invalid_reason='not_started_or_not_closed',
                        successful_completion_seconds=None,program_error=False), stage_observations=None)
        if item is not None:
            require(item.get('study_id') == STUDY and item.get('role') == ROLE and item.get('arm') == arm and
                    item.get('skill_version') == ARM_VERSIONS[arm] and item.get('protocol_sha256') == sha(protocol_path) and item.get('seed_audit_only')==case['seed'] and
                    item.get('task_scope')=='original_reset_complete_push_skill_choice' and
                    item.get('model_action_authority') is False and item.get('allowed_for_model_training') is False and
                    item.get('allowed_for_independent_model_validation') is False, 'Canonical selected source identity differs')
            row['canonical_source'] = item
            if item['status'] != 'started':
                try:
                    require(item.get('report') is not None, 'No registered native report')
                    report = verified(item['report']); require(report['seed']==case['seed'], 'Native report reset seed differs')
                    row['task'] = report_label(report, arm, item['returncode'])
                    row['joint_names']=report.get('joint_names')
                    if item.get('sequence') and item.get('metadata'):
                        try:
                            metadata=verified(item['metadata'])
                            require(metadata['evaluator_sha256']==EVALUATORS[arm] and metadata['recorder_sha256']==protocol['code_sha256']['v212_sequence_recording.py'], 'Recorded source drift')
                            require(sha(item['sequence']['path']) == item['sequence']['sha256'], 'Sequence source drift')
                            row['stage_observations'] = sequence_events(item['sequence']['path'], metadata)
                            row['initial_before'] = row['stage_observations']['initial_before']
                        except (ValueError,KeyError,OSError,IndexError,TypeError) as error:
                            row['stage_error']=str(error)
                            # Phase telemetry is optional for native endpoints. An
                            # independent, source-bound startup can still prove t0.
                            row['stage_observations']=None;row['initial_before']=None
                    if item.get('startup') and item.get('group_id'):
                        domain = verified(item['startup']); require(reset_fingerprint(domain) == item['group_id'], 'Measured reset fingerprint differs')
                        initial=domain['initial_states'][0]
                        if row['initial_before'] is None:row['initial_before']=initial
                        else:require(all(key in initial and same(initial[key],row['initial_before'].get(key)) for key in INITIAL_KEYS), 'Startup and first before state differ')
                        group = split['measured_groups'].get(item['group_id'], {})
                        require(group.get('role') == ROLE and item['episode_id'] in group.get('episodes', []), 'Measured owner role/membership differs')
                        row['source_valid'] = True
                except (ValueError, KeyError, OSError, IndexError, TypeError) as error:
                    row['source_error'] = str(error)
        records.append(row)
    for name,path in paths.items():require(sha(path)==checksums[name], 'Canonical registry changed during read-only evaluation; retry evaluation, not physics')
    return dict(schema='reach-existing-push-choice-evaluation-v1', adapter_version='native-arm-endpoints-v1r1', study_id=STUDY, role=ROLE,
        protocol=ref(protocol_path), implementation=ref(__file__), decision_event=protocol['decision_event'],
        registry_snapshot={name:dict(path=str(paths[name]),sha256=value) for name,value in checksums.items()},
        records=records, summary=summarize(records,protocol['cases']),
        allowed_for_model_training=False, allowed_for_independent_model_validation=False,
        registry_or_labels_permissions_mutated=False, new_physical_starts_by_reach=0, model_fits=0, model_forward=0,
        scope='Adopted two-full-call exposed-development pilot only, not original v5 validation, a precontact recovery or controller safety guarantee')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--shared',type=Path,required=True);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite an evaluation result')
    value=evaluate(a.shared,a.protocol);a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(value['summary'],ensure_ascii=False))


if __name__=='__main__':main()
