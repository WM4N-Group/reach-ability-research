"""New static state-height comparison; reuse closed .33m queries, no rerun.

Height is a condition, not a delivered navigation action. All13 queries still
run for every NEW candidate. Analytic pruning counts are not measured speedups.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import time
import traceback

import mujoco
import numpy as np

from model import Constraint, PhaseSample, NominalPath, candidate_score
from piper_kinematics import REPO, PiperKinematics, load_existing, no_physics_steps, sha
from piper_task_geometry import (bind_task_sources, task_world_pose, candidate_grid,
    task_in_base, common_orientation_pool, reference_bounds)
from run_piper_task_study import constructed_path, summarize, dump
from task_height_bound import height_bound

PROTOCOL_PATH = Path(__file__).with_name('piper_state_height_protocol_v1.json')


def load_frozen_inputs():
    p = json.loads(PROTOCOL_PATH.read_text())
    parent_path = REPO / p['parent_task_protocol']
    if sha(parent_path) != p['parent_task_protocol_sha256']:
        raise ValueError('Parent source task protocol changed')
    parent = json.loads(parent_path.read_text())
    bind_task_sources(parent)
    old = REPO / p['reused_control']['study_dir']
    for filename, key in [('candidate_queries_and_paths.json', 'queries_sha256'),
                          ('robot_contract.json', 'robot_contract_sha256')]:
        if sha(old / filename) != p['reused_control'][key]:
            raise ValueError('Closed control evidence changed')
    if (p['new_state_heights_m'] != [.28, .38] or p['reused_control']['height_m'] != .33
            or p['reused_control']['rerun_control'] is not False):
        raise ValueError('Only the frozen distinct state heights are implemented')
    cached = json.loads((old / 'candidate_queries_and_paths.json').read_text())
    contract = json.loads((old / 'robot_contract.json').read_text())
    if len(cached) != 75 or any(r['body_position_world_m'][2] != .33 for r in cached):
        raise ValueError('Unexpected reused control domain')
    return p, parent, cached, contract


def height_candidates(parent, height):
    if height not in (.28, .38):
        raise ValueError('Closed .33m control must be reused, not re-executed')
    return [(cid, np.array([pos[0], pos[1], height]), yaw)
            for cid, pos, yaw in candidate_grid(parent)]


def row_scores(rows, parent):
    p = parent['nominal_path']
    constraints = [Constraint('self_clearance', 'm', p['clearance_normalization_m']),
                   Constraint('hard_joint', 'rad', p['joint_margin_normalization_rad'])]
    endpoints, paths, costs = {}, {}, {}
    for r in rows:
        if not r['task_IK_found']:
            continue
        raw = r['nominal_path']
        path = NominalPath(raw['construction'], tuple(PhaseSample(s['phase'], s['signed_margins']) for s in raw['samples']),
                           sample_axis='normalized_phase')
        cid = r['candidate_id']
        endpoints[cid] = candidate_score([path], constraints, endpoint_only=True)
        paths[cid] = candidate_score([path], constraints)
        costs[cid] = r['common_reference_cost']
    return endpoints, paths, costs


def per_state_summary(rows, parent):
    endpoints, paths, costs = row_scores(rows, parent)
    report = summarize(rows, endpoints, paths, costs, parent)
    report.update(height_is_condition_NOT_NAV_action=True,
                  analytic_reference_excluded=sum(r['height_necessary_bound']['exclusion_gap_m'] > 0 for r in rows),
                  analytic_exclusion_and_task_IK_found=sum(r['height_necessary_bound']['exclusion_gap_m'] > 0 and r['task_IK_found'] for r in rows),
                  endpoint_path_disagreement_count=len(report['endpoint_pass_internal_violation_ids']))
    return report


def evaluate_new_candidate(model, checker, contract, parent, state_protocol, cid, body_p, yaw, deadline):
    target_p, target_q = task_world_pose(parent)
    p, q_task = task_in_base(body_p, yaw, target_p, target_q)
    bound = height_bound(contract, p, q_task)
    began = time.perf_counter()
    results = []
    for i, q in enumerate(common_orientation_pool(q_task)):
        if time.perf_counter() > deadline:
            raise TimeoutError('State-height CPU budget reached; preserve partial, no extension')
        result = model.solve(p, q)
        result.update(orientation_index=i, quaternion_base_wxyz=q.tolist(), exact_task_orientation=(i == 12))
        results.append(result)
    ik_wall = time.perf_counter() - began
    task = results[-1]
    if bound['exclusion_gap_m'] > 0 and task['found']:
        raise RuntimeError('Analytic exclusion contradicted by verified task IK witness')
    wide = sum(q['found'] for q in results) / 13
    delta = target_p[:2] - body_p[:2]
    alignment = float(1 - np.dot([np.cos(yaw), np.sin(yaw)], delta) / np.linalg.norm(delta))
    row = dict(candidate_id=cid, state_height_m=float(body_p[2]), body_position_world_m=body_p.tolist(),
        body_yaw_rad=yaw, target_base_m=p.tolist(), task_quaternion_base_wxyz=q_task.tolist(),
        queries=results, wide_fraction13=wide, task_fraction=float(task['found']), task_IK_found=task['found'],
        alignment_cost=alignment, common_reference_cost=.5*alignment+.5*(1-wide),
        height_necessary_bound=bound, reused_control=False, pose_queries_wall_s=ik_wall,
        unconstructed_scope=None if task['found'] else 'UNKNOWN_not_physical_failure')
    if task['found']:
        began = time.perf_counter()
        path, _, _ = constructed_path(model, checker, np.array(task['attempts'][-1]['q_rad']), parent,
            np.array(contract['hard_joint_low_rad']), np.array(contract['hard_joint_high_rad']), deadline=deadline)
        row.update(nominal_path=path, sampled_path_wall_s=time.perf_counter()-began)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('Existing output directory cannot be overwritten/retried')
    protocol, parent, cached, contract = load_frozen_inputs()
    args.output_dir.mkdir(parents=True)
    (args.output_dir / 'protocol.original.json').write_bytes(PROTOCOL_PATH.read_bytes())
    sources = [p for p in Path(__file__).parent.iterdir() if p.suffix in ('.py', '.json')]
    dump(args.output_dir / 'study_source_hashes.json', {str(p.relative_to(REPO)): sha(p) for p in sources})
    began = time.perf_counter()
    rows, error = [], None
    summary = dict(schema='piper-state-height-development-study-v1', status='NOT_COMPLETED',
                   protocol_sha256=sha(PROTOCOL_PATH), physical_integration_steps=0, actor_runs=0, training_runs=0,
                   python=sys.version.split()[0], mujoco=mujoco.__version__, numpy=np.__version__,
                   cached_control_height_m=.33, control_rerun=False, height_is_NOT_executable_NAV_action=True,
                   measured_navigation_or_task_rollouts=0)
    try:
        with no_physics_steps():
            ik = parent['matched_IK']
            model = PiperKinematics(native_collision_profile=True, position_tolerance_m=ik['position_tolerance_m'],
                orientation_tolerance_rad=ik['orientation_tolerance_rad'], max_iterations=ik['max_iterations_per_seed'])
            for rel, expected in contract['profile_USD_and_model_assets'].items():
                if sha(REPO / rel) != expected:
                    raise ValueError('Source mismatch with cached control: '+rel)
            for key, array in [('hard_joint_low_rad', model.oracle.arm_low), ('hard_joint_high_rad', model.oracle.arm_high)]:
                np.testing.assert_array_equal(contract[key], array)
            low, high = reference_bounds(model.oracle.arm_low, model.oracle.arm_high)
            model.oracle.arm_low, model.oracle.arm_high = low, high
            model.default_seed = np.clip(model.default_seed, low, high)
            model.midpoint_seed = (low+high)/2
            np.testing.assert_array_equal(model.default_seed, contract['study_default_seed_rad'])
            np.testing.assert_array_equal(model.midpoint_seed, contract['study_midpoint_seed_rad'])
            dump(args.output_dir / 'robot_contract.original.json', contract)
            clearance = load_existing('clearance', REPO / 'mujoco/reconfigurable_navigation/reachability')
            checker = clearance.PiperArmClearanceChecker(model.oracle.runtime, protected_body_names=clearance.PROTECTED_BODY_NAMES)
            initial = model.snapshot()
            for h in protocol['new_state_heights_m']:
                for cid, body_p, yaw in height_candidates(parent, h):
                    rows.append(evaluate_new_candidate(model, checker, contract, parent, protocol, cid, body_p, yaw,
                                began+protocol['resources']['max_cpu_wall_s']))
            if not model.restored(initial) or model.data.time != 0:
                raise RuntimeError('Private state/time restoration failed')
            new_queries = sum(len(r['queries']) for r in rows)
            attempts = sum(len(q['attempts']) for r in rows for q in r['queries'])
            samples = sum(len(r['nominal_path']['samples']) for r in rows if r['task_IK_found'])
            r = protocol['resources']
            if (len(rows) > r['new_candidates'] or new_queries > r['max_new_pose_queries']
                    or attempts > r['max_new_IK_attempts'] or samples > r['max_new_path_samples']):
                raise RuntimeError('Predeclared resource budget exceeded')
            old_rows = copy.deepcopy(cached)
            for row in old_rows:
                row['reused_control'] = True
                row['height_necessary_bound'] = height_bound(contract, row['target_base_m'], row['task_quaternion_base_wxyz'])
            states = {str(h): [x for x in (old_rows if h == .33 else rows) if x['body_position_world_m'][2] == h]
                      for h in protocol['combined_state_heights_m']}
            summary.update(status='COMPLETED_static_state_development_NOT_navigation_validation',
                new_candidates=len(rows), reused_candidates=len(old_rows), new_pose_queries=new_queries,
                new_IK_attempts=attempts, new_path_samples=samples,
                private_state_restored=True, private_time_s=float(model.data.time),
                states={h: per_state_summary(rs, parent) for h, rs in states.items()})
    except Exception as exc:
        error = traceback.format_exc()
        summary.update(status='FAILED_preserve_partial_no_retry', error_type=type(exc).__name__, error=str(exc),
                       completed_new_candidates=len(rows))
    finally:
        summary['new_study_cpu_wall_s'] = time.perf_counter()-began
        dump(args.output_dir / 'new_state_queries_and_paths.json', rows)
        dump(args.output_dir / 'summary.json', summary)
        if error:
            (args.output_dir / 'error.txt').write_text(error)
        print(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False))
    return int(error is not None)


if __name__ == '__main__':
    raise SystemExit(main())
