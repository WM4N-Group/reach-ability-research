"""Private V4 live-contact reader and contiguous stop monitor, not a controller.

No Runtime/Actor construction, stepping, target selection, success receipt or
state writes. Contact fields come from mj_contactForce in the contact frame;
its first component is normal force. Physics use is Data-owned only.
"""
import math,hashlib
from pathlib import Path
from v4_native_asset import validate,require
from capability_boundary import elevated_stop_sample_only

SNAPSHOT_SOURCE_SHA='8d42281aa890bd5224f7d8c0bacc2c44d1fa1bda0ba5a89fec8bffa59f701995'
def deck_normal_loads(foot_geom_to_index,deck_geom_id,contacts):
    """Pure arithmetic on actual contact records; fixtures are not provenance.

    Each contact is (geom1,geom2,contact_frame_normal_xyz,normal_force_N).
    geom ordering changes the normal sign, not the compressive load magnitude.
    Tangential/friction forces are not miscounted as vertical normal support.
    """
    require(type(deck_geom_id)is int and deck_geom_id not in foot_geom_to_index,'Distinct actual deck and foot geoms')
    require(set(foot_geom_to_index.values())==set(range(4)),'Four explicit foot geom groups')
    loads=[0.]*4
    for g1,g2,normal,force in contacts:
        require(len(normal)==3 and all(type(v)in(int,float)and math.isfinite(v)for v in [*normal,force])and force>=0.,'Finite compressive contact normal')
        if g1==deck_geom_id and g2 in foot_geom_to_index:foot=g2
        elif g2==deck_geom_id and g1 in foot_geom_to_index:foot=g1
        else:continue
        require(abs(sum(v*v for v in normal)-1.)<1e-6,'Original unit contact-frame normal')
        loads[foot_geom_to_index[foot]]+=force*abs(normal[2])
    return loads

def read_current_goal_sample(runtime,scene,*,source_root):
    """Read real model/data/contact forces without forward/step or world edits.

    This is private completion evidence only. Never pass the result to a VLM,
    WM, optimizer or rule policy. No caller-supplied sample/force overrides.
    """
    validate(scene)
    import numpy as np
    import mujoco
    from mujoco_zyh import native_behavior_executor as original
    path=Path(original.__file__).resolve();require(path==Path(source_root).resolve()/'mujoco_zyh/native_behavior_executor.py'and hashlib.sha256(path.read_bytes()).hexdigest()==SNAPSHOT_SOURCE_SHA,'Exact original world snapshot source')
    before=original.world_snapshot(runtime);p=runtime.sim;model=p.model;data=p.data
    from goal_support import goal_object,check_current_goal_geometry
    goal=goal_object(scene);bid=int(model.body(goal['body_name']).id);gid=int(model.geom(goal['body_name']+'_geom').id)
    check_current_goal_geometry(scene,box_size=(2*model.geom_size[gid]).tolist(),
        actual_geom_body_id=int(model.geom_bodyid[gid]),selected_body_id=bid,
        geom_is_box=int(model.geom_type[gid])==int(mujoco.mjtGeom.mjGEOM_BOX),
        xyz=data.geom_xpos[gid].tolist(),rotation=data.geom_xmat[gid].reshape(3,3).tolist())
    feet=[int(model.body(n+'_foot').id)for n in ('FR','FL','RR','RL')];require(len(set(feet))==4,'Four original compiled foot bodies')
    mapping={g:feet.index(int(model.geom_bodyid[g]))for g in range(model.ngeom)if int(model.geom_bodyid[g])in feet}
    contacts=[]
    for i in range(data.ncon):
        c=data.contact[i]
        if int(c.geom1)!=gid and int(c.geom2)!=gid:continue
        force=np.zeros(6);mujoco.mj_contactForce(model,data,i,force)
        contacts.append((int(c.geom1),int(c.geom2),[float(v)for v in c.frame[:3]],float(force[0])))
    deck_loads=deck_normal_loads(mapping,gid,contacts);speeds=[]
    for body in feet:
        velocity=np.zeros(6);mujoco.mj_objectVelocity(model,data,mujoco.mjtObj.mjOBJ_BODY,body,velocity,0);speeds.append(float(np.linalg.norm(velocity[3:])))
    R=data.xmat[p.base_id].reshape(3,3);minimum=scene['private_terminal_acceptance']['foot_normal_min_N']
    sample=dict(feet_world_m=data.xpos[feet].tolist(),foot_normal_N=p.forces[feet,2].tolist(),foot_speed_m_s=speeds,
        foot_support_refs=[goal['public_ref']if v>=minimum else 'NO_VERIFIED_GOAL_C_BOX_NORMAL_SUPPORT'for v in deck_loads],
        deck_contact_normal_N=deck_loads,base_linear_speed_m_s=float(np.linalg.norm(data.qvel[:3])),
        base_angular_speed_rad_s=float(np.linalg.norm(data.qvel[3:6])),tilt_rad=float(np.arccos(np.clip(R[2,2],-1.,1.))),
        time_s=float(data.time),tick=runtime.step_count,private_terminal_evidence_not_model_input=True,
        provenance='ACTUAL_CURRENT_C_BOX_MJ_CONTACT_FORCE_NOT_GEOMETRIC_HEIGHT_GUESS')
    require(original.world_snapshot(runtime)==before,'Terminal observation changed original world/FIFO')
    return sample

class ElevatedGoalDwell:
    """Necessary observed stop only, never a complete-task/native-success claim.

    The caller must also validate the actual current original owner, three
    immutable placements and a genuine same-world CLIMB chain. Positive dwell
    alone cannot create a task receipt; no self-certifying complete property.
    """
    def __init__(self,scene):validate(scene);self.scene=scene;self.last=None;self.since=None;self.ready=False
    def observe(self,sample):
        now,tick=sample['time_s'],sample['tick'];require(type(tick)is int and tick>=0 and type(now)in(int,float)and math.isfinite(now)and now>=0,'Actual finite clock/tick')
        valid=elevated_stop_sample_only(self.scene,sample)
        if self.last is not None:
            t,k=self.last;require(now>=t and tick>=k,'No clock or history rewind')
            if(now,tick)==self.last:
                if not valid:self.since=None;self.ready=False
                return self.ready
            if tick-k!=1 or abs(now-t-.005)>1e-7:self.since=None
        self.last=(now,tick)
        if valid:
            if self.since is None:self.since=now
            self.ready=now-self.since>=self.scene['private_terminal_acceptance']['dwell_s']-1e-8
        else:self.since=None;self.ready=False
        return self.ready
