"""Read-only supported-PUSH lateral reload capsule and guarded arm path."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
import torch
from scipy.optimize import least_squares


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('bundle',type=Path)
    parser.add_argument('--expected-version',type=int,choices=(23,24),default=23)
    parser.add_argument('--candidate-source',type=Path)
    args=parser.parse_args()
    root,bundle=args.root,args.bundle
    protocol=json.loads((root/'protocol.json').read_text())
    report=json.loads((root/'report.json').read_text())
    freeze=json.loads((root/'freeze.json').read_text())
    if (protocol['schema']!=f'piper-mujoco-compact-supported-recovery-v{args.expected_version}' or
            report['error']!="RuntimeError('supported_PUSH_precontact_alignment_timeout')" or
            Path(freeze['upstream_source']['root'])!=bundle):
        raise ValueError('Expected frozen lateral reload timeout')
    for name,expected in freeze['inputs'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Frozen input changed: '+name)
    closure=json.loads((root/'private-failure-capsules/closure.json').read_text())
    if not closure['all_required_captures_complete'] or closure['errors']:
        raise ValueError('Incomplete failure capsule')
    item=closure['files'][0]
    capsule_path=root/'private-failure-capsules'/item['path']
    if hashlib.sha256(capsule_path.read_bytes()).hexdigest()!=item['sha256']:
        raise ValueError('Failure capsule SHA mismatch')
    capsule=np.load(capsule_path,allow_pickle=False)
    with (root/'supported-push-200hz.jsonl').open() as stream:
        last=None
        for line in stream:last=json.loads(line)
    if last is None or last['alignment_stage']!='lateral_reload':
        raise ValueError('Episode did not stop during real lateral reload')

    sys.path.insert(0,str(bundle/'push'))
    from balance import WholeBodyQP
    from finish import CollisionGuard,FinishConfig
    from model import EFFORT,JOINTS,KD,KP,build_model
    from motor import MotorCommand
    if args.candidate_source:
        spec=importlib.util.spec_from_file_location('mujoco_zyh.supported_push_candidate',
            args.candidate_source)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plan_loaded_arm_contact=module.plan_loaded_arm_contact
        admit_alignment_path=module.admit_alignment_path
    else:
        from mujoco_zyh.supported_push import plan_loaded_arm_contact,admit_alignment_path

    model,_=build_model(friction=.45)
    data=mujoco.MjData(model)
    original=capsule['qpos'].copy()
    data.qpos[:]=original
    mujoco.mj_forward(model,data)
    jids=np.array([model.joint(name).id for name in JOINTS])
    qids=model.jnt_qposadr[jids]
    dids=model.jnt_dofadr[jids]
    feet=capsule['target_software__feet_ids']
    anchors=data.xpos[feet].copy()
    soft=capsule['target_software__soft_limits']
    physical=model.jnt_range[jids]
    inner=np.column_stack((np.maximum(soft[:,0],physical[:,0])+.01,
                           np.minimum(soft[:,1],physical[:,1])-.01))
    proxy=SimpleNamespace(model=model,data=data,jids=jids,qids=qids,dids=dids,
        feet_ids=feet,soft_limits=soft,base_id=model.body('base_link').id,
        box_id=model.body('push_box').id,
        controller=SimpleNamespace(hand_rotation=torch.as_tensor(
            capsule['controller__hand_rotation'])))
    guard=CollisionGuard(proxy,FinishConfig())
    R=data.xmat[proxy.box_id].reshape(3,3).copy()
    box=data.xpos[proxy.box_id].copy()
    arm_ref=np.asarray(last['actual_protected_proposal'][0][12:],dtype=float)
    stage_start=np.asarray(last['lateral_reload_start_base_world_m'],dtype=float)

    def equilibrium(qpos):
        data.qpos[:]=qpos
        data.qvel[:]=0.
        mujoco.mj_forward(model,data)
        command=MotorCommand(data.qpos[qids].copy(),np.zeros(18),KP.copy(),KD.copy(),
                             np.r_[np.zeros(12),data.qfrc_bias[dids[12:]]])
        qp=WholeBodyQP(proxy,FinishConfig(stance_posture_weight=0.))
        torque,*_=qp.solve(np.ones(4,dtype=bool),anchors,np.zeros((4,3)),
            np.zeros((4,3)),data.subtree_com[proxy.base_id].copy(),0.,
            data.qpos[qids[:12]].copy(),command)
        return float(np.min(qp.previous_force.reshape(4,3)[:,2])),float(
            np.max(np.abs(torque)/EFFORT[:12]))

    results=[]
    for offset in (0.,.005,.01,.015,.02):
        candidate=original.copy()
        candidate[:3]+=R[:,1]*offset
        def foot_error(legs):
            data.qpos[:]=candidate
            data.qpos[qids[:12]]=legs
            mujoco.mj_kinematics(model,data)
            return (data.xpos[feet]-anchors).ravel()
        fit=least_squares(foot_error,np.clip(original[qids[:12]],
            inner[:12,0]+1e-8,inner[:12,1]-1e-8),
            bounds=(inner[:12,0],inner[:12,1]),max_nfev=100)
        error=float(np.max(np.linalg.norm(foot_error(fit.x).reshape(4,3),axis=1)))
        candidate[qids[:12]]=fit.x
        data.qpos[:]=candidate
        mujoco.mj_forward(model,data)
        measured_shift=float(R[:,1]@(candidate[:3]-stage_start))
        outcome=dict(additional_left_shift_m=offset,
            cumulative_measured_shift_m=measured_shift,
            maximum_foot_anchor_error_m=error,
            minimum_leg_inner_margin_rad=float(np.min(np.minimum(
                fit.x-inner[:12,0],inner[:12,1]-fit.x))))
        try:
            data.qpos[:]=candidate
            mujoco.mj_forward(model,data)
            direct,direct_check=plan_loaded_arm_contact(proxy,guard,inner[12:],R,box,
                arm_ref)
            outcome['direct_path']=direct_check
        except (RuntimeError,ValueError) as exc:
            outcome['direct_error']=str(exc)
        try:
            path=admit_alignment_path(proxy,SimpleNamespace(CollisionGuard=CollisionGuard),
                FinishConfig(),np.stack((original[:3],candidate[:3])),arm_ref,anchors)
            center_local=(-.68,measured_shift+.01,-.02)
            center,center_check=plan_loaded_arm_contact(proxy,guard,inner[12:],R,box,
                arm_ref,target_local=center_local)
            data.qpos[:]=candidate
            data.qpos[qids[12:]]=center
            mujoco.mj_forward(model,data)
            contact,contact_check=plan_loaded_arm_contact(proxy,guard,inner[12:],R,box,
                center)
            loads=[];efforts=[]
            for start,end in ((arm_ref,center),(center,contact)):
                for fraction in np.linspace(0.,1.,21):
                    state=candidate.copy()
                    state[qids[12:]]=start+fraction*(end-start)
                    load,effort=equilibrium(state)
                    loads.append(load);efforts.append(effort)
            outcome.update(lateral_path=path,center_path=center_check,
                contact_path=contact_check,minimum_static_foot_N=min(loads),
                maximum_static_leg_effort_fraction=max(efforts),error='')
        except (RuntimeError,ValueError) as exc:
            outcome['error']=str(exc)
        if offset==.01:
            accepted=[];rejected={}
            for center_x in (-.74,-.72,-.70,-.68):
                for center_y_offset in (-.05,-.035,-.02,-.005,.01):
                    for center_z in (-.03,-.02):
                        data.qpos[:]=candidate
                        data.qpos[qids[12:]]=arm_ref
                        mujoco.mj_forward(model,data)
                        try:
                            middle,middle_check=plan_loaded_arm_contact(proxy,guard,
                                inner[12:],R,box,arm_ref,
                                target_local=(center_x,measured_shift+center_y_offset,
                                              center_z))
                            data.qpos[:]=candidate
                            data.qpos[qids[12:]]=middle
                            mujoco.mj_forward(model,data)
                            contact_goal,last_check=plan_loaded_arm_contact(proxy,guard,
                                inner[12:],R,box,middle)
                            path_loads=[];path_efforts=[]
                            for path_start,path_end in ((arm_ref,middle),(middle,contact_goal)):
                                for fraction in np.linspace(0.,1.,21):
                                    state=candidate.copy()
                                    state[qids[12:]]=path_start+fraction*(path_end-path_start)
                                    load,effort=equilibrium(state)
                                    path_loads.append(load);path_efforts.append(effort)
                            accepted.append(dict(center=[center_x,center_y_offset,center_z],
                                clearance_m=min(middle_check['planned_minimum_body_clearance_m'],
                                                last_check['planned_minimum_body_clearance_m']),
                                max_contact_y_m=last_check['maximum_contact_zone_abs_y_m'],
                                minimum_static_foot_N=min(path_loads),
                                maximum_static_leg_effort_fraction=max(path_efforts)))
                        except (RuntimeError,ValueError) as exc:
                            key=str(exc).split(':')[0]
                            rejected[key]=rejected.get(key,0)+1
            outcome['two_segment_grid']=dict(accepted=accepted,rejected_counts=rejected)
        results.append(outcome)
    print(json.dumps(dict(schema='read-only-supported-lateral-reload-v1',
        frozen_inputs_verified=len(freeze['inputs']),capsule_sha_verified=True,
        physical_steps=0,original_root_writes=0,
        terminal_actual_base_world_m=original[:3].tolist(),
        terminal_issued_base_target_world_m=last['fixed_base_target_world_m'],
        terminal_foot_normal_N=capsule['target_software__forces'][feet,2].tolist(),
        results=results,limitation='Isolated FK/IK/static QP only; no continuous dynamics or FIFO proof'),indent=2))


if __name__=='__main__':main()
