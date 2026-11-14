"""Read-only, posthoc STATIC ablations. No navigation rollout/success inference.

All arms share the same 75 SE2 candidates within each observed height state.
The cost is the PREVIOUS static alignment/directional-fraction reference, NOT
an actual navigation route cost and NOT the full OmniNav planner.
"""
import argparse
import copy
import json
from pathlib import Path

from piper_kinematics import REPO, sha


def selected_record(row):
    if row is None:
        return dict(status='abstain', candidate_id=None, actual_navigation_success=None)
    out = dict(status='selected_STATIC_nominal_only', candidate_id=row['candidate_id'],
               base_position_world_m=row['body_position_world_m'], yaw_rad=row['body_yaw_rad'],
               reference_cost=row['common_reference_cost'], wide_fraction13=row['wide_fraction13'],
               task_pose_IK_found=row['task_IK_found'], actual_navigation_success=None,
               actual_handoff_success=None, actual_physical_collision=None)
    if row['task_IK_found']:
        path = row['nominal_path']
        samples = path['samples']
        minimum = min(samples, key=lambda s: s['clearance']['minimum_clearance'])
        out.update(endpoint_rho=path['endpoint']['rho'], path_rho=path['path']['rho'],
                   endpoint_model_clearance_m=samples[-1]['clearance']['minimum_clearance'],
                   sampled_path_min_model_clearance_m=minimum['clearance']['minimum_clearance'],
                   minimum_model_pair=minimum['clearance'],
                   all21_nominal_samples_pass=path['path']['status'] == 'feasible')
    return out


def ablations_for_state(rows, height):
    found = [r for r in rows if r['task_IK_found']]
    endpoint = [r for r in found if r['nominal_path']['endpoint']['status'] == 'feasible']
    path = [r for r in found if r['nominal_path']['path']['status'] == 'feasible']
    sets = [('S0_wide_fraction_reference', rows, None),
            ('S1_exact_task_IK_filter', found, None),
            ('S2_endpoint_joint_clearance_gate', endpoint, None),
            ('S3_all21_samples_joint_clearance_gate', path, None),
            ('S4_same_path_gate_plus_frozen_margin_preference', path, 'path'),
            ('S5_S4_plus_analytic_necessary_gate', [r for r in path if r['height_necessary_bound']['exclusion_gap_m'] <= 0], 'path')]
    arms = []
    for name, eligible, margin in sets:
        def key(r):
            rho = r['nominal_path'][margin]['rho'] if margin else 0
            return r['common_reference_cost']-.1*rho, r['candidate_id']
        chosen = min(eligible, key=key) if eligible else None
        arms.append(dict(arm=name, eligible_candidates=len(eligible),
                         selected=selected_record(chosen),
                         selection_scope='this_state_evaluable_subset_NOT_global_optimum_over_unknowns'))
    excluded = [r for r in rows if r['height_necessary_bound']['exclusion_gap_m'] > 0]
    return dict(height_m=height, height_is_condition_NOT_control_action=True, candidates=len(rows),
                task_pose_found=len(found), task_solver_miss_UNKNOWN=len(rows)-len(found),
                endpoint_pass=len(endpoint), sampled_path_pass=len(path),
                endpoint_pass_but_path_violation=[r['candidate_id'] for r in endpoint if r not in path],
                found_but_model_clearance_below35mm=sum(r['nominal_path']['path']['status']=='infeasible' for r in found),
                task_paths_passing_with_global13_below_historical025=sum(r['wide_fraction13'] < .25 for r in path),
                analytic_excluded=len(excluded),
                actual_queries_saved_in_recorded_run=0,
                counterfactual_shared_queries_on_excluded_candidates=sum(len(r['queries']) for r in excluded),
                counterfactual_is_NOT_measured_speedup=True,
                solver_unknown_ids=[r['candidate_id'] for r in rows if not r['task_IK_found']], arms=arms)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    state = REPO/'evidence/2026-10-20/piper-state-height-static-v1'
    old = REPO/'evidence/2026-10-20/piper-source-task-static-v1'
    paths = [state/'new_state_queries_and_paths.json', state/'summary.json',
             old/'candidate_queries_and_paths.json', Path(__file__)]
    new = json.loads(paths[0].read_text())
    summary = json.loads(paths[1].read_text())
    cached = json.loads(paths[2].read_text())
    # Imported helper computes only an analytic bound; no FK/IK occurs here.
    from task_height_bound import height_bound
    contract = json.loads((state/'robot_contract.original.json').read_text())
    old_rows = copy.deepcopy(cached)
    for row in old_rows:
        row['height_necessary_bound'] = height_bound(contract, row['target_base_m'], row['task_quaternion_base_wxyz'])
    states = []
    for h in [.28, .33, .38]:
        rows = old_rows if h == .33 else [r for r in new if r['state_height_m'] == h]
        states.append(ablations_for_state(rows, h))
    report = dict(schema='piper-state-height-static-ablation-posthoc-v1',
                  role='exposed_development_NOT_preregistered_independent_paper_result',
                  source_hashes={str(p.relative_to(REPO)): sha(p) for p in paths},
                  cost_definition='frozen .5*alignment+.5*(1-global13_fraction); NOT_J_nav',
                  margin_weight=.1, original_task_queries_reused_NOT_rerun=975,
                  new_pose_queries=summary['new_pose_queries'], new_IK_attempts=summary['new_IK_attempts'],
                  new_path_samples=summary['new_path_samples'], new_cpu_wall_s=summary['new_study_cpu_wall_s'],
                  states=states, navigation_rollouts=0, physical_collision_or_success_claims=False,
                  supported='endpoint geometry filtering changes static candidate selection at .28m',
                  NOT_supported=['path_gate_increment_over_endpoint_in_this_set', 'margin_preference_physical_gain',
                                 'independent_generalization', 'overall_navigation_success_gain', 'measured_analytic_speedup'])
    with args.output.open('x') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')
    print('height | arm | eligible | selected | sampled model min clearance / mm')
    for state_row in states:
        for a in state_row['arms']:
            r = a['selected']
            print(state_row['height_m'], a['arm'], a['eligible_candidates'], r['candidate_id'],
                  None if 'sampled_path_min_model_clearance_m' not in r else 1000*r['sampled_path_min_model_clearance_m'])


if __name__ == '__main__':
    main()
