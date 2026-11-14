"""Real body-attached MuJoCo RGBD/proprio observer, strictly no stepping/writes."""
import numpy as np
import torch
from .scene import CAMERA_NAME, IDENTITY, calibration


class OnboardObserver:
    def __init__(self,runtime,config):
        import mujoco
        self.r,self.config=runtime,config; self.np=np
        self.K,self.mount=calibration(config['width'],config['height'])
        self.renderer=mujoco.Renderer(runtime.sim.model,height=config['height'],width=config['width'])
        model=runtime.sim.model
        camera=model.camera(CAMERA_NAME)
        if int(model.cam_bodyid[camera.id])!=runtime.sim.base_id:
            raise ValueError('Onboard camera is not attached to actual base_link')
        # Verify compiled camera extrinsics/intrinsics, not merely proposed config.
        if not np.allclose(model.cam_pos[camera.id],self.mount[:3,3],atol=1e-10):
            raise ValueError('Compiled camera mount differs')
        R=np.empty(9);mujoco.mju_quat2Mat(R,model.cam_quat[camera.id])
        if not np.allclose(R.reshape(3,3)@np.diag([1.,-1.,-1.]),self.mount[:3,:3],atol=1e-10):
            raise ValueError('Compiled ROS-optical camera rotation differs')
        f=config['height']/(2*np.tan(np.deg2rad(model.cam_fovy[camera.id])/2))
        if not np.allclose([f,f],self.K[[0,1],[0,1]],atol=1e-8):raise ValueError('Compiled camera intrinsics differ')
        self.frames=0

    def snapshot(self):
        p=self.r.sim
        return (float(p.data.time),*[getattr(p.data,n).copy() for n in ('qpos','qvel','act','ctrl')],
            [x.copy() for x in p.queue])

    @staticmethod
    def unchanged(before,after):
        return before[0]==after[0] and all(np.array_equal(a,b) for a,b in zip(before[1:5],after[1:5])) and (
            len(before[5])==len(after[5]) and all(np.array_equal(a,b) for a,b in zip(before[5],after[5])))

    def public_body_proprio(self):
        robot=self.r.sim.robot.data
        return np.r_[robot.projected_gravity_b[0].numpy(),robot.root_ang_vel_b[0].numpy(),robot.root_lin_vel_b[0].numpy()].astype(np.float32)

    def capture(self,control_tick,issued_previous):
        p=self.r.sim;before=self.snapshot()
        self.renderer.disable_depth_rendering();self.renderer.update_scene(p.data,camera=CAMERA_NAME)
        rgb=self.renderer.render().copy()
        self.renderer.enable_depth_rendering();self.renderer.update_scene(p.data,camera=CAMERA_NAME)
        depth=self.renderer.render().copy();self.renderer.disable_depth_rendering()
        if not self.unchanged(before,self.snapshot()):raise RuntimeError('Rendering changed physics/state/command queue')
        if rgb.dtype!=np.uint8 or rgb.shape!=(self.config['height'],self.config['width'],3):raise ValueError('Actual RGB shape required')
        if depth.shape!=(self.config['height'],self.config['width']):raise ValueError('Actual optical metric depth required')
        depth=np.where(np.isfinite(depth)&(depth>=.05)&(depth<=15.),depth,np.nan).astype(np.float32)
        robot=p.robot.data
        # These are the actual native MuJoCo bridge observations, not object truth.
        proprio=np.r_[p.data.qpos[p.qids],p.data.qvel[p.dids],self.public_body_proprio()].astype(np.float32)
        t=lambda a:torch.from_numpy(np.asarray(a).copy())
        packet=dict(rgb=t(rgb)[None,None],depth_m=t(depth[...,None])[None,None],camera_K=t(self.K)[None],
            T_base_optical=t(self.mount)[None],proprio=t(proprio)[None,None],
            actions_previous=t(np.asarray(issued_previous if control_tick else np.zeros(18),dtype=np.float32))[None,None],
            action_valid=torch.tensor([[control_tick>0]],dtype=torch.bool),timestamps_s=torch.tensor([[float(p.data.time)]],dtype=torch.float64))
        self.frames+=1
        return packet,self.private_catalog(control_tick)

    def private_catalog(self,tick):
        p=self.r.sim;R=p.data.xmat[p.base_id].reshape(3,3);base=p.data.xpos[p.base_id]
        ids=IDENTITY if self.config['scene_recipe'] in ('research_threebox','integrated_course') else {'upstream_demo':dict(body='push_box')}
        if self.config.get('probe_physics'):ids={'probe_object':dict(body='push_box')}
        objects=[]
        for opaque,item in ids.items():
            bid=p.model.body(item['body']).id
            objects.append(dict(opaque_object_id=opaque,body_name=item['body'],position_world_m=p.data.xpos[bid].tolist(),
                center_base_xyz_m=((p.data.xpos[bid]-base)@R).tolist(),quaternion_wxyz=p.data.xquat[bid].tolist(),
                mass_kg_private_only=float(p.model.body_mass[bid])))
        return dict(schema='mujoco-private-object-catalog-v1',model_input_allowed=False,control_tick=tick,
            actual_sim_time_s=float(p.data.time),objects=objects,
            root_position_world_m=base.tolist(),R_world_from_body=R.tolist())

    def close(self):self.renderer.close()
