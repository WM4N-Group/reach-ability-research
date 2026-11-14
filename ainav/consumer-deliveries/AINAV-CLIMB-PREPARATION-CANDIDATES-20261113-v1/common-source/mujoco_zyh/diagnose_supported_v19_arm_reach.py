"""Read-only V19 arm reach check in a separate native MuJoCo data object."""
import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def rotation(quaternion):
    return Rotation.from_quat(np.asarray(quaternion)[[1, 2, 3, 0]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    root, bundle = args.root, args.bundle
    protocol = json.loads((root / 'protocol.json').read_text())
    report = json.loads((root / 'report.json').read_text())
    freeze = json.loads((root / 'freeze.json').read_text())
    if (protocol['schema'] != 'piper-mujoco-compact-supported-recovery-v19'
            or report['error'] != "RuntimeError('supported_PUSH_precontact_alignment_timeout')"
            or Path(freeze['upstream_source']['root']) != bundle):
        raise ValueError('Expected the frozen V19 precontact timeout')
    for name, expected in freeze['inputs'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen input changed: ' + name)
    closure = json.loads((root / 'private-failure-capsules/closure.json').read_text())
    if not closure['all_required_captures_complete'] or closure['errors']:
        raise ValueError('Failure capsule is incomplete')
    item = closure['files'][0]
    capsule_path = root / 'private-failure-capsules' / item['path']
    if hashlib.sha256(capsule_path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError('Failure capsule SHA mismatch')
    capsule = np.load(capsule_path, allow_pickle=False)

    sys.path.insert(0, str(bundle / 'push'))
    from model import EFFORT, JOINTS, KD, KP, build_model
    from motor import MotorCommand
    from balance import WholeBodyQP
    from finish import CollisionGuard, FinishConfig

    model, _ = build_model(friction=.45)
    scratch = mujoco.MjData(model)
    scratch.qpos[:] = capsule['qpos']
    mujoco.mj_kinematics(model, scratch)
    arm_ids = np.array([model.joint(f'joint{i}').id for i in range(1, 7)])
    arm_qids = model.jnt_qposadr[arm_ids]
    joint_ids = np.array([model.joint(name).id for name in JOINTS])
    qids = model.jnt_qposadr[joint_ids]
    dids = model.jnt_dofadr[joint_ids]
    feet = capsule['target_software__feet_ids']
    proxy = SimpleNamespace(model=model, data=scratch, jids=joint_ids, qids=qids,
                            dids=dids, feet_ids=feet,
                            soft_limits=capsule['target_software__soft_limits'],
                            base_id=model.body('base_link').id,
                            box_id=model.body('push_box').id)
    guard = CollisionGuard(proxy, FinishConfig())
    hand_id = model.body('end_effector').id
    box_rotation = rotation(capsule['selected_box_quaternion_wxyz'])
    box_position = capsule['selected_box_position_world_m'].astype(float)
    target_rotation = box_rotation * rotation(capsule['controller__hand_rotation'][0])
    original_target = capsule['controller__target_position'][0].astype(float)
    actual = capsule['actual_joint_q'][12:].astype(float)
    soft = capsule['target_software__soft_limits'][12:]
    physical = model.jnt_range[arm_ids]
    inner = np.column_stack((np.maximum(soft[:, 0], physical[:, 0]) + .01,
                             np.minimum(soft[:, 1], physical[:, 1]) - .01))

    def hand_pose(q):
        scratch.qpos[arm_qids] = q
        mujoco.mj_kinematics(model, scratch)
        position = scratch.xpos[hand_id].copy()
        orientation_error = (target_rotation * rotation(scratch.xquat[hand_id]).inv()).as_rotvec()
        return position, orientation_error

    original_qpos = capsule['qpos'].copy()
    actual_feet = capsule['all_body_position_world_m'][feet].copy()

    def static_equilibrium(qpos):
        scratch.qpos[:] = qpos
        scratch.qvel[:] = 0.
        mujoco.mj_forward(model, scratch)
        command = MotorCommand(scratch.qpos[qids].copy(), np.zeros(18),
                               KP.copy(), KD.copy(),
                               np.r_[np.zeros(12), scratch.qfrc_bias[dids[12:]]])
        qp = WholeBodyQP(proxy, replace(FinishConfig(), stance_posture_weight=0.))
        try:
            torque, *_ = qp.solve(np.ones(4, dtype=bool), actual_feet,
                                  np.zeros((4, 3)), np.zeros((4, 3)),
                                  scratch.subtree_com[proxy.base_id].copy(),
                                  float(np.arctan2(scratch.xmat[proxy.base_id].reshape(3, 3)[1, 0],
                                                   scratch.xmat[proxy.base_id].reshape(3, 3)[0, 0])),
                                  scratch.qpos[qids[:12]].copy(), command)
            return dict(com_world_m=scratch.subtree_com[proxy.base_id].tolist(),
                        foot_normal_N=qp.previous_force.reshape(4, 3)[:, 2].tolist(),
                        leg_effort_fraction=float(np.max(np.abs(torque) / EFFORT[:12])),
                        error='')
        except RuntimeError as error:
            return dict(com_world_m=scratch.subtree_com[proxy.base_id].tolist(),
                        foot_normal_N=None, leg_effort_fraction=None, error=str(error))

    results = []
    for extra_x in (0., .02, .04, .06):
        target = original_target + box_rotation.apply([extra_x, 0., 0.])

        def residual(q):
            position, angle = hand_pose(q)
            return np.r_[20. * (position - target), angle, .03 * (q - actual)]

        fit = least_squares(residual, np.clip(actual, inner[:, 0] + 1e-8,
                                              inner[:, 1] - 1e-8),
                            bounds=(inner[:, 0], inner[:, 1]), max_nfev=160)
        position, angle = hand_pose(fit.x)
        mujoco.mj_comPos(model, scratch)
        com_position = scratch.subtree_com[proxy.base_id].copy()
        scratch.qpos[:] = original_qpos
        endpoint = guard.check(fit.x, allow_hand_contact=True)
        sweep_reason = ''
        for fraction in np.linspace(0., 1., 101):
            reason = guard.check(actual + fraction * (fit.x - actual),
                                 allow_hand_contact=True)
            if reason:
                sweep_reason = reason
                break
        candidate_qpos = original_qpos.copy()
        candidate_qpos[arm_qids] = fit.x
        equilibrium = static_equilibrium(candidate_qpos)
        results.append(dict(extra_target_forward_m=extra_x,
                            target_box_local_m=box_rotation.inv().apply(target - box_position).tolist(),
                            actual_result_box_local_m=box_rotation.inv().apply(position - box_position).tolist(),
                            position_error_m=float(np.linalg.norm(position - target)),
                            orientation_error_rad=float(np.linalg.norm(angle)),
                            joint_delta_rad=(fit.x - actual).tolist(),
                            static_COM_world_m=com_position.tolist(),
                            static_QP_foot_normal_N=equilibrium['foot_normal_N'],
                            static_QP_leg_effort_fraction=equilibrium['leg_effort_fraction'],
                            static_QP_error=equilibrium['error'],
                            minimum_inner_margin_rad=float(np.min(np.minimum(
                                fit.x - inner[:, 0], inner[:, 1] - fit.x))),
                            endpoint_collision=endpoint, sweep_collision=sweep_reason,
                            solver_success=bool(fit.success)))
    coupled_results = []
    leg_soft = capsule['target_software__soft_limits'][:12]
    leg_inner = np.column_stack((np.maximum(leg_soft[:, 0],
                                             model.jnt_range[joint_ids[:12], 0]) + .01,
                                 np.minimum(leg_soft[:, 1],
                                            model.jnt_range[joint_ids[:12], 1]) - .01))
    target = original_target + box_rotation.apply([.04, 0., 0.])
    path_endpoint = None
    for retreat_x in (.01, .02, .03, .04, .05, .06):
        candidate = original_qpos.copy()
        candidate[0] -= retreat_x

        def foot_residual(leg_q):
            scratch.qpos[:] = candidate
            scratch.qpos[qids[:12]] = leg_q
            mujoco.mj_kinematics(model, scratch)
            return (scratch.xpos[feet] - actual_feet).ravel()

        legs = least_squares(foot_residual, np.clip(original_qpos[qids[:12]],
                                                    leg_inner[:, 0] + 1e-8,
                                                    leg_inner[:, 1] - 1e-8),
                             bounds=(leg_inner[:, 0], leg_inner[:, 1]), max_nfev=100)
        foot_error = float(np.max(np.linalg.norm(foot_residual(legs.x).reshape(4, 3), axis=1)))
        candidate[qids[:12]] = legs.x

        def arm_residual(arm_q):
            scratch.qpos[:] = candidate
            position, angle = hand_pose(arm_q)
            return np.r_[20. * (position - target), angle, .03 * (arm_q - actual)]

        arm = least_squares(arm_residual, np.clip(actual, inner[:, 0] + 1e-8,
                                                 inner[:, 1] - 1e-8),
                            bounds=(inner[:, 0], inner[:, 1]), max_nfev=160)
        scratch.qpos[:] = candidate
        position, angle = hand_pose(arm.x)
        candidate[arm_qids] = arm.x
        scratch.qpos[:] = candidate
        collision = guard.check(arm.x, allow_hand_contact=True)
        equilibrium = static_equilibrium(candidate)
        if retreat_x == .05:
            path_endpoint = candidate.copy()
        coupled_results.append(dict(base_retreat_world_x_m=retreat_x,
                                    foot_anchor_max_error_m=foot_error,
                                    leg_inner_margin_rad=float(np.min(np.minimum(
                                        legs.x - leg_inner[:, 0], leg_inner[:, 1] - legs.x))),
                                    arm_inner_margin_rad=float(np.min(np.minimum(
                                        arm.x - inner[:, 0], inner[:, 1] - arm.x))),
                                    target_box_local_m=box_rotation.inv().apply(target - box_position).tolist(),
                                    hand_box_local_m=box_rotation.inv().apply(position - box_position).tolist(),
                                    hand_position_error_m=float(np.linalg.norm(position - target)),
                                    hand_orientation_error_rad=float(np.linalg.norm(angle)),
                                    endpoint_collision=collision, static_equilibrium=equilibrium,
                                    leg_solver_success=bool(legs.success),
                                    arm_solver_success=bool(arm.success)))
    path_summary = []
    leg_seed = original_qpos[qids[:12]].copy()
    for phase in ('base_retreat', 'arm_forward'):
        for fraction in np.linspace(0., 1., 51):
            candidate = original_qpos.copy()
            if phase == 'base_retreat':
                candidate[0] -= .05 * fraction

                def foot_error_for_path(leg_q):
                    scratch.qpos[:] = candidate
                    scratch.qpos[qids[:12]] = leg_q
                    mujoco.mj_kinematics(model, scratch)
                    return (scratch.xpos[feet] - actual_feet).ravel()

                legs = least_squares(foot_error_for_path, np.clip(leg_seed,
                                                                  leg_inner[:, 0] + 1e-8,
                                                                  leg_inner[:, 1] - 1e-8),
                                     bounds=(leg_inner[:, 0], leg_inner[:, 1]), max_nfev=80)
                leg_seed = legs.x
                candidate[qids[:12]] = legs.x
                foot_error = float(np.max(np.linalg.norm(
                    foot_error_for_path(legs.x).reshape(4, 3), axis=1)))
                allow_hand_contact = False
            else:
                candidate[:3] = path_endpoint[:3]
                candidate[qids[:12]] = path_endpoint[qids[:12]]
                candidate[arm_qids] = actual + fraction * (path_endpoint[arm_qids] - actual)
                foot_error = 0.
                allow_hand_contact = True
            scratch.qpos[:] = candidate
            collision = guard.check(candidate[arm_qids],
                                    allow_hand_contact=allow_hand_contact)
            scratch.qpos[:] = candidate
            mujoco.mj_kinematics(model, scratch)
            hand_local = box_rotation.inv().apply(scratch.xpos[hand_id] - box_position)
            equilibrium = static_equilibrium(candidate)
            path_summary.append(dict(phase=phase, fraction=float(fraction),
                                     hand_box_local_m=hand_local.tolist(),
                                     foot_anchor_max_error_m=foot_error,
                                     collision=collision,
                                     qp_foot_normal_N=equilibrium['foot_normal_N'],
                                     qp_error=equilibrium['error']))
    path_checks = {}
    for phase in ('base_retreat', 'arm_forward'):
        rows = [row for row in path_summary if row['phase'] == phase]
        loads = [row['qp_foot_normal_N'][3] for row in rows if row['qp_foot_normal_N'] is not None]
        path_checks[phase] = dict(samples=len(rows),
                                  max_foot_anchor_error_m=max(row['foot_anchor_max_error_m'] for row in rows),
                                  minimum_static_QP_rear_left_N=min(loads) if loads else None,
                                  first_collision=next((row for row in rows if row['collision']), None),
                                  first_QP_failure=next((row for row in rows if row['qp_error']), None),
                                  first_hand_beyond_original_target=next((row for row in rows
                                      if row['hand_box_local_m'][0] >= -.63), None),
                                  start=rows[0], end=rows[-1])
    staged_arm_path = []
    retreated = path_endpoint.copy()
    retreated[arm_qids] = actual
    arm_seed = actual.copy()
    for stage, local_target in (('center_outside_box', [-.72, 0., -.03]),
                                ('advance_to_face', [-.59, 0., -.03])):
        world_target = box_position + box_rotation.apply(local_target)

        def stage_residual(arm_q):
            scratch.qpos[:] = retreated
            position, angle = hand_pose(arm_q)
            return np.r_[20. * (position - world_target), angle,
                         .03 * (arm_q - arm_seed)]

        fit = least_squares(stage_residual, np.clip(arm_seed,
                                                   inner[:, 0] + 1e-8,
                                                   inner[:, 1] - 1e-8),
                            bounds=(inner[:, 0], inner[:, 1]), max_nfev=160)
        for fraction in np.linspace(0., 1., 101):
            candidate = retreated.copy()
            candidate[arm_qids] = arm_seed + fraction * (fit.x - arm_seed)
            scratch.qpos[:] = candidate
            mujoco.mj_kinematics(model, scratch)
            hand_local = box_rotation.inv().apply(scratch.xpos[hand_id] - box_position)
            collision = guard.check(candidate[arm_qids],
                                    allow_hand_contact=bool(hand_local[0] >= -.63))
            equilibrium = static_equilibrium(candidate)
            staged_arm_path.append(dict(stage=stage, fraction=float(fraction),
                                        hand_box_local_m=hand_local.tolist(),
                                        collision=collision,
                                        static_QP_rear_left_N=(equilibrium['foot_normal_N'][3]
                                            if equilibrium['foot_normal_N'] is not None else None),
                                        QP_error=equilibrium['error']))
        arm_seed = fit.x.copy()
    staged_checks = {}
    for stage in ('center_outside_box', 'advance_to_face'):
        rows = [row for row in staged_arm_path if row['stage'] == stage]
        contact_zone = [row for row in rows if row['hand_box_local_m'][0] >= -.63]
        staged_checks[stage] = dict(samples=len(rows), start=rows[0], end=rows[-1],
                                    minimum_static_QP_rear_left_N=min(
                                        row['static_QP_rear_left_N'] for row in rows
                                        if row['static_QP_rear_left_N'] is not None),
                                    max_contact_zone_abs_y_m=max((abs(row['hand_box_local_m'][1])
                                        for row in contact_zone), default=None),
                                    max_contact_zone_z_error_m=max((abs(row['hand_box_local_m'][2] + .03)
                                        for row in contact_zone), default=None),
                                    first_collision=next((row for row in rows if row['collision']), None),
                                    first_QP_failure=next((row for row in rows if row['QP_error']), None))
    lateral_routes = []
    for target_y in (-.03, -.02, -.01, 0., .01, .02, .03):
        candidate_base = path_endpoint.copy()
        candidate_base[arm_qids] = actual
        route_target = box_position + box_rotation.apply([-.59, target_y, -.03])

        def route_residual(arm_q):
            scratch.qpos[:] = candidate_base
            position, angle = hand_pose(arm_q)
            return np.r_[20. * (position - route_target), angle, .03 * (arm_q - actual)]

        fit = least_squares(route_residual, np.clip(actual, inner[:, 0] + 1e-8,
                                                   inner[:, 1] - 1e-8),
                            bounds=(inner[:, 0], inner[:, 1]), max_nfev=160)
        first_collision = None
        contact_zone = []
        route_loads = []
        route_qp_error = None
        for fraction in np.linspace(0., 1., 101):
            candidate = candidate_base.copy()
            candidate[arm_qids] = actual + fraction * (fit.x - actual)
            scratch.qpos[:] = candidate
            mujoco.mj_kinematics(model, scratch)
            hand_local = box_rotation.inv().apply(scratch.xpos[hand_id] - box_position)
            collision = guard.check(candidate[arm_qids],
                                    allow_hand_contact=bool(hand_local[0] >= -.63))
            if collision and first_collision is None:
                first_collision = dict(fraction=float(fraction), reason=collision,
                                       hand_box_local_m=hand_local.tolist())
            if hand_local[0] >= -.63:
                contact_zone.append(hand_local.copy())
            if target_y == -.03:
                equilibrium = static_equilibrium(candidate)
                if equilibrium['foot_normal_N'] is not None:
                    route_loads.append(equilibrium['foot_normal_N'][3])
                elif route_qp_error is None:
                    route_qp_error = dict(fraction=float(fraction),
                                          reason=equilibrium['error'])
        candidate_base[arm_qids] = fit.x
        equilibrium = static_equilibrium(candidate_base)
        lateral_routes.append(dict(target_box_local_y_m=target_y,
                                   endpoint_hand_box_local_m=box_rotation.inv().apply(
                                       scratch.xpos[hand_id] - box_position).tolist(),
                                   first_collision=first_collision,
                                   max_contact_zone_abs_y_m=max((abs(local[1])
                                       for local in contact_zone), default=None),
                                   max_contact_zone_z_error_m=max((abs(local[2] + .03)
                                       for local in contact_zone), default=None),
                                   static_QP_rear_left_N=(equilibrium['foot_normal_N'][3]
                                       if equilibrium['foot_normal_N'] is not None else None),
                                   minimum_path_static_QP_rear_left_N=(min(route_loads)
                                       if route_loads else None),
                                   first_path_QP_error=route_qp_error,
                                   static_QP_error=equilibrium['error'],
                                   arm_solver_success=bool(fit.success)))
    import torch
    from mujoco_zyh.supported_push import plan_loaded_arm_contact
    scratch.qpos[:] = path_endpoint
    scratch.qpos[arm_qids] = actual
    mujoco.mj_kinematics(model, scratch)
    proxy.controller = SimpleNamespace(hand_rotation=torch.as_tensor(
        capsule['controller__hand_rotation']))
    v20_goal, v20_admission = plan_loaded_arm_contact(
        proxy, guard, inner, scratch.xmat[proxy.box_id].reshape(3, 3),
        scratch.xpos[proxy.box_id].copy())
    scratch.qpos[:] = path_endpoint
    v20_hand, _ = hand_pose(v20_goal)
    v20_local = box_rotation.inv().apply(v20_hand - box_position)
    if (not np.allclose(v20_local, [-.59, -.03, -.03], atol=.002)
            or v20_admission['maximum_contact_zone_abs_y_m'] >= .04
            or v20_admission['maximum_contact_zone_z_error_m'] >= .025):
        raise ValueError('V20 runtime planner disagrees with independent V19 route')
    scratch.qpos[:] = original_qpos
    hand, _ = hand_pose(actual)
    output = dict(schema='read-only-v19-arm-reach-diagnosis-v1',
                  physical_steps=0, physical_state_or_original_root_writes=0,
                  frozen_inputs_verified=len(freeze['inputs']),
                  capsule_sha_verified=True,
                  actual_hand_box_local_m=box_rotation.inv().apply(hand - box_position).tolist(),
                  actual_foot_normal_N=capsule['target_software__forces'][feet, 2].tolist(),
                  actual_base_world_m=capsule['actual_base_position_world_m'].tolist(),
                  actual_base_COM_world_m=capsule['actual_base_subtree_COM_world_m'].tolist(),
                  actual_foot_positions_world_m=actual_feet.tolist(),
                  results=results,
                  coupled_static_candidates=coupled_results,
                  five_cm_retreat_then_arm_path=path_checks,
                  five_cm_retreat_center_then_advance=staged_checks,
                  five_cm_retreat_lateral_arm_routes=lateral_routes,
                  V20_actual_runtime_planner_on_isolated_retreated_capsule=dict(
                      goal_arm_rad=v20_goal.tolist(),
                      endpoint_hand_box_local_m=v20_local.tolist(), admission=v20_admission),
                  limitation='FK, collision, and artificial zero-velocity QP equilibrium only; no dynamic, FIFO, or live contact admission')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
