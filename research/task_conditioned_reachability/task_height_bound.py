"""Analytic necessary pose-height condition for the source-bound Piper chain.

Reads frozen model/task records only. No FK, IK, integration, data fitting or
seed search. Positive gap excludes the specified pose-tolerance set in this
model and reference joint domain; nonpositive gap is INCONCLUSIVE, not feasible.
This posthoc development analysis does not rewrite the frozen study results.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from piper_kinematics import REPO, sha


def quat_matrix(q):
    q = np.asarray(q, dtype=float)
    q = q / np.linalg.norm(q)
    w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def min_sinusoid(a, b, lo, hi):
    """Exact scalar extrema list: endpoints and any included stationary minima."""
    if not (np.isfinite([a, b, lo, hi]).all() and lo <= hi):
        raise ValueError('Need finite coefficients and nonempty interval')
    points = [lo, hi]
    first = math.atan2(b, a) + math.pi
    for k in range(math.ceil((lo-first)/(2*math.pi)), math.floor((hi-first)/(2*math.pi))+1):
        points.append(first + k * 2*math.pi)
    q = min(points, key=lambda t: a*math.cos(t) + b*math.sin(t))
    return dict(value=a*math.cos(q)+b*math.sin(q), at_joint2_rad=q)


def validate_structure(contract):
    """Bind algebraic assumptions to hashed XML/profile and frozen compiled chain."""
    hashes = contract['profile_USD_and_model_assets']
    xmlpath = REPO / 'mujoco/robots/go2_piper/go2piper.xml'
    profile_path = REPO / 'mujoco/deploy/piper_robot_profile.json'
    operation = REPO / 'mujoco/reconfigurable_navigation/piper_robot_profile.py'
    for p in (xmlpath, profile_path, operation):
        if sha(p) != hashes[str(p.relative_to(REPO))]:
            raise ValueError(f'Frozen model source changed: {p}')
    profile = json.loads(profile_path.read_text())
    axes = {j['name']: j['axis'] for j in profile['joints']}
    tree = ET.parse(xmlpath)
    for i in range(1, 7):
        j = tree.find(f".//joint[@name='joint{i}']")
        if j is None or axes[f'joint{i}'] != [0, 0, 1] or j.attrib.get('ref', '0') != '0':
            raise ValueError('Expected revolute z-axis, zero reference Piper joints')
        if not np.array_equal(np.fromstring(j.attrib.get('pos', '0 0 0'), sep=' '), np.zeros(3)):
            raise ValueError('Nonzero joint anchor unsupported by this bound')
        if j.attrib.get('type', 'hinge') != 'hinge':
            raise ValueError('Only revolute hinge chain supported')
    chain = {b['name']: b for b in contract['chain_from_tip_to_base']}
    parents = {'end_effector': 'link6', 'link6': 'link5', 'link5': 'link4',
               'link4': 'link3', 'link3': 'link2', 'link2': 'link1', 'link1': 'Piper', 'Piper': 'base_link'}
    if any(chain[k]['parent'] != v for k, v in parents.items()):
        raise ValueError('Unexpected chain order')
    for b in ('Piper', 'link1'):
        if not np.allclose(quat_matrix(chain[b]['local_quaternion_wxyz']), np.eye(3), atol=1e-12, rtol=0):
            raise ValueError('Mount/shoulder rotation not identity')
        if chain[b]['local_position_m'][:2] != [0, 0]:
            raise ValueError('Expected vertical mount/shoulder offsets')
    if chain['link2']['local_position_m'] != [0, 0, 0] or chain['link5']['local_position_m'] != [0, 0, 0]:
        raise ValueError('Unexpected shoulder/wrist translation')
    if chain['link3']['local_position_m'][1:] != [0, 0] or chain['end_effector']['local_position_m'][:2] != [0, 0]:
        raise ValueError('Expected upperarm x and tool z offsets')
    return chain


def height_bound(contract, target_base, task_quaternion_base, *, use_hard_limits=False):
    chain = validate_structure(contract)
    # q1 is a vertical-axis yaw. It cannot change any vertical component below.
    shoulder_z = chain['Piper']['local_position_m'][2] + chain['link1']['local_position_m'][2]
    upper_length = chain['link3']['local_position_m'][0]
    r2 = quat_matrix(chain['link2']['local_quaternion_wxyz'])
    lo_key, hi_key = ('hard_joint_low_rad', 'hard_joint_high_rad') if use_hard_limits else ('study_reference_low_rad', 'study_reference_high_rad')
    minimum = min_sinusoid(upper_length*r2[2, 0], upper_length*r2[2, 1],
                          contract[lo_key][1], contract[hi_key][1])
    forearm_length = np.linalg.norm(chain['link4']['local_position_m'])
    wrist_lower = shoulder_z + minimum['value'] - forearm_length
    # t6 = ell * (fixed_R6 z) + residual. Joint6 rotates around z;
    # therefore R5 fixed_R6 z = R6 z regardless of q6.
    fixed_r6 = quat_matrix(chain['link6']['local_quaternion_wxyz'])
    axis6 = fixed_r6[:, 2]
    t6 = np.array(chain['link6']['local_position_m'])
    ell = float(t6 @ axis6)
    residual = float(np.linalg.norm(t6 - ell*axis6))
    tool_length = chain['end_effector']['local_position_m'][2]
    length = tool_length + ell
    fixed_tool = quat_matrix(chain['end_effector']['local_quaternion_wxyz'])
    direction = quat_matrix(task_quaternion_base) @ fixed_tool.T[:, 2]
    pos_allowance = contract['position_tolerance_m']
    rot_allowance = 2*abs(length)*math.sin(contract['orientation_tolerance_rad']/2)
    # ||(R-R*)n|| <= 2 sin(theta/2); ||n||=1. Residual bounded by Cauchy.
    wrist_upper = float(target_base[2] - length*direction[2] + pos_allowance + rot_allowance + residual)
    guard = 1e-8  # explicit conservative arithmetic guard; not interval-arithmetic formal verification
    gap = float(wrist_lower - wrist_upper - guard)
    return dict(scope='fixed_body_model_pose_tolerance_and_declared_joint_domain_only',
                joint_domain='native_hard' if use_hard_limits else 'original90percent_reference',
                status='EXCLUDED_by_analytic_necessary_condition' if gap > 0 else 'INCONCLUSIVE_NOT_feasible',
                shoulder_height_in_base_m=shoulder_z, upperarm_min_height_contribution=minimum,
                forearm_length_m=float(forearm_length), wrist_height_lower_m=float(wrist_lower),
                direction_in_base=direction.tolist(), effective_wrist_tool_length_m=length,
                wrist_offset_residual_bound_m=residual, position_allowance_m=pos_allowance,
                orientation_allowance_m=rot_allowance, arithmetic_guard_m=guard,
                required_wrist_height_upper_m=wrist_upper, exclusion_gap_m=gap,
                not_claimed=['native_hard_infeasibility_from_reference_exclusion', 'other_body_heights_or_pitch',
                             'physical_safety', 'new_method_novelty', 'actual_contact_success'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study_dir', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    cp = args.study_dir / 'robot_contract.json'
    rp = args.study_dir / 'candidate_queries_and_paths.json'
    contract, rows = json.loads(cp.read_text()), json.loads(rp.read_text())
    results = [dict(candidate_id=r['candidate_id'],
                    reference=height_bound(contract, r['target_base_m'], r['task_quaternion_base_wxyz']),
                    native_hard=height_bound(contract, r['target_base_m'], r['task_quaternion_base_wxyz'], use_hard_limits=True)) for r in rows]
    out = dict(schema='piper-task-pose-height-necessary-bound-posthoc-v1',
               role='posthoc_analytic_model_diagnosis_NOT_unseen_validation_or_protocol_rerun',
               inputs={p.name: sha(p) for p in (cp, rp)}, analysis_code_sha256=sha(Path(__file__)),
               no_new_FK_IK_or_physics=True, candidates=len(results),
               reference_excluded=sum(r['reference']['exclusion_gap_m'] > 0 for r in results),
               native_hard_excluded=sum(r['native_hard']['exclusion_gap_m'] > 0 for r in results),
               reference_gap_range_m=[min(r['reference']['exclusion_gap_m'] for r in results), max(r['reference']['exclusion_gap_m'] for r in results)],
               native_hard_gap_range_m=[min(r['native_hard']['exclusion_gap_m'] for r in results), max(r['native_hard']['exclusion_gap_m'] for r in results)],
               method_benefit='model_domain_exclusion_explains_no_path;NOT_measured_task_or_runtime_improvement',
               results=results)
    with args.output.open('x') as f:
        json.dump(out, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'results'}, indent=2))
    print(json.dumps(results[0], indent=2))


if __name__ == '__main__':
    main()
