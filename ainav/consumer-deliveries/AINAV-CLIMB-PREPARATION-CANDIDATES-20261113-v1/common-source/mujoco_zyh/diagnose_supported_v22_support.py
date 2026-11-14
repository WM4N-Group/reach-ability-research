"""Read-only native QP sensitivity at the frozen V22 support-loss state."""
import argparse
import hashlib
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
import torch
from scipy.optimize import least_squares


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--candidate-source', type=Path)
    args = parser.parse_args()
    root, bundle = args.root, args.bundle
    protocol = json.loads((root / 'protocol.json').read_text())
    report = json.loads((root / 'report.json').read_text())
    freeze = json.loads((root / 'freeze.json').read_text())
    if (protocol['schema'] != 'piper-mujoco-compact-supported-recovery-v22'
            or report['error'] != "RuntimeError('supported_PUSH_arm_contact_support_below_12N')"
            or Path(freeze['upstream_source']['root']) != bundle):
        raise ValueError('Expected frozen V22 support-loss episode')
    for name, expected in freeze['inputs'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen input changed: ' + name)
    closure = json.loads((root / 'private-failure-capsules/closure.json').read_text())
    if not closure['all_required_captures_complete'] or closure['errors']:
        raise ValueError('Incomplete V22 capsule')
    item = closure['files'][0]
    capsule_path = root / 'private-failure-capsules' / item['path']
    if hashlib.sha256(capsule_path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError('V22 capsule SHA mismatch')
    capsule = np.load(capsule_path, allow_pickle=False)

    sys.path.insert(0, str(bundle / 'push'))
    from balance import WholeBodyQP
    from finish import CollisionGuard, FinishConfig
    from model import EFFORT, JOINTS, KD, KP, build_model
    from motor import MotorCommand
    if args.candidate_source:
        spec = importlib.util.spec_from_file_location('mujoco_zyh.supported_push_candidate',
            args.candidate_source)
        candidate_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(candidate_module)
        plan_loaded_arm_contact = candidate_module.plan_loaded_arm_contact
    else:
        from mujoco_zyh.supported_push import plan_loaded_arm_contact

    model, _ = build_model(friction=.45)
    data = mujoco.MjData(model)
    original = capsule['qpos'].copy()
    data.qpos[:] = original
    mujoco.mj_forward(model, data)
    joint_ids = np.array([model.joint(name).id for name in JOINTS])
    qids = model.jnt_qposadr[joint_ids]
    dids = model.jnt_dofadr[joint_ids]
    foot_ids = capsule['target_software__feet_ids']
    anchors = capsule['all_body_position_world_m'][foot_ids].copy()
    soft = capsule['target_software__soft_limits'][:12]
    physical = model.jnt_range[joint_ids[:12]]
    inner = np.column_stack((np.maximum(soft[:, 0], physical[:, 0]) + .01,
                             np.minimum(soft[:, 1], physical[:, 1]) - .01))
    proxy = SimpleNamespace(model=model, data=data, qids=qids, dids=dids,
                            jids=joint_ids, feet_ids=foot_ids,
                            soft_limits=capsule['target_software__soft_limits'],
                            base_id=model.body('base_link').id,
                            box_id=model.body('push_box').id,
                            controller=SimpleNamespace(hand_rotation=torch.as_tensor(
                                capsule['controller__hand_rotation'])))
    guard = CollisionGuard(proxy, FinishConfig())
    rotation = data.xmat[proxy.box_id].reshape(3, 3).copy()
    box = data.xpos[proxy.box_id].copy()
    arm_goal = np.array(report['stall_stow_recovery']['supported_push'][
        'read_only_arm_contact_path_admission']['goal_arm_rad'])

    def equilibrium(qpos):
        data.qpos[:] = qpos
        data.qvel[:] = 0.
        mujoco.mj_forward(model, data)
        command = MotorCommand(data.qpos[qids].copy(), np.zeros(18), KP.copy(),
                               KD.copy(), np.r_[np.zeros(12), data.qfrc_bias[dids[12:]]])
        qp = WholeBodyQP(proxy, replace(FinishConfig(), stance_posture_weight=0.))
        try:
            torque, *_ = qp.solve(np.ones(4, dtype=bool), anchors,
                np.zeros((4, 3)), np.zeros((4, 3)),
                data.subtree_com[proxy.base_id].copy(),
                float(np.arctan2(data.xmat[proxy.base_id].reshape(3, 3)[1, 0],
                                 data.xmat[proxy.base_id].reshape(3, 3)[0, 0])),
                data.qpos[qids[:12]].copy(), command)
            return dict(foot_normal_N=qp.previous_force.reshape(4, 3)[:, 2].tolist(),
                        leg_effort_fraction=float(np.max(np.abs(torque) / EFFORT[:12])),
                        error='')
        except RuntimeError as error:
            return dict(foot_normal_N=None, leg_effort_fraction=None, error=str(error))

    results = []
    for shift_y in (0., .01, .02, .03, .04, .05, .06):
        candidate = original.copy()
        candidate[:3] += rotation[:, 1] * shift_y

        def foot_error(legs):
            data.qpos[:] = candidate
            data.qpos[qids[:12]] = legs
            mujoco.mj_kinematics(model, data)
            return (data.xpos[foot_ids] - anchors).ravel()

        legs = least_squares(foot_error, np.clip(original[qids[:12]],
            inner[:, 0] + 1e-8, inner[:, 1] - 1e-8),
            bounds=(inner[:, 0], inner[:, 1]), max_nfev=100)
        max_foot_error = float(np.max(np.linalg.norm(foot_error(legs.x).reshape(4, 3), axis=1)))
        candidate[qids[:12]] = legs.x
        arms = {}
        for name, arm in (('current', original[qids[12:]]), ('planned_goal', arm_goal)):
            qpos = candidate.copy()
            qpos[qids[12:]] = arm
            data.qpos[:] = qpos
            mujoco.mj_kinematics(model, data)
            hand_local = rotation.T @ (data.xpos[model.body('end_effector').id] - box)
            collision = guard.check(arm, allow_hand_contact=True)
            arms[name] = dict(hand_box_local_m=hand_local.tolist(),
                              endpoint_collision=collision,
                              static_equilibrium=equilibrium(qpos))
        replanned = {}
        for name, start_arm in (('before_extension', np.asarray(report['stall_stow_recovery'][
                'supported_push']['read_only_arm_contact_path_admission']['issued_start_arm_rad'])),
                                ('at_failure', original[qids[12:]])):
            data.qpos[:] = candidate
            data.qpos[qids[12:]] = start_arm
            mujoco.mj_forward(model, data)
            phase = 'center'
            try:
                goal, admission = plan_loaded_arm_contact(proxy, guard, np.column_stack((
                    np.maximum(capsule['target_software__soft_limits'][12:, 0],
                               model.jnt_range[joint_ids[12:], 0]) + .01,
                    np.minimum(capsule['target_software__soft_limits'][12:, 1],
                               model.jnt_range[joint_ids[12:], 1]) - .01)),
                    rotation, box, start_reference=start_arm)
                force_path = []
                for fraction in np.linspace(0., 1., 21):
                    state = candidate.copy()
                    state[qids[12:]] = start_arm + fraction * (goal - start_arm)
                    force_path.append(equilibrium(state))
                replanned[name] = dict(admission=admission,
                    minimum_static_foot_N=float(min(min(x['foot_normal_N']) for x in force_path)),
                    maximum_static_leg_effort_fraction=float(max(
                        x['leg_effort_fraction'] for x in force_path)),
                    static_QP_errors=[x['error'] for x in force_path if x['error']])
            except (RuntimeError, ValueError) as error:
                replanned[name] = dict(error=str(error))
        if args.candidate_source and shift_y >= .03:
            start_arm = np.asarray(report['stall_stow_recovery']['supported_push'][
                'read_only_arm_contact_path_admission']['issued_start_arm_rad'])
            data.qpos[:] = candidate
            data.qpos[qids[12:]] = start_arm
            mujoco.mj_forward(model, data)
            try:
                arm_inner = np.column_stack((
                    np.maximum(capsule['target_software__soft_limits'][12:, 0],
                               model.jnt_range[joint_ids[12:], 0]) + .01,
                    np.minimum(capsule['target_software__soft_limits'][12:, 1],
                               model.jnt_range[joint_ids[12:], 1]) - .01))
                center_goal, center_admission = plan_loaded_arm_contact(proxy, guard,
                    arm_inner, rotation, box, start_reference=start_arm,
                    target_local=(-.68, shift_y - .015, -.03))
                data.qpos[qids[12:]] = center_goal
                mujoco.mj_forward(model, data)
                phase = 'contact'
                contact_goal, contact_admission = plan_loaded_arm_contact(proxy, guard,
                    arm_inner, rotation, box, start_reference=center_goal)
                path_forces = []
                for source, destination in ((start_arm, center_goal),
                                            (center_goal, contact_goal)):
                    for fraction in np.linspace(0., 1., 21):
                        state = candidate.copy()
                        state[qids[12:]] = source + fraction * (destination - source)
                        path_forces.append(equilibrium(state))
                replanned['two_segment'] = dict(center=center_admission,
                    contact=contact_admission,
                    minimum_static_foot_N=float(min(min(x['foot_normal_N'])
                        for x in path_forces if x['foot_normal_N'] is not None)),
                    static_QP_errors=[x['error'] for x in path_forces if x['error']])
            except (RuntimeError, ValueError) as error:
                replanned['two_segment'] = dict(failed_phase=phase,error=str(error))
        results.append(dict(lateral_base_shift_toward_left_m=shift_y,
                            foot_anchor_max_error_m=max_foot_error,
                            minimum_leg_inner_margin_rad=float(np.min(np.minimum(
                                legs.x - inner[:, 0], inner[:, 1] - legs.x))),
                            leg_solver_success=bool(legs.success), arms=arms,
                            replanned_arm_path=replanned))
    feet = capsule['target_software__feet_ids']
    output = dict(schema='read-only-v22-support-sensitivity-v1', physical_steps=0,
                  original_root_writes=0, frozen_inputs_verified=len(freeze['inputs']),
                  capsule_sha_verified=True,
                  actual_foot_normal_N=capsule['target_software__forces'][feet, 2].tolist(),
                  actual_base_world_m=capsule['actual_base_position_world_m'].tolist(),
                  actual_COM_world_m=capsule['actual_base_subtree_COM_world_m'].tolist(),
                  results=results,
                  limitation='Static isolated source QP/IK only; no consecutive dynamics, FIFO or legal contact')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
