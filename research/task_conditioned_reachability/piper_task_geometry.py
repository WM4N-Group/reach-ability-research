"""Source-bound pose-mode PUSH geometry. No controller/Isaac imports or execution."""
from __future__ import annotations

import ast
from itertools import product
import numpy as np
import mujoco

from piper_kinematics import REPO, sha
from workspace_fit import orientation_matrices

ISAAC = ('source/LeggedManip_Lab/LeggedManip_Lab/tasks/manager_based/'
         'leggedmanip_lab/config/go2_piper/box_env_cfg.py')
SOURCES = (ISAAC, 'mujoco/reconfigurable_navigation/piper_box_runtime.py',
           'mujoco/reconfigurable_navigation/box_push_runtime.py')


def bind_task_sources(protocol):
    """Fail closed on changed semantics; hash originals without importing runtimes."""
    trees = {p: ast.parse((REPO / p).read_text()) for p in SOURCES}
    required = {
        ISAAC: ['self.actions.joint_pos.align_hand_orientation = True',
                'self.actions.joint_pos.hand_pitch = 0.8',
                'self.push_approach_distance = 0.03',
                'robot.init_state.pos = (0.0, 0.0, 0.33)'],
        SOURCES[1]: ['push_hand_pitch=0.8', 'push_ik_mode=\'position\'',
                     'pos=[1.1, 0.0, height / 2]', 'size=[0.6, 0.6, height / 2]',
                     "'hand_body_name': 'end_effector'", "'hand_offset': (0, 0, 0)",
                     "'align_hand_orientation': push_ik_mode == 'pose'",
                     "'approach_distance': 0.03 if push_ik_mode == 'pose' else 0.1"],
        SOURCES[2]: ['half_range = 0.45 * np.ptp(self.model.jnt_range[joint_ids], axis=1)',
                     'press = 0.02 if self.approached and (not self.at_goal()) else -self.approach_distance',
                     'return position + rotation @ np.array([-self.box_size[0] / 2.0 + press, 0.0, self.hand_height_offset])',
                     'np.array([np.cos(self.hand_pitch / 2), 0, np.sin(self.hand_pitch / 2), 0])'],
    }
    # Whole-tree canonical AST text lets defaults/dictionary keys be verified too.
    for p, fragments in required.items():
        text = ast.unparse(trees[p])
        for fragment in fragments:
            if fragment not in text:
                raise ValueError(f'Task source binding changed: {p}: {fragment}')
    task = protocol['source_task']
    if not (task['hand_pitch_box_rad'] == .8 and task['precontact_face_distance_m'] == .03
            and task['hand_offset_m'] == [0, 0, 0] and task['end_effector_body'] == 'end_effector'
            and task['box_position_world_m'] == [1.1, 0, .1]
            and task['box_size_m'] == [1.2, 1.2, .2]
            and task['box_quaternion_world_wxyz'] == [1, 0, 0, 0]
            and protocol['candidate_body_positions_world']['height_m'] == .33
            and protocol['matched_IK']['original_reference_limit_fraction'] == .9):
        raise ValueError('Protocol differs from bound task source constants')
    return {p: sha(REPO / p) for p in SOURCES}


def task_world_pose(protocol):
    t = protocol['source_task']
    q_box = np.array(t['box_quaternion_world_wxyz'], dtype=float)
    r = np.empty(9)
    mujoco.mju_quat2Mat(r, q_box)
    offset = [-t['box_size_m'][0] / 2 - t['precontact_face_distance_m'], 0, 0]
    p = np.array(t['box_position_world_m']) + r.reshape(3, 3) @ offset
    a = t['hand_pitch_box_rad'] / 2
    q = np.empty(4)
    mujoco.mju_mulQuat(q, q_box, np.array([np.cos(a), 0, np.sin(a), 0]))
    return p, q


def candidate_grid(protocol):
    c = protocol['candidate_body_positions_world']
    axes = [np.linspace(*c[k]) for k in ('x_m', 'y_m', 'yaw_rad')]
    return [(f'b{i:03d}', np.array([x, y, c['height_m']]), float(yaw))
            for i, (x, y, yaw) in enumerate(product(*axes))]


def task_in_base(position_world, yaw, target_world, quat_world):
    c, s = np.cos(yaw), np.sin(yaw)
    r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    q_inv = np.array([np.cos(yaw/2), 0, 0, -np.sin(yaw/2)])
    q = np.empty(4)
    mujoco.mju_mulQuat(q, q_inv, quat_world)
    return r.T @ (target_world - position_world), q


def common_orientation_pool(task_quaternion_base):
    quats = []
    for r in orientation_matrices():
        q = np.empty(4)
        mujoco.mju_mat2Quat(q, r.ravel())
        quats.append(q / np.linalg.norm(q))
    return quats + [np.asarray(task_quaternion_base)]


def reference_bounds(hard_low, hard_high, fraction=.9):
    mid = (hard_low + hard_high) / 2
    half = fraction * (hard_high - hard_low) / 2
    return mid - half, mid + half


def quintic_path(start, end, samples):
    phases = np.linspace(0, 1, samples)
    h = 10 * phases**3 - 15 * phases**4 + 6 * phases**5
    return phases, start[None, :] + h[:, None] * (end - start)[None, :]
