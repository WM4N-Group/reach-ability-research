"""Explicit closed-source reserved conversion; no scanning, fitting or model execution.

Requires a final owner-frozen protocol and owner observation audit. This separate
adapter accepts audited exception prefixes without the old full-terminal builder.
An immutable export is NOT a purpose release; independent consumer alignment and
release_piper_v212_diagnostic.py are still required.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from bind_piper_v212_registry import read, sha
from export_piper_shared_label_examples import label
from export_piper_v212_labels import load_geometry, auxiliary_queries
from piper_v212_diagnostic_contract import (
    ROLE, SCHEMA, require, registry, protocol, observation_audit, source_bindings,
    purpose_permissions, code_hashes,
)

PHYSICAL_KEYS = ('root_position_xyz', 'root_quaternion_wxyz', 'root_linear_velocity_world_mps',
                 'root_angular_velocity_world_radps', 'joint_position_rad', 'joint_velocity_radps',
                 'box_position_xyz', 'box_quaternion_wxyz', 'box_linear_velocity_world_mps',
                 'box_angular_velocity_world_radps', 'feet_position_xyz', 'foot_force_world_n')


def observed_prefix(intervals, metadata, audit, geometry):
    """Only owner-audited contiguous prefix; never pad a future or cross reset.

    Final pre-reset `after` is a target observation, never a decision query.
    A last missing `after` does not discard the observed `before`. Missing geometry
    masks just the auxiliary target through the existing clearance_window kernel.
    """
    n = audit['valid_interval_count']
    require(type(n) is int and 0 <= n <= len(intervals), 'Invalid audited prefix length')
    require(type(audit['final_after_available']) is bool, 'Explicit after availability required')
    if n == 0:
        require(not audit['final_after_available'], 'Empty prefix cannot have terminal after')
        return [], [], [], {}
    require(metadata is not None and metadata['num_envs'] == 1 and metadata['model_action_authority'] is False,
            'Unexpected recorder environment/authority')
    dt = metadata['control_dt_s']
    require(type(dt) in (int, float) and math.isclose(dt, .02, abs_tol=1e-10), 'Expected actual 20ms samples')
    names = metadata['joint_names']
    require(len(names) == len(set(names)), 'Duplicate joint names')
    slots = [names.index(f'joint{i}') for i in range(1, 7)]
    states = []
    previous = None
    for step, row in enumerate(intervals[:n]):
        require(row['index'] == step and row['env_id'] == 0 and
                math.isclose(row['interval_start_s'], step * dt, abs_tol=1e-8) and
                math.isclose(row['interval_end_s'], (step + 1) * dt, abs_tol=1e-8), 'Interval timing/identity gap')
        require(type(row['terminal']) is bool, 'Explicit terminal state required')
        require(not row['terminal'] or step == n - 1, 'Continuation after terminal/reset')
        before = row['before']
        if previous is not None:
            require(all(previous['after'][k] == before[k] for k in PHYSICAL_KEYS), 'Physical state discontinuity')
        # Before is always a real recorded decision-time state.
        require(all(k in before for k in PHYSICAL_KEYS), 'Incomplete observed state')
        states.append(before)
        if step < n - 1 or audit['final_after_available']:
            require(isinstance(row.get('after'), dict) and all(k in row['after'] for k in PHYSICAL_KEYS),
                    'Missing audited after state')
        previous = row
    last = intervals[n - 1]
    if audit['final_after_available']:
        require(not last['terminal'] or last.get('after_captured_before_reset') is True,
                'Terminal after must be captured before reset')
        states.append(last['after'])
    rows = []
    for step, state in enumerate(states):
        value = None
        positions = state.get('joint_position_rad', [])
        if len(positions) == len(names) and all(type(v) in (int, float) and math.isfinite(v) for v in positions):
            measured = float(geometry.clearance([positions[i] for i in slots]))
            value = measured if math.isfinite(measured) else None
        rows.append(dict(step=step, time_s=step * dt, clearance_m=value))
    # auxiliary_queries excludes final state. A missing after still leaves the last
    # before query eligible; append no observation, just a non-iterated sentinel.
    query_states = states if audit['final_after_available'] else states + [None]
    queries = auxiliary_queries(query_states, rows, dt)
    return states, rows, queries, last.get('termination_flags', {})


def convert(item, audit, intervals, metadata, geometry):
    states, rows, queries, flags = observed_prefix(intervals, metadata, audit, geometry)
    end = rows[-1]['time_s'] if rows else None
    status = audit['execution_status']
    success = audit['verified_task_success']
    require(success is None or type(success) is bool, 'Task success must be bool or unknown')
    normal = status in ('normal_completion', 'normal_timeout', 'native_termination')
    if normal:
        require(flags and all(type(v) is bool for v in flags.values()) and any(flags.values()),
                'Native termination flags missing or ambiguous')
        require(rows and intervals[audit['valid_interval_count'] - 1]['terminal'] and audit['final_after_available'],
                'Normal termination needs observed pre-reset terminal after')
        observed_success = flags.get('box_settled') is True and not any(
            v for k, v in flags.items() if k not in ('box_settled', 'time_out'))
        require(success is observed_success and (status == 'normal_completion') == observed_success,
                'Native terminal and owner success disagree')
        require(status != 'normal_timeout' or flags.get('time_out') is True, 'Timeout flag absent')
    else:
        require(success is None or success is True, 'Unknown runtime/missing-log consequence cannot be filled with false')
    if success is True:
        t = audit['verified_goal_time_s']
        require(type(t) in (int, float) and math.isfinite(t) and end is not None and 0 <= t <= end,
                'Verified success requires an observed goal timestamp')
    contact = next((r['time_s'] for r, s in zip(rows, states) if s['legal_hand_contact'] is True and
                    not s['invalid_hand_contact'] and not s['forbidden_box_contact']), None)
    reason = None if success is not None else 'unknown_physical_outcome_after_' + status
    outcome = label(success, reason, audit['verified_goal_time_s'] if success is True else end, 'owner_verified_native_event' if success is not None else None,
                    end if success is None else None)
    contact_label = label(True, None, contact, 'observed_legal_contact') if contact is not None else label(
        False if normal else None, None if normal else 'unobserved_contact_outcome', end,
        'native_terminal' if normal else None, end if not normal else None)
    return dict(episode_id=item['episode_id'], group_id=item['group_id'], owner_recorded_role=ROLE,
                skill_version=item['skill_version'], task_scope=item['task_scope'],
                sources=source_bindings(item), observation_audit=item['diagnostic_observation_audit'],
                source_path=(item.get('sequence') or {}).get('path'),
                report_sha256=(item.get('report') or {}).get('sha256'),
                source_sha256=(item.get('sequence') or {}).get('sha256'),
                execution_status=status, verified_task_success=success, native_flags=flags,
                verified_goal_time_s=audit.get('verified_goal_time_s'),
                exception_type=audit.get('exception_type'), exception_time_s=audit.get('exception_time_s'),
                last_valid_observation_time_s=end, actual_sample_period_s=.02,
                first_recorded_legal_contact_s=contact, query_count=len(queries),
                no_valid_queries=not queries, no_complete_auxiliary_targets=not any(
                    t['valid'] for q in queries for t in q['targets']),
                stages=dict(transition_complete=label(None, 'no_nav_transition_in_independent_push', end),
                            contact_established=contact_label, push_complete=outcome,
                            whole_task_complete=outcome,
                            exit_complete=label(None, 'not_entered_in_independent_push_task', end),
                            next_skill_complete=label(None, 'not_entered_in_independent_push_task', end)),
                queries=queries)


def export(shared, source_root, protocol_path, episode_ids):
    manifest, split, selected, snapshots = registry(shared, episode_ids)
    psha = sha(protocol_path)
    frozen = protocol(protocol_path, episode_ids, split['version'], snapshots['label_contract_v1.json']['sha256'])
    audits = [observation_audit(item, psha) for item in selected]
    for a in audits:
        require(a['auditor'] == frozen['observation_auditor'], 'Unfrozen observation auditor')
    geometry, provenance = (load_geometry(source_root) if any(a['valid_interval_count'] for a in audits)
                            else (None, None))
    if provenance is not None:
        require(provenance['manifest_sha256'] == manifest['frozen_skill_inventory']['sha256'], 'Geometry inventory drift')
    episodes = []
    for item, audit in zip(selected, audits):
        n = audit['valid_interval_count']
        if not item['recorded']:
            require(n == 0 and audit['execution_status'] == 'missing_log', 'Missing log needs explicit zero-prefix disposition')
        metadata = read(item['metadata']['path']) if item.get('metadata') else None
        if metadata is not None:
            require(metadata['recorder_sha256'] == frozen['recorder_sha256'] and
                    metadata['evaluator_sha256'] == frozen['evaluator_sha256'], 'Recorder/evaluator drift')
        intervals = []
        if item.get('sequence'):
            with Path(item['sequence']['path']).open() as stream:
                for _ in range(n):
                    intervals.append(json.loads(next(stream)))
        episode = convert(item, audit, intervals, metadata, geometry)
        episode['group_split_version'] = split['version']
        episode['skill_bundle_hash'] = manifest['frozen_skill_inventory']['sha256']
        if 'query_count' in item:
            require(item['query_count'] == episode['query_count'], 'Owner query denominator differs')
        if 'outcome' in item and 'verified_task_success' in item['outcome']:
            require(item['outcome']['verified_task_success'] is episode['verified_task_success'],
                    'Owner manifest outcome differs')
        episodes.append(episode)
    # Recheck only identities/refs, allowing unrelated owner-registry appends.
    _, live_split, current, live_snapshots = registry(shared, episode_ids)
    require(current == selected and live_split['version'] == split['version'] and sha(protocol_path) == psha and
            live_snapshots['label_contract_v1.json']['sha256'] == snapshots['label_contract_v1.json']['sha256'],
            'Selected registry/protocol changed during conversion')
    for item in selected:
        observation_audit(item, psha)
    return dict(schema=SCHEMA, label_schema_version='reach-wm-v212-v1', dataset_role=ROLE,
                evaluation_protocol=dict(path=str(Path(protocol_path).resolve()), sha256=psha),
                group_split_version=split['version'], contract_sha256=snapshots['label_contract_v1.json']['sha256'],
                registry_snapshots=snapshots, reach_code_sha256=code_hashes(), geometry_provenance=provenance,
                **purpose_permissions(), permissions=purpose_permissions(), training_released=False, development_evaluation_released=False,
                diagnostic_evaluation_released=False, independent_alignment='pending',
                episodes=episodes, episode_count=len(episodes), independent_group_count=len({e['group_id'] for e in episodes}),
                new_physical_episodes=0, reserved_source_outcomes_read=True,
                denominator='Every explicitly requested closed attempt, including exceptions/missing/zero-query attempts; owner ledger remains authoritative')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('shared', 'source-root', 'protocol', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--episode-id', action='append', required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('Refusing to overwrite diagnostic labels')
    result = export(a.shared, a.source_root, a.protocol, a.episode_id)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print('Exported closed reserved sources; diagnostic release still pending')


if __name__ == '__main__':
    main()
