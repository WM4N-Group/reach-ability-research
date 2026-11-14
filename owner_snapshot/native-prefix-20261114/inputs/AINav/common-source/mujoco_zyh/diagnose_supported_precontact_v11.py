"""Read V11 evidence and test arm reach in an isolated MuJoCo FK data object.

This program does not step physics or write to the episode or source bundle.
Its geometric fits are candidates, not contact or dynamic admission.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def rotation(wxyz):
    return Rotation.from_quat(np.asarray(wxyz)[[1, 2, 3, 0]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    root = args.root
    protocol = json.loads((root / 'protocol.json').read_text())
    report = json.loads((root / 'report.json').read_text())
    freeze = json.loads((root / 'freeze.json').read_text())
    if (protocol['schema'] != 'piper-mujoco-compact-supported-recovery-v11'
            or report['error'] != "RuntimeError('supported_PUSH_precontact_alignment_timeout')"
            or freeze['upstream_source']['commit'] != '340d7d8b0fffbf3c566e503a919c8a92393c5cbe'
            or Path(freeze['upstream_source']['root']) != args.bundle):
        raise ValueError('Expected frozen V11 timeout and exact pinned native bundle')
    for name, expected in freeze['inputs'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen V11 input changed: ' + name)
    closure = json.loads((root / 'private-failure-capsules/closure.json').read_text())
    if not closure['all_required_captures_complete'] or closure['errors']:
        raise ValueError('Incomplete V11 failure capsules')
    for item in closure['files']:
        capsule_path = root / 'private-failure-capsules' / item['path']
        if hashlib.sha256(capsule_path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Failure capsule SHA mismatch: ' + item['path'])
    rows = [json.loads(line) for line in (root / 'supported-push-200hz.jsonl').open()]
    if len(rows) != report['stall_stow_recovery']['supported_push']['protected_motor_steps']:
        raise ValueError('Protected command stream length mismatch')
    catalog = [json.loads(line) for line in (root / 'episode/private-catalog.jsonl').open()]
    capsule = np.load(root / 'private-failure-capsules/000000-supported_push_precontact_alignment_timeout.npz', allow_pickle=False)
    sys.path.insert(0, str(args.bundle / 'push'))
    from model import JOINTS, build_model
    from finish import CollisionGuard, FinishConfig

    model, _ = build_model(friction=.45)
    scratch = mujoco.MjData(model)
    scratch.qpos[:] = capsule['qpos']
    arm_qids = model.jnt_qposadr[[model.joint(f'joint{i}').id for i in range(1, 7)]]
    jids = np.array([model.joint(name).id for name in JOINTS])
    qids = model.jnt_qposadr[jids]
    guard = CollisionGuard(SimpleNamespace(model=model, data=scratch, jids=jids, qids=qids,
                                            base_id=model.body('base_link').id,
                                            box_id=model.body('push_box').id), FinishConfig())
    hand_id = model.body('end_effector').id
    target = capsule['controller__target_position'][0].astype(float)
    target_rot = rotation(capsule['selected_box_quaternion_wxyz']) * rotation(capsule['controller__hand_rotation'][0])
    soft = capsule['target_software__soft_limits'][12:]
    physical = model.jnt_range[[model.joint(f'joint{i}').id for i in range(1, 7)]]
    inner = np.column_stack((np.maximum(soft[:, 0], physical[:, 0]) + .01,
                             np.minimum(soft[:, 1], physical[:, 1]) - .01))
    base = capsule['actual_base_position_world_m'].astype(float)
    q0 = capsule['actual_joint_q'][12:].astype(float)

    def pose(q, dx=0., dy=0.):
        scratch.qpos[:2] = base[:2] + [dx, dy]
        scratch.qpos[arm_qids] = q
        mujoco.mj_kinematics(model, scratch)
        position = scratch.xpos[hand_id].copy()
        angular = (target_rot * rotation(scratch.xquat[hand_id]).inv()).as_rotvec()
        return position, angular

    actual_hand, actual_angular = pose(q0)
    expected_hand = target - capsule['controller__debug_pose_position_error'][0]
    if np.linalg.norm(actual_hand - expected_hand) > .002:
        raise ValueError('Frozen native FK and terminal controller hand position disagree')
    mujoco.mj_comPos(model, scratch)
    hand_jp, hand_jr = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    box_jp, box_jr = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    mujoco.mj_jacBody(model, scratch, hand_jp, hand_jr, hand_id)
    mujoco.mj_jacBody(model, scratch, box_jp, box_jr, model.body('push_box').id)
    actual_hand_velocity = hand_jp @ capsule['qvel']
    actual_box_velocity = box_jp @ capsule['qvel']
    actual_box_angular_velocity = box_jr @ capsule['qvel']

    fits = []
    for dx in (-.08, 0., .08):
        for dy in (-.10, -.05, 0., .05, .10):
            def residual(q):
                position, angular = pose(q, dx, dy)
                return np.r_[20. * (position - target), angular]
            fit = least_squares(residual, np.clip(q0, inner[:, 0], inner[:, 1]),
                                bounds=(inner[:, 0], inner[:, 1]), max_nfev=120)
            position, angular = pose(fit.x, dx, dy)
            scratch.qpos[:2] = base[:2] + [dx, dy]
            scratch.qpos[arm_qids] = q0
            endpoint_collision = guard.check(fit.x, allow_hand_contact=True)
            joint_sweep_collision = guard.segment(q0, fit.x)
            fits.append(dict(base_shift_xy_m=[dx, dy],
                             hand_position_error_world_m=(target - position).tolist(),
                             hand_position_error_norm_m=float(np.linalg.norm(target - position)),
                             hand_orientation_error_rad=float(np.linalg.norm(angular)),
                             arm_q_rad=fit.x.tolist(),
                             maximum_joint_displacement_from_actual_rad=float(np.max(abs(fit.x - q0))),
                             endpoint_collision_reason=endpoint_collision,
                             joint_sweep_collision_reason=joint_sweep_collision,
                             minimum_inner_limit_margin_rad=float(np.min(np.minimum(fit.x - inner[:, 0], inner[:, 1] - fit.x)))))

    local_lower = np.maximum(inner[:, 0], q0 - .4)
    local_upper = np.minimum(inner[:, 1], q0 + .4)
    local_fit = least_squares(lambda q: np.r_[20. * (pose(q)[0] - target), pose(q)[1]],
                              q0, bounds=(local_lower, local_upper), max_nfev=120)
    local_position, local_angular = pose(local_fit.x)
    scratch.qpos[:2] = base[:2]
    scratch.qpos[arm_qids] = q0
    local_endpoint_collision = guard.check(local_fit.x, allow_hand_contact=True)
    local_sweep_collision = guard.segment(q0, local_fit.x)
    box_rot = rotation(capsule['selected_box_quaternion_wxyz'])
    box_pos = capsule['selected_box_position_world_m']
    actual_local = box_rot.inv().apply(actual_hand - box_pos)
    hand_relative_velocity_local = box_rot.inv().apply(
        actual_hand_velocity - actual_box_velocity - np.cross(actual_box_angular_velocity, actual_hand - box_pos))
    retreat = box_rot.apply([-.70 - actual_local[0], 0., 0.])
    align = box_rot.apply([0., -actual_local[1], -.03 - actual_local[2]])
    body_sweep_reasons = []
    for start, end in ((np.zeros(3), retreat), (retreat, retreat + align)):
        for fraction in np.linspace(0., 1., 21):
            scratch.qpos[:3] = base + start + fraction * (end - start)
            scratch.qpos[arm_qids] = q0
            reason = guard.check(q0)
            if reason:
                body_sweep_reasons.append(reason)
    scratch.qpos[:3] = base + retreat + align
    scratch.qpos[arm_qids] = q0
    mujoco.mj_kinematics(model, scratch)
    shifted_local = box_rot.inv().apply(scratch.xpos[hand_id] - box_pos)
    scratch.qpos[:] = capsule['qpos']
    mujoco.mj_kinematics(model, scratch)
    foot_ids = capsule['target_software__feet_ids']
    foot_anchors = capsule['all_body_position_world_m'][foot_ids]
    if np.max(np.linalg.norm(scratch.xpos[foot_ids] - foot_anchors, axis=1)) > .002:
        raise ValueError('Frozen native FK and terminal foot anchors disagree')
    leg_qids = qids[:12]
    leg0 = capsule['actual_joint_q'][:12]
    leg_soft = capsule['target_software__soft_limits'][:12]
    leg_physical = model.jnt_range[jids[:12]]
    leg_inner = np.column_stack((np.maximum(leg_soft[:, 0], leg_physical[:, 0]) + .01,
                                 np.minimum(leg_soft[:, 1], leg_physical[:, 1]) - .01))
    leg_seed = leg0.copy()
    foot_errors = []
    leg_margins = []
    guarded_foot_path_reasons = []
    nonhand_box_contacts = []
    hand_contact_bodies = {model.body('link6').id, hand_id}
    for start, end in ((np.zeros(3), retreat), (retreat, retreat + align)):
        for fraction in np.linspace(0., 1., 21):
            offset = start + fraction * (end - start)
            def foot_residual(q):
                scratch.qpos[:3] = base + offset
                scratch.qpos[leg_qids] = q
                mujoco.mj_kinematics(model, scratch)
                return (scratch.xpos[foot_ids] - foot_anchors).ravel()
            fit = least_squares(foot_residual, leg_seed, bounds=(leg_inner[:, 0], leg_inner[:, 1]), max_nfev=80)
            foot_errors.append(float(np.max(np.linalg.norm(foot_residual(fit.x).reshape(4, 3), axis=1))))
            leg_margins.append(float(np.min(np.minimum(fit.x - leg_inner[:, 0], leg_inner[:, 1] - fit.x))))
            reason = guard.check(q0)
            if reason:
                guarded_foot_path_reasons.append(reason)
            mujoco.mj_collision(model, scratch)
            for contact in scratch.contact[:scratch.ncon]:
                body1, body2 = model.geom_bodyid[[contact.geom1, contact.geom2]]
                if model.body('push_box').id in (body1, body2):
                    other = body2 if body1 == model.body('push_box').id else body1
                    if other not in hand_contact_bodies and other != 0:
                        nonhand_box_contacts.append(model.body(int(other)).name)
            leg_seed = fit.x

    complete = [row for row in rows if row['body_approach_stage_admission']['native_joint_waypoint_complete']]
    nearest = lambda time: min(catalog, key=lambda row: abs(row['actual_sim_time_s'] - time))
    result = dict(schema='supported-PUSH-V11-readonly-FK-diagnostic-v1',
                  input_root=str(root), original_bundle=str(args.bundle),
                  no_physics_step_or_live_state_write=True,
                  support_rows=len(rows), first_waypoint_complete_s=complete[0]['time_s'],
                  start=dict(time_s=rows[0]['time_s'], local_hand_m=rows[0]['actual_box_local_hand'],
                             standoff_m=rows[0]['actual_standoff_m']),
                  first_waypoint_complete=dict(time_s=complete[0]['time_s'], local_hand_m=complete[0]['actual_box_local_hand'],
                                               standoff_m=complete[0]['actual_standoff_m'], base_velocity_m_s=complete[0]['actual_base_velocity']),
                  last=dict(time_s=rows[-1]['time_s'], local_hand_m=rows[-1]['actual_box_local_hand'],
                            standoff_m=rows[-1]['actual_standoff_m'], base_velocity_m_s=rows[-1]['actual_base_velocity']),
                  catalog_samples=[dict(time_s=row['actual_sim_time_s'], base_world_m=row['root_position_world_m'],
                                        box_world_m=row['objects'][0]['position_world_m'])
                                   for row in (nearest(11.3), nearest(17.0), nearest(23.2))],
                  target_world_m=target.tolist(), terminal_hand_world_fk_m=actual_hand.tolist(),
                  terminal_position_error_world_m=(target - actual_hand).tolist(),
                  terminal_orientation_error_rad=float(np.linalg.norm(actual_angular)),
                  terminal_actual_arm_q_rad=q0.tolist(), terminal_native_pose_desired_rad=capsule['controller__debug_pose_desired'][0].tolist(),
                  terminal_native_reference_rad=capsule['controller__reference'][0].tolist(),
                  terminal_inner_limits_rad=inner.tolist(), terminal_soft_limits_rad=soft.tolist(),
                  terminal_foot_normal_N=capsule['target_software__forces'][capsule['target_software__feet_ids'], 2].tolist(),
                  terminal_geometry_blocked=bool(capsule['controller__geometry_blocked'][0]),
                  terminal_geometry_clearance_m=float(capsule['controller__geometry_clearance'][0]),
                  local_branch_fit_within_point4rad=dict(arm_q_rad=local_fit.x.tolist(),
                      position_error_world_m=(target - local_position).tolist(),
                      position_error_norm_m=float(np.linalg.norm(target - local_position)),
                      orientation_error_rad=float(np.linalg.norm(local_angular)),
                      endpoint_collision_reason=local_endpoint_collision,
                      joint_sweep_collision_reason=local_sweep_collision),
                  fixed_arm_body_translation_geometry_only=dict(target_hand_box_local_m=[-.70, 0., -.03],
                      body_translation_world_m=(retreat + align).tolist(),
                      result_hand_box_local_m=shifted_local.tolist(),
                      original_guard_rejection_count=len(body_sweep_reasons),
                      original_guard_reasons_on_retreat_then_alignment=body_sweep_reasons[:5],
                      leg_anchors_QP_dynamics_FIFO_and_contact_unverified=True),
                  fixed_arm_body_translation_foot_anchor_IK=dict(path_samples=len(foot_errors),
                      maximum_foot_anchor_error_m=max(foot_errors),
                      final_foot_anchor_error_m=foot_errors[-1],
                      minimum_leg_inner_limit_margin_rad=min(leg_margins),
                      maximum_leg_joint_change_rad=float(np.max(abs(leg_seed - leg0))),
                      final_leg_q_rad=leg_seed.tolist(),
                      original_arm_guard_rejection_count=len(guarded_foot_path_reasons),
                      original_arm_guard_reasons=sorted(set(guarded_foot_path_reasons)),
                      nonhand_box_contact_bodies=sorted(set(nonhand_box_contacts)),
                      foot_load_slip_torque_and_dynamic_reachability_unverified=True),
                  geometric_fits_only_no_sweep_contact_or_dynamics_admission=fits)
    result['terminal_hand_linear_velocity_world_m_s'] = actual_hand_velocity.tolist()
    result['terminal_hand_relative_box_velocity_local_m_s'] = hand_relative_velocity_local.tolist()
    result['terminal_base_linear_velocity_world_m_s'] = capsule['base_free_joint_linear_velocity_world_m_s'].tolist()
    result['terminal_actual_arm_joint_speed_max_rad_s'] = float(abs(capsule['actual_joint_dq'][12:]).max())
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
