"""One frozen source-task study: shared pose queries, sampled self-clearance paths.

No physics integration, controller/actor, fitted shell, or recorded robot outcomes.
A bounded solver miss means UNKNOWN, not a physical reachability failure.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
import traceback

import mujoco
import numpy as np

from model import Constraint, PhaseSample, NominalPath, candidate_score, select_exact_candidate
from piper_kinematics import PiperKinematics, REPO, load_existing, sha, no_physics_steps
from piper_task_geometry import (bind_task_sources, task_world_pose, candidate_grid,
    task_in_base, common_orientation_pool, reference_bounds, quintic_path)


def dump(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')


def constructed_path(model, checker, end, protocol, hard_low, hard_high, *, deadline=None):
    p = protocol['nominal_path']
    phases, qs = quintic_path(model.default_seed, end, p['samples'])
    constraints = [Constraint('self_clearance', 'm', p['clearance_normalization_m']),
                   Constraint('hard_joint', 'rad', p['joint_margin_normalization_rad'])]
    rows, samples = [], []
    initial = model.snapshot()
    for phase, q in zip(phases, qs):
        if deadline is not None and time.perf_counter() > deadline:
            raise TimeoutError('Static path CPU budget reached; no extension')
        if np.any(q < model.oracle.arm_low - 1e-12) or np.any(q > model.oracle.arm_high + 1e-12):
            raise ValueError('Interpolated path outside original 90percent reference interval')
        result = checker.evaluate(np.zeros(3), q, required_clearance=p['self_clearance_required_m'])
        if not model.restored(initial) or model.data.time != 0:
            raise RuntimeError('Clearance checker changed private state or integrated physics')
        joint_margin = float(np.min(np.minimum(q - hard_low, hard_high - q)))
        margins = dict(self_clearance=result.minimum_clearance - p['self_clearance_required_m'],
                       hard_joint=joint_margin - p['hard_joint_margin_required_rad'])
        samples.append(PhaseSample(float(phase), margins))
        rows.append(dict(phase=float(phase), arm_q_rad=q.tolist(), clearance=asdict(result),
                         hard_joint_margin_rad=joint_margin, signed_margins=margins))
    path = NominalPath('single_quintic_first_found', tuple(samples), sample_axis='normalized_phase')
    endpoint = candidate_score([path], constraints, endpoint_only=True)
    whole = candidate_score([path], constraints)
    return dict(construction=p['construction'], axis='normalized_phase_NOT_seconds', samples=rows,
                endpoint=asdict(endpoint), path=asdict(whole)), endpoint, whole


def summarize(rows, endpoint_scores, path_scores, costs, protocol):
    found = [r for r in rows if r['task_IK_found']]
    unknown_ids = [r['candidate_id'] for r in rows if not r['task_IK_found']]
    endpoint_ok = [r for r in found if r['nominal_path']['endpoint']['status'] == 'feasible']
    path_ok = [r for r in found if r['nominal_path']['path']['status'] == 'feasible']
    counterexamples = [r['candidate_id'] for r in endpoint_ok
                      if r['nominal_path']['path']['status'] == 'infeasible']
    select = lambda scores: select_exact_candidate(costs, scores, protocol['comparison']['margin_weight'])
    # Both selectors use EXACT SAME constructed subset, never a global optimum claim.
    selections = dict(scope='constructed_path_subset_only_unknowns_excluded_NOT_global_optimum',
                      constructed_ids=[r['candidate_id'] for r in found], excluded_unknown_ids=unknown_ids,
                      endpoint=select(endpoint_scores), sampled_path=select(path_scores))
    return dict(candidates=len(rows), pose_queries=sum(len(r['queries']) for r in rows),
                IK_attempts=sum(len(q['attempts']) for r in rows for q in r['queries']),
                task_IK_found=len(found), task_solver_miss_UNKNOWN=len(unknown_ids),
                task_found_and_global13_below_historical025=sum(r['wide_fraction13'] < .25 for r in found),
                task_miss_and_global13_atleast_historical025=sum(r['wide_fraction13'] >= .25 for r in rows if not r['task_IK_found']),
                historical025_is_descriptive_only_NOT_fitted_gate=True,
                sampled_paths=len(found), path_samples=sum(len(r['nominal_path']['samples']) for r in found),
                endpoint_35mm_and_hard_joint_nonnegative=len(endpoint_ok),
                all21_samples_35mm_and_hard_joint_nonnegative=len(path_ok),
                endpoint_pass_internal_violation_ids=counterexamples, selections=selections,
                task_found_ids=[r['candidate_id'] for r in found])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('Output already exists: no overwrite or rerun of completed study')
    protocol_path = Path(__file__).with_name('piper_task_protocol_v1.json')
    protocol = json.loads(protocol_path.read_text())
    source_binding = bind_task_sources(protocol)  # check before creating run evidence
    candidates = candidate_grid(protocol)
    if len(candidates) != protocol['resources']['candidate_count']:
        raise ValueError('Unexpected candidate count')
    args.output_dir.mkdir(parents=True)
    (args.output_dir / 'protocol.original.json').write_bytes(protocol_path.read_bytes())
    hashes = {str(p.relative_to(REPO)): sha(p) for p in Path(__file__).parent.iterdir()
              if p.suffix == '.py' or p == protocol_path}
    dump(args.output_dir / 'study_source_hashes.json', hashes)
    began = time.perf_counter()
    rows, endpoints, paths, costs = [], {}, {}, {}
    summary = dict(schema='piper-source-task-static-study-v1', status='NOT_COMPLETED',
                   protocol_sha256=sha(protocol_path), task_source_hashes=source_binding,
                   physical_integration_steps=0, actor_loads=0, training_runs=0,
                   actual_robot_trials=0, python=sys.version.split()[0],
                   numpy=np.__version__, mujoco=mujoco.__version__)
    error = None
    try:
        with no_physics_steps():
            ik = protocol['matched_IK']
            model = PiperKinematics(native_collision_profile=True,
                position_tolerance_m=ik['position_tolerance_m'],
                orientation_tolerance_rad=ik['orientation_tolerance_rad'],
                max_iterations=ik['max_iterations_per_seed'])
            contract = model.contract()  # native HARD limits captured BEFORE private reference restriction
            hard_low, hard_high = model.oracle.arm_low.copy(), model.oracle.arm_high.copy()
            low, high = reference_bounds(hard_low, hard_high, ik['original_reference_limit_fraction'])
            model.oracle.arm_low, model.oracle.arm_high = low, high
            model.default_seed = np.clip(model.default_seed, low, high)
            model.midpoint_seed = (low + high) / 2
            contract.update(study_reference_low_rad=low.tolist(), study_reference_high_rad=high.tolist(),
                study_default_seed_rad=model.default_seed.tolist(), study_midpoint_seed_rad=model.midpoint_seed.tolist(),
                collision_checked_in_study='arm_to_base_and_front_legs_only_per_record',
                private_model_height_m=.35, source_task_candidate_height_m=.33,
                frame_note='relative task pose transformed into identity base axes; .35m private translation cancels for self-distance/FK')
            original_dir = REPO / 'mujoco/reconfigurable_navigation/reachability'
            clearance = load_existing('clearance', original_dir)
            checker = clearance.PiperArmClearanceChecker(model.oracle.runtime,
                protected_body_names=clearance.PROTECTED_BODY_NAMES)
            model.provenance[str((original_dir / 'clearance.py').relative_to(REPO))] = sha(original_dir / 'clearance.py')
            contract.update(protected_body_names=sorted(clearance.PROTECTED_BODY_NAMES),
                            arm_body_names=sorted(clearance.ARM_BODY_NAMES))
            dump(args.output_dir / 'robot_contract.json', contract)
            dump(args.output_dir / 'robot_source_hashes.json', model.provenance)
            initial = model.snapshot()
            target_p, target_q = task_world_pose(protocol)
            summary.update(target_world_m=target_p.tolist(), target_world_wxyz=target_q.tolist())
            for cid, body_p, yaw in candidates:
                p, q_task = task_in_base(body_p, yaw, target_p, target_q)
                orientation_pool = common_orientation_pool(q_task)
                results = []
                for i, q in enumerate(orientation_pool):
                    if time.perf_counter() - began > protocol['resources']['max_cpu_wall_s']:
                        raise TimeoutError('CPU wall budget reached; preserve partial/unknown, no extension')
                    r = model.solve(p, q)
                    r.update(orientation_index=i, quaternion_base_wxyz=q.tolist(), exact_task_orientation=(i == 12))
                    results.append(r)
                task = results[-1]
                wide_fraction = sum(r['found'] for r in results) / len(results)
                delta = target_p[:2] - body_p[:2]
                alignment = float(1 - np.dot([np.cos(yaw), np.sin(yaw)], delta) / np.linalg.norm(delta))
                base_cost = .5 * alignment + .5 * (1 - wide_fraction)
                row = dict(candidate_id=cid, body_position_world_m=body_p.tolist(), body_yaw_rad=yaw,
                    target_base_m=p.tolist(), task_quaternion_base_wxyz=q_task.tolist(), queries=results,
                    wide_fraction13=wide_fraction, task_fraction=1. if task['found'] else 0.,
                    task_IK_found=task['found'], alignment_cost=alignment, common_reference_cost=base_cost,
                    unconstructed_scope='UNKNOWN_not_physical_failure' if not task['found'] else None)
                if task['found']:
                    end = np.array(task['attempts'][-1]['q_rad'])
                    detail, endpoint, path = constructed_path(model, checker, end, protocol, hard_low, hard_high,
                        deadline=began + protocol['resources']['max_cpu_wall_s'])
                    row['nominal_path'] = detail
                    endpoints[cid], paths[cid], costs[cid] = endpoint, path, base_cost
                rows.append(row)
            if not model.restored(initial) or model.data.time != 0:
                raise RuntimeError('Private state restoration or no-physics guard failed')
            summary.update(summarize(rows, endpoints, paths, costs, protocol))
            if summary['pose_queries'] > protocol['resources']['max_pose_queries'] or summary['IK_attempts'] > protocol['resources']['max_IK_attempts'] or summary['path_samples'] > protocol['resources']['max_path_samples']:
                raise RuntimeError('Predeclared budget exceeded')
            summary.update(status='COMPLETED_static_development_NOT_physical_validation', private_state_restored=True,
                           private_data_time_s=float(model.data.time))
    except Exception as exc:
        error = traceback.format_exc()
        summary.update(status='FAILED_preserve_partial_no_retry', error_type=type(exc).__name__, error=str(exc),
                       completed_candidates=len(rows))
    finally:
        summary['cpu_wall_s'] = time.perf_counter() - began
        dump(args.output_dir / 'candidate_queries_and_paths.json', rows)
        dump(args.output_dir / 'summary.json', summary)
        if error:
            (args.output_dir / 'error.txt').write_text(error)
        print(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False))
    return int(error is not None)


if __name__ == '__main__':
    raise SystemExit(main())
