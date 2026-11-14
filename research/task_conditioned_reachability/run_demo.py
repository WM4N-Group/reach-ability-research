"""Run explicit toy ablations and optionally ONE already-reviewed Piper example.

No saved success pose injection, simulator, training, candidate search or new FK.
A0 uses paper-form costs with SYNTHETIC ellipsoids, not a fitted Piper model.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
import time

from model import (BasePose, Constraint, Ellipsoid, NominalPath, OmniNavParameters,
                   Sample, candidate_score, omninav_cost, quasi_static_torque,
                   select_exact_candidate)

RECEIPT_SHA = '868c486060789306ef03a108c7b6872c53e50068c62ad280a1029bbe9f0bae59'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return '-infinity' if value < 0 else '+infinity'
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def paper_costs():
    # Deliberately synthetic; not ARX constants or inferred Piper ellipsoids.
    p = OmniNavParameters(
        Ellipsoid((.4, 0, .25), ((1/.7**2, 0, 0), (0, 1/.5**2, 0), (0, 0, 1/.5**2))),
        Ellipsoid((.4, 0, .25), ((1/.12**2, 0, 0), (0, 1/.12**2, 0), (0, 0, 1/.12**2))),
        1/3, 1/3, 1/3, .5, .25, .035)
    poses = {'near': BasePose.planar(0, 0, 0, .3), 'offset': BasePose.planar(0, -.1, 0, .3)}
    return {name: omninav_cost(pose, (.6, 0, .5), [], p)['total'] for name, pose in poses.items()}


def nominal_path(name, gaps, torques):
    return NominalPath(name, tuple(Sample(i * .5, dict(clearance=gap,
                         effort=None if tau is None else 5 - abs(tau)))
                         for i, (gap, tau) in enumerate(zip(gaps, torques))))


def synthetic_ablations():
    constraints = (Constraint('clearance', 'm', .01), Constraint('effort', 'Nm', 2))
    costs = paper_costs()
    def static_torque(jx, fx):
        return quasi_static_torque([2], [[jx], [0], [0], [0], [0], [0]], [fx, 0, 0, 0, 0, 0])[0]
    near_loaded = [static_torque(jx, -1) for jx in [.5, 4, .5]]
    near_unloaded = [static_torque(jx, 0) for jx in [.5, 4, .5]]
    cases = {
        'interior_clearance': {
            'near': [nominal_path('near-path', [.02, -.002, .02], [2, 2, 2])],
            'offset': [nominal_path('offset-path', [.006, .006, .006], [3, 3, 3])]},
        'interior_static_load': {
            'near': [nominal_path('near-path', [.02, .02, .02], near_loaded)],
            'offset': [nominal_path('offset-path', [.006, .006, .006], [3, 3, 3])]},
        'same_geometry_without_load': {
            'near': [nominal_path('near-path', [.02, .02, .02], near_unloaded)],
            'offset': [nominal_path('offset-path', [.006, .006, .006], [3, 3, 3])]},
        'missing_load_model': {
            'near': [nominal_path('near-path', [.02, .02, .02], [2, None, 2])],
            'offset': [nominal_path('offset-path', [.006, .006, .006], [3, 3, 3])]},
    }
    outputs = []
    for name, alternatives in cases.items():
        full = {k: candidate_score(v, constraints) for k, v in alternatives.items()}
        endpoint = {k: candidate_score(v, constraints, endpoint_only=True) for k, v in alternatives.items()}
        a0 = dict(status='selected_by_synthetic_paper_cost', candidate_id=min(costs, key=costs.get))
        methods = {'A0_paper_form_synthetic_fit': a0,
                   'A1_endpoint_margins': select_exact_candidate(costs, endpoint, .1),
                   'A2_path_bottleneck': select_exact_candidate(costs, full, .1)}
        for result in methods.values():
            cid = result['candidate_id']
            # This label is toy algebra truth, never a simulated task success.
            result['selected_path_complete_nominal_status'] = full[cid].status if cid is not None else None
        outputs.append(dict(case=name, methods=methods,
                            full_candidate_scores={k: asdict(v) for k, v in full.items()},
                            endpoint_candidate_scores={k: asdict(v) for k, v in endpoint.items()}))
    return dict(parameter_role='fixed_handwritten_toy_NOT_Piper_or_ARX_fit_NOT_calibrated',
                actual_robot_or_task_trials=0, fitted_models=0,
                cost_components='OmniNav v1 Eqs33-42, not logarithmic reach or travel term',
                synthetic_paper_costs=costs, scales={'clearance_m': .01, 'effort_Nm': 2},
                margin_weight=.1, cases=outputs,
                caveat='Cases constructed to exercise algebra, not a benchmark, physical effectiveness or novelty proof.')


def recorded_scalar_example(receipt):
    if sha(receipt) != RECEIPT_SHA:
        raise ValueError('Recorded receipt differs from explicitly reviewed developer-source version')
    d = json.loads(receipt.read_text())
    case = next(x for x in d['conclusions']['sample_cases'] if x['candidate_index'] == 2870)
    assert case['initial_gap_m'] == .005915969610214233
    scale, threshold = .005, .005
    # Arithmetic on existing reported extrema; do not fabricate seconds for
    # an original normalized phase fraction or reconstruct an absent trajectory.
    endpoint = (case['endpoint_gap_m'] - threshold) / scale
    bottleneck = (case['path_gap_m'] - threshold) / scale
    assert endpoint > 0 and bottleneck < 0
    return dict(receipt=dict(path=str(receipt.resolve()), sha256=sha(receipt)),
                original_source=d['original_identity'], candidate_index=2870,
                existing_reported_gap_m={k: case[k] for k in ['initial_gap_m', 'path_gap_m', 'endpoint_gap_m']},
                original_required_gap_m=threshold, normalization_scale_m=scale,
                endpoint_single_constraint=dict(rho=endpoint, status="feasible"),
                path_single_constraint=dict(rho=bottleneck, status="infeasible"),
                original_worst_sample_fraction=case["fraction"],
                actual_path_time_or_duration_not_available_here=True,
                scope='Already-reviewed exposed Go2/Piper CLIMB model-path counterexample only. Not native collision, '
                      'new planner/FK/physics, A0/A1/A2 base-pose comparison, PUSH result or new empirical method benefit. '
                      'Other full-swing margin gates also reject this original candidate; NOT an all-gate endpoint-safe path.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recorded-receipt', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    # Do not overwrite evidence or any input files.
    if args.output.exists():
        parser.error('Output already exists; use a fresh path')
    began = time.perf_counter()
    out = dict(schema='task-conditioned-reachability-math-prototype-v1',
               source_files={p.name: sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
               python=sys.version.split()[0], synthetic=synthetic_ablations(),
               recorded=None if args.recorded_receipt is None else recorded_scalar_example(args.recorded_receipt),
               new_physical_starts=0, new_FK_IK=0, new_training_or_calibration=0,
               omitted_work=['Piper ellipsoid fitting/IK-map construction', 'robot-specific force/support modeling',
                             'candidate trajectory generation', 'matched new physical A0/A1/A2 outcomes'],
               elapsed_cpu_wall_s=time.perf_counter() - began)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(json_safe(out), stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(args.output)


if __name__ == '__main__':
    main()
