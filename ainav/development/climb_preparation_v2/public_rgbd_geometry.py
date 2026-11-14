"""Public calibrated DEPTH RAYS only, never object center/reference/world pose.

Uses the exact existing proposal convention: pixel index + .5, optical Z and
T_base_optical. No private correspondence/catalogue, learned model or controller.
No assumed metric uncertainty: missing bound remains None. Region bounds are
sample AABBs, NOT object occupancy, tracking slack, or native admission proof.
"""
import ast
import hashlib
import math
from pathlib import Path
import struct


def need(ok,message):
    if not ok:raise ValueError(message)


def number(v):return type(v) in (int,float) and math.isfinite(v)


def validate_calibration(K,T,image_hw):
    need(type(image_hw) in (tuple,list) and len(image_hw)==2 and
         all(type(v) is int and v>0 for v in image_hw) and math.prod(image_hw)<=1_000_000,'Bounded actual image H/W')
    need(type(K) in (list,tuple) and len(K)==3 and all(type(r) in (list,tuple) and len(r)==3 for r in K),'Actual 3x3 K')
    need(type(T) in (list,tuple) and len(T)==4 and all(type(r) in (list,tuple) and len(r)==4 for r in T),'Actual 4x4 T_base_optical')
    need(all(number(v) for r in K for v in r) and all(number(v) for r in T for v in r),'Finite calibration, no Boolean numbers')
    h,w=image_hw
    need(K[0][0]>0 and K[1][1]>0 and K[0][1]==K[1][0]==0 and list(K[2])==[0,0,1]
         and 0<=K[0][2]<w and 0<=K[1][2]<h,'Original zero-skew pinhole calibration')
    need(list(T[3])==[0,0,0,1],'Rigid homogeneous calibration')
    R=[r[:3] for r in T[:3]]
    need(all(abs(sum(R[k][i]*R[k][j] for k in range(3))-(1 if i==j else 0))<=1e-5
         for i in range(3) for j in range(3)),'Proper orthonormal rotation, no scaled transform')
    det=(R[0][0]*(R[1][1]*R[2][2]-R[1][2]*R[2][1])
         -R[0][1]*(R[1][0]*R[2][2]-R[1][2]*R[2][0])
         +R[0][2]*(R[1][0]*R[2][1]-R[1][1]*R[2][0]))
    need(abs(det-1)<=1e-5,'Proper rotation, not reflected world/optical transform')


def backproject_pixel(pixel_xy,depth_z_m,K,T,image_hw):
    """Nominal observed ray intersection at the pixel CENTER, optical Z in m.

    This is not a centroid estimate. Authenticated depth/calibration/clock and
    any validated measurement error bounds must be established by the caller.
    """
    validate_calibration(K,T,image_hw)
    need(type(pixel_xy) in (list,tuple) and len(pixel_xy)==2 and all(type(v) is int for v in pixel_xy),'Integer pixel indices')
    x,y=pixel_xy;h,w=image_hw
    need(0<=x<w and 0<=y<h and number(depth_z_m) and .05<=depth_z_m<=15.,'Original valid optical depth/raster range')
    return _project(x,y,depth_z_m,K,T)


def _project(x,y,depth_z_m,K,T):
    optical=((x+.5-K[0][2])*depth_z_m/K[0][0],(y+.5-K[1][2])*depth_z_m/K[1][1],float(depth_z_m))
    body=tuple(sum(T[i][j]*optical[j] for j in range(3))+T[i][3] for i in range(3))
    need(all(math.isfinite(v) for v in body),'Finite projected surface ray')
    return body


def summarize_bbox_rays(depth_rows,bbox_xyxy,K,T):
    """Use the PUBLIC detector rectangle, NOT a private object mask/association.

    Valid depth pixels may include object/background/other surfaces. Bounding
    rectangle membership must NEVER be upgraded to object-point membership.
    No center fit, nearest-object fallback, hidden registration or target pose.
    """
    need(type(depth_rows) in (list,tuple) and depth_rows and type(depth_rows[0]) in (list,tuple),'Public 2D depth grid')
    h,w=len(depth_rows),len(depth_rows[0]);validate_calibration(K,T,(h,w))
    need(all(type(r) in (list,tuple) and len(r)==w for r in depth_rows),'Rectangular depth grid')
    need(type(bbox_xyxy) in (list,tuple) and len(bbox_xyxy)==4 and all(number(v) for v in bbox_xyxy),'Finite public detector bbox')
    x0,y0,x1,y1=bbox_xyxy
    need(0<=x0<x1<=w and 0<=y0<y1<=h,'Original bbox within current image')
    # Source convention uses pixel centers x+.5, y+.5; half-open XYXY region.
    xs=range(max(0,math.ceil(x0-.5)),min(w,math.ceil(x1-.5)))
    ys=range(max(0,math.ceil(y0-.5)),min(h,math.ceil(y1-.5)))
    valid=invalid=0;low=[math.inf]*3;high=[-math.inf]*3;example=None
    for y in ys:
        for x in xs:
            z=depth_rows[y][x]
            need(type(z) in (int,float),'Numeric optical depth grid, not objects/Boolean/pickle')
            if not math.isfinite(z) or not .05<=z<=15.:
                invalid+=1;continue
            p=_project(x,y,z,K,T);valid+=1
            low=[min(a,b) for a,b in zip(low,p)];high=[max(a,b) for a,b in zip(high,p)]
            if example is None:example=dict(pixel_index_xy=[x,y],optical_Z_m=z,nominal_point_parent_base_m=list(p))
    return dict(status='NOMINAL_UNASSOCIATED_BBOX_DEPTH_RAYS' if valid else 'UNKNOWN_NO_VALID_REGION_DEPTH',
        valid_region_depth_pixels=valid,invalid_region_depth_pixels=invalid,
        nominal_sample_AABB_parent_base_m=[low,high] if valid else None,example_first_valid_ray=example,
        frame='Provided T_base_optical camera-parent base frame, NOT world',depth_semantics='OPTICAL_Z_METERS_PIXEL_CENTER_PLUS_HALF',
        object_mask_or_point_association_verified=False,object_center_base_xyz_m=None,
        registered_reference_relative_pose=None,world_pose=None,validated_metric_error_bound_m=None,
        calibration_uncertainty_available=False,continuous_surface_or_complete_object_extent_proven=False,
        native_admission=False,trajectory_or_successor_cost_predicted=False)


def read_recorded_depth_npy(path,*,expected_sha256,expected_hw):
    """Bounded reader ONLY for archived public NPY1.0 little-endian f32 HxWx1.

    No NumPy/pickle/eval or general archive support. Does not rewrite original
    paths/bytes. A file hash authenticates against its caller-supplied source pin,
    not an independent license to use historical data as online input or fit.
    """
    need(type(expected_sha256) is str and len(expected_sha256)==64 and all(c in '0123456789abcdef' for c in expected_sha256),'Explicit public file SHA pin')
    need(type(expected_hw) in (list,tuple) and len(expected_hw)==2 and all(type(v) is int and v>0 for v in expected_hw)
         and math.prod(expected_hw)<=1_000_000,'Bounded expected actual image shape')
    p=Path(path);need(not p.is_symlink(),'No depth symlink substitution')
    with p.open('rb') as f:raw=f.read(4_001_035)
    need(len(raw)<=4_001_034 and hashlib.sha256(raw).hexdigest()==expected_sha256,'Exact bounded archived depth bytes')
    need(raw[:8]==b'\x93NUMPY\x01\x00' and len(raw)>=10,'Only original NPY1.0 depth, no pickle/NPZ or newer format')
    length=struct.unpack('<H',raw[8:10])[0]
    need(0<length<=1024 and 10+length<=len(raw) and (10+length)%16==0,'Bounded aligned NPY1.0 header')
    header=raw[10:10+length];need(header.endswith(b'\n'),'NPY header newline')
    tree=ast.parse(header.decode('ascii').strip(),mode='eval')
    need(isinstance(tree.body,ast.Dict),'Literal NPY metadata dictionary')
    keys=[ast.literal_eval(k) for k in tree.body.keys]
    need(len(keys)==len(set(keys)) and set(keys)=={'descr','fortran_order','shape'},'Exact unique NPY depth header fields')
    meta=ast.literal_eval(tree)
    need(meta['descr']=='<f4' and meta['fortran_order'] is False,'Only C-order float32 depth, never object/structured pickle')
    shape=meta['shape'];need(type(shape) is tuple and len(shape)==3 and all(type(v) is int for v in shape)
         and shape==(*expected_hw,1),'Exact HxWx1 archived depth shape')
    payload=raw[10+length:];need(len(payload)==4*math.prod(shape),'Exact depth payload, no trailing data')
    flat=[v[0] for v in struct.iter_unpack('<f',payload)];h,w=expected_hw
    return [flat[y*w:(y+1)*w] for y in range(h)]
