"""Export v212 P0 labels from recorded actual states; no physics or model fitting."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

from audit_piper_source_transition_trace import sha256
from export_piper_shared_label_examples import clearance_window, label


def load_geometry(source_root):
    manifest_path = source_root.parent.parent.parent/'GO2-PIPER-SIM2REAL/docs/push-v212-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    entries = [e for e in manifest['files'] if '/runtime-push-detour-v1/mujoco/' in e['path']]
    if len(entries) != 225:
        raise ValueError('Unexpected geometry inventory; register a new adapter')
    for entry in entries:
        p = source_root.parent/entry['path'].split('/artifacts/go2-piper/', 1)[1]
        if sha256(p) != entry['sha256']:
            raise ValueError(f'Geometry inventory mismatch: {p}')
    plan = json.loads((source_root/'push-direct-approach-v212/plan.json').read_text())
    rel = 'source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/leggedmanip_lab/mdp/box_push_geometry.py'
    module_path = source_root/'push-direct-approach-v212/train'/rel
    if sha256(module_path) != plan['source_hashes'][rel]:
        raise ValueError('Frozen geometry code mismatch')
    geometry_root = source_root/'runtime-push-detour-v1/mujoco'
    sys.path.insert(0, str(geometry_root))
    spec = importlib.util.spec_from_file_location('reach_frozen_v212_geometry', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    geometry = module.PiperBaseArmGeometryShield(geometry_root, 0.035)
    provenance = dict(manifest_path=str(manifest_path), manifest_sha256=sha256(manifest_path),
                      geometry_files_matched=len(entries), code_path=str(module_path),
                      code_sha256=sha256(module_path), origin='recomputed_from_actual_state',
                      operation='mj_forward and geometry distance only; never mj_step or Isaac',
                      distance_pairs='profile link1-link6 collision geometries vs base_link')
    return geometry, provenance


def normalize(intervals, metadata, geometry):
    """Input interval continuity/pre-reset integrity must pass owner audit first."""
    import numpy as np
    names = metadata['joint_names']
    slots = [names.index(f'joint{i}') for i in range(1, 7)]
    states = [r['before'] for r in intervals]+[intervals[-1]['after']]
    dt = metadata['control_dt_s']
    rows = []
    for step, state in enumerate(states):
        actual = np.asarray([state['joint_position_rad'][i] for i in slots])
        clearance = float(geometry.clearance(actual))
        if not math.isfinite(clearance):
            raise ValueError('Nonfinite actual-state geometry')
        rows.append(dict(step=step, time_s=step*dt, clearance_m=clearance))
    return states, rows


def auxiliary_queries(states, rows, dt):
    contact_seen = False
    queries = []
    for step, state in enumerate(states[:-1]):
        contact_seen |= bool(state['legal_hand_contact'] and not state['invalid_hand_contact']
                             and not state['forbidden_box_contact'])
        if step % 5:
            continue
        queries.append(dict(query_time_s=step*dt,
            query_event='skill_initial' if step==0 else 'observed_control_sample',
            remaining_budget_s=48.0-step*dt,
            inputs=dict(actual_clearance_m=rows[step]['clearance_m'], legal_contact_seen=contact_seen),
            history_0p4s_available=step*dt>=0.4-1e-8,
            targets=[dict(name='arm_base_clearance_margin_min_m',
                          **clearance_window(rows, step, dt, h)) for h in (0.4,1.0)]))
    return queries


def baseline_summary(episodes):
    result = []
    for horizon in (0.4, 1.0):
        per_group = []
        for ep in episodes:
            labels = [t for q in ep['queries'] if q['inputs']['legal_contact_seen']
                      and q['history_0p4s_available'] for t in q['targets']
                      if t['requested_horizon_s']==horizon and t['valid']]
            errors = [t['constant_reference_m']-t['value'] for t in labels]
            if errors:
                per_group.append(dict(group_id=ep['group_id'],count=len(errors),
                    mae_m=sum(abs(e) for e in errors)/len(errors),
                    mean_optimistic_error_m=sum(max(e,0) for e in errors)/len(errors),
                    max_optimistic_error_m=max(max(e,0) for e in errors)))
        result.append(dict(horizon_s=horizon,
            query_scope='causal_legal_contact_seen_and_0.4s_history_and_complete_horizon',
            reference='current_actual_clearance_minus_35mm', independent_groups=len(per_group),
            mean_group_mae_m=sum(g['mae_m'] for g in per_group)/len(per_group) if per_group else None,
            groups=per_group, calibration_status='training_diagnostic_only_no_risk_threshold_fitted'))
    return result


def export(batch_root, source_root, world_scripts, contract_path):
    sys.path.insert(0, str(world_scripts))
    from build_v212_sequences import build
    contract = json.loads(contract_path.read_text())
    if contract['label_schema_version']!='reach-wm-v212-v1' or contract['auxiliary_target']['threshold_m']!=0.035:
        raise ValueError('Contract drift')
    geometry, provenance = load_geometry(source_root)
    episodes = []
    # Only the already exposed three P0 training groups. Never discover/read reserved runs.
    for name in ('p0-02-recorded-5301','p0-03-recorded-5302','p0-04-recorded-5303'):
        root = batch_root/name
        built = build(root, 'train')  # Owner's official source/time/continuity audit and group fingerprint.
        meta = json.loads((root/'sequence-meta.json').read_text())
        if meta['recorder_sha256']!=sha256(world_scripts/'v212_sequence_recording.py'):
            raise ValueError('Recorder source mismatch')
        intervals = [json.loads(line) for line in (root/'control-sequence.jsonl').read_text().splitlines()]
        report = json.loads((root/'report.json').read_text())
        if meta['evaluator_sha256']!=sha256(source_root/'push-direct-approach-v212/train/scripts/evaluate_residual_push.py'):
            raise ValueError('Evaluator source mismatch')
        states, rows = normalize(intervals, meta, geometry)
        dt, end = meta['control_dt_s'], rows[-1]['time_s']
        flags = intervals[-1]['termination_flags']
        success = flags.get('box_settled') is True and not any(v for k,v in flags.items() if k not in ('box_settled','time_out'))
        if success != built['terminal_label']['success']:
            raise ValueError('Terminal success flags conflict with owner report')
        contact = next((r['time_s'] for r,s in zip(rows,states)
                        if s['legal_hand_contact'] and not s['invalid_hand_contact'] and not s['forbidden_box_contact']), None)
        approach = next((r['time_s'] for r,s in zip(rows,states)
                         if s['controller_observed']['safe_approach_complete'] is True),None)
        next_not_entered = label(None,'not_entered_in_independent_push_task',end)
        episodes.append(dict(episode_id=name, source_path=str(root/'control-sequence.jsonl'),
            source_sha256=sha256(root/'control-sequence.jsonl'), report_sha256=sha256(root/'report.json'),
            skill_version='push-direct-approach-v212', task_scope='original_reset_independent_push',
            skill_bundle_hash=provenance['manifest_sha256'],
            bundle_hash_semantics='SHA256 of owner frozen v212 inventory; run source checked by owner audit',
            group_id=built['group_id'], owner_recorded_role='train', group_split_version=None,
            split_status='owner_P0_train_role_known_shared_canonical_split_pending',
            execution_status='normal_completion' if success else 'normal_timeout' if flags.get('time_out') else 'native_termination',
            verified_task_success=success, native_flags=flags,
            last_valid_observation_time_s=end, actual_sample_period_s=dt,
            first_recorded_legal_contact_s=contact, first_recorded_safe_approach_complete_s=approach,
            stages=dict(transition_complete=label(None,'no_nav_transition_in_independent_push',end),
                contact_established=label(contact is not None,None,contact if contact is not None else end,'observed_legal_contact'),
                push_complete=label(success,None,end,'native_terminal'),
                whole_task_complete=label(success,None,end,'native_terminal_independent_push_scope'),
                exit_complete=next_not_entered, next_skill_complete=next_not_entered),
            sampled_actual_clearance_range_m=[min(r['clearance_m'] for r in rows),max(r['clearance_m'] for r in rows)],
            physical_safety_report=report['physical_safety_control_samples'],
            queries=auxiliary_queries(states, rows, dt)))
    return dict(label_schema_version=contract['label_schema_version'],
        adapter_version='v212-recorded-p0-labels-v1r1', exporter_sha256=sha256(Path(__file__)),
        window_kernel_sha256=sha256(Path(__file__).with_name('export_piper_shared_label_examples.py')),
        contract_sha256=sha256(contract_path), geometry_provenance=provenance,
        owner_builder_path=str(world_scripts/'build_v212_sequences.py'),
        owner_builder_sha256=sha256(world_scripts/'build_v212_sequences.py'),
        owner_auditor_sha256=sha256(world_scripts/'audit_v212_sequence.py'),
        episode_count=len(episodes), physical_episode_count_added=0,
        scope='P0 training-group offline labels; not reserved evaluation or full-chain safety acceptance',
        cross_group_alignment='pending_owner_review', episodes=episodes,
        rule_baselines=baseline_summary(episodes))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-root',type=Path,required=True)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--world-scripts',type=Path,required=True)
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite labels')
    result=export(args.batch_root,args.source_root,args.world_scripts,args.contract)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(episodes=result['episode_count'],
                         queries=sum(len(e['queries']) for e in result['episodes']),
                         new_physical_episodes=0)))


if __name__=='__main__':
    main()
