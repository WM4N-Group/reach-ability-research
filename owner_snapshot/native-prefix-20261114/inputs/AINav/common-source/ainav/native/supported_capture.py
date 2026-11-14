"""Cold-start supported compact capture without claiming any PUSH failure/NAV arrival.

Uses the existing native WholeBodyQP, collision guard and protected arm reference
intersection. Only software references change; no live qpos/qvel/force/FIFO writes.
This is an engineering startup primitive, never a model-selected task skill.
"""
from collections import deque
from dataclasses import replace
import math


def capture_ready(metrics):
    """Same strict loaded-stationary gates used by protected compact handoff."""
    values=[*metrics['foot_normal_N'],metrics['max_foot_speed'],metrics['base_linear_speed'],
        metrics['base_angular_speed'],metrics['tilt_rad'],metrics['arm_error'],metrics['arm_speed'],
        metrics['reference_error'],metrics['reference_speed'],metrics['hand_force_N']]
    if len(metrics['foot_normal_N'])!=4 or not all(math.isfinite(x) for x in values):return False
    return (min(metrics['foot_normal_N'])>=12. and metrics['max_foot_speed']<.03
        and metrics['base_linear_speed']<.02 and metrics['base_angular_speed']<.1 and metrics['tilt_rad']<.1
        and metrics['arm_error']<.04 and metrics['arm_speed']<.12 and metrics['reference_error']<.002
        and metrics['reference_speed']<.02 and metrics['hand_force_N']<3. and metrics['on_declared_support'])


class ActualCaptureWitness:
    def __init__(self,owner):
        if not owner.complete or owner.actual_issued_steps<2 or len(owner.last_two)!=2:
            raise ValueError('Actual completed stationary capture and issued commands required')
        self.owner=owner;self.r=owner.r;self.data=owner.s.data;self.queue=owner.s.queue
        self.observed_time=float(self.data.time);self.support_ref=owner.support_ref
        self.original_goal_sha=owner.goal_sha;self.original_history_sha=owner.history_sha
        self.validate(self.r)

    def validate(self,runtime):
        if runtime is not self.r or runtime.sim.data is not self.data or runtime.sim.queue is not self.queue:
            raise ValueError('Capture belongs to another runtime/world/FIFO')
        if float(self.data.time)<self.observed_time:raise ValueError('Capture clock regressed')
        self.owner.check_guards()
        if not self.owner.complete or not capture_ready(self.owner.measure()):raise RuntimeError('Actual supported capture lost')
        return True

    def report(self):return dict(kind='actual_cold_start_supported_capture',time_s=self.observed_time,
        support_ref=self.support_ref,actual_issued_steps=self.owner.actual_issued_steps,
        no_PUSH_failure_claimed=True,no_NAV_arrival_claimed=True,model_input=False)


class SupportedCapture:
    def __init__(self,runtime,registry,*,support_ref,journal):
        import numpy as np
        import mujoco
        from mujoco_zyh.stall_stow import history_sha
        from mujoco_zyh.native_behavior_executor import array_sha
        from mujoco_zyh.resume_nav import NAV_ARM
        r=runtime;p=r.sim
        if r.step_count!=0 or p.data.time!=0 or len(p.queue):raise ValueError('Cold capture only before first task step')
        if support_ref not in registry.surfaces:raise ValueError('Actual declared cold-start support required')
        self.r,self.s,self.registry,self.support_ref,self.journal=r,p,registry,support_ref,journal
        self.pm=r.push['model'];self.old=r.last;self.goal=NAV_ARM.copy();self.reference=self.old.position[12:].copy()
        self.origin_reference=self.reference.copy();self.velocity=np.zeros(6);self.start_ff=self.old.feedforward[12:].copy()
        self.last_two=deque(maxlen=2);self.actual_issued_steps=0;self.phase='GRAVITY_RECONCILIATION'
        self.started=float(p.data.time);self.last_command_time=None;self.complete=False;self.stable_since=None
        self.goal_sha=array_sha(p.box_push_target.numpy());self.history_sha=history_sha(p)
        finish=r.push['finish'];self.config=replace(finish.FinishConfig(),stance_posture_weight=0.,arm_pose=tuple(self.goal),arm_speed=.45,deadline=15.)
        p.feet_ids=np.array([p.model.body(n+'_foot').id for n in ('FR','FL','RR','RL')])
        p.soft_limits=p.robot.data.soft_joint_pos_limits.numpy()[0][[p.robot.joint_names.index(n) for n in self.pm.JOINTS]]
        self.qp=r.push['balance'].WholeBodyQP(p,self.config);self.guard=finish.CollisionGuard(p,self.config)
        limits=p.model.jnt_range[p.jids[12:]]
        self.limits=np.column_stack((np.maximum(limits[:,0],p.soft_limits[12:,0]),np.minimum(limits[:,1],p.soft_limits[12:,1])))
        self.posture=p.data.qpos[p.qids[:12]].copy();self.anchors=p.data.xpos[p.feet_ids].copy()
        self.anchor_since=None;self.anchors_latched=False;self.base_origin=p.data.qpos[:3].copy()
        R=p.data.xmat[p.base_id].reshape(3,3);self.yaw=float(np.arctan2(R[1,0],R[0,0]))
        self.fk=mujoco.MjData(p.model);self.last_com=-math.inf;self.com=None;self.reference_receipts=[]
        journal(dict(event='registered_cold_capture_constructed',time_s=0.,initial_reference_is_configuration_not_issued_history=True,
            original_native_QP=True,no_failed_PUSH_created=True,no_completed_owner_fabricated=True,model_input=False))

    def measure(self):
        import numpy as np
        import mujoco
        p=self.s;R=p.data.xmat[p.base_id].reshape(3,3);speeds=[]
        for bid in p.feet_ids:
            J=np.zeros((3,p.model.nv));mujoco.mj_jacBody(p.model,p.data,J,None,int(bid));speeds.append(float(np.linalg.norm(J@p.data.qvel)))
        feet=p.data.xpos[p.feet_ids];support=self.registry.surfaces[self.support_ref];x0,x1,y0,y1=support.bounds_xy_m
        force=p.scene.sensors['box_contact_hand'].data.force_matrix_w.numpy().sum(axis=(1,2))[0]
        return dict(foot_normal_N=p.forces[p.feet_ids,2].tolist(),max_foot_speed=max(speeds),
            base_linear_speed=float(np.linalg.norm(p.data.qvel[:3])),base_angular_speed=float(np.linalg.norm(p.data.qvel[3:6])),
            tilt_rad=float(np.arccos(np.clip(R[2,2],-1,1))),arm_error=float(np.max(abs(p.data.qpos[p.qids[12:]]-self.goal))),
            arm_speed=float(np.max(abs(p.data.qvel[p.dids[12:]]))),reference_error=float(np.max(abs(self.reference-self.goal))),
            reference_speed=float(np.max(abs(self.velocity))),hand_force_N=float(np.linalg.norm(force)),
            on_declared_support=bool(np.all((feet[:,0]>x0)&(feet[:,0]<x1)&(feet[:,1]>y0)&(feet[:,1]<y1))
                and np.all(abs(feet[:,2]-support.top_z_m-.022)<.04)),
            drift_m=float(np.linalg.norm(p.data.qpos[:2]-self.base_origin[:2])))

    def check_guards(self):
        import numpy as np
        from mujoco_zyh.stall_stow import history_sha
        from mujoco_zyh.native_behavior_executor import array_sha
        from .registered_guards import check_object_contacts
        p=self.s;m=self.measure()
        if history_sha(p)!=self.history_sha or array_sha(p.box_push_target.numpy())!=self.goal_sha:raise RuntimeError('Cold capture modified original PUSH history/goal')
        check_object_contacts(self.r,self.registry)
        reason=self.guard.check(p.data.qpos[p.qids[12:]],allow_hand_contact=False,record=True)
        if reason:raise RuntimeError('cold_capture_actual_geometry:'+reason)
        if m['drift_m']>.18 or m['base_linear_speed']>.15:raise RuntimeError('Cold capture outside original stationary envelope')
        if np.max(abs(p.torque[12:])/self.pm.EFFORT[12:])>=.98:raise RuntimeError('cold_capture_original_arm_effort_gate')
        if self.phase=='COMPACT_TRANSFER' and min(m['foot_normal_N'])<12:raise RuntimeError('Cold capture loaded support lost during arm transfer')
        return m

    def command(self):
        import numpy as np
        import mujoco
        from mujoco_zyh.stall_stow import unload_reference,select_reference
        p=self.s;now=float(p.data.time);age=now-self.started
        if self.last_command_time is not None and abs(now-self.last_command_time-.005)>1e-7:
            raise RuntimeError('Capture requires one actually issued 5ms command per call')
        self.last_command_time=now
        if age>15.:raise RuntimeError('Cold capture deadline reached')
        m=self.check_guards();planted=min(m['foot_normal_N'])>=12 and m['max_foot_speed']<.03
        self.anchor_since=(self.anchor_since if self.anchor_since is not None else now) if planted else None
        if not self.anchors_latched and self.anchor_since is not None and now-self.anchor_since>=.1-1e-8 and self.actual_issued_steps>=20:
            self.anchors=p.data.xpos[p.feet_ids].copy();self.anchors_latched=True
            self.journal(dict(event='cold_capture_actual_loaded_anchor_reference',time_s=now,actual_steps=self.actual_issued_steps,model_input=False))
        gravity=p.robot.get_gravity_compensation_forces().numpy()[0]
        gravity=gravity[[p.robot.joint_names.index('joint'+str(i)) for i in range(1,7)]]
        if self.phase=='GRAVITY_RECONCILIATION' and age>=1. and self.anchors_latched and m['arm_speed']<.12 and m['base_linear_speed']<.02:
            self.phase='COMPACT_TRANSFER';self.journal(dict(event='cold_capture_compact_transfer_started',time_s=now,model_input=False))
        if self.phase=='GRAVITY_RECONCILIATION':
            self.reference,self.velocity,ff,self.reference_receipts=unload_reference(self.origin_reference,self.origin_reference,self.reference,self.velocity,
                p.data.qpos[p.qids[12:]],p.data.qvel[p.dids[12:]],self.pm.KP[12:],self.pm.KD[12:],gravity,self.pm.EFFORT[12:],self.limits,age,dt=.005,start_ff=self.start_ff)
            arm_pd_v=np.zeros(6)
        else:
            ff=gravity
            self.reference,self.velocity,self.reference_receipts=select_reference(self.goal,self.reference,self.velocity,
                p.data.qpos[p.qids[12:]],p.data.qvel[p.dids[12:]],self.pm.KP[12:],self.pm.KD[12:],ff,self.pm.EFFORT[12:],self.limits,dt=.005)
            arm_pd_v=self.velocity
        reason=self.guard.segment(p.data.qpos[p.qids[12:]],self.reference)
        if reason:raise RuntimeError('cold_capture_reference_geometry:'+reason)
        warning=self.guard.check(p.data.qpos[p.qids[12:]]+.1*p.data.qvel[p.dids[12:]],joint_limits=False)
        if warning:raise RuntimeError('cold_capture_velocity_forecast:'+warning)
        if now-self.last_com>=.02-1e-8:
            self.last_com=now;before=p.data.qpos.copy();self.fk.qpos[:]=p.data.qpos;self.fk.qvel[:]=0.
            self.fk.qpos[p.qids[:12]]=self.posture;self.fk.qpos[3:7]=[np.cos(self.yaw/2),0.,0.,np.sin(self.yaw/2)]
            mujoco.mj_forward(p.model,self.fk)
            self.com=self.anchors.mean(axis=0)+self.fk.subtree_com[p.base_id]-self.fk.xpos[p.feet_ids].mean(axis=0)
            if not np.array_equal(before,p.data.qpos):raise RuntimeError('Reference FK modified live task')
        command=self.r.Command(np.r_[self.posture,self.reference],np.r_[np.zeros(12),arm_pd_v],self.pm.KP.copy(),self.pm.KD.copy(),np.r_[np.zeros(12),ff])
        torque,*_=self.qp.solve(p.forces[p.feet_ids,2]>4.,self.anchors,np.zeros((4,3)),np.zeros((4,3)),self.com,self.yaw,self.posture,command)
        takeover=np.clip(age/.1,0,1);takeover=takeover*takeover*(3-2*takeover)
        q=p.data.qpos[p.qids[:12]];dq=p.data.qvel[p.dids[:12]]
        command.position[:12]=q;command.kp[:12]=(1-takeover)*self.old.kp[:12]+takeover*5.
        command.kd[:12]=(1-takeover)*self.old.kd[:12]+takeover
        command.feedforward[:12]=(1-takeover)*(self.old.kp[:12]*(self.old.position[:12]-q)+self.old.kd[:12]*self.old.velocity[:12]+self.old.feedforward[:12])+takeover*(torque+dq)
        return command

    def after_step(self):
        now=float(self.s.data.time)
        if self.last_command_time is None or abs(now-self.last_command_time-.005)>1e-7:raise RuntimeError('No actual capture step to acknowledge')
        if self.r.step_count!=self.actual_issued_steps+1:raise RuntimeError('Capture step already acknowledged or native step count skipped')
        self.actual_issued_steps+=1;self.last_two.append(self.r.last.position.copy());m=self.check_guards()
        good=self.anchors_latched and self.phase=='COMPACT_TRANSFER' and capture_ready(m)
        self.stable_since=(now if self.stable_since is None else self.stable_since) if good else None
        self.complete=bool(good and now-self.stable_since>=.5-1e-8)
        self.journal(dict(event='cold_capture_actual_sample',time_s=now,phase=self.phase,metrics=m,complete=self.complete,model_input=False))

    def report(self):
        return dict(kind='cold_start_supported_capture',complete=self.complete,phase=self.phase,actual_steps=self.actual_issued_steps,
            stable_seconds=(float(self.s.data.time)-self.stable_since if self.stable_since is not None else 0.),
            metrics=self.measure(),support_ref=self.support_ref,original_goal_sha256=self.goal_sha,
            no_failed_PUSH_created=True,no_NAV_arrival_claimed=True,model_decision=False)
