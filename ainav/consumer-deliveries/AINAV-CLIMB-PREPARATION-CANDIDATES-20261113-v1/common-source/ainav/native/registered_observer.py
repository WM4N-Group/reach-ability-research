"""Unchanged native RGBD/proprio acquisition with registry-driven PRIVATE catalog."""
import numpy as np
from mujoco_zyh.observer import OnboardObserver


class RegisteredObserver(OnboardObserver):
    def __init__(self,runtime,config,registry):
        registry.verify_compiled(runtime.sim.model);self.registry=registry
        super().__init__(runtime,config)

    def private_catalog(self,tick):
        p=self.r.sim;R=p.data.xmat[p.base_id].reshape(3,3);base=p.data.xpos[p.base_id]
        objects=[]
        for o in self.registry.objects.values():
            body=p.model.body(o.body_name).id;geom=p.model.geom(o.body_name+'_geom').id
            world_R=p.data.geom_xmat[geom].reshape(3,3);center=p.data.geom_xpos[geom]
            objects.append(dict(object_id=o.ref,body_name=o.body_name,position_world_m=center.tolist(),
                rotation_world_from_object=world_R.tolist(),center_base_xyz_m=((center-base)@R).tolist(),
                rotation_base_from_object=(R.T@world_R).tolist(),size_m=(2*p.model.geom_size[geom]).tolist()))
        return dict(schema='ainav-private-registered-object-catalog-v1',model_input=False,control_tick=tick,
            time_s=float(p.data.time),objects=objects,material_truth_included=False)
