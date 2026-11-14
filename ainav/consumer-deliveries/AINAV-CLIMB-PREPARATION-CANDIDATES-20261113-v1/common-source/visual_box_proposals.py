"""Shared, nonlearned RGB-D appearance proposals; NO engine object access.

Bootstraps candidate discovery for the raw-pixel latent WM and equally informed
baselines. A color-family component is NOT a semantic box certificate, physical
object ID, mass estimate, hidden property, or a learned detector. Geometry is the
VISIBLE surface in the body frame, not full-object center/size or world pose.
Missing/occluded candidates remain missing; never backfill an engine registry.
"""
from dataclasses import dataclass
from copy import deepcopy
import hashlib
import numpy as np


@dataclass(frozen=True)
class ProposalConfig:
    minimum_pixels: int = 64
    minimum_depth_pixels: int = 32
    minimum_depth_fraction: float = .2
    minimum_saturation: float = .18
    minimum_value: float = .08
    minimum_depth_m: float = .05
    maximum_depth_m: float = 15.

    def __post_init__(self):
        if (type(self.minimum_pixels) is not int or self.minimum_pixels<1
                or type(self.minimum_depth_pixels) is not int or self.minimum_depth_pixels<1
                or not all(np.isfinite(v) for v in (self.minimum_depth_fraction,self.minimum_saturation,
                    self.minimum_value,self.minimum_depth_m,self.maximum_depth_m))
                or not 0<=self.minimum_saturation<=1 or not 0<=self.minimum_value<=1
                or not 0<=self.minimum_depth_fraction<=1
                or not 0<self.minimum_depth_m<self.maximum_depth_m):
            raise ValueError('Finite explicit pixel/depth thresholds required')


# Visible hue families only; no family -> kg or success mapping exists here.
HUE_FAMILIES=(('warm',.035,.16),('green',.28,.50),('violet',.70,.90),('red',.95,.035))


def _validate(rgb,depth,K,mount):
    if not isinstance(rgb,np.ndarray) or rgb.dtype!=np.uint8 or rgb.ndim!=3 or rgb.shape[2]!=3:
        raise ValueError('Actual uint8 RGB [H,W,3] required, not simulator colors')
    h,w,_=rgb.shape
    if min(h,w)<16:raise ValueError('Actual image too small')
    if not isinstance(depth,np.ndarray) or depth.shape not in ((h,w),(h,w,1)) or depth.dtype.kind!='f':
        raise ValueError('Actual floating optical Z image required')
    if (not isinstance(K,np.ndarray) or K.shape!=(3,3) or not np.isfinite(K).all()
            or K[0,0]<=0 or K[1,1]<=0 or K[0,1]!=0 or K[1,0]!=0
            or not np.array_equal(K[2],[0,0,1]) or not 0<=K[0,2]<w or not 0<=K[1,2]<h):
        raise ValueError('Calibrated zero-skew camera K required')
    if not isinstance(mount,np.ndarray) or mount.shape!=(4,4) or not np.isfinite(mount).all():
        raise ValueError('Actual body-from-optical calibration required')
    rotation=mount[:3,:3]
    if (not np.allclose(mount[3],[0,0,0,1]) or not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-5)
            or not np.isclose(np.linalg.det(rotation),1.,atol=1e-5)):
        raise ValueError('Rigid body-from-optical calibration required')
    return depth.reshape(h,w)


def _hsv(rgb):
    values=rgb.astype(np.float32)/255.;high=values.max(2);low=values.min(2);delta=high-low
    saturation=np.divide(delta,high,out=np.zeros_like(delta),where=high>0)
    hue=np.zeros_like(high);valid=delta>0
    # Mutually exclusive argmax avoids ambiguous channel ties.
    channel=values.argmax(2)
    for index in range(3):
        mask=valid&(channel==index)
        a,b=((1,2),(2,0),(0,1))[index]
        hue[mask]=((values[...,a][mask]-values[...,b][mask])/delta[mask]+2*index)/6.
    return hue%1.,saturation,high


def _components(mask):
    h,w=mask.shape;remaining=mask.copy()
    for y,x in zip(*np.nonzero(mask)):
        if not remaining[y,x]:continue
        remaining[y,x]=False;todo=[(int(y),int(x))];pixels=[]
        while todo:
            yy,xx=todo.pop();pixels.append((yy,xx))
            for ny,nx in ((yy-1,xx),(yy+1,xx),(yy,xx-1),(yy,xx+1)):
                if 0<=ny<h and 0<=nx<w and remaining[ny,nx]:
                    remaining[ny,nx]=False;todo.append((ny,nx))
        yield np.asarray(pixels,dtype=np.int64)


def visual_calibration_sha(camera_K,T_base_optical):
    return hashlib.sha256(np.asarray(camera_K,dtype='<f8').tobytes()+np.asarray(T_base_optical,dtype='<f8').tobytes()).hexdigest()


def propose_visual_candidates(rgb,depth_m,camera_K,T_base_optical,*,config=ProposalConfig()):
    """No source/scene registry, labels, mass, object positions or goal truth.

    Proposal refs are frame-local. Runtime identity tracking and across-reset
    rebinding must be separately established; refs may NOT be carried blindly.
    Returns visible-only proposals even when depth is unusable, with geometry
    explicitly null. No assumption that there must be three boxes or one/color.
    """
    if not isinstance(config,ProposalConfig):raise ValueError('Declared image-only configuration required')
    depth=_validate(rgb,depth_m,camera_K,T_base_optical)
    hue,saturation,value=_hsv(rgb)
    chromatic=(saturation>=config.minimum_saturation)&(value>=config.minimum_value)
    proposals=[]
    for family,low,high in HUE_FAMILIES:
        in_family=((hue>=low)&(hue<high)) if low<high else ((hue>=low)|(hue<high))
        for pixels in _components(chromatic&in_family):
            if len(pixels)<config.minimum_pixels:continue
            y,x=pixels[:,0],pixels[:,1];z=depth[y,x]
            valid=np.isfinite(z)&(z>=config.minimum_depth_m)&(z<=config.maximum_depth_m)
            good=int(valid.sum());fraction=good/len(pixels)
            geometry=good>=config.minimum_depth_pixels and fraction>=config.minimum_depth_fraction
            center=extent=None
            if geometry:
                zv=z[valid].astype(np.float64);u=x[valid]+.5;v=y[valid]+.5
                optical=np.stack(((u-camera_K[0,2])*zv/camera_K[0,0],(v-camera_K[1,2])*zv/camera_K[1,1],zv),axis=1)
                body=optical@T_base_optical[:3,:3].T+T_base_optical[:3,3]
                center=np.median(body,axis=0).tolist()
                extent=(np.quantile(body,.9,axis=0)-np.quantile(body,.1,axis=0)).tolist()
            proposals.append(dict(appearance_family=family,pixel_bbox_xyxy=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],
                pixel_count=len(pixels),pixel_centroid_uv=[float(np.median(x+.5)),float(np.median(y+.5))],
                median_observed_RGB=np.median(rgb[y,x],axis=0).tolist(),valid_depth_pixels=good,valid_depth_fraction=fraction,
                geometry_valid=bool(geometry),visible_surface_median_base_xyz_m=center,visible_surface_p10_p90_extent_base_m=extent,
                geometry_missing_reason=None if geometry else 'insufficient_visible_optical_depth'))
    proposals.sort(key=lambda p:(p['appearance_family'],p['pixel_bbox_xyxy'][0],p['pixel_bbox_xyxy'][1]))
    for index,p in enumerate(proposals):p['frame_local_ref']=f'visual-proposal-{index}'
    groups=[]
    for family,_,_ in HUE_FAMILIES:
        members=[p['frame_local_ref'] for p in proposals if p['appearance_family']==family]
        if members:groups.append(dict(appearance_family=family,member_frame_local_refs=members,
            multiple_fragments_or_instances_unresolved=len(members)>1,distinct_physical_object_count=None))
    return dict(schema='pixel-only-appearance-proposals-v1',RGB_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),
        calibration_sha256=visual_calibration_sha(camera_K,T_base_optical),
        candidates=proposals,appearance_groups=groups,
        ambiguous_same_family_components=any(g['multiple_fragments_or_instances_unresolved'] for g in groups),
        unique_color_per_object_not_assumed=True,
        executable_object_binding_certified=False,frame_local_refs_not_physical_or_persistent_ids=True,
        learned_detector=False,complete_object_inventory_certified=False,
        known_mass_or_task_success_inferred=False,raw_pixel_WM_input_unchanged=True)


def single_visible_hypothesis(result,frame_local_ref,*,current_RGB_sha256):
    """Fail closed on stale pixels, missing depth or ambiguous same-color pieces.

    Only retrieves a frame-local visual descriptor, NOT a controller target or
    physical ID. Runtime/episode tracking and executor binding remain separate.
    An occluding arm can split ONE box into several components. Do not silently
    pick the largest, merge same-color boxes, or call components three objects.
    """
    if result.get('schema')!='pixel-only-appearance-proposals-v1' or result['RGB_sha256']!=current_RGB_sha256:
        raise ValueError('Current actual RGB identity required; no stale-frame reference')
    matches=[p for p in result['candidates'] if p['frame_local_ref']==frame_local_ref]
    if len(matches)!=1:raise ValueError('Missing or nonunique frame-local reference')
    proposal=matches[0]
    siblings=[p for p in result['candidates'] if p['appearance_family']==proposal['appearance_family']]
    if len(siblings)!=1:raise ValueError('Same-family fragments or physical instances unresolved; no implicit largest-component choice')
    if not proposal['geometry_valid']:raise ValueError('No usable optical-depth geometry for action hypothesis')
    return deepcopy(proposal)
