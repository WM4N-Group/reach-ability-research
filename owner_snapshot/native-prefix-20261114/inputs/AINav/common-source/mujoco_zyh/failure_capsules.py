"""Opt-in bounded PRIVATE before-raise evidence, never a recovery controller.

No mj_step/mj_forward, refresh, observation, termination, solver call or state
write. Existing protocols do NOT install this recorder. A future independently
frozen protocol must explicitly budget/install it; CPU preparation is not a
physical dispatch authorization.
"""
import hashlib
import inspect
import io
import json
from pathlib import Path
import re

import numpy as np

CONFIG = dict(schema='mujoco-private-failure-capsules-v1', max_capsules=8,
              max_bytes=2 * 1024 * 1024, max_contacts=256,
              model_input_allowed=False, training_allowed=False)


def validate_config(config):
    if config != CONFIG:
        raise ValueError('Exact independently registered private capsule budget required')
    return dict(config)


def array(value):
    if hasattr(value, 'detach'):
        value = value.detach().cpu().numpy()
    return np.array(value, copy=True)


def json_value(value):
    """Lossless arrays live in NPZ; JSON uses null for missing sensor points."""
    if isinstance(value, dict):return {str(k):json_value(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):return [json_value(v) for v in value]
    if isinstance(value, np.ndarray):return json_value(value.tolist())
    if isinstance(value, np.generic):return json_value(value.item())
    if isinstance(value, float) and not np.isfinite(value):return None
    if value is None or isinstance(value, (str,int,float,bool)):return value
    raise TypeError('Unregistered capsule metadata type: '+type(value).__name__)


def hand_details(view, box):
    """Expose native conjunction components; compare to the ORIGINAL readers.

    Uses the exact native tensor quaternion operations and cached sensor point,
    not a closest point or unselected object's strongest contact. No cache reset.
    """
    import torch
    sensor=view.scene.sensors['box_contact_hand'].data
    force=sensor.force_matrix_w.sum(dim=(1,2));contact=sensor.contact_pos_w[:,0,0]
    finite=torch.isfinite(contact).all(dim=1)
    hand=view.scene['robot'].data.body_pos_w[:,view.hand_cfg.body_ids[0]]
    tip_distance=torch.linalg.vector_norm(torch.nan_to_num(contact)-hand,dim=1)
    radius=getattr(view.cfg,'push_contact_tip_radius',.07)
    selected=view.scene['box'].data
    local=box.quat_apply_inverse(selected.root_quat_w,contact-selected.root_pos_w)
    axis=torch.zeros_like(force);axis[:,0]=1.;axis=box.quat_apply(selected.root_quat_w,axis)
    strength=torch.linalg.vector_norm(force,dim=1);resisting=-(force*axis).sum(dim=1)
    size=view.cfg.box_size;margin=getattr(view.cfg,'push_contact_height_margin',.01)
    terms=dict(finite_point=finite,near_tip=tip_distance<radius,
               resisting_force_gt_1N=resisting>1.,resisting_axis_ratio_gt_point8=resisting>.8*strength,
               front_face=(local[:,0]+size[0]/2.).abs()<.02,
               lateral_inside=local[:,1].abs()<size[1]/2.,
               height_inside=local[:,2].abs()<=size[2]/2.-margin+1e-4)
    conjunction=torch.ones_like(finite)
    for v in terms.values():conjunction &= v
    native=box.hand_contact(view,view.hand_cfg)
    invalid=box.invalid_hand_contact(view,view.hand_cfg)
    if not torch.equal(conjunction,native) or not torch.equal((strength>1.) & ~conjunction,invalid):
        raise ValueError('Diagnostic conjunction does not match pinned native contact predicate')
    return dict(native_hand_contact=array(native),native_invalid_hand_contact=array(invalid),
                native_forbidden_box_contact=array(box.forbidden_box_contact(view)),
                native_box_tipped=array(box.box_tipped(view)),components={k:array(v) for k,v in terms.items()},
                force_world_N=array(force),representative_point_world_m=array(contact),
                EEF_world_m=array(hand),tip_distance_m=array(tip_distance),tip_radius_m=radius,
                selected_box_cached_position_world_m=array(selected.root_pos_w),
                selected_box_cached_quaternion_wxyz=array(selected.root_quat_w),
                representative_point_box_local_m=array(local),box_front_axis_world=array(axis),
                force_norm_N=array(strength),resisting_force_N=array(resisting),box_size_m=list(size),
                contact_height_margin_m=margin,
                native_predicate_source_sha256={name:hashlib.sha256(inspect.getsource(getattr(box,name)).encode()).hexdigest()
                    for name in ('hand_contact','invalid_hand_contact','forbidden_box_contact','box_tipped','valid_front_contact')})


def integration(runtime):
    import mujoco
    s=runtime.sim;spec=mujoco.mjtState.mjSTATE_INTEGRATION
    state=np.empty(mujoco.mj_stateSize(s.model,spec))
    mujoco.mj_getState(s.model,s.data,state,spec)
    return state



def copy_history_terms(arrays,views):
    """Native PUSH has seven DIFFERENT-width3-frame terms, never stack them."""
    layout={}
    for name,bridge in views:
        history=getattr(bridge,'history',None);layout[name]=[]
        for index,value in enumerate(history if history is not None else []):
            key=name+'_policy_observation_history_term_'+str(index)
            values=array(value);arrays[key]=values
            layout[name].append(dict(key=key,shape=list(values.shape),dtype=str(values.dtype)))
    return layout


def snapshot(runtime, view=None):
    import mujoco
    s=runtime.sim;view=s if view is None else view
    if view.model is not s.model or view.data is not s.data:
        raise ValueError('Capsule target must share the SAME live world, not a reconstruction')
    before=integration(runtime);queue=[array(v) for v in s.queue];last=array(runtime.last.array())
    if s.data.ncon>CONFIG['max_contacts']:raise ValueError('Actual contacts exceed independently registered capsule budget')
    arrays=dict(integration_state=before,qpos=array(s.data.qpos),qvel=array(s.data.qvel),
                qacc=array(s.data.qacc),ctrl=array(s.data.ctrl),qacc_warmstart=array(s.data.qacc_warmstart),
                last_actually_issued_command=last,delay_steps=array(s.delays),
                immutable_FIFO=np.stack(queue) if queue else np.empty((0,5,18)),
                actual_raw_torque=array(s.raw_torque),actual_clipped_torque=array(s.torque),
                native_software_targets_unissued=array(view.targets),
                actual_joint_q=array(s.data.qpos[s.qids]),actual_joint_dq=array(s.data.qvel[s.dids]),
                actual_base_position_world_m=array(s.data.xpos[s.base_id]),
                actual_base_quaternion_wxyz=array(s.data.xquat[s.base_id]),
                base_free_joint_linear_velocity_world_m_s=array(s.data.qvel[:3]),
                base_free_joint_angular_velocity_local_rad_s=array(s.data.qvel[3:6]),
                actual_base_subtree_COM_world_m=array(s.data.subtree_com[s.base_id]),
                selected_box_position_world_m=array(s.data.xpos[view.box_id]),
                selected_box_quaternion_wxyz=array(s.data.xquat[view.box_id]),
                selected_box_original_goal_world_m=array(view.box_push_target),
                selected_contact_forces_by_body_world_N=array(view.forces),
                all_body_position_world_m=array(s.data.xpos),all_body_quaternion_wxyz=array(s.data.xquat),
                selected_box_free_joint_velocity=array(s.data.qvel[view.box_did:view.box_did+6]),
                global_A_original_goal_world_m=array(s.box_push_target))
    history_layout=copy_history_terms(arrays,(('selected',view),('global_A',s)))
    cache_names=[]
    software=getattr(getattr(view,'target_context',None),'_software',vars(view))
    for prefix,values in (('controller',vars(view.controller)),('target_software',software)):
        for name,value in sorted(values.items()):
            if isinstance(value,np.ndarray) or hasattr(value,'detach'):
                arrays[prefix+'__'+name]=array(value);cache_names.append(prefix+'__'+name)
    J=np.zeros((3,s.model.nv));mujoco.mj_jacSubtreeCom(s.model,s.data,J,s.base_id)
    arrays['actual_COM_velocity_world_m_s']=J@s.data.qvel
    contacts=[];contact_arrays=[]
    for i in range(s.data.ncon):
        c=s.data.contact[i];w=np.zeros(6);mujoco.mj_contactForce(s.model,s.data,i,w)
        g=[int(c.geom1),int(c.geom2)];b=[int(s.model.geom_bodyid[v]) for v in g]
        contacts.append(dict(index=i,geom_ids=g,geom_names=[s.model.geom(v).name for v in g],
                             body_ids=b,body_names=[s.model.body(v).name for v in b],
                             includes_selected_box=int(view.box_id) in b,dist_m=float(c.dist),
                             efc_address=int(c.efc_address),dim=int(c.dim)))
        contact_arrays.append(np.r_[c.pos,c.frame,w,c.frame.reshape(3,3).T@w[:3]])
    arrays['contact_pos_frame_wrench_world_force']=np.stack(contact_arrays) if contacts else np.empty((0,21))
    names=[]
    for name,sensor in sorted(view.scene.sensors.items()):
        if not (name.startswith('box_contact_') or name=='contact_forces'):continue
        names.append(name)
        for field in ('force_matrix_w','contact_pos_w','net_forces_w'):
            if hasattr(sensor.data,field):arrays['sensor__'+name+'__'+field]=array(getattr(sensor.data,field))
    details=hand_details(view,runtime.push['bridge'].box_push)
    metadata=dict(state_spec=int(mujoco.mjtState.mjSTATE_INTEGRATION),actual_time_s=float(s.data.time),
                  actual_physical_steps=runtime.step_count,selected_box_body_id=int(view.box_id),
                  selected_box_body_name=s.model.body(int(view.box_id)).name,
                  global_A_alias_box_body_id=int(s.box_id),
                  active_opaque_candidate=getattr(runtime,'wm_active_candidate',None),
                  selected_view_controller_env_same_scene_box=(view.controller.env.scene['box'] is view.scene['box']),
                  selected_view_is_global_A_bridge=view is s,selected_native_contact_sensor_names=names,
                  copied_numeric_controller_and_target_software_buffers=cache_names,
                  native_policy_history_term_layout=history_layout,
                  world_body_catalog=[dict(id=i,name=s.model.body(i).name,parent_id=int(s.model.body_parentid[i])) for i in range(s.model.nbody)],
                  exact_native_hand_predicate=details,raw_contacts=contacts,
                  contact_array_columns='pos_world3,contact_frame9,wrench_contact_frame6,world_force3; native force is on geom2, negate for geom1',
                  observed_cached_channels_not_refreshed_by_capture=True,
                  model_input_allowed=False,training_allowed=False,
                  physical_state_writes=0,new_physics_or_actor_or_WM_forwards=0)
    if not np.array_equal(before,integration(runtime),equal_nan=True):raise RuntimeError('Capsule changed integration state')
    if len(queue)!=len(s.queue) or any(not np.array_equal(a,b,equal_nan=True) for a,b in zip(queue,s.queue)):
        raise RuntimeError('Capsule changed immutable FIFO')
    if not np.array_equal(last,runtime.last.array(),equal_nan=True):raise RuntimeError('Capsule changed last-issued command')
    return arrays,metadata


class PrivateFailureCapsules:
    def __init__(self, root, runtime, config):
        self.config=validate_config(config);self.runtime=runtime;self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=False)
        self.rows=[];self.bytes=0;self.errors=[];self.closed=False

    def capture(self,event,view=None,extra=None):
        if self.closed or len(self.rows)>=self.config['max_capsules']:raise ValueError('Private capsule count/closure refusal')
        if not re.fullmatch('[a-z][a-z0-9_]{0,63}',event):raise ValueError('Invalid diagnostic event')
        arrays,meta=snapshot(self.runtime,view)
        meta.update(schema=self.config['schema'],event=event,extra=extra or {},
                    exact_measured_event_not_interpolated=True)
        arrays['metadata_utf8']=np.frombuffer(json.dumps(json_value(meta),allow_nan=False,sort_keys=True).encode(),dtype=np.uint8)
        buf=io.BytesIO();np.savez_compressed(buf,**arrays);payload=buf.getvalue()
        if self.bytes+len(payload)>self.config['max_bytes']:raise ValueError('Private capsule byte budget refusal')
        name=f'{len(self.rows):06d}-{event}.npz'
        with (self.root/name).open('xb') as f:f.write(payload)
        row=dict(path=name,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),
                 time_s=meta['actual_time_s'],event=event,selected_box_body_id=meta['selected_box_body_id'])
        self.rows.append(row);self.bytes+=len(payload)
        return row

    def close(self):
        if self.closed:raise ValueError('Capsule recorder already closed')
        self.closed=True
        out=dict(schema=self.config['schema'],files=self.rows,bytes=self.bytes,errors=self.errors,
                 all_required_captures_complete=not self.errors,private_only=True,model_input_allowed=False,
                 training_allowed=False,physical_state_writes=0,new_physics_or_actor_or_WM_forwards=0)
        with (self.root/'closure.json').open('x') as f:json.dump(out,f,indent=2,allow_nan=False)
        return out


def emit(runtime,event,view=None,extra=None,preserve_primary_failure=False):
    recorder=getattr(runtime,'wm_private_capsules',None)
    if recorder is None:return None  # no protocol silently enables new logging
    try:return recorder.capture(event,view=view,extra=extra)
    except Exception as exc:
        recorder.errors.append(dict(event=event,error=repr(exc)))
        if not preserve_primary_failure:
            raise RuntimeError('required_private_failure_capsule_refused:'+event) from exc
        return None  # a diagnostic failure must NOT mask/continue past the hard guard


def install(runtime, root, config):
    """Software-only, BEFORE first task step; never called by old protocols."""
    if runtime.step_count or float(runtime.sim.data.time) or len(runtime.sim.queue):
        raise ValueError('Capsule admission/install is forbidden after task physics or queue issuance')
    if getattr(runtime,'wm_private_capsules',None) is not None:
        raise ValueError('Capsule recorder already installed; no reuse/replacement')
    recorder=PrivateFailureCapsules(Path(root)/'private-failure-capsules',runtime,config)
    runtime.wm_private_capsules=recorder
    return recorder
