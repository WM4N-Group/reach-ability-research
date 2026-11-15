"""Visible front-plane geometry from a CURRENT RGBD-selected appearance proposal.

No odometry, object registry, physical center/dimensions, mass or scene state.
The output is a visible plane/declared standoff goal, not executable binding or
proof that the scene, pose, contact, lateral alignment, or climb entry is safe.
"""
from dataclasses import dataclass,asdict
import hashlib,math
import numpy as np
from visual_box_proposals import (ProposalConfig,propose_visual_candidates,single_visible_hypothesis,
    _hsv,_components,HUE_FAMILIES)

@dataclass(frozen=True)
class FrontPlaneConfig:
    trials:int=1024
    minimum_points:int=32
    plane_tolerance_m:float=.005
    minimum_inlier_fraction:float=.15
    minimum_lateral_span_m:float=.08
    minimum_vertical_span_m:float=.035
    maximum_normal_angle_rad:float=math.radians(35.)
    seed:int=62027
    def __post_init__(self):
        if type(self.trials) is not int or self.trials<1 or type(self.minimum_points) is not int or self.minimum_points<3:raise ValueError('Explicit positive RANSAC budget/point count required')
        if not 0<self.plane_tolerance_m<.02 or not 0<self.minimum_inlier_fraction<=1 or not 0<self.maximum_normal_angle_rad<math.pi/2:raise ValueError('Finite registered front-plane thresholds required')
        if not 0<self.minimum_lateral_span_m or not 0<self.minimum_vertical_span_m:raise ValueError('Positive visible spans required')


def front_plane(points,config=FrontPlaneConfig()):
    points=np.asarray(points,dtype=np.float64)
    if points.ndim!=2 or points.shape[1]!=3 or len(points)<config.minimum_points or not np.isfinite(points).all():raise ValueError('Sufficient finite visible body-frame points required')
    random=np.random.default_rng(config.seed);best=None;threshold=math.cos(config.maximum_normal_angle_rad)
    for _ in range(config.trials):
        sample=points[random.choice(len(points),3,replace=False)];n=np.cross(sample[1]-sample[0],sample[2]-sample[0]);norm=np.linalg.norm(n)
        if norm<1e-10:continue
        n/=norm
        if n[0]<0:n=-n
        if n[0]<threshold:continue
        d=float(n@sample[0]);inliers=abs(points@n-d)<=config.plane_tolerance_m
        if best is None or inliers.sum()>best.sum():best=inliers
    if best is None or best.sum()<config.minimum_points or best.mean()<config.minimum_inlier_fraction:raise ValueError('No sufficiently supported visible front-facing plane')
    fit=points[best];center=fit.mean(0);_,_,v=np.linalg.svd(fit-center,full_matrices=False);n=v[-1]
    if n[0]<0:n=-n
    d=float(n@center);residual=abs(points@n-d);inliers=residual<=config.plane_tolerance_m;fit=points[inliers]
    if n[0]<threshold or len(fit)<config.minimum_points or inliers.mean()<config.minimum_inlier_fraction:raise ValueError('Refined visible plane outside front-facing support domain')
    span=np.quantile(fit,.9,axis=0)-np.quantile(fit,.1,axis=0)
    if span[1]<config.minimum_lateral_span_m or span[2]<config.minimum_vertical_span_m:raise ValueError('Insufficient visible width/height to infer a vertical front plane')
    point=np.median(fit,axis=0);point[0]=(d-n[1]*point[1]-n[2]*point[2])/n[0]
    return dict(normal_body_xyz=n.tolist(),plane_offset_body_m=d,visible_point_body_xyz_m=point.tolist(),
        inlier_points=int(inliers.sum()),input_points=len(points),inlier_fraction=float(inliers.mean()),
        p90_inlier_residual_m=float(np.quantile(residual[inliers],.9)),visible_p10_p90_span_body_m=span.tolist(),
        full_box_center_or_extent_inferred=False)


def describe_visible_goal(rgb,depth,K,mount,*,frame_local_ref,current_RGB_sha256,standoff_m,proposal_config=ProposalConfig(),plane_config=FrontPlaneConfig()):
    if type(standoff_m) not in (int,float) or not math.isfinite(standoff_m) or not .5<=standoff_m<=1.5:raise ValueError('Declared bounded native-approach standoff required')
    result=propose_visual_candidates(rgb,depth,K,mount,config=proposal_config)
    chosen=single_visible_hypothesis(result,frame_local_ref,current_RGB_sha256=current_RGB_sha256)
    hue,saturation,value=_hsv(rgb);family=chosen['appearance_family'];_,low,high=next(row for row in HUE_FAMILIES if row[0]==family)
    mask=((hue>=low)&(hue<high)) if low<high else ((hue>=low)|(hue<high))
    mask&=(saturation>=proposal_config.minimum_saturation)&(value>=proposal_config.minimum_value)
    candidates=[]
    for pixels in _components(mask):
        y,x=pixels[:,0],pixels[:,1];box=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
        if box==chosen['pixel_bbox_xyxy'] and len(pixels)==chosen['pixel_count']:candidates.append(pixels)
    if len(candidates)!=1:raise ValueError('Current selected component could not be recovered uniquely')
    y,x=candidates[0].T;z=depth.reshape(rgb.shape[:2])[y,x]
    valid=np.isfinite(z)&(z>=proposal_config.minimum_depth_m)&(z<=proposal_config.maximum_depth_m)
    z=z[valid].astype(np.float64);u=x[valid]+.5;v=y[valid]+.5
    optical=np.stack(((u-K[0,2])*z/K[0,0],(v-K[1,2])*z/K[1,1],z),1)
    points=optical@mount[:3,:3].T+mount[:3,3];plane=front_plane(points,plane_config)
    normal=np.asarray(plane['normal_body_xyz']);point=np.asarray(plane['visible_point_body_xyz_m'])
    # A geometric normal-standoff point. Lateral target/entry safety are not
    # certified by a cropped surface's median point and must be admitted apart.
    goal=point-normal*standoff_m
    return dict(schema='visible-front-plane-declared-standoff-v2',RGB_sha256=result['RGB_sha256'],calibration_sha256=result['calibration_sha256'],
        frame_local_ref=frame_local_ref,appearance_family=family,plane=plane,declared_standoff_m=float(standoff_m),
        diagnostic_normal_standoff_point_body_xyz_m=goal.tolist(),plane_configuration=asdict(plane_config),
        uses_only_current_RGBD_and_calibration=True,uses_integrated_odometry=False,uses_hidden_pose_or_mass=False,
        lateral_goal_or_executable_binding_certified=False,physical_action_admitted=False)
