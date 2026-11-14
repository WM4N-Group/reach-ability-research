"""Controlled finite-cloud math/observer for original v317; never an actuator.

Common 41x64 FK construction/observation is shared by E0-E3. The ONLY arm
variation is the scalar minimum_shift_m. Native support, actual controller,
clock/history/physics and final source-hand/READY gates stay in original probe.
"""
import itertools
import json
from pathlib import Path
import time
import numpy as np

ARM=None
OUTPUT=None
CONTEXT=None
SEQ=0
LAST_ID=None


def rotation(q):
    w,x,y,z=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def array(x):
    if hasattr(x,'detach'):x=x.detach().cpu().numpy()
    return np.asarray(x).copy()


def configure_study(arm,output):
    global ARM,OUTPUT
    if arm not in ('E0','E1','E2','E3'):raise ValueError('Unregistered arm')
    ARM=arm;OUTPUT=Path(output)


def set_query_context(env,joint_ids,joint_names):
    global CONTEXT
    step=int(env.episode_length_buf[0])
    CONTEXT=dict(env=env,step=step,time_s=step*float(env.step_dt),joint_names=list(joint_names),
                 dq_rad_s=array(env.scene['robot'].data.joint_vel[0,joint_ids]).tolist())


def write_record(value):
    if OUTPUT is None:raise ValueError('Unbound study output')
    with (OUTPUT/'entry_geometry.jsonl').open('a') as f:
        f.write(json.dumps(value,allow_nan=False,separators=(',',':'))+'\n')


def record_source_hand_guard(error):
    if CONTEXT is None or LAST_ID is None:raise ValueError('No same-call source context')
    write_record(dict(event='source_hand_FK_guard',query_id=LAST_ID,arm=ARM,
        step=CONTEXT['step'],time_s=CONTEXT['time_s'],error_m=float(error),original_limit_m=.0002,
        passed=float(error)<=.0002))


def choose_request(points,nominal_ids,half,axis,inflation,arm):
    """Exact fixed-gate source expression; E3 only expands the yz membership.

    Original raw float32 quaternion transform is kept for every arm. Near-unit
    projection drift is logged, not silently normalized. This is a finite
    model-coordinate preview, not an interval or physical safety certificate.
    """
    if arm not in ('E0','E1','E2','E3'):raise ValueError('Unknown arm')
    cap=.04
    valid=(np.abs(points[:,1])<=half[1]+inflation+(cap*abs(axis[1]) if arm=='E3' else 0))
    valid&=(np.abs(points[:,2])<=half[2]+inflation+(cap*abs(axis[2]) if arm=='E3' else 0))
    if arm=='E1':valid&=(nominal_ids==40)
    ids=np.flatnonzero(valid)
    maximum=None if not len(ids) else float(np.max(points[ids,0]))
    needed=0. if maximum is None or arm=='E0' else float(max(0.,(maximum+half[0]+inflation)/axis[0]))
    return needed,maximum,int(len(ids))


def required_standoff(g,joint_names,q,root_position,root_quaternion,box_position,box_quaternion,waypoints,box_size,*,residual_limit,nominal_translation_w=None,forecast_margin_m=0.):
    global SEQ,LAST_ID
    if ARM is None or CONTEXT is None:raise ValueError('Unbound native math/observation context')
    if list(joint_names)!=CONTEXT['joint_names']:raise ValueError('Joint-name/source context mismatch')
    if int(CONTEXT['env'].episode_length_buf[0])!=CONTEXT['step']:raise ValueError('Native query step changed')
    before=time.perf_counter();saved=g.data.qpos.copy()
    SEQ+=1;LAST_ID=f'{ARM}-q{SEQ}-step{CONTEXT["step"]}'
    record=dict(event='finite_tip_query',query_id=LAST_ID,arm=ARM,step=CONTEXT['step'],time_s=CONTEXT['time_s'],
        joint_names=list(joint_names),q_rad=np.asarray(q).tolist(),dq_rad_s=CONTEXT['dq_rad_s'],
        root_position_w=np.asarray(root_position).tolist(),root_quaternion_wxyz=np.asarray(root_quaternion).tolist(),
        box_position_w=np.asarray(box_position).tolist(),box_quaternion_wxyz=np.asarray(box_quaternion).tolist(),
        box_size_m=np.asarray(box_size,dtype=float).tolist(),waypoints_rad=np.asarray(waypoints).tolist(),residual_limit_rad=float(residual_limit),
        nominal_translation_w=None if nominal_translation_w is None else np.asarray(nominal_translation_w).tolist(),
        forecast_margin_m=float(forecast_margin_m),censored_by_yz_gate=False,
        scope='finite nominal cloud only; not actual tracking/full robot/continuous guarantee')
    try:
        g.data.qpos[:3]=root_position;g.data.qpos[3:7]=root_quaternion
        for name,value in zip(joint_names,q):g.data.qpos[g.model.joint(name).qposadr[0]]=value
        g.mujoco.mj_forward(g.model,g.data)
        hand=g.model.body('end_effector').id;source=g.data.xpos[hand].copy()
        spheres=[i for i in range(g.model.ngeom) if g.model.geom_bodyid[i]==hand and g.model.geom_type[i]==g.mujoco.mjtGeom.mjGEOM_SPHERE]
        if len(spheres)!=1:raise ValueError('Unknown hand collision sphere geometry')
        radius=float(g.model.geom_size[spheres[0],0])
        if abs(radius-.01)>1e-6:raise ValueError('Unexpected source hand sphere radius')
        half=np.asarray(box_size,dtype=float)*.5
        if half.shape!=(3,) or np.any(half<=0.):raise ValueError('Invalid box size')
        if not 0.<=residual_limit<=.02+1e-7:raise ValueError('Unexpected frozen approach residual envelope')
        translation=np.zeros(3) if nominal_translation_w is None else np.asarray(nominal_translation_w,dtype=float)
        br=rotation(box_quaternion)
        if br[0,0]<.95:raise ValueError('Box standoff outside existing aligned entry domain')
        drift=float(np.linalg.norm(br@br.T-np.eye(3)))
        if drift>1e-5:raise ValueError('Common source-frame quality outside registered floating domain')
        waypoints=np.asarray(waypoints)
        if waypoints.shape!=(2,6):raise ValueError('Not the frozen two-point path')
        joints=[g.model.joint(f'joint{i}').id for i in range(1,7)];bounds=g.model.jnt_range[joints]
        if not 0.<=forecast_margin_m<=.005:raise ValueError('Invalid forecast standoff reserve')
        inflation=radius+.005+forecast_margin_m
        points=[];nominal_ids=[];corner_ids=[]
        corners=list(itertools.product([-residual_limit,residual_limit],repeat=6))
        for i,u in enumerate(np.linspace(0.,1.,41)):
            nominal=waypoints[0]+u*(waypoints[1]-waypoints[0])
            for j,corner in enumerate(corners):
                g.data.qpos[g.arm_qpos]=np.clip(nominal+corner,bounds[:,0],bounds[:,1])
                g.mujoco.mj_forward(g.model,g.data)
                local=br.T@(g.data.xpos[hand]+translation-box_position)
                points.append(local.copy());nominal_ids.append(i);corner_ids.append(j)
        cloud_wall=time.perf_counter()-before
        points=np.asarray(points);nominal_ids=np.asarray(nominal_ids)
        needed,maximum,count=choose_request(points,nominal_ids,half,br[0],inflation,ARM)
        record.update(tip_cloud_box_m=points.tolist(),nominal_indices=nominal_ids.tolist(),residual_corner_indices=corner_ids,
            world_x_in_box=br[0].tolist(),box_rotation_orthogonality_error=drift,
            samples_in_expanded_yz=count,maximum_box_local_x=maximum,minimum_shift_m=needed,
            source_hand_position_w=source.tolist(),common_cloud_observation_wall_s=cloud_wall,
            total_query_wall_s=time.perf_counter()-before,request_within_original40mm=needed<=.04)
        write_record(record)
        if needed>.04:raise ValueError('Box approach needs more than40mm preparation')
        return dict(minimum_shift_m=needed,tip_radius_m=radius,planning_margin_m=.005,forecast_margin_m=forecast_margin_m,
                    residual_limit_rad=residual_limit,samples_in_expanded_yz=count,maximum_box_local_x=maximum,
                    source_hand_position_w=source,study_arm=ARM,query_id=LAST_ID,
                    scope='Controlled finite-cloud scalar request; original support/actual gates remain')
    except Exception as exc:
        if 'tip_cloud_box_m' not in record:
            record.update(error_type=type(exc).__name__,error=str(exc));write_record(record)
        raise
    finally:
        g.data.qpos[:]=saved;g.mujoco.mj_forward(g.model,g.data)
        if int(CONTEXT['env'].episode_length_buf[0])!=CONTEXT['step']:raise RuntimeError('Physical step advanced inside private geometry query')
