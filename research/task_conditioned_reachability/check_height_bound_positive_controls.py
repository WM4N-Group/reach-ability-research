"""Twelve prelisted legal-joint FK witnesses check the new necessary-bound algebra.

Not task outcomes, extra IK seeds, or a rerun of the task protocol.
"""
import argparse
from itertools import product
import json
from pathlib import Path
import time

import numpy as np

from piper_kinematics import PiperKinematics, REPO, no_physics_steps, sha
from piper_task_geometry import reference_bounds
from task_height_bound import height_bound


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Existing output cannot be overwritten/retried')
    protocol_path = Path(__file__).with_name('piper_height_bound_positive_controls_v1.json')
    protocol = json.loads(protocol_path.read_text())
    contract_path = REPO / 'evidence/2026-10-20/piper-source-task-static-v1/robot_contract.json'
    c = json.loads(contract_path.read_text())
    source_paths = [Path(__file__), protocol_path, contract_path,
                    Path(__file__).with_name('task_height_bound.py'),
                    Path(__file__).with_name('piper_kinematics.py')]
    out = dict(schema='piper-height-bound-positive-witnesses-v1', role=protocol['role'],
               frozen_protocol=protocol,
               source_hashes={str(p.relative_to(REPO)): sha(p) for p in source_paths},
               results=[], status='NOT_COMPLETED', physics_steps=0, IK_queries=0, FK_queries=0)
    began = time.perf_counter()
    try:
        with no_physics_steps():
            model = PiperKinematics(native_collision_profile=True)
            for name, actual in [('hard_joint_low_rad', model.oracle.arm_low),
                                 ('hard_joint_high_rad', model.oracle.arm_high)]:
                np.testing.assert_array_equal(actual, c[name])
            lo, hi = reference_bounds(model.oracle.arm_low, model.oracle.arm_high)
            model.oracle.arm_low, model.oracle.arm_high = lo, hi
            mid = (lo + hi)/2
            configs = []
            for q2, q3, q5 in product([lo[1], mid[1], hi[1]], [lo[2], hi[2]], [lo[4], hi[4]]):
                q = mid.copy()
                q[[1, 2, 4]] = [q2, q3, q5]
                configs.append(q)
            if len(configs) != protocol['resources']['FK_queries']:
                raise RuntimeError('Unexpected prelisted configuration count')
            initial = model.snapshot()
            for i, q in enumerate(configs):
                if time.perf_counter() - began > protocol['resources']['max_cpu_wall_s']:
                    raise TimeoutError('Positive-control CPU budget reached; no extension')
                pos_world, quat = model.fk(q)
                out['FK_queries'] += 1
                # The private compiled base has identity rotation. No body/physics movement.
                np.testing.assert_array_equal(model.base_rotation, np.eye(3))
                pos = pos_world - model.base_position
                bounds = dict(reference=height_bound(c, pos, quat),
                              native_hard=height_bound(c, pos, quat, use_hard_limits=True))
                out['results'].append(dict(witness_id=i, q_rad=q.tolist(), target_base_m=pos.tolist(),
                                            target_quaternion_base_wxyz=quat.tolist(), bounds=bounds))
                if any(b['exclusion_gap_m'] > 0 for b in bounds.values()):
                    raise RuntimeError('Necessary-bound FALSE EXCLUSION of exact legal FK witness')
                if not model.restored(initial) or model.data.time != 0:
                    raise RuntimeError('Private state/time changed')
            out.update(status='PASSED_model_positive_controls_NOT_task_validation',
                       private_state_restored=True, private_time_s=float(model.data.time),
                       false_exclusions_reference=0, false_exclusions_native_hard=0)
    except Exception as exc:
        out.update(status='FAILED_preserve_no_retry', error_type=type(exc).__name__, error=str(exc))
    finally:
        out['cpu_wall_s'] = time.perf_counter()-began
        with args.output.open('x') as f:
            json.dump(out, f, indent=2, ensure_ascii=False, allow_nan=False)
            f.write('\n')
        print(json.dumps({k: v for k, v in out.items() if k not in ('results', 'frozen_protocol', 'source_hashes')}, indent=2))
    return int(out['status'].startswith('FAILED'))


if __name__ == '__main__':
    raise SystemExit(main())
