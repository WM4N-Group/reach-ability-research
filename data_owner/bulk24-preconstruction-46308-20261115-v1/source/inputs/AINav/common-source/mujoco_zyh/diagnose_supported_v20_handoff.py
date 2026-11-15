"""Read-only V20 stage handoff and V21 arm-path check on an isolated native model."""
import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--planning-surface-clearance-m', type=float, default=.035)
    args = parser.parse_args()
    root, bundle = args.root, args.bundle
    protocol = json.loads((root / 'protocol.json').read_text())
    report = json.loads((root / 'report.json').read_text())
    freeze = json.loads((root / 'freeze.json').read_text())
    if (protocol['schema'] != 'piper-mujoco-compact-supported-recovery-v20'
            or report['error'] != "RuntimeError('supported_PUSH_precontact_alignment_timeout')"
            or Path(freeze['upstream_source']['root']) != bundle):
        raise ValueError('Expected the frozen V20 precontact timeout')
    for name, expected in freeze['inputs'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen input changed: ' + name)
    closure = json.loads((root / 'private-failure-capsules/closure.json').read_text())
    if not closure['all_required_captures_complete'] or closure['errors']:
        raise ValueError('Incomplete failure capsule')
    item = closure['files'][0]
    capsule_path = root / 'private-failure-capsules' / item['path']
    if hashlib.sha256(capsule_path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError('Failure capsule SHA mismatch')
    capsule = np.load(capsule_path, allow_pickle=False)
    stream = root / 'supported-push-200hz.jsonl'
    with stream.open() as handle:
        rows = (json.loads(line) for line in handle)
        retreat_rows = [row for row in rows if row['alignment_stage'] == 'rebalance_retreat']
    if not retreat_rows:
        raise ValueError('V20 did not reach real rebalance retreat')
    first, last = retreat_rows[0], retreat_rows[-1]

    sys.path.insert(0, str(bundle / 'push'))
    from model import JOINTS, build_model
    from finish import CollisionGuard, FinishConfig
    from mujoco_zyh.supported_push import plan_loaded_arm_contact

    model, _ = build_model(friction=.45)
    scratch = mujoco.MjData(model)
    scratch.qpos[:] = capsule['qpos']
    mujoco.mj_kinematics(model, scratch)
    joint_ids = np.array([model.joint(name).id for name in JOINTS])
    qids = model.jnt_qposadr[joint_ids]
    sim = SimpleNamespace(model=model, data=scratch, jids=joint_ids, qids=qids,
                          box_id=model.body('push_box').id,
                          base_id=model.body('base_link').id,
                          controller=SimpleNamespace(hand_rotation=torch.as_tensor(
                              capsule['controller__hand_rotation'])))
    guard = CollisionGuard(sim, replace(FinishConfig(),
        surface_clearance=args.planning_surface_clearance_m))
    soft = capsule['target_software__soft_limits'][12:]
    physical = model.jnt_range[joint_ids[12:]]
    inner = np.column_stack((np.maximum(soft[:, 0], physical[:, 0]) + .01,
                             np.minimum(soft[:, 1], physical[:, 1]) - .01))
    rotation = scratch.xmat[sim.box_id].reshape(3, 3)
    box = scratch.xpos[sim.box_id].copy()
    goal, admission = plan_loaded_arm_contact(sim, guard, inner, rotation, box)
    scratch.qpos[qids[12:]] = goal
    mujoco.mj_kinematics(model, scratch)
    hand_local = rotation.T @ (scratch.xpos[model.body('end_effector').id] - box)
    actual_base = capsule['actual_base_position_world_m'].astype(float)
    first_base_target = np.array(first['fixed_base_target_world_m'])
    last_base_target = np.array(last['fixed_base_target_world_m'])
    displacement = actual_base - first_base_target
    foot_loads = capsule['target_software__forces'][capsule['target_software__feet_ids'], 2]
    output = dict(schema='read-only-v20-stage-handoff-diagnosis-v1', physical_steps=0,
                  original_root_writes=0, frozen_inputs_verified=len(freeze['inputs']),
                  capsule_sha_verified=True, retreat_stage_rows=len(retreat_rows),
                  first_retreat_time_s=first['time_s'], last_retreat_time_s=last['time_s'],
                  first_retreat_base_target_world_m=first_base_target.tolist(),
                  terminal_base_world_m=actual_base.tolist(),
                  terminal_base_target_world_m=last_base_target.tolist(),
                  terminal_base_target_error_m=(actual_base - last_base_target).tolist(),
                  measured_retreat_along_box_axis_m=float(-rotation[:, 0] @ displacement),
                  measured_lateral_drift_m=float(abs(rotation[:, 1] @ displacement)),
                  measured_vertical_drift_m=float(abs(displacement[2])),
                  terminal_foot_normal_N=foot_loads.tolist(),
                  terminal_base_linear_speed_m_s=float(np.linalg.norm(
                      capsule['base_free_joint_linear_velocity_world_m_s'])),
                  planning_surface_clearance_m=args.planning_surface_clearance_m,
                  arm_planner_admission=admission,
                  arm_goal_endpoint_box_local_m=hand_local.tolist(),
                  limitation='Read-only FK and collision on terminal state; no dynamic step, contact, FIFO, or force acceptance')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
