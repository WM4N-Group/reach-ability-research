"""EXECUTOR/AUDIT ONLY: ground a preselected pixel hypothesis to a native target.

Private measured geometry disambiguates the already selected visual region; it
never ranks plans, estimates mass or enters the WM's eight-field observation.
This module does not call an actor/step/reset, certify native entry gates, or
retarget a running skill. A future caller must still pass original native gates.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import secrets
import numpy as np
from visual_box_proposals import single_visible_hypothesis,visual_calibration_sha


def require(condition,message):
    if not condition:raise ValueError(message)


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()

def is_sha(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def array(value):
    if hasattr(value,'detach'):value=value.detach().cpu().numpy()
    return np.asarray(value,dtype=np.float64)


def rotation(quaternion):
    q=array(quaternion)
    require(q.shape==(4,) and np.isfinite(q).all() and abs(np.linalg.norm(q)-1)<1e-4,'Measured unit wxyz quaternion required')
    w,x,y,z=q/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def capture_private_catalog(env,*,object_keys,episode_id,control_tick,RGB_sha256,base_body_name='base'):
    """Current live object poses and declared cuboid sizes, sidecar ONLY.

    Body frame is the camera's actual parent body, not an assumed root frame.
    Missing pose/size is an error: never reconstruct stale data from config pose,
    synthesize an old receipt, or read mass/friction/semantic color properties.
    """
    require(isinstance(episode_id,str) and episode_id and type(control_tick) is int and control_tick>=0 and is_sha(RGB_sha256),'Exact episode/tick/RGB identity required')
    require(isinstance(object_keys,(list,tuple)) and object_keys and len(set(object_keys))==len(object_keys)
            and all(isinstance(key,str) and key and key!='robot' for key in object_keys),'Explicit unique executor object keys required')
    robot=env.scene['robot'];names=list(robot.body_names)
    require(names.count(base_body_name)==1,'Camera-parent body must be uniquely measured')
    index=names.index(base_body_name)
    positions=array(robot.data.body_pos_w);quats=array(robot.data.body_quat_w)
    require(positions.shape==(1,len(names),3) and quats.shape==(1,len(names),4),'Single native environment required')
    base_pos=positions[0,index];base_rotation=rotation(quats[0,index]);objects=[]
    require(np.isfinite(base_pos).all(),'Finite actual camera-parent position required')
    for key in object_keys:
        body=env.scene[key];pos=array(body.data.root_pos_w);quat=array(body.data.root_quat_w)
        require(pos.shape==(1,3) and quat.shape==(1,4) and np.isfinite(pos).all(),'Current object pose unavailable')
        size=array(getattr(env.cfg.scene,key).spawn.size)
        require(size.shape==(3,) and np.isfinite(size).all() and (size>0).all(),'Declared frozen cuboid geometry required')
        objects.append(dict(executor_scene_key=key,center_base_xyz_m=((pos[0]-base_pos)@base_rotation).tolist(),
            rotation_base_from_object=(base_rotation.T@rotation(quat[0])).tolist(),size_m=size.tolist()))
    return dict(schema='private-native-object-catalog-v1',model_input_allowed=False,episode_id=episode_id,
        control_tick=control_tick,RGB_sha256=RGB_sha256,camera_parent_body=base_body_name,objects=objects)


@dataclass(frozen=True)
class BindingThresholds:
    minimum_bbox_iou: float=.35
    maximum_surface_error_m: float=.04
    near_optical_z_m: float=.05
    def __post_init__(self):
        require(all(type(x) in (int,float) and np.isfinite(x) for x in (self.minimum_bbox_iou,self.maximum_surface_error_m,self.near_optical_z_m))
            and 0<self.minimum_bbox_iou<=1 and self.maximum_surface_error_m>0 and self.near_optical_z_m>0,'Explicit finite correspondence thresholds required')


def match_geometry(proposal,obj,K,mount,image_hw,thresholds):
    require(set(obj)=={'executor_scene_key','center_base_xyz_m','rotation_base_from_object','size_m'},'Only private geometry, no mass/labels')
    center=array(obj['center_base_xyz_m']);R=array(obj['rotation_base_from_object']);size=array(obj['size_m'])
    require(isinstance(obj['executor_scene_key'],str) and obj['executor_scene_key'] and center.shape==(3,) and R.shape==(3,3)
        and size.shape==(3,) and all(np.isfinite(a).all() for a in (center,R,size)) and (size>0).all()
        and np.allclose(R.T@R,np.eye(3),atol=1e-5) and np.isclose(np.linalg.det(R),1,atol=1e-5),'Measured cuboid geometry invalid')
    local=array(proposal['visible_surface_median_base_xyz_m'])
    require(local.shape==(3,) and np.isfinite(local).all(),'Visible surface point required')
    q=np.abs((local-center)@R)-size/2
    sdf=np.linalg.norm(np.maximum(q,0))+min(float(q.max()),0.)
    corners=np.array([[x,y,z] for x in (-1,1) for y in (-1,1) for z in (-1,1)])*size/2
    body=corners@R.T+center
    optical=(body-mount[:3,3])@mount[:3,:3]
    if (optical[:,2]<=thresholds.near_optical_z_m).any():return None
    pixels=optical@K.T;pixels=pixels[:,:2]/pixels[:,2:]
    h,w=image_hw;box=[max(0.,float(pixels[:,0].min())),max(0.,float(pixels[:,1].min())),
                      min(float(w),float(pixels[:,0].max())),min(float(h),float(pixels[:,1].max()))]
    selected=proposal['pixel_bbox_xyxy']
    area=max(0,box[2]-box[0])*max(0,box[3]-box[1]);chosen=max(0,selected[2]-selected[0])*max(0,selected[3]-selected[1])
    intersection=max(0,min(box[2],selected[2])-max(box[0],selected[0]))*max(0,min(box[3],selected[3])-max(box[1],selected[1]))
    union=area+chosen-intersection;iou=intersection/union if union>0 else 0.
    if iou<thresholds.minimum_bbox_iou or abs(sdf)>thresholds.maximum_surface_error_m:return None
    return dict(executor_scene_key=obj['executor_scene_key'],projected_bbox_xyxy=box,bbox_iou=float(iou),surface_error_m=float(abs(sdf)))


class NativeVisualTargetBinder:
    """Ephemeral, one-use EXECUTOR capability; never pass tokens to a model.

    Advancing a frame invalidates old tokens. New episodes require explicit
    registry reset and cannot reuse an old episode. This clears mappings only,
    NOT physical state/controllers/belief; full-reset verification stays separate.
    """
    def __init__(self,episode_id,*,thresholds=BindingThresholds()):
        require(isinstance(episode_id,str) and episode_id,'New episode identity required')
        require(isinstance(thresholds,BindingThresholds),'Explicit correspondence configuration required')
        self.episode_id=episode_id;self.seen={episode_id};self.frame=None;self.tokens={};self.issued_refs=set();self.thresholds=thresholds
    def new_episode(self,episode_id):
        require(isinstance(episode_id,str) and episode_id and episode_id not in self.seen,'No old episode/registry reuse')
        self.tokens.clear();self.issued_refs.clear();self.frame=None;self.episode_id=episode_id;self.seen.add(episode_id)
    def observe_frame(self,*,episode_id,control_tick,RGB_sha256):
        require(episode_id==self.episode_id and type(control_tick) is int and control_tick>=0 and is_sha(RGB_sha256),'Current episode/tick/RGB required')
        new=(episode_id,control_tick,RGB_sha256)
        if self.frame is not None:
            require(control_tick>=self.frame[1],'No reset/reverse clock inside an episode')
            require(control_tick!=self.frame[1] or new==self.frame,'Same tick cannot change acquisition identity')
        if new!=self.frame:self.tokens.clear();self.issued_refs.clear();self.frame=new
    def bind_selected(self,result,frame_local_ref,catalog,*,camera_K,T_base_optical,image_hw):
        require(self.frame is not None,'Observe actual current frame first')
        require(set(catalog)=={'schema','model_input_allowed','episode_id','control_tick','RGB_sha256','camera_parent_body','objects'}
            and catalog['schema']=='private-native-object-catalog-v1' and catalog['model_input_allowed'] is False,'Private executor-only catalog required')
        require((catalog['episode_id'],catalog['control_tick'],catalog['RGB_sha256'])==self.frame,'Stale catalog/episode correspondence')
        require(frame_local_ref not in self.issued_refs,'No repeated binding of selected reference in the same frame')
        p=single_visible_hypothesis(result,frame_local_ref,current_RGB_sha256=self.frame[2])
        K=array(camera_K);mount=array(T_base_optical)
        require(K.shape==(3,3) and np.isfinite(K).all() and K[0,0]>0 and K[1,1]>0 and np.array_equal(K[2],[0,0,1]),'Camera K required')
        require(mount.shape==(4,4) and np.isfinite(mount).all() and np.allclose(mount[3],[0,0,0,1])
            and np.allclose(mount[:3,:3].T@mount[:3,:3],np.eye(3),atol=1e-5) and np.isclose(np.linalg.det(mount[:3,:3]),1,atol=1e-5),'Body-from-optical calibration required')
        require(result.get('calibration_sha256')==visual_calibration_sha(K,mount),'Selected pixel geometry calibration mismatch')
        require(K[0,1]==0 and K[1,0]==0,'Zero-skew camera required')
        require(len(image_hw)==2 and all(type(x) is int and x>=16 for x in image_hw),'Actual image shape required')
        require(0<=K[0,2]<image_hw[1] and 0<=K[1,2]<image_hw[0],'Principal point outside actual image')
        require(isinstance(catalog['objects'],list) and catalog['objects'],'No current executor objects')
        keys=[x['executor_scene_key'] for x in catalog['objects']];require(len(set(keys))==len(keys),'Duplicate native object keys')
        matches=[m for obj in catalog['objects'] if (m:=match_geometry(p,obj,K,mount,image_hw,self.thresholds)) is not None]
        require(len(matches)==1,'No unique measured geometric correspondence; no default/nearest-object fallback')
        token=secrets.token_hex(16)
        receipt=dict(schema='private-native-visual-binding-v1',model_input_allowed=False,
            episode_id=self.frame[0],control_tick=self.frame[1],RGB_sha256=self.frame[2],selected_visual_ref=frame_local_ref,
            catalog_sha256=digest(catalog),correspondence=matches[0],native_entry_gates_certified=False,actor_invoked=False)
        self.tokens[token]=deepcopy(receipt);self.issued_refs.add(frame_local_ref)
        return token,deepcopy(receipt)
    def resolve_once_for_executor(self,token,*,episode_id,control_tick,RGB_sha256):
        require(self.frame==(episode_id,control_tick,RGB_sha256) and token in self.tokens,'Stale/unknown/consumed executor token')
        return self.tokens.pop(token)['correspondence']['executor_scene_key']
