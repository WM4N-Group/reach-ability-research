"""Build one frozen-protocol static Piper pose-IK map and training-only shell.

No simulation integration, actors, recorded robot data, grid extension or retry.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import traceback

import mujoco
import numpy as np

from model import Ellipsoid, OmniNavParameters, BasePose, omninav_cost
from piper_kinematics import PiperKinematics, no_physics_steps, sha
from workspace_fit import position_grids, orientation_matrices, fit_dual_ellipsoid, approximation_metrics


def dump(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=Path(__file__).with_name('piper_map_protocol_v1.json'))
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('Output directory exists; choose one new study directory, no overwrites/retries')
    protocol_bytes = args.protocol.read_bytes()
    protocol = json.loads(protocol_bytes)
    expected = json.loads(Path(__file__).with_name('piper_map_protocol_v1.json').read_text())
    if protocol != expected:
        parser.error('This baseline implements only the explicit predeclared v1 protocol')
    train, validation = position_grids(protocol)
    rotations = orientation_matrices()
    assert (len(train) + len(validation)) * len(rotations) == protocol['resources']['max_queries']
    args.output_dir.mkdir(parents=True)
    (args.output_dir / 'protocol.original.json').write_bytes(protocol_bytes)
    source_hashes = {p.name: sha(p) for p in Path(__file__).parent.iterdir()
                     if p.suffix == '.py' or p.name == 'piper_map_protocol_v1.json'}
    dump(args.output_dir / 'source_hashes.json', source_hashes)
    began = time.perf_counter()
    rows, fit, error = [], None, None
    summary = dict(schema='piper-static-workspace-study-v1', status='NOT_COMPLETED',
                   protocol_sha256=sha(args.protocol), physics_steps=0, actor_loads_or_forwards=0,
                   world_model_training=0, actual_robot_trials=0,
                   numpy_version=np.__version__, mujoco_version=mujoco.__version__, python=sys.version.split()[0])
    try:
        with no_physics_steps():
            model = PiperKinematics(position_tolerance_m=protocol['IK']['position_tolerance_m'],
                                    orientation_tolerance_rad=protocol['IK']['orientation_tolerance_rad'],
                                    max_iterations=protocol['IK']['max_iterations_per_seed'])
            dump(args.output_dir / 'robot_contract.json', model.contract())
            initial = model.snapshot()
            queries = 0
            orientation_quats = []
            for r in rotations:
                quat = np.empty(4)
                mujoco.mju_mat2Quat(quat, r.ravel())
                quat /= np.linalg.norm(quat)
                orientation_quats.append(quat.tolist())
            dump(args.output_dir / 'target_orientations_base_wxyz.json', orientation_quats)
            for split, points in [('fit_development', train), ('validation_spatial_holdout', validation)]:
                for point in points:
                    results = []
                    for q in orientation_quats:
                        if time.perf_counter() - began > protocol['resources']['max_cpu_wall_s']:
                            raise TimeoutError('Static CPU budget reached; no fit from partial grid')
                        result = model.solve(point, q)  # base world R=identity fixed by explicit contract
                        queries += 1
                        results.append(result)
                    found = sum(r['found'] for r in results)
                    rows.append(dict(split=split, target_base_m=point.tolist(),
                                     orientations_tested=len(results), bounded_IK_found=found,
                                     psi_sampled=found / len(results), orientation_results=results))
            if not model.restored(initial) or model.data.time != 0:
                raise RuntimeError('Private static model state/time changed beyond original-oracle restoration')
            positive = [r for row in rows for r in row['orientation_results'] if r['found']]
            fit_rows = [r for r in rows if r['split'] == 'fit_development']
            validation_rows = [r for r in rows if r['split'] == 'validation_spatial_holdout']
            fit = fit_dual_ellipsoid(train, [r['psi_sampled'] for r in fit_rows], protocol['fit'])
            dump(args.output_dir / 'dual_ellipsoid_fit.json', fit)
            # Bind fitted metric directly into prior paper-cost implementation, not hand-written toy axes.
            outer = Ellipsoid(tuple(fit['center_base_m']), tuple(tuple(x) for x in fit['outer_metric_m_minus2']))
            inner = Ellipsoid(tuple(fit['center_base_m']), tuple(tuple(x) for x in fit['inner_metric_m_minus2']))
            objective = OmniNavParameters(outer, inner, 1/3, 1/3, 1/3, .5, .25, .035)
            probes = [dict(target_base_m=r['target_base_m'], sampled_psi=r['psi_sampled'],
                           fitted_shell_target_cost=omninav_cost(BasePose.planar(0, 0, 0, 0),
                                            r['target_base_m'], [], objective)['target'])
                      for r in validation_rows if np.linalg.norm(r['target_base_m'][:2]) > 1e-10]
            dump(args.output_dir / 'fitted_target_cost_validation.json', probes)
            summary.update(status='COMPLETE_STATIC_MAP_AND_FIXED_FIT',
                           fit_metrics=approximation_metrics(train, [r['psi_sampled'] for r in fit_rows], fit),
                           validation_metrics=approximation_metrics(validation,
                                                [r['psi_sampled'] for r in validation_rows], fit),
                           query_positions=len(rows), pose_orientation_queries=queries,
                           IK_attempts=sum(len(r['attempts']) for row in rows for r in row['orientation_results']),
                           pose_IK_solutions_found=len(positive),
                           independently_rechecked_max_position_error_m=max(r['verified_position_error_m'] for r in positive),
                           independently_rechecked_max_orientation_error_rad=max(r['verified_orientation_error_rad'] for r in positive),
                           private_qpos_qvel_ctrl_restored=True, private_time_unchanged_zero=True,
                           all_positive_solutions_fresh_FK_verified=True,
                           error_label='bounded solver misses, not certified unreachable or task failure',
                           fit_uses_only='125 fit-development positions, never the64 validation positions',
                           selected_or_changed_after_validation=False)
    except Exception:
        error = traceback.format_exc()
        summary.update(status='INCOMPLETE_OR_REJECTED_FIXED_PROTOCOL', error=error,
                       completed_position_rows=len(rows), fitted=False,
                       automatic_grid_extension_or_retry=False)
    dump(args.output_dir / 'pose_ik_map.json', rows)
    summary['elapsed_cpu_wall_s'] = time.perf_counter() - began
    summary['evidence_sha256'] = {p.name: sha(p) for p in args.output_dir.iterdir() if p.is_file()}
    summary['limitations'] = protocol['not_included'] + [
        'repository asset/profile matching is not hardware calibration',
        '12 chosen orientations/two seeds are not exact orientation volume or global IK infeasibility',
        'one covariance shell, not exact original OmniNav fitting or certified safe workspace',
        '64 spatial holdout points are not independent physical trials',
        'no original task, forces, collisions, path or real success tested']
    dump(args.output_dir / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'evidence_sha256'}, indent=2))
    return 0 if error is None else 1


if __name__ == '__main__':
    raise SystemExit(main())
