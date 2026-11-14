"""Prepare source-backed hardware field dependencies for the existing clearance label."""
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from bind_piper_v212_registry import read,sha
from export_piper_v212_labels import load_geometry


def audit(source_root,episode,hardware_docs):
    geometry,provenance=load_geometry(source_root)
    import numpy as np
    meta=read(episode/'sequence-meta.json');summary=read(episode/'sequence-summary.json')
    if sha(episode/'control-sequence.jsonl')!=summary['sequence_sha256']:
        raise ValueError('Recorded joint-state source changed')
    intervals=[json.loads(line) for line in (episode/'control-sequence.jsonl').read_text().splitlines()]
    states=[row['before'] for row in intervals]+[intervals[-1]['after']]
    names=[f'joint{i}' for i in range(1,7)];slots=[meta['joint_names'].index(name) for name in names]
    actual=[np.asarray([s['joint_position_rad'][i] for i in slots]) for s in states]
    distances=[float(geometry.clearance(q)) for q in actual]
    selected=[0,min(range(len(distances)),key=distances.__getitem__)]
    model=geometry.model;mujoco=geometry.mujoco
    frees=[i for i in range(model.njnt) if model.jnt_type[i]==mujoco.mjtJoint.mjJNT_FREE]
    if len(frees)!=1:raise ValueError('Rigid single-base model scope changed')
    start=int(model.jnt_qposadr[frees[0]]);nominal=geometry.data.qpos.copy()
    mount_id=model.body('Piper').id;mount_position=model.body_pos[mount_id].copy()
    xml=source_root/'runtime-push-detour-v1/mujoco/robots/go2_piper/go2piper.xml'
    raw_mount=ET.parse(xml).getroot().find('.//body[@name="Piper"]')
    if raw_mount is None:raise ValueError('Missing source mount body')
    raw_position=np.asarray([float(v) for v in raw_mount.get('pos').split()])
    transform_tests=[];mount_tests=[]
    for step in selected:
        geometry.data.qpos[:]=nominal;baseline=float(geometry.clearance(actual[step]))
        for tag,translation,quat in [('translated',[1.,-2.,.5],[1.,0.,0.,0.]),
                                      ('translated_yaw90',[1.,-2.,.5],[math.sqrt(.5),0.,0.,math.sqrt(.5)])]:
            geometry.data.qpos[:]=nominal;geometry.data.qpos[start:start+3]=translation
            geometry.data.qpos[start+3:start+7]=quat
            changed=float(geometry.clearance(actual[step]))
            if not math.isclose(changed,baseline,abs_tol=1e-7):raise ValueError('Unexpected dependence on common root transform')
            transform_tests.append(dict(source_step=step,common_transform=tag,clearance_m=changed,absolute_difference_m=abs(changed-baseline)))
        geometry.data.qpos[:]=nominal
        model.body_pos[mount_id]=raw_position
        raw_value=float(geometry.clearance(actual[step]))
        model.body_pos[mount_id]=mount_position
        restored=float(geometry.clearance(actual[step]))
        if not math.isclose(restored,baseline,abs_tol=1e-10):raise ValueError('In-memory model probe did not restore nominal geometry')
        mount_tests.append(dict(source_step=step,time_s=step*meta['control_dt_s'],
            runtime_profile_clearance_m=baseline,raw_xml_mount_counterfactual_clearance_m=raw_value,
            counterfactual_difference_m=raw_value-baseline,
            meaning='Offline in-memory profile-omission probe only; neither real mount error nor executed new configuration'))
    profile=source_root/'runtime-push-detour-v1/mujoco/deploy/piper_robot_profile.json'
    collision=source_root/'runtime-push-detour-v1/mujoco/deploy/piper_collision_profile.json'
    fields=[
      dict(name='arm_joint_position_rad',scope='current specified arm/base geometry only',unit='rad',
           canonical_names=names,recorded_isaac_slots=slots,hardware_slots=None,hardware_units=None,
           hardware_signs=None,hardware_zero_offsets=None,verification='simulation mapping verified; hardware mapping pending'),
      dict(name='observation_clock',required=['sample_time','clock_domain','collector_time','message_sequence_or_frame_id','state_age'],
           verification='hardware clock alignment and latency not established; nominal 20ms simulation clock is not a hardware measurement'),
      dict(name='geometry_bundle',required=['robot_profile_sha256','collision_profile_sha256','mount_calibration_version','actual_joint_mapping_version'],
           verification='v212 nominal runtime files matched; hardware-calibrated version not provided'),
      dict(name='arm_base_clearance_margin_m',unit='m',kind='derived_model_quantity_not_direct_sensor',
           definition='source_matched_surface_distance(actual_named_arm_joints)-0.035',
           verification='can be calculated under model assumptions; not validated as actual hardware surface distance')]
    return dict(schema='reach-deployable-clearance-input-draft-v1',status='source_review_draft_not_hardware_acceptance',
       scope='Only v212 link1-link6 versus base_link current model clearance; not complete PUSH inputs or all-collision safety',
       geometry_provenance=provenance,sources=[dict(path=str(p.resolve()),sha256=sha(p)) for p in
           (profile,collision,xml,episode/'sequence-meta.json',episode/'control-sequence.jsonl',*hardware_docs)],
       nominal_profile_mount_position_m=mount_position.tolist(),raw_xml_mount_position_m=raw_position.tolist(),
       profile_hardware_calibrated=read(profile)['hardware_calibrated'],
       fields=fields,common_root_pose_required_for_this_pair_distance=False,
       root_invariance_reason='Both geometry sets share a rigid root; common SE(3) transformation preserves pairwise Euclidean distances',
       invariance_checks=transform_tests,profile_omission_static_probes=mount_tests,
       unavailable_hardware_evidence=['SDK/CAN sample with units, axis/zero/sign mapping','measured mount/collision envelope','clock alignment and latency distribution'],
       excluded_claims=['No real joint feedback reviewed','No joint velocity/current/torque equivalence assumed','No contact or foot-load availability inferred',
                        'No extension to arm-leg, arm-box, deformable covers or cable clearance','No runtime PUSH qualification granted'],
       hardware_messages_sent=0,new_physical_episodes=0,new_training_runs=0,reserved_outcomes_read=False,
       nominal_source_models_written=False,analysis_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--episode',type=Path,required=True)
    p.add_argument('--hardware-doc',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refusing to overwrite field dependency draft')
    result=audit(a.source_root,a.episode,a.hardware_doc)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('Prepared source-backed field dependencies; no hardware command or physical step')
    for test in result['profile_omission_static_probes']:print(test)


if __name__=='__main__':main()
