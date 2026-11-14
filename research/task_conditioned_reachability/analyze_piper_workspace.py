"""Posthoc developer diagnosis of one completed static map, without new IK.

Retain rejected global shell. Report ALL12 directional slices, not the best one.
Conditional slice fitting changes the query, NOT the original .25 global gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from piper_kinematics import sha
from workspace_fit import fit_dual_ellipsoid, approximation_metrics


def analyze(root):
    summary = json.loads((root / 'summary.json').read_text())
    protocol = json.loads((root / 'protocol.original.json').read_text())
    rows = json.loads((root / 'pose_ik_map.json').read_text())
    orientations = json.loads((root / 'target_orientations_base_wxyz.json').read_text())
    contract = json.loads((root / 'robot_contract.json').read_text())
    # Verify all original map payloads before consuming; never run the solver.
    for name, expected in summary['evidence_sha256'].items():
        if sha(root / name) != expected:
            raise ValueError(f'Original map evidence hash mismatch: {name}')
    if len(rows) != 189 or any(r['orientations_tested'] != 12 for r in rows):
        raise ValueError('Not a complete189x12 original map; no analysis from partial grid')
    train = [r for r in rows if r['split'] == 'fit_development']
    val = [r for r in rows if r['split'] == 'validation_spatial_holdout']
    ptrain = [r['target_base_m'] for r in train]
    pval = [r['target_base_m'] for r in val]
    all_found = [r for row in rows for r in row['orientation_results'] if r['found']]
    original_fit_positive = sum(r['psi_sampled'] >= .25 for r in train)
    assert original_fit_positive == 0
    directional = []
    for i, q in enumerate(orientations):
        flags_train = [float(r['orientation_results'][i]['found']) for r in train]
        flags_val = [float(r['orientation_results'][i]['found']) for r in val]
        config = {**protocol['fit'], 'positive_success_fraction_threshold': 1.0}
        result = dict(orientation_index=i, target_quaternion_base_wxyz=q,
                      found_train_positions=int(sum(flags_train)), found_validation_positions=int(sum(flags_val)))
        try:
            fitted = fit_dual_ellipsoid(ptrain, flags_train, config)
            result.update(status='DIRECTIONAL_DEVELOPMENT_FIT_ONLY', fit=fitted,
                          fit_metrics=approximation_metrics(ptrain, flags_train, fitted),
                          validation_metrics=approximation_metrics(pval, flags_val, fitted))
        except ValueError as exc:
            result.update(status='DIRECTIONAL_FIT_UNSUPPORTED', reason=str(exc))
        directional.append(result)
    return dict(schema='piper-static-map-posthoc-diagnosis-v1',
                global_v1_fit_status_preserved=summary['status'],
                original_protocol_and_grid_unchanged=True,
                original_global_success_fraction_threshold=.25,
                original_global_positive_train_positions=original_fit_positive,
                total_pose_queries=2268,
                total_IK_attempts=sum(len(r['attempts']) for row in rows for r in row['orientation_results']),
                found_pose_queries=len(all_found),
                max_fresh_FK_position_error_m=max(r['verified_position_error_m'] for r in all_found),
                max_fresh_FK_orientation_error_rad=max(r['verified_orientation_error_rad'] for r in all_found),
                training_success_count_histogram={str(n):sum(r['bounded_IK_found']==n for r in train) for n in range(13)},
                validation_success_count_histogram={str(n):sum(r['bounded_IK_found']==n for r in val) for n in range(13)},
                robot_mount_position_in_base_m=contract['mount_position_in_base_m'],
                directional_development_fits=directional,
                orientation_selected_or_tuned_for_real_task=False,
                scope='Posthoc directional slice developer diagnosis, ALL12 orientations retained. '
                      'Binary task-orientation found labels are a DIFFERENT query from12-direction global fraction. '
                      'Not repair/acceptance of rejectedv1, exact OmniNav fit, new measured trials, '
                      'independent task validation or a choice of best task orientation after seeing outcomes.',
                proposed_math_query='psi_a(p;s)=sum_i omega_a(R_i)*I[bounded_pose_IK_found]/sum_i omega_a(R_i); '
                                    'task allowable orientations/weights must be set BEFORE later real tests, not chosen from this result.',
                next_limit='Before claiming effect, bind actual Piper task orientation and model/path/force domain. '
                           'Bounded IK misses remain unknown, not proof of global unreachability. No new grid/threshold change here.',
                original_map_refs={name:sha(root/name) for name in ['summary.json','protocol.original.json',
                                      'robot_contract.json','pose_ik_map.json','target_orientations_base_wxyz.json']},
                new_IK_or_FK_or_physics_or_actor_runs=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map-dir',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output exists; never overwrite original evidence')
    began=time.perf_counter();out=analyze(args.map_dir);out['elapsed_cpu_wall_s']=time.perf_counter()-began
    with args.output.open('x') as f:json.dump(out,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print('Found pose queries:',out['found_pose_queries'],'original global fit positives:',out['original_global_positive_train_positions'])
    print('ALL12 directional fit outcomes:',[(x['orientation_index'],x['status'],x['found_train_positions']) for x in out['directional_development_fits']])
    for x in out['directional_development_fits']:
        if x['status']=='DIRECTIONAL_DEVELOPMENT_FIT_ONLY':
            m=x['validation_metrics'];print(x['orientation_index'],'validation TP/FP/FN/TN',[m[k] for k in ['true_positive_vs_sampled_rate','false_accept_vs_sampled_rate','false_reject_vs_sampled_rate','true_negative_vs_sampled_rate']])


if __name__=='__main__':main()
