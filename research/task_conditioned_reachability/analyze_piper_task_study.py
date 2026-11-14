"""Read-only diagnosis of an exposed study; never FK/IK, fit, seeds, or thresholds."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study_dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.study_dir / 'candidate_queries_and_paths.json'
    summary_path = args.study_dir / 'summary.json'
    contract_path = args.study_dir / 'robot_contract.json'
    rows = json.loads(source.read_text())
    summary = json.loads(summary_path.read_text())
    contract = json.loads(contract_path.read_text())
    pos_tol, ang_tol = contract['position_tolerance_m'], contract['orientation_tolerance_rad']
    low, high = contract['study_reference_low_rad'], contract['study_reference_high_rad']
    tasks, saturation = [], [0] * len(low)
    for r in rows:
        for a in r['queries'][-1]['attempts']:
            tasks.append((r['candidate_id'], a))
            for j, v in enumerate(a['q_rad']):
                saturation[j] += int(abs(v-low[j]) < 1e-8 or abs(v-high[j]) < 1e-8)
    def residual_record(pair):
        cid, a = pair
        return dict(candidate_id=cid, seed=a['seed'], position_error_m=a['position_error_m'],
                    orientation_error_rad=a['orientation_error_rad'], joint_margin_rad=a['joint_margin_rad'])
    counts = [sum(r['queries'][i]['found'] for r in rows) for i in range(13)]
    # These minima are labelled diagnostic only, NOT new seeds or chosen candidates.
    out = dict(schema='piper-source-task-exposed-readonly-diagnosis-v1',
        source_hashes={p.name: sha(p) for p in (source, summary_path, contract_path)},
        study_status=summary['status'], candidates=len(rows), found_by_orientation_index=counts,
        orientation_index12_is_source_task=True,
        global13_found_histogram={str(n): sum(sum(q['found'] for q in r['queries']) == n for r in rows)
                                 for n in sorted({sum(q['found'] for q in r['queries']) for r in rows})},
        task_attempts=len(tasks), task_attempts_position_tolerance_met=sum(a['position_error_m'] <= pos_tol for _, a in tasks),
        task_attempts_orientation_tolerance_met=sum(a['orientation_error_rad'] <= ang_tol for _, a in tasks),
        task_attempts_both_tolerances_met=sum(a['position_error_m'] <= pos_tol and a['orientation_error_rad'] <= ang_tol for _, a in tasks),
        task_attempts_touching_reference_boundary_by_joint=saturation,
        min_position_residual_attempt=residual_record(min(tasks, key=lambda p: p[1]['position_error_m'])),
        min_orientation_residual_attempt=residual_record(min(tasks, key=lambda p: p[1]['orientation_error_rad'])),
        explanation='Failure means no bounded solution found; boundary/residual data do NOT certify infeasibility or identify a causal solver fault.',
        path_comparison_status='NOT_EVALUABLE_no_source_task_pose_solution' if not summary['sampled_paths'] else 'see_original_matched_paths',
        formula_benefit='NOT_ESTABLISHED', no_new_FK_IK_or_physics=True,
        next_question='Need independently source-bound positive pose witnesses and independent solver/analytic check under NEW declared protocol; do not tune or rerun this configuration.')
    with args.output.open('x') as f:
        json.dump(out, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
