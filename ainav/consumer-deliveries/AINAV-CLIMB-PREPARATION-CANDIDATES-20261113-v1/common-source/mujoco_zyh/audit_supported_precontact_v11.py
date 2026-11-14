"""Read-only audit of the bounded V11 precontact development run."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from mujoco_zyh.audit import audit as audit_stream


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(root):
    root = Path(root)
    freeze = json.loads((root / 'freeze.json').read_text())
    protocol = json.loads((root / 'protocol.json').read_text())
    report = json.loads((root / 'report.json').read_text())
    for name, expected in freeze['inputs'].items():
        if sha(root / name) != expected:
            raise ValueError('Frozen input changed: ' + name)
    if protocol['schema'] != 'piper-mujoco-compact-supported-recovery-v11':
        raise ValueError('Unexpected protocol')
    stream = audit_stream(root / 'episode')
    if not stream['data_integrity_pass']:
        raise ValueError('Episode integrity: ' + str(stream['errors']))
    capsule = json.loads((root / 'private-failure-capsules/closure.json').read_text())
    if not capsule['all_required_captures_complete'] or capsule['errors']:
        raise ValueError('Failure capsule incomplete')
    for row in capsule['files']:
        if sha(root / 'private-failure-capsules' / row['path']) != row['sha256']:
            raise ValueError('Failure capsule SHA mismatch')
    rows = [json.loads(line) for line in (root / 'supported-push-200hz.jsonl').open()]
    support = report['stall_stow_recovery']['supported_push']
    if len(rows) != support['protected_motor_steps']:
        raise ValueError('Protected step count mismatch')
    stage_counts = {}
    for row in rows:
        stage = row['body_approach_stage_admission']
        admitted = stage['allow_body_approach']
        if admitted != (row['measured_contact_entry_admission']['reference_stage_admitted']
                       and stage['native_joint_waypoint_complete']):
            raise ValueError('Approach stage decision mismatch')
        if admitted and row['body_mode'] != 'bounded_body_approach_after_centered_native_waypoint_gate':
            raise ValueError('Approach mode mismatch')
        if not admitted and (row['body_mode'] != 'hold_body_until_actual_arm_face_height_and_native_ready'
                             or not np.array_equal(row['approach_velocity_target_m_s'], [0., 0.])):
            raise ValueError('Body approached before measured stage gate')
        key = ('waypoint_complete' if stage['native_joint_waypoint_complete'] else 'waypoint_pending',
               'approach' if admitted else 'hold')
        stage_counts[str(key)] = stage_counts.get(str(key), 0) + 1
    local = np.asarray([row['actual_box_local_hand'] for row in rows])
    if report['task_success'] or report['error'] != "RuntimeError('supported_PUSH_precontact_alignment_timeout')":
        raise ValueError('Unexpected terminal result')
    if report['reset_after_initial'] or any(report[k] for k in ('training_runs', 'WM_forwards', 'WM_control')):
        raise ValueError('Reset or training was enabled')
    if report['source_postflight']['original_source_or_weights_modified']:
        raise ValueError('Frozen skill source changed')
    return dict(schema='supported-PUSH-V11-readonly-precontact-audit-v1',
                integrity_pass=True, frozen_inputs_pass=True, capsule_pass=True,
                terminated_by_registered_precontact_timeout=True,
                task_success=False, actual_soft_failure_recovery_pass=False,
                sim_seconds=report['sim_seconds'], protected_motor_steps=len(rows),
                stage_counts=stage_counts, first_local_hand_m=local[0].tolist(),
                last_local_hand_m=local[-1].tolist(),
                local_hand_ranges_m=np.stack((local.min(0), local.max(0)), axis=1).tolist(),
                any_body_approach_admitted=any(row['body_approach_stage_admission']['allow_body_approach'] for row in rows),
                native_motion_ready_ticks=sum(row['native_motion_ready'] for row in rows),
                last_alignment_checks=rows[-1]['measured_contact_entry_admission']['checks'],
                original_source_verified_files=report['source_postflight']['verified_files'],
                training_runs=0, WM_forwards=0, WM_control=0, reset_after_initial=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
